#!/usr/bin/env python3
"""Monitor multi-cella delle traiettorie radar in avvicinamento verso Giammoro."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import nowcast_v2 as v2

MAX_ASSOCIATION_SPEED_KMH = 120.0
MAX_ASSOCIATION_DISTANCE_KM = 32.0
MAX_OUTPUT_CELLS = 4

SECTOR_LABELS = {
    "N": "nord",
    "NNE": "nord-nordest",
    "NE": "nord-est",
    "ENE": "est-nordest",
    "E": "est",
    "ESE": "est-sudest",
    "SE": "sud-est",
    "SSE": "sud-sudest",
    "S": "sud",
    "SSW": "sud-sudovest",
    "SW": "sud-ovest",
    "WSW": "ovest-sudovest",
    "W": "ovest",
    "WNW": "ovest-nordovest",
    "NW": "nord-ovest",
    "NNW": "nord-nordovest",
}


def _num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _sector_label(sector: Any) -> str | None:
    key = str(sector or "").upper()
    return SECTOR_LABELS.get(key) if key else None


def _angular_difference(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _candidate_sector(candidate: dict, rlat: float, rlon: float) -> tuple[float | None, str | None]:
    bearing = _num(candidate.get("bearing_deg"))
    if bearing is None:
        lat = _num(candidate.get("lat"))
        lon = _num(candidate.get("lon"))
        if lat is not None and lon is not None:
            bearing = v2.bearing_deg(rlat, rlon, lat, lon)
    sector = str(candidate.get("bearing") or v2.compass(bearing)).upper() if bearing is not None else None
    return bearing, sector


def _association(previous: dict, current: dict, interval_hours: float) -> dict | None:
    plat = _num(previous.get("lat"))
    plon = _num(previous.get("lon"))
    clat = _num(current.get("lat"))
    clon = _num(current.get("lon"))
    if None in {plat, plon, clat, clon} or interval_hours <= 0:
        return None

    displacement = v2.haversine_km(plat, plon, clat, clon)
    speed = displacement / interval_hours
    if speed > MAX_ASSOCIATION_SPEED_KMH or displacement > MAX_ASSOCIATION_DISTANCE_KM:
        return None

    prev_peak = max(0.1, _num(previous.get("peak_value")) or 0.1)
    curr_peak = max(0.1, _num(current.get("peak_value")) or 0.1)
    prev_pixels = max(1.0, _num(previous.get("pixels")) or 1.0)
    curr_pixels = max(1.0, _num(current.get("pixels")) or 1.0)
    intensity_penalty = abs(math.log(curr_peak / prev_peak)) * 3.0
    area_penalty = abs(math.log(curr_pixels / prev_pixels)) * 1.2
    score = displacement + intensity_penalty + area_penalty
    return {
        "score": round(score, 2),
        "displacement_km": round(displacement, 1),
        "implied_speed_kmh": round(speed, 1),
    }


def _match_candidates(previous: list[dict], current: list[dict], interval_hours: float) -> list[tuple[dict, dict, dict]]:
    possible: list[tuple[float, int, int, dict]] = []
    for ci, cur in enumerate(current):
        if not isinstance(cur, dict):
            continue
        for pi, prev in enumerate(previous):
            if not isinstance(prev, dict):
                continue
            assoc = _association(prev, cur, interval_hours)
            if assoc is not None:
                possible.append((float(assoc["score"]), ci, pi, assoc))

    possible.sort(key=lambda row: row[0])
    used_current: set[int] = set()
    used_previous: set[int] = set()
    matched: list[tuple[dict, dict, dict]] = []
    for _, ci, pi, assoc in possible:
        if ci in used_current or pi in used_previous:
            continue
        used_current.add(ci)
        used_previous.add(pi)
        matched.append((previous[pi], current[ci], assoc))
    return matched


def _approach_class(closest_km: float | None) -> str:
    if closest_km is None:
        return "approaching"
    if closest_km <= 5:
        return "direct"
    if closest_km <= 12:
        return "near_pass"
    return "approaching"


def _confidence(association_score: float | None, heading_error: float | None) -> str:
    if association_score is not None and association_score <= 7 and heading_error is not None and heading_error <= 35:
        return "high"
    if association_score is not None and association_score <= 14:
        return "medium"
    return "low"


def build_monitor(data: dict, previous_data: dict, rlat: float, rlon: float) -> dict:
    tracking = data.get("nowcast_tracking", {}) or {}
    previous_tracking = previous_data.get("nowcast_tracking", {}) or {}
    timestamp = tracking.get("timestamp")
    product = tracking.get("product")
    unit = tracking.get("unit")
    current_candidates = [c for c in (tracking.get("candidates", []) or []) if isinstance(c, dict)]

    base = {
        "status": "none",
        "timestamp": timestamp,
        "product": product,
        "unit": unit,
        "reference": "Giammoro, Pace del Mela (ME)",
        "observed_cells": len(current_candidates),
        "matched_cells": 0,
        "count": 0,
        "dominant_from": None,
        "dominant_from_label": None,
        "cells": [],
    }

    if tracking.get("status") != "detected" or not current_candidates:
        base["summary"] = "Nessuna cella radar significativa rilevata nell'area di monitoraggio."
        return base

    previous_candidates = [c for c in (previous_tracking.get("candidates", []) or []) if isinstance(c, dict)]
    current_time = _parse_iso(timestamp)
    previous_time = _parse_iso(previous_tracking.get("timestamp"))
    if (
        not previous_candidates
        or current_time is None
        or previous_time is None
        or previous_tracking.get("product") != product
    ):
        base["status"] = "insufficient_history"
        base["summary"] = "Celle radar presenti, ma servono almeno due scansioni coerenti per stabilire la traiettoria di avvicinamento."
        return base

    interval_hours = (current_time - previous_time).total_seconds() / 3600.0
    if interval_hours <= 0.03 or interval_hours > 1.0:
        base["status"] = "insufficient_history"
        base["summary"] = "Celle radar presenti, ma l'intervallo fra le scansioni non consente un confronto affidabile della traiettoria."
        return base

    matches = _match_candidates(previous_candidates, current_candidates, interval_hours)
    base["matched_cells"] = len(matches)
    approaching: list[dict] = []

    for previous, current, assoc in matches:
        points = [
            {"timestamp": previous_tracking.get("timestamp"), "lat": previous.get("lat"), "lon": previous.get("lon")},
            {"timestamp": timestamp, "lat": current.get("lat"), "lon": current.get("lon")},
        ]
        motion = v2.regression_motion(points, rlat, rlon)
        if motion.get("status") != "tracked" or not motion.get("approaching"):
            continue

        speed = _num(motion.get("speed_kmh"))
        approach_rate = _num(motion.get("approach_rate_kmh"))
        if speed is None or approach_rate is None or approach_rate <= 3:
            continue

        current_distance = _num(current.get("distance_km"))
        if current_distance is None:
            current_distance = v2.haversine_km(rlat, rlon, float(current["lat"]), float(current["lon"]))
        previous_distance = _num(previous.get("distance_km"))
        if previous_distance is None:
            previous_distance = v2.haversine_km(rlat, rlon, float(previous["lat"]), float(previous["lon"]))

        bearing_deg, from_sector = _candidate_sector(current, rlat, rlon)
        motion_deg = _num(motion.get("direction_deg"))
        target_heading = v2.bearing_deg(float(current["lat"]), float(current["lon"]), rlat, rlon)
        heading_error = _angular_difference(motion_deg, target_heading)
        closest_km = _num(motion.get("closest_approach_km"))
        direction = str(motion.get("direction") or v2.compass(motion_deg) or "") or None
        peak = _num(current.get("peak_value"))

        cell = {
            "approach_from": from_sector,
            "approach_from_label": _sector_label(from_sector),
            "bearing_deg": None if bearing_deg is None else round(bearing_deg, 1),
            "distance_km": round(current_distance, 1),
            "previous_distance_km": round(previous_distance, 1),
            "distance_change_km": round(current_distance - previous_distance, 1),
            "lat": current.get("lat"),
            "lon": current.get("lon"),
            "peak_value": None if peak is None else round(peak, 2),
            "pixels": current.get("pixels"),
            "movement_toward": direction,
            "movement_toward_label": _sector_label(direction),
            "movement_direction_deg": None if motion_deg is None else round(motion_deg, 1),
            "speed_kmh": round(speed, 1),
            "approach_rate_kmh": round(approach_rate, 1),
            "closest_approach_km": None if closest_km is None else round(closest_km, 1),
            "closest_approach_minutes": motion.get("closest_approach_minutes"),
            "eta_minutes": motion.get("eta_minutes"),
            "heading_error_deg": None if heading_error is None else round(heading_error, 1),
            "approach_class": _approach_class(closest_km),
            "confidence": _confidence(_num(assoc.get("score")), heading_error),
            "association": assoc,
        }
        approaching.append(cell)

    approaching.sort(
        key=lambda c: (
            c.get("closest_approach_km") if c.get("closest_approach_km") is not None else 999.0,
            c.get("distance_km") if c.get("distance_km") is not None else 999.0,
            -(c.get("peak_value") or 0.0),
        )
    )
    approaching = approaching[:MAX_OUTPUT_CELLS]
    base["cells"] = approaching
    base["count"] = len(approaching)

    if not approaching:
        base["summary"] = "Nessuna delle celle radar associate fra le ultime scansioni risulta in avvicinamento verso Giammoro."
        return base

    main = approaching[0]
    base["status"] = "detected"
    base["dominant_from"] = main.get("approach_from")
    base["dominant_from_label"] = main.get("approach_from_label")
    from_text = main.get("approach_from_label") or main.get("approach_from") or "direzione non definita"
    toward_text = main.get("movement_toward_label") or main.get("movement_toward") or "direzione non definita"
    closest = main.get("closest_approach_km")
    closest_text = f"; minima distanza proiettata ~{closest:.1f} km" if closest is not None else ""
    eta = main.get("eta_minutes")
    eta_text = f"; ingresso entro 5 km stimato in ~{eta} min" if eta is not None else ""
    base["summary"] = (
        f"{len(approaching)} cella/e radar in avvicinamento: la più rilevante arriva da {from_text}, "
        f"si muove verso {toward_text} a ~{main['speed_kmh']:.1f} km/h, ora a ~{main['distance_km']:.1f} km"
        f"{closest_text}{eta_text}."
    )
    return base


def update(data: dict, previous_data: dict, rlat: float, rlon: float) -> dict:
    monitor = build_monitor(data, previous_data, rlat, rlon)
    data["approaching_cells"] = monitor
    data.setdefault("nowcast_evidence", {})["approaching_cells"] = monitor.get("summary")
    return monitor
