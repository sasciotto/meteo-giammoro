#!/usr/bin/env python3
"""Persistenza compatta e diagnostica per la futura calibrazione del nowcast.

Non modifica soglie operative e non produce probabilita' calibrate.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
MAX_ROWS = 5000
HORIZONS = (30, 60, 120)


def _dt(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) if dt else None
    except (TypeError, ValueError):
        return None


def _num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _key(row: dict[str, Any]) -> str:
    return f"{row.get('snapshot_id') or 'unknown'}:{int(_num(row.get('horizon_minutes')) or -1)}"


def _compact(row: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row.get("predicted_event"), bool) or not isinstance(row.get("observed_event"), bool):
        return None
    if row.get("outcome") == "inconclusive":
        return None
    obs = row.get("observation") or {}
    return {
        "key": _key(row),
        "snapshot_id": row.get("snapshot_id"),
        "issued_at": row.get("issued_at"),
        "verified_at": row.get("verified_at"),
        "horizon_minutes": int(_num(row.get("horizon_minutes")) or -1),
        "predicted_event": row.get("predicted_event"),
        "predicted_watch": bool(row.get("predicted_watch")),
        "observed_event": row.get("observed_event"),
        "outcome": row.get("outcome"),
        "prediction_reasons": list(row.get("prediction_reasons") or []),
        "watch_reasons": list(row.get("watch_reasons") or []),
        "event_drivers": list(obs.get("event_drivers") or []),
        "radar_distance_km": _num(obs.get("radar_distance_km")),
        "rain_1h_mm": _num(obs.get("rain_1h_mm")),
        "lightning_20km": _num(obs.get("lightning_20km")),
    }


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(1 for r in rows if r["predicted_event"] and r["observed_event"])
    tn = sum(1 for r in rows if not r["predicted_event"] and not r["observed_event"])
    fp = sum(1 for r in rows if r["predicted_event"] and not r["observed_event"])
    fn = sum(1 for r in rows if not r["predicted_event"] and r["observed_event"])
    def pct(a: int, b: int) -> float | None:
        return round(100.0 * a / b, 1) if b else None
    pod = pct(tp, tp + fn)
    spec = pct(tn, tn + fp)
    return {
        "samples": len(rows), "true_positive": tp, "true_negative": tn,
        "false_positive": fp, "false_negative": fn, "event_samples": tp + fn,
        "pod_percent": pod, "precision_percent": pct(tp, tp + fp),
        "far_percent": pct(fp, tp + fp), "specificity_percent": spec,
        "csi_percent": pct(tp, tp + fp + fn),
        "balanced_accuracy_percent": round((pod + spec) / 2, 1) if pod is not None and spec is not None else None,
    }


def _counter(rows: list[dict[str, Any]], field: str, predicate) -> dict[str, int]:
    c: Counter[str] = Counter()
    for row in rows:
        if not predicate(row):
            continue
        for item in row.get(field) or []:
            if item:
                c[str(item)] += 1
    return dict(c.most_common())


def build_report(rows: list[dict[str, Any]], updated_at: str | None = None) -> dict[str, Any]:
    by_horizon = {str(h): _metrics([r for r in rows if r.get("horizon_minutes") == h]) for h in HORIZONS}
    overall = _metrics(rows)
    event_samples = overall["event_samples"]
    watch_positive = [r for r in rows if r.get("predicted_watch")]
    watch_false = [r for r in watch_positive if not r.get("observed_event")]
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": updated_at,
        "status": "calibration_ready" if event_samples >= 20 else "collecting",
        "minimum_event_samples": 20,
        "note": "Diagnostica osservativa: non rappresenta una probabilita' calibrata e non modifica le soglie operative.",
        "overall": overall,
        "by_horizon": by_horizon,
        "diagnostics": {
            "prediction_reasons_true_positive": _counter(rows, "prediction_reasons", lambda r: r["predicted_event"] and r["observed_event"]),
            "prediction_reasons_false_positive": _counter(rows, "prediction_reasons", lambda r: r["predicted_event"] and not r["observed_event"]),
            "event_drivers_false_negative": _counter(rows, "event_drivers", lambda r: not r["predicted_event"] and r["observed_event"]),
            "watch": {
                "positive_samples": len(watch_positive),
                "false_positive_samples": len(watch_false),
                "false_positive_ratio_percent": round(100.0 * len(watch_false) / len(watch_positive), 1) if watch_positive else None,
                "reasons_false_positive": _counter(rows, "watch_reasons", lambda r: r.get("predicted_watch") and not r.get("observed_event")),
            },
        },
    }


def update(verification: dict[str, Any], history: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    history = dict(history or {})
    merged: dict[str, dict[str, Any]] = {}
    for row in history.get("rows") or []:
        if isinstance(row, dict) and row.get("key"):
            merged[str(row["key"])] = row
    for raw in verification.get("results") or []:
        if isinstance(raw, dict):
            row = _compact(raw)
            if row:
                merged[row["key"]] = row
    rows = sorted(merged.values(), key=lambda r: _dt(r.get("verified_at")) or datetime.min.replace(tzinfo=timezone.utc))[-MAX_ROWS:]
    updated_at = verification.get("updated_at") or datetime.now(timezone.utc).isoformat()
    payload = {"schema_version": SCHEMA_VERSION, "updated_at": updated_at, "max_rows": MAX_ROWS, "rows": rows}
    return payload, build_report(rows, updated_at)


def _read(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--verification", default="verification.json")
    p.add_argument("--history", default="calibration_history.json")
    p.add_argument("--report", default="nowcast_calibration.json")
    args = p.parse_args()
    verification = _read(Path(args.verification), {"results": []})
    history = _read(Path(args.history), {})
    history, report = update(verification, history)
    Path(args.history).write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Calibrazione diagnostica: {len(history['rows'])} righe, eventi={report['overall']['event_samples']}, stato={report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
