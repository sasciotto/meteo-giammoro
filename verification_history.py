#!/usr/bin/env python3
"""Conserva metriche cumulative della verifica ex-post senza farle sparire dal rolling window."""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

METRIC_VERSION = "local-event-v2"
SEMANTICS_START = "2026-10-22T13:46:39+00:00"
SEMANTICS_COMMIT = "b63ae2becaf09e42cbfa7568bb368fa52232ece1"
MAX_PROCESSED_KEYS = 900
MAX_EVENT_ARCHIVE = 600

# Ultimo snapshot completo prima del cambio semantico. È mantenuto separato:
# non viene sommato alle metriche v2 perché usava una definizione diversa della cella locale.
LEGACY_BASELINE = {
    "metric_version": "legacy-event-v1",
    "source_commit": "626b2f168212dc46d27f3fb03191a0b4174fb9d4",
    "updated_at": "2026-10-21T12:27:27+00:00",
    "samples": 300,
    "event_metrics": {
        "samples": 300,
        "true_positive": 14,
        "true_negative": 234,
        "false_positive": 9,
        "false_negative": 43,
        "event_samples": 57,
        "no_event_samples": 243,
        "event_detection_percent": 24.6,
        "precision_percent": 60.9,
        "false_alarm_ratio_percent": 39.1,
        "specificity_percent": 96.3,
        "balanced_accuracy_percent": 60.5,
        "csi_percent": 21.2,
    },
    "note": (
        "Baseline storica reale precedente al cambio semantico del 22/10/2026. "
        "Non viene combinata con la metrica v2 perché la v2 usa la cella radar significativa "
        "più vicina per l'impatto locale e richiede un timestamp fulmini valido."
    ),
}


def _num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _parse_iso(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value)) if value else None
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) if dt else None
    except (TypeError, ValueError):
        return None


def _row_key(row: dict) -> str:
    return f"{row.get('snapshot_id') or 'unknown'}:{int(_num(row.get('horizon_minutes')) or -1)}"


def _empty_counts() -> dict[str, int]:
    return {"true_positive": 0, "true_negative": 0, "false_positive": 0, "false_negative": 0}


def _classify(row: dict) -> str | None:
    predicted = row.get("predicted_event")
    observed = row.get("observed_event")
    if not isinstance(predicted, bool) or not isinstance(observed, bool):
        return None
    if predicted and observed:
        return "true_positive"
    if predicted and not observed:
        return "false_positive"
    if not predicted and observed:
        return "false_negative"
    return "true_negative"


def _pct(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 1) if denominator else None


def metrics_from_counts(counts: dict[str, int]) -> dict[str, Any]:
    tp = int(counts.get("true_positive", 0))
    tn = int(counts.get("true_negative", 0))
    fp = int(counts.get("false_positive", 0))
    fn = int(counts.get("false_negative", 0))
    samples = tp + tn + fp + fn
    pod = _pct(tp, tp + fn)
    specificity = _pct(tn, tn + fp)
    precision = _pct(tp, tp + fp)
    far = _pct(fp, tp + fp)
    csi = _pct(tp, tp + fp + fn)
    balanced = round((pod + specificity) / 2.0, 1) if pod is not None and specificity is not None else None
    return {
        "samples": samples,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "event_samples": tp + fn,
        "no_event_samples": tn + fp,
        "event_detection_percent": pod,
        "precision_percent": precision,
        "false_alarm_ratio_percent": far,
        "specificity_percent": specificity,
        "balanced_accuracy_percent": balanced,
        "csi_percent": csi,
        "accuracy_percent": _pct(tp + tn, samples),
    }


def _initial_state() -> dict[str, Any]:
    return {
        "metric_version": METRIC_VERSION,
        "semantics_start": SEMANTICS_START,
        "semantics_commit": SEMANTICS_COMMIT,
        "counts": _empty_counts(),
        "by_horizon": {str(h): _empty_counts() for h in (30, 60, 120)},
        "processed_keys": [],
        "latest_verified_at": None,
    }


