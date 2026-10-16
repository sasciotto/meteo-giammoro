#!/usr/bin/env python3
"""Adattatore verifica ex-post: hazard locale separato dal track radar."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import verification_engine as base

_ORIGINAL_UPDATE_EVENTS = base.update_events
_ORIGINAL_BUILD_SUMMARY = base.build_summary


def observation(data: dict) -> dict[str, Any]:
    """Valuta l'impatto locale usando hazard_cell; track_id resta del tracker."""
    tr = data.get("nowcast_tracking", {}) or {}
    hazard = tr.get("hazard_cell", {}) or tr.get("cell", {}) or {}
    radar_distance = base.num(hazard.get("distance_km"))
    radar_age = base.num(tr.get("age_minutes"))
    radar_fresh = tr.get("status") == "detected" and radar_age is not None and radar_age <= 40

    metrics = ((data.get("territory", {}) or {}).get("metrics", {}) or {})
    rain = base.num((metrics.get("rain_1h", {}) or {}).get("value"))
    rain_available = rain is not None

    lightning = data.get("lightning", {}) or {}
    lightning_age = base.num(lightning.get("age_minutes"))
    flashes20 = base.lightning_count(data, 20)
    flashes30 = base.lightning_count(data, 30)
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
        "cell_lat": base.num(hazard.get("lat")),
        "cell_lon": base.num(hazard.get("lon")),
        "cell_role": "hazard_cell" if tr.get("hazard_cell") else "cell",
    }


def update_events(events_doc: dict, current: dict, now):
    """Archivia distanza/picco del fenomeno localmente più rilevante."""
    tr = current.get("nowcast_tracking", {}) or {}
    hazard = tr.get("hazard_cell", {}) or tr.get("cell", {}) or {}
    if hazard is tr.get("cell") or not hazard:
        return _ORIGINAL_UPDATE_EVENTS(events_doc, current, now)

    adapted = dict(current)
    adapted_tr = dict(tr)
    adapted_tr["cell"] = dict(hazard)
    if hazard.get("peak_value") is not None:
        adapted_tr["peak_value"] = hazard.get("peak_value")
    adapted["nowcast_tracking"] = adapted_tr
    return _ORIGINAL_UPDATE_EVENTS(events_doc, adapted, now)


def _pct(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 1) if denominator else None


def build_summary(results: list[dict]) -> dict[str, Any]:
    """Aggiunge metriche event-sensitive alla sintesi storica."""
    summary = _ORIGINAL_BUILD_SUMMARY(results)
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
    balanced = None
    if recall is not None and specificity is not None:
        balanced = round((recall + specificity) / 2.0, 1)

    summary["event_metrics"] = {
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
    summary["note"] = (
        "Metriche sperimentali ex-post. L'accuracy globale è mantenuta per compatibilità "
        "ma può essere dominata dai casi senza evento; per la qualità degli eventi usare "
        "POD/event detection, false alarm ratio, CSI e balanced accuracy."
    )
    return summary


def install() -> None:
    base.observation = observation
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
