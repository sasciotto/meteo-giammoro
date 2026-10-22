#!/usr/bin/env python3
"""Adattatore verifica ex-post: impatto locale separato dal track radar e diagnostica per orizzonte."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import verification_engine as base

_ORIGINAL_UPDATE_EVENTS = base.update_events
_ORIGINAL_BUILD_SUMMARY = base.build_summary
_ORIGINAL_MAKE_SNAPSHOT = base.make_snapshot


def _candidate_distance(candidate: dict) -> float | None:
    return base.num((candidate or {}).get("distance_km"))


def _local_candidates(tracking: dict) -> list[dict]:
    candidates = [
        dict(candidate)
        for candidate in (tracking.get("candidates", []) or [])
        if isinstance(candidate, dict) and _candidate_distance(candidate) is not None
    ]
    if candidates:
        return candidates

    for key in ("hazard_cell", "cell"):
        candidate = tracking.get(key, {}) or {}
        if isinstance(candidate, dict) and _candidate_distance(candidate) is not None:
            row = dict(candidate)
            row["_fallback_role"] = key
            return [row]
    return []


def _nearest_local_candidate(tracking: dict) -> tuple[dict, str]:
    candidates = _local_candidates(tracking)
    if not candidates:
        return {}, "none"
    nearest = min(candidates, key=lambda candidate: _candidate_distance(candidate) or 9999.0)
    role = str(nearest.pop("_fallback_role", "") or "")
    if not role:
        role = "nearest_candidate"
    return nearest, role


def _tracked_cell(tracking: dict) -> dict:
    return dict(tracking.get("tracked_cell") or tracking.get("cell") or {})


def observation(data: dict) -> dict[str, Any]:
    """Valuta l'impatto locale su tutte le celle significative; la traiettoria resta legata al track principale."""
    tr = data.get("nowcast_tracking", {}) or {}
    local, local_role = _nearest_local_candidate(tr)
    tracked = _tracked_cell(tr)

    radar_distance = base.num(local.get("distance_km"))
    radar_age = base.num(tr.get("age_minutes"))
    radar_fresh = tr.get("status") == "detected" and radar_age is not None and radar_age <= 40

    metrics = ((data.get("territory", {}) or {}).get("metrics", {}) or {})
    rain = base.num((metrics.get("rain_1h", {}) or {}).get("value"))
    rain_available = rain is not None

    lightning = data.get("lightning", {}) or {}
    lightning_age = base.num(lightning.get("age_minutes"))
    flashes20 = base.lightning_count(data, 20)
    flashes30 = base.lightning_count(data, 30)
    # Un timestamp mancante non equivale a un dato fresco.
    lightning_fresh = lightning.get("status") == "ok" and lightning_age is not None and lightning_age <= 35

    event_drivers: list[str] = []
    if radar_fresh and radar_distance is not None and radar_distance <= 15:
        event_drivers.append("radar_15km")
    if rain_available and rain >= 2.0:
        event_drivers.append("rain_1h")
    if lightning_fresh and flashes20 is not None and flashes20 > 0:
        event_drivers.append("lightning_20km")

    strict = bool(event_drivers)
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
        "event_drivers": event_drivers,
        "radar_distance_km": radar_distance,
        "radar_fresh": radar_fresh,
        "radar_candidate_count": len(_local_candidates(tr)),
        "rain_1h_mm": rain,
        "lightning_20km": flashes20,
        "lightning_30km": flashes30,
        "lightning_fresh": lightning_fresh,
        "track_id": tr.get("track_id"),
        "cell_lat": base.num(local.get("lat")),
        "cell_lon": base.num(local.get("lon")),
        "cell_role": local_role,
        "tracked_cell_lat": base.num(tracked.get("lat")),
        "tracked_cell_lon": base.num(tracked.get("lon")),
    }


def make_snapshot(data: dict, issued_at):
    """Archivia precursori locali senza confonderli con la traiettoria del track principale."""
    snapshot = _ORIGINAL_MAKE_SNAPSHOT(data, issued_at)
    prediction = snapshot.setdefault("prediction", {})
    radar = prediction.setdefault("radar", {})
    tr = data.get("nowcast_tracking", {}) or {}
    local, _ = _nearest_local_candidate(tr)

    radar["local_nearest_distance_km"] = base.num(local.get("distance_km"))
    radar["local_nearest_lat"] = base.num(local.get("lat"))
    radar["local_nearest_lon"] = base.num(local.get("lon"))
    radar["local_nearest_peak_value"] = base.num(local.get("peak_value"))
    radar["local_candidate_count"] = len(_local_candidates(tr))

    quality = data.get("analysis_quality", {}) or {}
    trajectory = data.get("trajectory_reliability", {}) or {}
    predictive = data.get("predictive_confidence", {}) or {}
    prediction["data_quality_score"] = base.num(quality.get("score"))
    prediction["trajectory_reliability_score"] = base.num(trajectory.get("score"))
    prediction["predictive_confidence_status"] = predictive.get("status") or "uncalibrated"
    prediction["confidence_score"] = None
    prediction["confidence_label"] = "Non calibrata"

    home_nowcast = ((data.get("home_summary", {}) or {}).get("nowcast_simple", {}) or {})
    prediction["watch_status"] = home_nowcast.get("status")
    return snapshot