def apply(data: dict, verification: dict, events: dict) -> tuple[dict, dict, dict]:
    state = events.get("verification_cumulative", {}) or {}
    if state.get("metric_version") != METRIC_VERSION:
        state = _initial_state()

    processed = [str(key) for key in (state.get("processed_keys", []) or []) if key]
    processed_set = set(processed)
    start = _parse_iso(SEMANTICS_START)
    new_event_rows: list[dict] = []
    latest = _parse_iso(state.get("latest_verified_at"))

    rows = [row for row in (verification.get("results", []) or []) if isinstance(row, dict)]
    rows.sort(key=lambda row: _parse_iso(row.get("verified_at")) or datetime.min.replace(tzinfo=timezone.utc))
    for row in rows:
        verified_at = _parse_iso(row.get("verified_at"))
        if verified_at is None or (start is not None and verified_at < start):
            continue
        key = _row_key(row)
        if key in processed_set:
            continue
        outcome = _classify(row)
        if outcome is None or row.get("outcome") == "inconclusive":
            continue

        state["counts"][outcome] = int(state["counts"].get(outcome, 0)) + 1
        horizon = str(int(_num(row.get("horizon_minutes")) or -1))
        if horizon in state["by_horizon"]:
            state["by_horizon"][horizon][outcome] = int(state["by_horizon"][horizon].get(outcome, 0)) + 1

        processed.append(key)
        processed_set.add(key)
        if latest is None or verified_at > latest:
            latest = verified_at
        if bool(row.get("predicted_event")) or bool(row.get("observed_event")):
            new_event_rows.append(row)

    state["processed_keys"] = processed[-MAX_PROCESSED_KEYS:]
    state["latest_verified_at"] = latest.isoformat(timespec="seconds") if latest else state.get("latest_verified_at")

    archive = [row for row in (events.get("verification_event_archive", []) or []) if isinstance(row, dict)]
    merged: dict[str, dict] = {_row_key(row): row for row in archive}
    for row in new_event_rows:
        merged[_row_key(row)] = row
    archive = sorted(
        merged.values(),
        key=lambda row: _parse_iso(row.get("verified_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:MAX_EVENT_ARCHIVE]

    cumulative = metrics_from_counts(state["counts"])
    by_horizon = {
        horizon: metrics_from_counts(counts)
        for horizon, counts in state.get("by_horizon", {}).items()
    }

    summary = verification.setdefault("summary", {})
    summary["metric_version"] = METRIC_VERSION
    summary["cumulative_event_metrics"] = cumulative
    summary["cumulative_by_horizon"] = by_horizon
    summary["legacy_baseline"] = LEGACY_BASELINE
    summary["retention_note"] = (
        "Le metriche cumulative v2 sono conservate separatamente dal rolling window di 300 risultati. "
        "La baseline v1 resta visibile ma non viene sommata perché usa una definizione precedente dell'evento locale."
    )

    events["verification_cumulative"] = state
    events["verification_event_archive"] = archive
    verification["schema_version"] = "1.1"

    data_verification = data.setdefault("verification", {})
    data_verification["summary"] = summary
    data_verification["updated_at"] = verification.get("updated_at")
    data_verification["metric_version"] = METRIC_VERSION
    return data, verification, events


def _read(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def run(data_path: Path, verification_path: Path, events_path: Path) -> tuple[dict, dict, dict]:
    data = _read(data_path, {})
    verification = _read(verification_path, {"schema_version": "1.0", "summary": {}, "results": []})
    events = _read(events_path, {"schema_version": "1.0", "events": [], "active_event": None})
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
    metrics = (verification.get("summary", {}) or {}).get("cumulative_event_metrics", {}) or {}
    print(
        "Storico verifica v2 conservato: "
        f"{metrics.get('samples', 0)} campioni cumulativi, "
        f"{metrics.get('event_samples', 0)} campioni evento, "
        f"{len(events.get('verification_event_archive', []) or [])} risultati evento archiviati"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
