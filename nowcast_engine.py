#!/usr/bin/env python3
"""Post-processore nowcasting per Meteo Giammoro: cella radar, moto, ETA e confidenza."""
from __future__ import annotations
import argparse, json, math
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
import numpy as np
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds
from rasterio.warp import transform, transform_bounds
from rasterio.transform import xy

EARTH_KM=6371.0088
COMPASS=("N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW")

def f(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def haversine_km(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c); dp=math.radians(c-a); dl=math.radians(d-b)
    q=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*EARTH_KM*math.asin(min(1,math.sqrt(q)))

def bearing_deg(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c); dl=math.radians(d-b)
    y=math.sin(dl)*math.cos(p2); x=math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y,x))+360)%360

def compass(deg): return COMPASS[int((deg+11.25)//22.5)%16] if deg is not None else None

def local_xy(lat,lon,rlat,rlon):
    return (math.radians(lon-rlon)*EARTH_KM*math.cos(math.radians((lat+rlat)/2)), math.radians(lat-rlat)*EARTH_KM)

def bbox(lon,lat,r):
    dy=r/111.32; dx=r/max(1,111.32*math.cos(math.radians(lat))); return lon-dx,lat-dy,lon+dx,lat+dy

def detect_cell(content:bytes, rlat:float, rlon:float, product:str, radius_km:float=40)->dict[str,Any]:
    product=product.upper(); base=1.0 if product=="SRI" else 30.0; unit="mm/h" if product=="SRI" else "dBZ"
    with MemoryFile(content) as mem, mem.open() as ds:
        if not ds.crs: raise RuntimeError("raster senza CRS")
        l,b,r,t=bbox(rlon,rlat,radius_km)
        if str(ds.crs).upper() not in {"EPSG:4326","OGC:CRS84"}: l,b,r,t=transform_bounds("EPSG:4326",ds.crs,l,b,r,t,densify_pts=21)
        win=from_bounds(l,b,r,t,transform=ds.transform).round_offsets().round_lengths()
        arr=np.asarray(ds.read(1,window=win,boundless=True,masked=True).filled(np.nan),dtype=float)
        arr[(~np.isfinite(arr))|(arr<=-9000)]=np.nan
        if not np.isfinite(arr).any(): return {"status":"no_data","product":product}
        peak=float(np.nanmax(arr))
        if peak<base: return {"status":"no_cell","product":product,"peak_value":round(peak,2),"unit":unit}
        threshold=max(base,peak*(.55 if product=="SRI" else .72)); rows,cols=np.where(arr>=threshold)
        vals=arr[rows,cols]; gr=rows+int(win.row_off); gc=cols+int(win.col_off); xs,ys=xy(ds.transform,gr.tolist(),gc.tolist(),offset="center")
        if str(ds.crs).upper() not in {"EPSG:4326","OGC:CRS84"}: lons,lats=transform(ds.crs,"EPSG:4326",list(xs),list(ys))
        else: lons,lats=list(xs),list(ys)
        weights=np.maximum(.01,vals-threshold+.01); lat=float(np.average(np.asarray(lats),weights=weights)); lon=float(np.average(np.asarray(lons),weights=weights))
        dist=haversine_km(rlat,rlon,lat,lon); br=bearing_deg(rlat,rlon,lat,lon)
        return {"status":"detected","product":product,"unit":unit,"threshold":round(threshold,2),"peak_value":round(peak,2),"cell":{"lat":round(lat,5),"lon":round(lon,5),"distance_km":round(dist,1),"bearing_deg":round(br,1),"bearing":compass(br),"pixels":int(len(rows))}}

def parse_iso(s):
    try:return datetime.fromisoformat(s) if s else None
    except ValueError:return None

def track_motion(cur:dict,prev:dict|None,rlat:float,rlon:float)->dict:
    out=dict(cur); out["motion"]={"status":"insufficient_history"}
    if cur.get("status")!="detected" or not prev or prev.get("status")!="detected": return out
    if cur.get("product")!=prev.get("product"): out["motion"]={"status":"product_changed"}; return out
    ct,pt=parse_iso(cur.get("timestamp")),parse_iso(prev.get("timestamp"))
    if not ct or not pt: out["motion"]={"status":"missing_timestamp"}; return out
    dt=(ct-pt).total_seconds()/3600
    if dt<=.03 or dt>1.75: out["motion"]={"status":"invalid_interval","interval_minutes":round(dt*60,1)}; return out
    cc,pc=cur.get("cell",{}),prev.get("cell",{}); clat,clon,plat,plon=map(f,[cc.get("lat"),cc.get("lon"),pc.get("lat"),pc.get("lon")])
    if any(v is None for v in [clat,clon,plat,plon]): out["motion"]={"status":"missing_position"}; return out
    disp=haversine_km(plat,plon,clat,clon); speed=disp/dt
    if disp>55 or speed>160: out["motion"]={"status":"cell_mismatch","displacement_km":round(disp,1),"speed_kmh":round(speed,1)}; return out
    move=bearing_deg(plat,plon,clat,clon); pd=haversine_km(rlat,rlon,plat,plon); cd=haversine_km(rlat,rlon,clat,clon); approach=(pd-cd)/dt
    x0,y0=local_xy(plat,plon,rlat,rlon); x1,y1=local_xy(clat,clon,rlat,rlon); vx,vy=(x1-x0)/dt,(y1-y0)/dt; v2=vx*vx+vy*vy
    eta=None; closest=cd; closest_min=None
    if v2>1:
        tc=-(x1*vx+y1*vy)/v2
        if 0<tc<=3: closest=math.hypot(x1+vx*tc,y1+vy*tc); closest_min=tc*60
        a=v2; b=2*(x1*vx+y1*vy); c=x1*x1+y1*y1-25; disc=b*b-4*a*c
        if c<=0: eta=0
        elif disc>=0 and b<0:
            roots=[(-b-math.sqrt(disc))/(2*a),(-b+math.sqrt(disc))/(2*a)]; fut=[z for z in roots if 0<z<=3]
            if fut: eta=min(fut)*60
    out["motion"]={"status":"tracked","interval_minutes":round(dt*60,1),"displacement_km":round(disp,1),"speed_kmh":round(speed,1),"direction_deg":round(move,1),"direction":compass(move),"approach_rate_kmh":round(approach,1),"approaching":bool(approach>3 and closest<=max(8,cd)),"closest_approach_km":round(closest,1),"closest_approach_minutes":None if closest_min is None else int(round(closest_min)),"eta_minutes":None if eta is None else int(round(eta))}
    return out

def confidence(data:dict,tr:dict)->dict:
    age=f(tr.get("age_minutes")); rp=0 if age is None else 30 if age<=10 else 25 if age<=20 else 18 if age<=35 else 10 if age<=60 else 3
    parts={"radar_freshness":rp,"cell_detection":15 if tr.get("status")=="detected" else 0,"motion_tracking":20 if tr.get("motion",{}).get("status")=="tracked" else 0}
    p=data.get("dpc_observations",{}).get("products",{}); parts["radar_crosscheck"]=10 if p.get("SRI",{}).get("ok") and p.get("VMI",{}).get("ok") else 0
    sts=[s for s in data.get("stations",[]) if s.get("status")=="online" and s.get("source_quality") in {"official","reliable"}]; parts["station_support"]=min(15,len(sts)*3)
    parts["model_availability"]=min(10,sum(1 for x in data.get("model_details",[]) if x.get("ok"))*2)
    score=min(90,sum(parts.values())); label="Bassa" if score<40 else "Media" if score<65 else "Alta" if score<85 else "Molto alta"
    return {"score":int(score),"label":label,"components":parts,"note":"Confidenza nowcasting da freschezza radar, tracking, SRI/VMI, stazioni affidabili e modelli. Fulminazioni non ancora integrate."}

def summary(tr:dict)->str:
    if tr.get("status")!="detected": return "Nessun nucleo radar sufficientemente definito per il tracking nel raggio analizzato."
    c=tr.get("cell",{}); s=f"Nucleo radar a circa {c.get('distance_km','—')} km {c.get('bearing','')} di Giammoro, picco {tr.get('peak_value','—')} {tr.get('unit','')}"
    m=tr.get("motion",{})
    if m.get("status")!="tracked": return s+". Movimento non ancora stimabile con confidenza: serve un secondo frame coerente."
    s+=f"; movimento {m.get('direction','—')} a ~{m.get('speed_kmh','—')} km/h"
    if m.get("eta_minutes") is not None:s+=f". Possibile ingresso entro 5 km in ~{m['eta_minutes']} min"
    elif m.get("approaching"):s+=f". In avvicinamento; minima distanza proiettata ~{m.get('closest_approach_km','—')} km"
    else:s+=". Traiettoria non diretta verso Giammoro"
    return s+"."

def enhance(data:dict,previous:dict,tr:dict)->dict:
    data["nowcast_tracking"]=tr; data["analysis_confidence"]=confidence(data,tr); txt=summary(tr); old=str(data.get("nowcast",{}).get("note","")).strip(); data.setdefault("nowcast",{})["note"]=(old+" "+txt).strip()
    pm=(previous.get("nowcast_tracking",{}) or {}).get("motion",{}); m=tr.get("motion",{}); collector_changed=data.get("latest_change")!=previous.get("latest_change") if previous else True
    if not collector_changed and m.get("status")=="tracked" and m.get("approaching") and not pm.get("approaching"):
        stamp=str(data.get("meta",{}).get("last_check","—")).rsplit(" ",1)[0]; eta=m.get("eta_minutes"); ch={"time":stamp,"title":"Nucleo radar in avvicinamento verso Giammoro","text":txt,"window":f"circa {eta} minuti" if eta is not None else "prossime 0–3 ore","confidence":data["analysis_confidence"]["label"].lower(),"evidence":f"Tracking {tr.get('product')} su due cicli; distanza {tr.get('cell',{}).get('distance_km','—')} km; direzione {m.get('direction','—')}; velocità {m.get('speed_kmh','—')} km/h."}
        data["latest_change"]=ch; data["history"]=([{"time":ch["time"],"text":ch["title"]}]+data.get("history",[]))[:50]
    return data

def run(data_path:Path,previous_path:Path|None=None,history_path:Path|None=None):
    import collector
    data=json.loads(data_path.read_text(encoding="utf-8")); prev=json.loads(previous_path.read_text(encoding="utf-8")) if previous_path and previous_path.exists() else {}; rlat,rlon=float(collector.REF["latitude"]),float(collector.REF["longitude"]); tr={"status":"unavailable","motion":{"status":"unavailable"}}; errs=[]
    for product in ("SRI","VMI"):
        try:
            latest=collector.dpc_last_product(product); ts=int(latest["time"]); raw=collector.dpc_download_product(product,ts); det=detect_cell(raw,rlat,rlon,product); stamp=datetime.fromtimestamp(ts/1000,tz=ZoneInfo("UTC")).astimezone(collector.TZ); det["timestamp"]=stamp.isoformat(timespec="minutes"); det["age_minutes"]=max(0,int((collector.now_local()-stamp).total_seconds()/60))
            if det.get("status")=="detected": tr=det; break
            if tr.get("status")=="unavailable":tr=det
        except Exception as e:errs.append(f"{product}: {e}")
    if errs:tr["errors"]=errs
    tr=track_motion(tr,prev.get("nowcast_tracking") if prev else None,rlat,rlon); data=enhance(data,prev,tr); data_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if history_path:history_path.write_text(json.dumps(data.get("history",[]),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return data

def main():
    p=argparse.ArgumentParser();p.add_argument("--data",default="data.json");p.add_argument("--previous");p.add_argument("--history",default="history.json");a=p.parse_args();run(Path(a.data),Path(a.previous) if a.previous else None,Path(a.history) if a.history else None);print("Nowcast tracking aggiornato");return 0
if __name__=="__main__":raise SystemExit(main())