def prediction_for_horizon(snapshot: dict, horizon: int) -> dict[str, Any]:
    """Separa previsione evento e segnale di attenzione/precursore."""
    p = snapshot.get("prediction", {}) or {}
    radar = p.get("radar", {}) or {}
    eta = base.num(radar.get("eta_minutes"))
    closest = base.num(radar.get("closest_approach_km"))
    closest_min = base.num(radar.get("closest_approach_minutes"))
    tracked_distance = base.num(radar.get("distance_km"))
    local_distance = base.num(radar.get("local_nearest_distance_km"))
    if local_distance is None:
        local_distance = tracked_distance
    approaching = bool(radar.get("approaching"))
    lightning = p.get("lightning", {}) or {}
    flashes20 = base.num(lightning.get("count_20km"))
    flashes30 = base.num(lightning.get("count_30km"))

    predicted = False
    reasons: list[str] = []
    if local_distance is not None and local_distance <= 15 and horizon <= 60:
        predicted = True
        reasons.append("nucleo radar locale già entro 15 km")
    if eta is not None and eta <= horizon + 15:
        predicted = True
        reasons.append(f"ETA {eta:.0f} min")
    if approaching and closest is not None and closest <= 8 and (closest_min is None or closest_min <= horizon + 15):
        predicted = True
        reasons.append("traiettoria verso Giammoro")
    if flashes20 is not None and flashes20 > 0 and horizon <= 30:
        predicted = True
        reasons.append("flash già entro 20 km")

    watch = predicted
    watch_reasons = list(reasons)
    if horizon <= 60 and local_distance is not None and local_distance <= 25:
        watch = True
        watch_reasons.append("nucleo radar significativo entro 25 km")
    if horizon <= 60 and flashes30 is not None and flashes30 > 0:
        watch = True
        watch_reasons.append("attività elettrica entro 30 km")
    if approaching and closest is not None and closest <= 15 and (closest_min is None or closest_min <= horizon + 30):
        watch = True
        watch_reasons.append("traiettoria con passaggio entro 15 km")
    if horizon <= 60 and str(p.get("watch_status") or "") in {"watch", "incoming", "active"}:
        watch = True
        watch_reasons.append("sintesi nowcasting in monitoraggio")

    watch_reasons = list(dict.fromkeys(watch_reasons))
    return {
        "event": predicted,
        "reasons": reasons,
        "eta_minutes": eta,
        "watch": watch,
        "watch_reasons": watch_reasons,
    }


def trajectory_error(snapshot: dict, obs: dict, horizon: int) -> float | None:
    """Misura il track contro la stessa cella tracciata, non contro una cella locale secondaria."""
    radar = (snapshot.get("prediction", {}) or {}).get("radar", {}) or {}
    if not radar.get("track_id") or radar.get("track_id") != obs.get("track_id"):
        return None
    lat, lon = base.num(radar.get("lat")), base.num(radar.get("lon"))
    speed, direction = base.num(radar.get("speed_kmh")), base.num(radar.get("direction_deg"))
    olat = base.num(obs.get("tracked_cell_lat"))
    olon = base.num(obs.get("tracked_cell_lon"))
    if olat is None or olon is None:
        olat, olon = base.num(obs.get("cell_lat")), base.num(obs.get("cell_lon"))
    if None in (lat, lon, speed, direction, olat, olon):
        return None
    plat, plon = base.destination(lat, lon, direction, speed * horizon / 60.0)
    return round(base.haversine_km(plat, plon, olat, olon), 1)


