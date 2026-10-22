#!/usr/bin/env python3
"""Verifica prospettica della presenza di pioggia locale a 30/60/120 minuti.

Questa metrica è separata dagli eventi significativi: misura se il sistema riconosce/prevede
la semplice presenza di precipitazione nell'area di Giammoro, usando il contesto radar
multi-raggio prodotto da runtime_quality.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HORIZONS = (30, 60, 120)
MAX_PENDING = 120
MAX_RESULTS = 600
MAX_PROCESSED = 1200
METRIC_VERSION = "local-precipitation-v1"


def _num(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _parse_iso(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value)) if value else None
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _prediction(data: dict) -> dict[str, Any]:
    local = data.get("local_precipitation", {}) or {}
    forecast = local.get("forecast_0_3h", {}) or {}
    current_wet = int(_num(forecast.get("current_wet_models")) or 0)
    wet = int(_num(forecast.get("wet_models")) or 0)
    notable = int(_num(forecast.get("notable_models")) or 0)
    status = str(forecast.get("status") or "low")
    observed_now = local.get("status") == "active"

    by_horizon = {
        "30": bool(observed_now or current_wet >= 2),
        "60": bool(observed_now or status == "supported" or notable >= 2),
        "120": bool(observed_now or status in {"weak", "supported"}),
    }
    return {
        "by_horizon": by_horizon,
        "forecast_status": status,
        "wet_models": wet,
        "current_wet_models": current_wet,
        "notable_models": notable,
        "max_precip_0_3h_mm": _num(forecast.get("max_precip_0_3h_mm")),
        "observed_at_issue": observed_now,
    }


def _history(data: dict) -> list[dict]:
    return [
        row for row in ((data.get("local_precipitation", {}) or {}).get("history", []) or [])
        if isinstance(row, dict) and _parse_iso(row.get("timestamp")) is not None
    ]


def _observed_between(history: list[dict], start: datetime, end: datetime) -> bool:
    for row in history:
        stamp = _parse_iso(row.get("timestamp"))
        if stamp is not None and start <= stamp <= end and bool(row.get("rain_detected")):
            return True
    return False


def _empty_counts() -> dict[str, int]:
    return {"true_positive": 0, "true_negative": 0, "false_positive": 0, "false_negative": 0}


def _classify(predicted: bool, observed: bool) -> str:
    if predicted and observed:
        return "true_positive"
    if predicted and not observed:
        return "false_positive"
    if not predicted and observed:
        return "false_negative"
    return "true_negative"


def _pct(a: int, b: int) -> float | None:
    return round(100.0 * a / b, 1) if b else None


def _metrics(counts: dict[str, int]) -> dict[str, Any]:
    tp = int(counts.get("true_positive", 0))
    tn = int(counts.get("true_negative", 0))
    fp = int(counts.get("false_positive", 0))
    fn = int(counts.get("false_negative", 0))
    samples = tp + tn + fp + fn
    return {
        "samples": samples,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "rain_samples": tp + fn,
        "dry_samples": tn + fp,
        "rain_detection_percent": _pct(tp, tp + fn),
        "precision_percent": _pct(tp, tp + fp),
        "false_alarm_ratio_percent": _pct(fp, tp + fp),
        "accuracy_percent": _pct(tp + tn, samples),
    }


def _initial_state() -> dict[str, Any]:
    return {
        "metric_version": METRIC_VERSION,
        "pending": [],
        "results": [],
        "counts": _empty_counts(),
        "by_horizon": {str(h): _empty_counts() for h in HORIZONS},
        "processed_keys": [],
    }


def apply(data: dict, verification: dict, events: dict, now: datetime | None = None) -> tuple[dict, dict, dict]:
    now = now or _parse_iso((data.get("meta", {}) or {}).get("last_check_iso")) or datetime.now(timezone.utc)
    now = now.astimezone(timezone.utc)
    state = events.get("precipitation_verification", {}) or {}
    if state.get("metric_version") != METRIC_VERSION:
        state = _initial_state()

    pending = [row for row in (state.get("pending", []) or []) if isinstance(row, dict)]
    results = [row for row in (state.get("results", []) or []) if isinstance(row, dict)]
    processed = [str(key) for key in (state.get("processed_keys", []) or []) if key]
    processed_set = set(processed)
    history = _history(data)

    retained: list[dict] = []
    for snapshot in pending:
        issued = _parse_iso(snapshot.get("issued_at"))
        if issued is None:
            continue
        evaluated = {int(x) for x in (snapshot.get("evaluated_horizons", []) or []) if _num(x) is not None}
        prediction = snapshot.get("prediction", {}) or {}
        by_horizon = prediction.get("by_horizon", {}) or {}

        for horizon in HORIZONS:
            if horizon in evaluated:
                continue
            due = issued + timedelta(minutes=horizon)
            if now < due - timedelta(minutes=5):
                continue
            if now > due + timedelta(minutes=35):
                evaluated.add(horizon)
                continue

            key = f"{snapshot.get('id')}:{horizon}"
            if key in processed_set:
                evaluated.add(horizon)
                continue
            predicted = bool(by_horizon.get(str(horizon), False))
            observed = _observed_between(history, issued, min(now, due + timedelta(minutes=15)))
            outcome = _classify(predicted, observed)
            result = {
                "snapshot_id": snapshot.get("id"),
                "issued_at": snapshot.get("issued_at"),
                "verified_at": _iso(now),
                "horizon_minutes": horizon,
                "predicted_rain": predicted,
                "observed_rain": observed,
                "outcome": outcome,
                "forecast_status": prediction.get("forecast_status"),
                "wet_models": prediction.get("wet_models"),
                "current_wet_models": prediction.get("current_wet_models"),
            }
            results.append(result)
            state["counts"][outcome] = int(state["counts"].get(outcome, 0)) + 1
            state["by_horizon"][str(horizon)][outcome] = int(state["by_horizon"][str(horizon)].get(outcome, 0)) + 1
            processed.append(key)
            processed_set.add(key)
            evaluated.add(horizon)

        snapshot["evaluated_horizons"] = sorted(evaluated)
        if len(evaluated) < len(HORIZONS) and now - issued <= timedelta(hours=4):
            retained.append(snapshot)

    local = data.get("local_precipitation", {}) or {}
    if local:
        snapshot_id = now.strftime("%Y%m%dT%H%M%SZ")
        if not any(str(row.get("id")) == snapshot_id for row in retained):
            retained.append({
                "id": snapshot_id,
                "issued_at": _iso(now),
                "prediction": _prediction(data),
                "evaluated_horizons": [],
            })

    state["pending"] = retained[-MAX_PENDING:]
    state["results"] = results[-MAX_RESULTS:]
    state["processed_keys"] = processed[-MAX_PROCESSED:]
    events["precipitation_verification"] = state

    summary = verification.setdefault("summary", {})
    summary["precipitation_presence"] = {
        "metric_version": METRIC_VERSION,
        "semantic": "rain_presence_not_severity",
        "cumulative": _metrics(state["counts"]),
        "by_horizon": {key: _metrics(value) for key, value in state["by_horizon"].items()},
        "note": (
            "Metrica separata dagli eventi significativi: misura la presenza di pioggia locale a 30/60/120 min. "
            "Il rilevamento osservato usa la persistenza radar multi-raggio e non trasforma i massimi areali in accumuli puntuali."
        ),
    }
    data.setdefault("verification", {})["precipitation_presence"] = summary["precipitation_presence"]
    return data, verification, events


def _read(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def run(data_path: Path, verification_path: Path, events_path: Path) -> tuple[dict, dict, dict]:
    data = _read(data_path, {})
    verification = _read(verification_path, {"summary": {}})
    events = _read(events_path, {})
    data, verification, events = apply(data, verification, events)
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
    metrics = (((verification.get("summary", {}) or {}).get("precipitation_presence", {}) or {}).get("cumulative", {}) or {})
    print(
        "Verifica pioggia locale: "
        f"{metrics.get('samples', 0)} campioni, {metrics.get('rain_samples', 0)} con pioggia, "
        f"POD={metrics.get('rain_detection_percent')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
