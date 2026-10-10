from datetime import datetime, timedelta, timezone
from nowcast_engine import confidence, haversine_km, track_motion, summary

def cell(lat, lon, timestamp):
    return {"status":"detected","product":"SRI","timestamp":timestamp.isoformat(timespec="minutes"),"age_minutes":5,"peak_value":12.0,"unit":"mm/h","cell":{"lat":lat,"lon":lon,"distance_km":0,"bearing":"W"}}

def test_haversine_reasonable():
    assert 10.9 < haversine_km(38.2,15.2,38.2,15.325) < 11.1

def test_motion_approaching_and_eta():
    rlat,rlon=38.2,15.318; t0=datetime(2026,10,10,12,0,tzinfo=timezone.utc)
    out=track_motion(cell(rlat,15.20,t0+timedelta(minutes=30)),cell(rlat,15.09,t0),rlat,rlon)
    m=out["motion"]
    assert m["status"]=="tracked"
    assert m["approaching"] is True
    assert m["speed_kmh"]>15
    assert m["eta_minutes"] is not None and m["eta_minutes"]<30

def test_motion_away_has_no_eta():
    rlat,rlon=38.2,15.318; t0=datetime(2026,10,10,12,0,tzinfo=timezone.utc)
    out=track_motion(cell(38.06,15.18,t0+timedelta(minutes=30)),cell(38.10,15.20,t0),rlat,rlon)
    assert out["motion"]["status"]=="tracked"
    assert out["motion"]["approaching"] is False
    assert out["motion"]["eta_minutes"] is None

def test_confidence_high_with_tracking_and_sources():
    data={"dpc_observations":{"products":{"SRI":{"ok":True},"VMI":{"ok":True}}},"stations":[{"status":"online","source_quality":"official"},{"status":"online","source_quality":"reliable"}],"model_details":[{"ok":True}]*4}
    c=confidence(data,{"status":"detected","age_minutes":5,"motion":{"status":"tracked"}})
    assert c["score"]>=80
    assert c["label"] in {"Alta","Molto alta"}

def test_summary_requires_second_frame():
    text=summary({"status":"detected","peak_value":8,"unit":"mm/h","cell":{"distance_km":18,"bearing":"WSW"},"motion":{"status":"insufficient_history"}})
    assert "Movimento non ancora stimabile" in text
