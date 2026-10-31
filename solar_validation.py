#!/usr/bin/env python3
"""Confronto diagnostico tra LSA SAF e stazioni solari al suolo.

Allinea ogni prodotto satellitare al campione al suolo temporalmente piu' vicino
entro una finestra controllata. Il report e' diagnostico e non certifica la
validazione scientifica del prodotto.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
LSA_ID = "lsa-saf"
EXPECTED_LSA_CADENCE_MINUTES = 15
DEFAULT_MATCH_WINDOW_MINUTES = 20


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


def _source_time(sample: dict[str, Any], source: dict[str, Any]) -> datetime | None:
    return _dt(source.get("observed_at")) or _dt(source.get("retrieved_at")) or _dt(sample.get("timestamp"))


def _points(history: dict[str, Any]) -> dict[str, list[tuple[datetime, float]]]:
    out: dict[str, list[tuple[datetime, float]]] = {}
    seen: set[tuple[str, datetime]] = set()
    for sample in history.get("samples") or []:
        if not isinstance(sample, dict):
            continue
        for source_id, source in (sample.get("sources") or {}).items():
            if not isinstance(source, dict) or source.get("status") != "ok":
                continue
            stamp = _source_time(sample, source)
            value = _num(source.get("solar_wm2"))
            if stamp is None or value is None:
                continue
            key = (str(source_id), stamp)
            if key in seen:
                continue
            seen.add(key)
            out.setdefault(str(source_id), []).append((stamp, value))
    for values in out.values():
        values.sort(key=lambda item: item[0])
    return out


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    if den == 0:
        return None
    return round(sum(a*b for a, b in zip(dx, dy)) / den, 3)


def _match(satellite: list[tuple[datetime, float]], ground: list[tuple[datetime, float]], max_minutes: int) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    limit = max_minutes * 60
    for sat_t, sat_v in satellite:
        if not ground:
            continue
        grd_t, grd_v = min(ground, key=lambda item: abs((item[0] - sat_t).total_seconds()))
        delta = abs((grd_t - sat_t).total_seconds())
        if delta <= limit:
            matches.append({
                "satellite_at": sat_t.isoformat().replace("+00:00", "Z"),
                "ground_at": grd_t.isoformat().replace("+00:00", "Z"),
                "delta_minutes": round(delta / 60.0, 1),
                "satellite_wm2": round(sat_v, 1),
                "ground_wm2": round(grd_v, 1),
                "satellite_minus_ground_wm2": round(sat_v - grd_v, 1),
            })
    return matches


def build_report(history: dict[str, Any], match_window_minutes: int = DEFAULT_MATCH_WINDOW_MINUTES) -> dict[str, Any]:
    points = _points(history)
    sat = points.get(LSA_ID, [])
    gaps = [round((b[0] - a[0]).total_seconds() / 60.0, 1) for a, b in zip(sat, sat[1:]) if b[0] > a[0]]
    cadence = {
        "expected_minutes": EXPECTED_LSA_CADENCE_MINUTES,
        "distinct_samples": len(sat),
        "first_observed_at": sat[0][0].isoformat().replace("+00:00", "Z") if sat else None,
        "last_observed_at": sat[-1][0].isoformat().replace("+00:00", "Z") if sat else None,
        "median_gap_minutes": sorted(gaps)[len(gaps)//2] if gaps else None,
        "max_gap_minutes": max(gaps) if gaps else None,
        "gaps_over_30_minutes": sum(1 for g in gaps if g > 30),
    }
    sources: dict[str, Any] = {}
    for source_id, ground in sorted(points.items()):
        if source_id == LSA_ID:
            continue
        matches = _match(sat, ground, match_window_minutes)
        diffs = [m["satellite_minus_ground_wm2"] for m in matches]
        sat_values = [m["satellite_wm2"] for m in matches]
        grd_values = [m["ground_wm2"] for m in matches]
        sources[source_id] = {
            "matched_pairs": len(matches),
            "match_window_minutes": match_window_minutes,
            "mean_bias_satellite_minus_ground_wm2": round(sum(diffs) / len(diffs), 1) if diffs else None,
            "mae_wm2": round(sum(abs(x) for x in diffs) / len(diffs), 1) if diffs else None,
            "rmse_wm2": round(math.sqrt(sum(x*x for x in diffs) / len(diffs)), 1) if diffs else None,
            "correlation": _corr(sat_values, grd_values),
            "mean_time_offset_minutes": round(sum(m["delta_minutes"] for m in matches) / len(matches), 1) if matches else None,
            "pairs": matches,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": history.get("updated_at"),
        "status": "diagnostic",
        "note": "Confronto temporale best-effort. Differenze spaziali, ombre locali e timestamp di acquisizione delle PWS possono produrre scarti reali; il report non certifica una validazione scientifica.",
        "lsa_cadence": cadence,
        "ground_comparisons": sources,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--history", default="solar_history.json")
    p.add_argument("--report", default="solar_validation.json")
    p.add_argument("--match-window-minutes", type=int, default=DEFAULT_MATCH_WINDOW_MINUTES)
    args = p.parse_args()
    history = json.loads(Path(args.history).read_text(encoding="utf-8"))
    report = build_report(history, max(1, args.match_window_minutes))
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validazione solare diagnostica: LSA={report['lsa_cadence']['distinct_samples']} campioni, confronti={len(report['ground_comparisons'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