def evaluate_snapshot(snapshot: dict, current: dict, now) -> list[dict[str, Any]]:
    """Valuta evento e watch separatamente, conservando la semantica storica degli outcome."""
    issued = base.parse_iso(snapshot.get("issued_at"))
    if not issued:
        return []
    elapsed = (now.astimezone(base.timezone.utc) - issued).total_seconds() / 60.0
    done = set(int(x) for x in snapshot.get("evaluated_horizons", []) if base.num(x) is not None)
    obs = observation(current)
    results = []

    for horizon in base.HORIZONS:
        if horizon in done or elapsed < horizon - 5:
            continue
        if elapsed > horizon + 35:
            snapshot.setdefault("evaluated_horizons", []).append(horizon)
            results.append({
                "snapshot_id": snapshot.get("id"),
                "issued_at": snapshot.get("issued_at"),
                "verified_at": base.iso(now),
                "horizon_minutes": horizon,
                "outcome": "inconclusive",
                "reason": "finestra di verifica superata",
                "predicted_event": None,
                "predicted_watch": None,
                "observed_event": None,
            })
            continue

        pred = prediction_for_horizon(snapshot, horizon)
        outcome = base.classify(bool(pred["event"]), obs)
        if obs.get("event") and snapshot.get("first_observed_event_minutes") is None:
            snapshot["first_observed_event_minutes"] = int(round(elapsed))

        eta_error = None
        eta = pred.get("eta_minutes")
        first = base.num(snapshot.get("first_observed_event_minutes"))
        if eta is not None and first is not None:
            eta_error = round(abs(first - eta), 1)

        result = {
            "snapshot_id": snapshot.get("id"),
            "issued_at": snapshot.get("issued_at"),
            "verified_at": base.iso(now),
            "horizon_minutes": horizon,
            "outcome": outcome,
            "predicted_event": bool(pred["event"]),
            "predicted_watch": bool(pred["watch"]),
            "observed_event": bool(obs.get("event")) if obs.get("evaluable") else None,
            "nearby_signal": bool(obs.get("nearby_signal")) if obs.get("evaluable") else None,
            "prediction_reasons": pred.get("reasons", []),
            "watch_reasons": pred.get("watch_reasons", []),
            "confidence_score": base.num((snapshot.get("prediction", {}) or {}).get("confidence_score")),
            "eta_predicted_minutes": eta,
            "eta_error_minutes": eta_error,
            "trajectory_error_km": trajectory_error(snapshot, obs, horizon),
            "observation": obs,
        }
        snapshot.setdefault("evaluated_horizons", []).append(horizon)
        results.append(result)
    return results


def update_events(events_doc: dict, current: dict, now):
    """Archivia la cella locale più vicina senza riusare la qualità dati come confidenza previsionale."""
    tr = current.get("nowcast_tracking", {}) or {}
    local, _ = _nearest_local_candidate(tr)
    adapted = dict(current)
    adapted["analysis_confidence"] = {"score": None, "label": "Non calibrata"}
    if local:
        adapted_tr = dict(tr)
        adapted_tr["cell"] = dict(local)
        if local.get("peak_value") is not None:
            adapted_tr["peak_value"] = local.get("peak_value")
        adapted["nowcast_tracking"] = adapted_tr
    return _ORIGINAL_UPDATE_EVENTS(events_doc, adapted, now)


def _pct(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 1) if denominator else None


def _event_metrics(results: list[dict]) -> dict[str, Any]:
    binary = [
        row for row in results
        if row.get("outcome") != "inconclusive"
        and isinstance(row.get("predicted_event"), bool)
        and isinstance(row.get("observed_event"), bool)
    ]
    tp = sum(1 for r in binary if r["predicted_event"] and r["observed_event"])
    tn = sum(1 for r in binary if not r["predicted_event"] and not r["observed_event"])
    fp = sum(1 for r in binary if r["predicted_event"] and not r["observed_event"])
    fn = sum(1 for r in binary if not r["predicted_event"] and r["observed_event"])
    recall = _pct(tp, tp + fn)
    specificity = _pct(tn, tn + fp)
    precision = _pct(tp, tp + fp)
    far = _pct(fp, tp + fp)
    csi = _pct(tp, tp + fp + fn)
    balanced = round((recall + specificity) / 2.0, 1) if recall is not None and specificity is not None else None
    return {
        "samples": len(binary),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "event_samples": tp + fn,
        "no_event_samples": tn + fp,
        "event_detection_percent": recall,
        "precision_percent": precision,
        "false_alarm_ratio_percent": far,
        "specificity_percent": specificity,
        "balanced_accuracy_percent": balanced,
        "csi_percent": csi,
    }


