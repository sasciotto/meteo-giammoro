#!/usr/bin/env python3
"""Nowcasting v2 Meteo Giammoro: associazione multi-cella, tracking multi-frame e fulminazioni DPC LTG."""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import requests
from rasterio.io import MemoryFile
from rasterio.transform import xy
from rasterio.windows import from_bounds
from rasterio.warp import transform, transform_bounds

import nowcast_engine as legacy

COMPASS = ("N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW")
EARTH_KM = 6371.0088
WMS_URL = "https://radar-geowebcache.protezionecivile.it/service/wms"


def f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def haversine_km(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    q=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*EARTH_KM*math.asin(min(1,math.sqrt(q)))


def bearing_deg(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c); dl=math.radians(d-b)
    y=math.sin(dl)*math.cos(p2)
    x=math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y,x))+360)%360


def compass(deg):
    return COMPASS[int((deg+11.25)//22.5)%16] if deg is not None else None


def local_xy(lat,lon,rlat,rlon):
    return (
        math.radians(lon-rlon)*EARTH_KM*math.cos(math.radians((lat+rlat)/2)),
        math.radians(lat-rlat)*EARTH_KM,
    )


def bbox(lon,lat,r):
    dy=r/111.32
    dx=r/max(1,111.32*math.cos(math.radians(lat)))
    return lon-dx,lat-dy,lon+dx,lat+dy


def connected_components(mask: np.ndarray) -> list[list[tuple[int,int]]]:
    h,w=mask.shape
    seen=np.zeros(mask.shape,dtype=bool)
    comps=[]
    for r in range(h):
        for c in range(w):
            if not mask[r,c] or seen[r,c]:
                continue
            stack=[(r,c)]; seen[r,c]=True; comp=[]
            while stack:
                rr,cc=stack.pop(); comp.append((rr,cc))
                for dr in (-1,0,1):
                    for dc in (-1,0,1):
                        if dr==0 and dc==0:
                            continue
                        nr,nc=rr+dr,cc+dc
                        if 0<=nr<h and 0<=nc<w and mask[nr,nc] and not seen[nr,nc]:
                            seen[nr,nc]=True; stack.append((nr,nc))
            comps.append(comp)
    return comps


def extract_candidates(content: bytes, rlat: float, rlon: float, product: str, radius_km: float=45, max_candidates: int=10) -> dict[str,Any]:
    product=product.upper()
    base=1.0 if product=="SRI" else 30.0
    unit="mm/h" if product=="SRI" else "dBZ"
    with MemoryFile(content) as mem, mem.open() as ds:
        if not ds.crs:
            raise RuntimeError("raster senza CRS")
        l,b,r,t=bbox(rlon,rlat,radius_km)
        if str(ds.crs).upper() not in {"EPSG:4326","OGC:CRS84"}:
            l,b,r,t=transform_bounds("EPSG:4326",ds.crs,l,b,r,t,densify_pts=21)
        win=from_bounds(l,b,r,t,transform=ds.transform).round_offsets().round_lengths()
        arr=np.asarray(ds.read(1,window=win,boundless=True,masked=True).filled(np.nan),dtype=float)
        arr[(~np.isfinite(arr))|(arr<=-9000)]=np.nan
        if not np.isfinite(arr).any():
            return {"status":"no_data","product":product,"unit":unit,"candidates":[]}
        global_peak=float(np.nanmax(arr))
        if global_peak<base:
            return {"status":"no_cell","product":product,"unit":unit,"peak_value":round(global_peak,2),"candidates":[]}
        if product=="SRI":
            threshold=max(2.0,min(global_peak*0.45,12.0))
        else:
            threshold=max(30.0,min(global_peak*0.66,40.0))
        mask=np.isfinite(arr)&(arr>=threshold)
        comps=connected_components(mask)
        candidates=[]
        for comp in comps:
            if len(comp)<2:
                continue
            rows=np.array([x[0] for x in comp],dtype=int)
            cols=np.array([x[1] for x in comp],dtype=int)
            vals=arr[rows,cols]
            peak=float(np.nanmax(vals)); mean=float(np.nanmean(vals))
            gr=rows+int(win.row_off); gc=cols+int(win.col_off)
            xs,ys=xy(ds.transform,gr.tolist(),gc.tolist(),offset="center")
            if str(ds.crs).upper() not in {"EPSG:4326","OGC:CRS84"}:
                lons,lats=transform(ds.crs,"EPSG:4326",list(xs),list(ys))
            else:
                lons,lats=list(xs),list(ys)
            weights=np.maximum(.01,vals-threshold+.01)
            lat=float(np.average(np.asarray(lats),weights=weights)); lon=float(np.average(np.asarray(lons),weights=weights))
            dist=haversine_km(rlat,rlon,lat,lon)
            if dist>radius_km*1.08:
                continue
            br=bearing_deg(rlat,rlon,lat,lon)
            relevance=(peak/max(base,1))*math.sqrt(len(comp))/(1+dist/18)
            candidates.append({
                "lat":round(lat,5),"lon":round(lon,5),"distance_km":round(dist,1),
                "bearing_deg":round(br,1),"bearing":compass(br),"pixels":int(len(comp)),
                "peak_value":round(peak,2),"mean_value":round(mean,2),"relevance":round(relevance,3),
            })
        candidates.sort(key=lambda x:x["relevance"],reverse=True)
        candidates=candidates[:max_candidates]
        return {
            "status":"detected" if candidates else "no_cell","product":product,"unit":unit,
            "threshold":round(threshold,2),"peak_value":round(global_peak,2),
            "candidate_count":len(candidates),"candidates":candidates,
        }


def parse_iso(s):
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def predicted_position(prev: dict, hours: float) -> tuple[float,float] | None:
    cell=prev.get("cell",{})
    lat,lon=f(cell.get("lat")),f(cell.get("lon"))
    m=prev.get("motion",{})
    speed=f(m.get("speed_kmh")); direction=f(m.get("direction_deg"))
    if lat is None or lon is None:
        return None
    if m.get("status")!="tracked" or speed is None or direction is None or hours<=0:
        return lat,lon
    dist=speed*hours; ang=math.radians(direction)
    north=math.cos(ang)*dist; east=math.sin(ang)*dist
    plat=lat+math.degrees(north/EARTH_KM)
    plon=lon+math.degrees(east/(EARTH_KM*math.cos(math.radians(lat))))
    return plat,plon


def choose_candidate(candidates: list[dict], previous: dict|None, timestamp: str) -> tuple[dict|None,dict]:
    if not candidates:
        return None,{"status":"no_candidate"}
    if not previous or previous.get("status")!="detected":
        return candidates[0],{"status":"new_track","reason":"nessuna cella precedente"}
    ct=parse_iso(timestamp); pt=parse_iso(previous.get("timestamp"))
    if not ct or not pt:
        return candidates[0],{"status":"new_track","reason":"timestamp insufficiente"}
    dt=(ct-pt).total_seconds()/3600
    if dt<=0.03 or dt>1.75:
        return candidates[0],{"status":"new_track","reason":"intervallo non valido","interval_minutes":round(dt*60,1)}
    pred=predicted_position(previous,dt)
    if not pred:
        return candidates[0],{"status":"new_track","reason":"posizione precedente assente"}
    prev_peak=f(previous.get("peak_value")) or f(previous.get("cell",{}).get("peak_value")) or 1.0
    prev_pix=f(previous.get("cell",{}).get("pixels")) or 1.0
    scored=[]
    for cand in candidates:
        spatial=haversine_km(pred[0],pred[1],cand["lat"],cand["lon"])
        direct=haversine_km(previous["cell"]["lat"],previous["cell"]["lon"],cand["lat"],cand["lon"])
        implied_speed=direct/dt
        if implied_speed>145 or spatial>max(10,145*dt+5):
            continue
        peak=max(.1,f(cand.get("peak_value")) or .1); pix=max(1,f(cand.get("pixels")) or 1)
        intensity_pen=abs(math.log(peak/max(.1,prev_peak)))*4.0
        area_pen=abs(math.log(pix/max(1,prev_pix)))*1.5
        score=spatial+intensity_pen+area_pen
        scored.append((score,spatial,implied_speed,cand))
    if not scored:
        return candidates[0],{"status":"new_track","reason":"nessuna associazione fisicamente plausibile"}
    scored.sort(key=lambda x:x[0])
    score,spatial,speed,cand=scored[0]
    if score>22:
        return candidates[0],{"status":"new_track","reason":"associazione debole","best_score":round(score,2)}
    return cand,{"status":"matched","score":round(score,2),"predicted_error_km":round(spatial,1),"implied_speed_kmh":round(speed,1),"candidates_evaluated":len(scored)}


def track_id(product: str, timestamp: str, cell: dict) -> str:
    safe=timestamp.replace("-","").replace(":","").replace("+","").replace("T","")[:12]
    return f"{product}-{safe}-{cell.get('bearing','X')}{int(round(cell.get('distance_km',0)))}"


def regression_motion(points: list[dict], rlat: float, rlon: float) -> dict:
    if len(points)<2:
        return {"status":"insufficient_history"}
    times=[parse_iso(p.get("timestamp")) for p in points]
    if any(t is None for t in times):
        return {"status":"missing_timestamp"}
    t0=times[0]
    ts=np.array([(t-t0).total_seconds()/3600 for t in times],dtype=float)
    if ts[-1]<=.03:
        return {"status":"invalid_interval"}
    xs=[]; ys=[]
    for p in points:
        x,y=local_xy(float(p["lat"]),float(p["lon"]),rlat,rlon); xs.append(x); ys.append(y)
    xs=np.array(xs); ys=np.array(ys)
    if len(points)>=3:
        px=np.polyfit(ts,xs,1); py=np.polyfit(ts,ys,1)
        vx=float(px[0]); vy=float(py[0]); method="multi_frame_linear_fit"
    else:
        px=py=None
        vx=float((xs[-1]-xs[0])/(ts[-1]-ts[0])); vy=float((ys[-1]-ys[0])/(ts[-1]-ts[0])); method="two_frame"
    speed=math.hypot(vx,vy)
    if speed>145:
        return {"status":"cell_mismatch","speed_kmh":round(speed,1),"method":method}
    direction=(math.degrees(math.atan2(vx,vy))+360)%360
    x1,y1=xs[-1],ys[-1]; current_dist=math.hypot(x1,y1); v2=vx*vx+vy*vy
    closest=current_dist; closest_min=None; eta=None
    radial=(-(x1*vx+y1*vy)/current_dist) if current_dist>0 else speed
    if v2>1:
        tc=-(x1*vx+y1*vy)/v2
        if 0<tc<=3:
            closest=math.hypot(x1+vx*tc,y1+vy*tc); closest_min=tc*60
        a=v2; b=2*(x1*vx+y1*vy); c=x1*x1+y1*y1-25; disc=b*b-4*a*c
        if c<=0:
            eta=0
        elif disc>=0 and b<0:
            roots=[(-b-math.sqrt(disc))/(2*a),(-b+math.sqrt(disc))/(2*a)]
            future=[z for z in roots if 0<z<=3]
            if future:
                eta=min(future)*60
    residual=None
    if len(points)>=3:
        fitx=np.polyval(px,ts); fity=np.polyval(py,ts)
        residual=float(np.sqrt(np.mean((xs-fitx)**2+(ys-fity)**2)))
    return {"status":"tracked","method":method,"frames":len(points),"interval_minutes":round(ts[-1]*60,1),"speed_kmh":round(speed,1),"direction_deg":round(direction,1),"direction":compass(direction),"approach_rate_kmh":round(radial,1),"approaching":bool(radial>3 and closest<=max(8,current_dist)),"closest_approach_km":round(closest,1),"closest_approach_minutes":None if closest_min is None else int(round(closest_min)),"eta_minutes":None if eta is None else int(round(eta)),"fit_residual_km":None if residual is None else round(residual,1)}


def build_tracking(detection: dict, previous: dict|None, timestamp: str, age_minutes: int, rlat: float, rlon: float) -> dict:
    if detection.get("status")!="detected":
        return {**detection,"timestamp":timestamp,"age_minutes":age_minutes,"motion":{"status":"unavailable"},"association":{"status":"no_candidate"}}
    selected,assoc=choose_candidate(detection.get("candidates",[]),previous,timestamp)
    if not selected:
        return {**detection,"timestamp":timestamp,"age_minutes":age_minutes,"motion":{"status":"unavailable"},"association":assoc}
    matched=assoc.get("status")=="matched"
    tid=previous.get("track_id") if matched and previous else None
    if not tid:
        tid=track_id(detection["product"],timestamp,selected)
    old_history=[]
    if matched and previous:
        old_history=[p for p in previous.get("track_history",[]) if p.get("track_id",tid)==tid]
        if not old_history and previous.get("cell"):
            pc=previous["cell"]
            old_history=[{"track_id":tid,"timestamp":previous.get("timestamp"),"lat":pc.get("lat"),"lon":pc.get("lon"),"peak_value":previous.get("peak_value"),"pixels":pc.get("pixels")}]
    current_point={"track_id":tid,"timestamp":timestamp,"lat":selected["lat"],"lon":selected["lon"],"peak_value":selected.get("peak_value"),"pixels":selected.get("pixels")}
    history=(old_history+[current_point])[-4:]
    motion=regression_motion(history,rlat,rlon) if matched else {"status":"new_cell"}
    cell=dict(selected); cell.pop("relevance",None)
    return {"status":"detected","product":detection["product"],"unit":detection["unit"],"threshold":detection.get("threshold"),"peak_value":selected.get("peak_value"),"scene_peak_value":detection.get("peak_value"),"candidate_count":detection.get("candidate_count",0),"candidates":detection.get("candidates",[]),"cell":cell,"timestamp":timestamp,"age_minutes":age_minutes,"track_id":tid,"association":assoc,"track_history":history,"motion":motion}


def _raster_values(content: bytes, rlat: float, rlon: float, radii=(5,10,20,30)) -> dict:
    with MemoryFile(content) as mem, mem.open() as ds:
        if not ds.crs:
            raise RuntimeError("LTG raster senza CRS")
        band=np.asarray(ds.read(1,masked=True).filled(np.nan),dtype=float)
        band[(~np.isfinite(band))|(band<0)]=np.nan
        rows,cols=np.where(np.isfinite(band)&(band>0))
        if len(rows)==0:
            return {"positive_cells":0,"nearest_km":None,"radii":{str(r):{"frequency_sum":0.0,"positive_cells":0} for r in radii}}
        xs,ys=xy(ds.transform,rows.tolist(),cols.tolist(),offset="center")
        if str(ds.crs).upper() not in {"EPSG:4326","OGC:CRS84"}:
            lons,lats=transform(ds.crs,"EPSG:4326",list(xs),list(ys))
        else:
            lons,lats=list(xs),list(ys)
        dists=np.array([haversine_km(rlat,rlon,la,lo) for la,lo in zip(lats,lons)])
        vals=band[rows,cols]
        out={"positive_cells":int(len(rows)),"nearest_km":round(float(np.min(dists)),1),"radii":{}}
        for rad in radii:
            sel=dists<=rad
            out["radii"][str(rad)]={"frequency_sum":round(float(np.nansum(vals[sel])),1),"positive_cells":int(np.count_nonzero(sel)),"max_cell":round(float(np.nanmax(vals[sel])),1) if np.any(sel) else 0.0}
        return out


def _wms_lightning(rlat: float, rlon: float, radius_km: float=40) -> dict:
    l,b,r,t=bbox(rlon,rlat,radius_km)
    common={"service":"WMS","request":"GetMap","styles":"","format":"image/png","transparent":"true","version":"1.1.1","tiled":"true","width":"512","height":"512","srs":"EPSG:4326","bbox":f"{l},{b},{r},{t}"}
    errors=[]
    for layer in ("radar:ltg","radar:LTG","ltg"):
        try:
            resp=requests.get(WMS_URL,params={**common,"layers":layer},timeout=20)
            resp.raise_for_status()
            if b"ServiceException" in resp.content[:1000] or not resp.content.startswith(b"\x89PNG"):
                errors.append(f"{layer}: risposta non PNG"); continue
            with MemoryFile(resp.content) as mem, mem.open() as ds:
                arr=ds.read()
                active=arr[3]>0 if arr.shape[0]>=4 else np.any(arr[:3]<245,axis=0)
                rows,cols=np.where(active)
                if len(rows)==0:
                    return {"status":"ok_wms","source":"Radar-DPC LTG / LAMPINET","quality":"rendered_layer","activity":False,"nearest_km":None,"rendered_pixels":0,"layer":layer}
                lons=l+(cols+0.5)/ds.width*(r-l); lats=t-(rows+0.5)/ds.height*(t-b)
                dists=np.array([haversine_km(rlat,rlon,float(la),float(lo)) for la,lo in zip(lats,lons)])
                return {"status":"ok_wms","source":"Radar-DPC LTG / LAMPINET","quality":"rendered_layer","activity":True,"nearest_km":round(float(np.min(dists)),1),"rendered_pixels":int(len(rows)),"layer":layer}
        except Exception as e:
            errors.append(f"{layer}: {e}")
    return {"status":"unavailable","source":"Radar-DPC LTG / LAMPINET","errors":errors}


def fetch_lightning(collector, rlat: float, rlon: float) -> dict:
    errors=[]
    try:
        latest=collector.dpc_last_product("LTG")
        ts=int(latest["time"]); raw=collector.dpc_download_product("LTG",ts)
        stamp=datetime.fromtimestamp(ts/1000,tz=ZoneInfo("UTC")).astimezone(collector.TZ)
        sampled=_raster_values(raw,rlat,rlon)
        return {"status":"ok","source":"Radar-DPC LTG / LAMPINET (Aeronautica Militare - CNMCA)","quality":"raw_product","timestamp":stamp.isoformat(timespec="minutes"),"age_minutes":max(0,int((collector.now_local()-stamp).total_seconds()/60)),**sampled}
    except Exception as e:
        errors.append(f"REST LTG: {e}")
    fallback=_wms_lightning(rlat,rlon)
    if fallback.get("status")!="unavailable":
        fallback["retrieved_at"]=collector.now_local().isoformat(timespec="minutes"); fallback["errors"]=errors; return fallback
    fallback["errors"]=errors+fallback.get("errors",[])
    return fallback


def lightning_summary(l: dict) -> str:
    if l.get("status")=="ok":
        r5=l.get("radii",{}).get("5",{}).get("frequency_sum",0); r10=l.get("radii",{}).get("10",{}).get("frequency_sum",0); r20=l.get("radii",{}).get("20",{}).get("frequency_sum",0); nearest=l.get("nearest_km")
        if r20>0:
            return f"LTG/LAMPINET: attività elettrica rilevata; somma frequenze 5/10/20 km = {r5:g}/{r10:g}/{r20:g}; punto attivo più vicino ~{nearest} km."
        return "LTG/LAMPINET: nessuna attività elettrica positiva entro 20 km nel campione disponibile."
    if l.get("status")=="ok_wms":
        if l.get("activity"):
            return f"LTG/LAMPINET: attività visibile nel layer ufficiale, punto renderizzato più vicino ~{l.get('nearest_km')} km; il fallback grafico non viene trasformato in numero di fulmini."
        return "LTG/LAMPINET: nessuna attività visibile nel layer ufficiale nell'area analizzata."
    return "LTG/LAMPINET non disponibile in questo ciclo; nessun dato di fulminazione viene inventato."


def enhanced_confidence(data: dict, tr: dict, lightning: dict) -> dict:
    c=legacy.confidence(data,tr); pts=0
    if lightning.get("status")=="ok":
        age=f(lightning.get("age_minutes")); pts=10 if age is not None and age<=20 else 6
    elif lightning.get("status")=="ok_wms":
        pts=4
    c["components"]["lightning_support"]=pts; c["score"]=min(100,c["score"]+pts)
    c["label"]="Bassa" if c["score"]<40 else "Media" if c["score"]<65 else "Alta" if c["score"]<85 else "Molto alta"
    c["note"]="Confidenza nowcasting da radar, associazione multi-cella, tracking multi-frame, LTG/LAMPINET, stazioni affidabili e modelli."
    return c


def significant_lightning_change(data: dict, previous: dict, lightning: dict) -> None:
    if lightning.get("status")!="ok" or not previous:
        return
    cur10=f(lightning.get("radii",{}).get("10",{}).get("frequency_sum")) or 0
    prev=previous.get("lightning",{}); prev10=f(prev.get("radii",{}).get("10",{}).get("frequency_sum")) or 0
    if cur10<=0 or cur10<=prev10 or data.get("latest_change")!=previous.get("latest_change"):
        return
    stamp=str(data.get("meta",{}).get("last_check","—")).rsplit(" ",1)[0]; nearest=lightning.get("nearest_km")
    ch={"time":stamp,"title":"Aumento dell'attività elettrica vicino a Giammoro","text":lightning_summary(lightning),"window":"prossime 0–3 ore","confidence":data.get("analysis_confidence",{}).get("label","—").lower(),"evidence":f"Radar-DPC LTG/LAMPINET: frequenza aggregata entro 10 km {prev10:g} → {cur10:g}; punto attivo più vicino ~{nearest} km."}
    data["latest_change"]=ch; data["history"]=([{"time":stamp,"text":ch["title"]}]+data.get("history",[]))[:50]


def run(data_path: Path, previous_path: Path|None=None, history_path: Path|None=None):
    import collector
    data=json.loads(data_path.read_text(encoding="utf-8")); prev=json.loads(previous_path.read_text(encoding="utf-8")) if previous_path and previous_path.exists() else {}
    rlat,rlon=float(collector.REF["latitude"]),float(collector.REF["longitude"])
    tr={"status":"unavailable","motion":{"status":"unavailable"}}; errors=[]
    for product in ("SRI","VMI"):
        try:
            latest=collector.dpc_last_product(product); ts=int(latest["time"]); raw=collector.dpc_download_product(product,ts)
            detection=extract_candidates(raw,rlat,rlon,product)
            stamp=datetime.fromtimestamp(ts/1000,tz=ZoneInfo("UTC")).astimezone(collector.TZ); timestamp=stamp.isoformat(timespec="minutes"); age=max(0,int((collector.now_local()-stamp).total_seconds()/60))
            candidate_tracking=build_tracking(detection,prev.get("nowcast_tracking") if prev else None,timestamp,age,rlat,rlon)
            if candidate_tracking.get("status")=="detected":
                tr=candidate_tracking; break
            if tr.get("status")=="unavailable":
                tr=candidate_tracking
        except Exception as e:
            errors.append(f"{product}: {e}")
    if errors:
        tr["errors"]=errors
    lightning=fetch_lightning(collector,rlat,rlon)
    data=legacy.enhance(data,prev,tr); data["lightning"]=lightning; data["analysis_confidence"]=enhanced_confidence(data,tr,lightning)
    data.setdefault("nowcast_evidence",{})["lightning"]=lightning_summary(lightning)
    note=str(data.get("nowcast",{}).get("note","")); stale="Fulminazioni non ancora acquisite automaticamente."
    if stale in note:
        note=note.replace(stale,lightning_summary(lightning))
    elif lightning_summary(lightning) not in note:
        note=(note+" "+lightning_summary(lightning)).strip()
    data.setdefault("nowcast",{})["note"]=note
    significant_lightning_change(data,prev,lightning)
    data_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if history_path:
        history_path.write_text(json.dumps(data.get("history",[]),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return data


def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="data.json"); p.add_argument("--previous"); p.add_argument("--history",default="history.json"); a=p.parse_args()
    run(Path(a.data),Path(a.previous) if a.previous else None,Path(a.history) if a.history else None)
    print("Nowcast v2 multi-cella + LTG aggiornato"); return 0


if __name__=="__main__":
    raise SystemExit(main())
