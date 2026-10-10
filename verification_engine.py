#!/usr/bin/env python3
"""Verifica ex-post per Meteo Giammoro.

Il modulo osserva il sistema senza modificarne le decisioni operative. Ogni ciclo:
1. valuta gli snapshot precedenti a ~30/60/120 minuti;
2. misura esito locale, ETA e traiettoria quando osservabili;
3. aggiorna statistiche cumulative e archivio eventi;
4. aggiunge a data.json una sintesi leggibile dalla dashboard.

Le soglie sono euristiche del progetto, non soglie ufficiali di allertamento.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HORIZONS = (30, 60, 120)
MAX_RESULTS = 300
MAX_EVENTS = 150


def num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value) if value else None
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) if dt else None
    except (TypeError, ValueError):
        return None


def haversine_km(a: float, b: float, c: float, d: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(a), math.radians(c)
    dp = math.radians(c - a)
    dl = math.radians(d - b)
    q = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1, math.sqrt(q)))


def destination(lat: float, lon: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    r = 6371.0088
    br = math.radians(bearing_deg)
    p1 = math.radians(lat)
    l1 = math.radians(lon)
    d = distance_km / r
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(br))
    l2 = l1 + math.atan2(math.sin(br) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), ((math.degrees(l2) + 540) % 360) - 180


def lightning_count(data: dict, radius: int) -> int | None:
    lightning = data.get("lightning", {}) or {}
    if lightning.get("status") != "ok":
        return None
    item = (lightning.get("radii", {}) or {}).get(str(radius), {}) or {}
    value = item.get("flash_count", item.get("frequency_sum"))
    n = num(value)
    return int(n) if n is not None else 0


def observation(data: dict) -> dict[str, Any]:
    tr = data.get("nowcast_tracking", {}) or {}
    cell = tr.get("cell", {}) or {}
    radar_distance = num(cell.get("distance_km"))
    radar_age = num(tr.get("age_minutes"))
    radar_fresh = tr.get("status") == "detected" and radar_age is not None and radar_age <= 40

    metrics = ((data.get("territory", {}) or {}).get("metrics", {}) or {})
    rain = num((metrics.get("rain_1h", {}) or {}).get("value"))
    rain_available = rain is not None

    lightning = data.get("lightning", {}) or {}
    lightning_age = num(lightning.get("age_minutes"))
    flashes20 = lightning_count(data, 20)
    flashes30 = lightning_count(data, 30)
    lightning_fresh = lightning.get("status") == "ok" and (lightning_age is None or lightning_age <= 35)

    strict = bool(
        (radar_fresh and radar_distance is not None and radar_distance <= 15)
        or (rain_available and rain >= 2.0)
        or (lightning_fresh and flashes20 is not None and flashes20 > 0)
    )
    nearby = bool(
        strict
        or (radar_fresh and radar_distance is not None and radar_distance <= 25)
        or (rain_available and rain >= 0.5)
        or (lightning_fresh and flashes30 is not None and flashes30 > 0)
    )
    evaluable = bool(radar_fresh or rain_available or lightning_fresh)
    return {
        "evaluable": evaluable,
        "event": strict,
        "nearby_signal": nearby,
        "radar_distance_km": radar_distance,
        "radar_fresh": radar_fresh,
        "rain_1h_mm": rain,
        "lightning_20km": flashes20,
        "lightning_30km": flashes30,
        "lightning_fresh": lightning_fresh,
        "track_id": tr.get("track_id"),
        "cell_lat": num(cell.get("lat")),
        "cell_lon": num(cell.get("lon")),
    }


def prediction_for_horizon(snapshot: dict, horizon: int) -> dict[str, Any]:
    p = snapshot.get("prediction", {}) or {}
    radar = p.get("radar", {}) or {}
    eta = num(radar.get("eta_minutes"))
    closest = num(radar.get("closest_approach_km"))
    closest_min = num(radar.get("closest_approach_minutes"))
    distance = num(radar.get("distance_km"))
    approaching = bool(radar.get("approaching"))
    flashes20 = num((p.get("lightning", {}) or {}).get("count_20km"))

    predicted = False
    reasons: list[str] = []
    if distance is not None and distance <= 15 and horizon <= 60:
        predicted = True
        reasons.append("cella già entro 15 km")
    if eta is not None and eta <= horizon + 15:
        predicted = True
        reasons.append(f"ETA {eta:.0f} min")
    if approaching and closest is not None and closest <= 8 and (closest_min is None or closest_min <= horizon + 15):
        predicted = True
        reasons.append("traiettoria verso Giammoro")
    if flashes20 is not None and flashes20 > 0 and horizon <= 30:
        predicted = True
        reasons.append("flash già entro 20 km")
    return {"event": predicted, "reasons": reasons, "eta_minutes": eta}


def make_snapshot(data: dict, issued_at: datetime) -> dict[str, Any]:
    tr = data.get("nowcast_tracking", {}) or {}
    cell = tr.get("cell", {}) or {}
    motion = tr.get("motion", {}) or {}
    lightning = data.get("lightning", {}) or {}
    snap_id = issued_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return {
        "id": snap_id,
        "issued_at": iso(issued_at),
        "prediction": {
            "nowcast_level": (data.get("nowcast", {}) or {}).get("level"),
            "nowcast_label": (data.get("nowcast", {}) or {}).get("label"),
            "confidence_score": num((data.get("analysis_confidence", {}) or {}).get("score")),
            "confidence_label": (data.get("analysis_confidence", {}) or {}).get("label"),
            "radar": {
                "track_id": tr.get("track_id"),
                "status": tr.get("status"),
                "lat": num(cell.get("lat")),
                "lon": num(cell.get("lon")),
                "distance_km": num(cell.get("distance_km")),
                "speed_kmh": num(motion.get("speed_kmh")),
                "direction_deg": num(motion.get("direction_deg")),
                "approaching": bool(motion.get("approaching")),
                "closest_approach_km": num(motion.get("closest_approach_km")),
                "closest_approach_minutes": num(motion.get("closest_approach_minutes")),
                "eta_minutes": num(motion.get("eta_minutes")),
            },
            "lightning": {
                "status": lightning.get("status"),
                "count_20km": lightning_count(data, 20),
                "count_30km": lightning_count(data, 30),
            },
            "risk_48h": (data.get("risk_48h", {}) or {}).get("level"),
        },
        "evaluated_horizons": [],
        "first_observed_event_minutes": None,
    }


def trajectory_error(snapshot: dict, obs: dict, horizon: int) -> float | None:
    radar = (snapshot.get("prediction", {}) or {}).get("radar", {}) or {}
    if not radar.get("track_id") or radar.get("track_id") != obs.get("track_id"):
        return None
    lat, lon = num(radar.get("lat")), num(radar.get("lon"))
    speed, direction = num(radar.get("speed_kmh")), num(radar.get("direction_deg"))
    olat, olon = obs.get("cell_lat"), obs.get("cell_lon")
    if None in (lat, lon, speed, direction, olat, olon):
        return None
    plat, plon = destination(lat, lon, direction, speed * horizon / 60.0)
    return round(haversine_km(plat, plon, olat, olon), 1)


def classify(predicted: bool, obs: dict) -> str:
    if not obs.get("evaluable"):
        return "inconclusive"
    actual = bool(obs.get("event"))
    nearby = bool(obs.get("nearby_signal"))
    if predicted and actual:
        return "correct"
    if not predicted and not actual:
        return "correct"
    if predicted and not actual and nearby:
        return "partial"
    if predicted and not actual:
        return "false_alarm"
    return "missed_event"


def evaluate_snapshot(snapshot: dict, current: dict, now: datetime) -> list[dict[str, Any]]:
    issued = parse_iso(snapshot.get("issued_at"))
    if not issued:
        return []
    elapsed = (now.astimezone(timezone.utc) - issued).total_seconds() / 60.0
    done = set(int(x) for x in snapshot.get("evaluated_horizons", []) if num(x) is not None)
    obs = observation(current)
    results = []
    for horizon in HORIZONS:
        if horizon in done or elapsed < horizon - 5:
            continue
        # Non valutare troppo tardi uno specifico orizzonte: il campione non rappresenterebbe più quella finestra.
        if elapsed > horizon + 35:
            snapshot.setdefault("evaluated_horizons", []).append(horizon)
            results.append({
                "snapshot_id": snapshot.get("id"), "issued_at": snapshot.get("issued_at"),
                "verified_at": iso(now), "horizon_minutes": horizon, "outcome": "inconclusive",
                "reason": "finestra di verifica superata", "predicted_event": None, "observed_event": None,
            })
            continue
        pred = prediction_for_horizon(snapshot, horizon)
        outcome = classify(bool(pred["event"]), obs)
        if obs.get("event") and snapshot.get("first_observed_event_minutes") is None:
            snapshot["first_observed_event_minutes"] = int(round(elapsed))
        eta_error = None
        eta = pred.get("eta_minutes")
        first = num(snapshot.get("first_observed_event_minutes"))
        if eta is not None and first is not None:
            eta_error = round(abs(first - eta), 1)
        tr_error = trajectory_error(snapshot, obs, horizon)
        result = {
            "snapshot_id": snapshot.get("id"),
            "issued_at": snapshot.get("issued_at"),
            "verified_at": iso(now),
            "horizon_minutes": horizon,
            "outcome": outcome,
            "predicted_event": bool(pred["event"]),
            "observed_event": bool(obs.get("event")) if obs.get("evaluable") else None,
            "nearby_signal": bool(obs.get("nearby_signal")) if obs.get("evaluable") else None,
            "prediction_reasons": pred.get("reasons", []),
            "confidence_score": num((snapshot.get("prediction", {}) or {}).get("confidence_score")),
            "eta_predicted_minutes": eta,
            "eta_error_minutes": eta_error,
            "trajectory_error_km": tr_error,
            "observation": obs,
        }
        snapshot.setdefault("evaluated_horizons", []).append(horizon)
        results.append(result)
    return results


def confidence_bin(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score < 40:
        return "low"
    if score < 65:
        return "medium"
    if score < 85:
        return "high"
    return "very_high"


def build_summary(results: list[dict]) -> dict[str, Any]:
    evaluable = [r for r in results if r.get("outcome") != "inconclusive"]
    counts = {k: sum(1 for r in evaluable if r.get("outcome") == k) for k in ("correct", "partial", "false_alarm", "missed_event")}
    weighted_ok = counts["correct"] + 0.5 * counts["partial"]
    accuracy = round(100 * weighted_ok / len(evaluable), 1) if evaluable else None
    eta = [num(r.get("eta_error_minutes")) for r in evaluable]
    eta = [x for x in eta if x is not None]
    traj = [num(r.get("trajectory_error_km")) for r in evaluable]
    traj = [x for x in traj if x is not None]
    by_conf: dict[str, Any] = {}
    for name in ("low", "medium", "high", "very_high"):
        bucket = [r for r in evaluable if confidence_bin(num(r.get("confidence_score"))) == name]
        ok = sum(1 for r in bucket if r.get("outcome") == "correct") + 0.5 * sum(1 for r in bucket if r.get("outcome") == "partial")
        by_conf[name] = {"samples": len(bucket), "accuracy_percent": round(100 * ok / len(bucket), 1) if bucket else None}
    return {
        "total_results": len(results),
        "evaluable_results": len(evaluable),
        "correct": counts["correct"],
        "partial": counts["partial"],
        "false_alarm": counts["false_alarm"],
        "missed_event": counts["missed_event"],
        "accuracy_percent": accuracy,
        "eta_samples": len(eta),
        "eta_mae_minutes": round(sum(eta) / len(eta), 1) if eta else None,
        "trajectory_samples": len(traj),
        "trajectory_mae_km": round(sum(traj) / len(traj), 1) if traj else None,
        "by_confidence": by_conf,
        "note": "Metriche sperimentali ex-post; soglie e classificazione sono euristiche del progetto e saranno calibrate con più campioni.",
    }


def update_events(events_doc: dict, current: dict, now: datetime) -> dict:
    events = list(events_doc.get("events", []))
    active = events_doc.get("active_event")
    obs = observation(current)
    tr = current.get("nowcast_tracking", {}) or {}
    cell = tr.get("cell", {}) or {}
    peak = num(tr.get("peak_value"))
    rain = obs.get("rain_1h_mm")
    flashes20 = obs.get("lightning_20km")
    conf = num((current.get("analysis_confidence", {}) or {}).get("score"))

    if obs.get("event"):
        if not active:
            active = {
                "id": now.astimezone(timezone.utc).strftime("EVT-%Y%m%dT%H%M%SZ"),
                "type": "local_convective_signal",
                "started_at": iso(now),
                "last_seen_at": iso(now),
                "ended_at": None,
                "samples": 0,
                "min_radar_distance_km": None,
                "max_radar_peak": None,
                "max_rain_1h_mm": None,
                "max_flashes_20km": 0,
                "max_confidence_score": None,
            }
        active["last_seen_at"] = iso(now)
        active["samples"] = int(active.get("samples", 0)) + 1
        distance = num(cell.get("distance_km"))
        if distance is not None:
            old = num(active.get("min_radar_distance_km"))
            active["min_radar_distance_km"] = round(distance if old is None else min(old, distance), 1)
        if peak is not None:
            old = num(active.get("max_radar_peak"))
            active["max_radar_peak"] = round(peak if old is None else max(old, peak), 2)
        if rain is not None:
            old = num(active.get("max_rain_1h_mm"))
            active["max_rain_1h_mm"] = round(rain if old is None else max(old, rain), 2)
        if flashes20 is not None:
            active["max_flashes_20km"] = max(int(active.get("max_flashes_20km", 0)), int(flashes20))
        if conf is not None:
            old = num(active.get("max_confidence_score"))
            active["max_confidence_score"] = int(round(conf if old is None else max(old, conf)))
    elif active:
        active["ended_at"] = iso(now)
        events.insert(0, active)
        active = None

    events_doc["schema_version"] = "1.0"
    events_doc["updated_at"] = iso(now)
    events_doc["active_event"] = active
    events_doc["events"] = events[:MAX_EVENTS]
    return events_doc


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (json.JSONDecodeError, OSError):
        return default


def run(data_path: Path, verification_path: Path, events_path: Path, now: datetime | None = None) -> tuple[dict, dict, dict]:
    now = now or utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    data = read_json(data_path, {})
    verification = read_json(verification_path, {"schema_version": "1.0", "pending": [], "results": []})
    events = read_json(events_path, {"schema_version": "1.0", "active_event": None, "events": []})

    pending = list(verification.get("pending", []))
    results = list(verification.get("results", []))
    new_results: list[dict] = []
    for snapshot in pending:
        new_results.extend(evaluate_snapshot(snapshot, data, now))

    results = (new_results + results)[:MAX_RESULTS]
    pending = [s for s in pending if set(int(x) for x in s.get("evaluated_horizons", [])) != set(HORIZONS)]
    pending = [s for s in pending if (now - (parse_iso(s.get("issued_at")) or now)).total_seconds() <= 4 * 3600]

    # Evita duplicati se il workflow viene rilanciato nello stesso minuto.
    current_id = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%MZ")
    if not any(str(s.get("id", "")).startswith(current_id) for s in pending):
        pending.append(make_snapshot(data, now))
    pending = pending[-12:]

    summary = build_summary(results)
    verification = {
        "schema_version": "1.0",
        "updated_at": iso(now),
        "horizons_minutes": list(HORIZONS),
        "summary": summary,
        "pending": pending,
        "results": results,
    }
    events = update_events(events, data, now)

    data["verification"] = {
        "updated_at": verification["updated_at"],
        "summary": summary,
        "latest_result": results[0] if results else None,
        "active_event": events.get("active_event"),
        "completed_events": len(events.get("events", [])),
    }

    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verification_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    events_path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data, verification, events


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data.json")
    p.add_argument("--verification", default="verification.json")
    p.add_argument("--events", default="events.json")
    args = p.parse_args()
    _, verification, events = run(Path(args.data), Path(args.verification), Path(args.events))
    print(
        "Verifica ex-post aggiornata: "
        f"{verification['summary']['evaluable_results']} campioni valutabili, "
        f"{len(verification['pending'])} snapshot in attesa, "
        f"{len(events.get('events', []))} eventi conclusi"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