def _drivers_from_result(row: dict) -> list[str]:
    obs = row.get("observation", {}) or {}
    explicit = [str(x) for x in (obs.get("event_drivers", []) or []) if x]
    if explicit:
        return explicit

    drivers: list[str] = []
    distance = base.num(obs.get("radar_distance_km"))
    if obs.get("radar_fresh") and distance is not None and distance <= 15:
        drivers.append("radar_15km")
    rain = base.num(obs.get("rain_1h_mm"))
    if rain is not None and rain >= 2.0:
        drivers.append("rain_1h")
    flashes20 = base.num(obs.get("lightning_20km"))
    if obs.get("lightning_fresh") and flashes20 is not None and flashes20 > 0:
        drivers.append("lightning_20km")
    return drivers


def build_summary(results: list[dict]) -> dict[str, Any]:
    """Aggiunge metriche per orizzonte e diagnostica dei miss senza alterare le soglie operative."""
    summary = _ORIGINAL_BUILD_SUMMARY(results)
    summary["event_metrics"] = _event_metrics(results)
    summary["by_horizon"] = {
        str(horizon): _event_metrics([
            row for row in results
            if int(base.num(row.get("horizon_minutes")) or -1) == horizon
        ])
        for horizon in base.HORIZONS
    }

    missed = [
        row for row in results
        if row.get("outcome") != "inconclusive"
        and row.get("predicted_event") is False
        and row.get("observed_event") is True
    ]
    by_driver = {"radar_15km": 0, "rain_1h": 0, "lightning_20km": 0, "multiple": 0, "unknown": 0}
    for row in missed:
        drivers = _drivers_from_result(row)
        if not drivers:
            by_driver["unknown"] += 1
        if len(drivers) > 1:
            by_driver["multiple"] += 1
        for driver in drivers:
            if driver in by_driver:
                by_driver[driver] += 1

    summary["miss_diagnostics"] = {
        "false_negative_total": len(missed),
        "by_horizon": {
            str(horizon): sum(
                1 for row in missed
                if int(base.num(row.get("horizon_minutes")) or -1) == horizon
            )
            for horizon in base.HORIZONS
        },
        "by_event_driver": by_driver,
        "note": "Un singolo miss può avere più driver osservati e quindi comparire in più categorie.",
    }

    watch_rows = [
        row for row in results
        if isinstance(row.get("predicted_watch"), bool)
        and isinstance(row.get("observed_event"), bool)
        and row.get("outcome") != "inconclusive"
    ]
    watch_events = [row for row in watch_rows if row["observed_event"]]
    covered = sum(1 for row in watch_events if row.get("predicted_event") or row.get("predicted_watch"))
    positives = [row for row in watch_rows if row.get("predicted_event") or row.get("predicted_watch")]
    false_positives = sum(1 for row in positives if not row["observed_event"])
    summary["watch_metrics"] = {
        "status": "collecting" if len(watch_events) < 20 else "diagnostic",
        "samples": len(watch_rows),
        "event_samples": len(watch_events),
        "covered_events": covered,
        "event_coverage_percent": _pct(covered, len(watch_events)),
        "positive_samples": len(positives),
        "false_positive_samples": false_positives,
        "false_positive_ratio_percent": _pct(false_positives, len(positives)),
        "note": "Il watch è un precursore diagnostico, non un'allerta né una probabilità calibrata.",
    }

    summary["by_confidence"] = {
        "status": "disabled_until_probabilistic_calibration",
        "note": "I vecchi punteggi di qualità tecnica non vengono più trattati come confidenza probabilistica.",
    }
    summary["note"] = (
        "Metriche sperimentali ex-post. L'accuracy globale è secondaria; POD, FAR, CSI e balanced accuracy "
        "sono ora disponibili anche separatamente a 30/60/120 minuti. Il watch registra precursori deboli "
        "senza trasformarli in eventi operativi. La confidenza probabilistica resta non calibrata."
    )
    return summary


def install() -> None:
    base.observation = observation
    base.make_snapshot = make_snapshot
    base.prediction_for_horizon = prediction_for_horizon
    base.trajectory_error = trajectory_error
    base.evaluate_snapshot = evaluate_snapshot
    base.update_events = update_events
    base.build_summary = build_summary


def run(data_path: Path, verification_path: Path, events_path: Path, now=None):
    install()
    return base.run(data_path, verification_path, events_path, now=now)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data.json")
    p.add_argument("--verification", default="verification.json")
    p.add_argument("--events", default="events.json")
    args = p.parse_args()
    _, verification, events = run(Path(args.data), Path(args.verification), Path(args.events))
    metrics = (verification["summary"].get("event_metrics") or {})
    print(
        "Verifica ex-post v2 aggiornata: "
        f"{verification['summary']['evaluable_results']} campioni valutabili, "
        f"{metrics.get('event_samples', 0)} campioni evento, "
        f"{len(verification['pending'])} snapshot in attesa, "
        f"{len(events.get('events', []))} eventi conclusi"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
