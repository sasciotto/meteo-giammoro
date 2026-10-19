#!/usr/bin/env python3
"""Monitor multi-cella delle traiettorie radar in avvicinamento verso Giammoro."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

import nowcast_v2 as v2

MAX_ASSOCIATION_SPEED_KMH = 120.0
MAX_ASSOCIATION_DISTANCE_KM = 32.0
MAX_OUTPUT_CELLS = 4
MAIN_TRACK_MATCH_KM = 2.5
SECONDARY_DIRECTION_TOLERANCE_DEG = 45.0
RADAR_EVENT_TTL_MINUTES = 45

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

RADAR_APPROACH_TITLE = "Nucleo radar in avvicinamento verso Giammoro"
RADAR_RESOLVED_TITLE = "Cella radar non più in avvicinamento verso Giammoro"
RADAR_UNCONFIRMED_TITLE = "Traiettoria radar verso Giammoro non confermata"


def _num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except (TypeError, ValueError):
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


def _position_distance_km(a: dict, b: dict) -> float | None:
    alat = _num((a or {}).get("lat"))
    alon = _num((a or {}).get("lon"))
    blat = _num((b or {}).get("lat"))
    blon = _num((b or {}).get("lon"))
    if None in {alat, alon, blat, blon}:
        return None
    return v2.haversine_km(alat, alon, blat, blon)


def _same_cell(a: dict, b: dict, max_km: float = MAIN_TRACK_MATCH_KM) -> bool:
    distance = _position_distance_km(a, b)
    return distance is not None and distance <= max_km


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


def _main_track_for_candidate(tracking: dict, current: dict) -> tuple[dict | None, dict]:
    tracked = tracking.get("tracked_cell") or tracking.get("cell") or {}
    if not tracked or not _same_cell(current, tracked):
        return None, {}
    return tracking.get("motion", {}) or {}, tracking.get("track_quality", {}) or {}


def _main_track_confidence(motion: dict, quality: dict) -> str:
    status = str(quality.get("status") or "unknown")
    frames = int(_num(motion.get("frames")) or 0)
    if status == "good" and frames >= 3:
        return "high"
    if status in {"good", "degraded"}:
        return "medium"
    return "low"


def _secondary_three_frame_confirmation(previous_data: dict, previous_candidate: dict, current_motion: dict) -> dict | None:
    previous_monitor = previous_data.get("approaching_cells", {}) or {}
    for old in previous_monitor.get("cells", []) or []:
        if not isinstance(old, dict) or not _same_cell(old, previous_candidate):
            continue
        old_rate = _num(old.get("approach_rate_kmh"))
        old_direction = _num(old.get("movement_direction_deg"))
        current_direction = _num(current_motion.get("direction_deg"))
        direction_error = _angular_difference(old_direction, current_direction)
        if old_rate is None or old_rate <= 3:
            continue
        if old_direction is None or current_direction is None or direction_error is None:
            continue
        if direction_error > SECONDARY_DIRECTION_TOLERANCE_DEG:
            continue
        if str(old.get("confidence") or "low") == "low":
            continue
        return old
    return None


def _unconfirmed_cell(current: dict, motion: dict, rlat: float, rlon: float) -> dict:
    bearing_deg, sector = _candidate_sector(current, rlat, rlon)
    distance = _num(current.get("distance_km"))
    return {
        "approach_from": sector,
        "approach_from_label": _sector_label(sector),
        "bearing_deg": None if bearing_deg is None else round(bearing_deg, 1),
        "distance_km": None if distance is None else round(distance, 1),
        "movement_toward": motion.get("direction"),
        "movement_direction_deg": _num(motion.get("direction_deg")),
        "reason": "servono tre scansioni coerenti per confermare una cella secondaria",
    }


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
        "unconfirmed_count": 0,
        "suppressed_by_main_track": 0,
        "dominant_from": None,
        "dominant_from_label": None,
        "cells": [],
        "unconfirmed_cells": [],
        "policy": "track principale multi-frame autoritativo; celle secondarie confermate solo dopo tre scansioni coerenti",
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
        base["summary"] = "Celle radar presenti, ma servono scansioni coerenti successive per stabilire una traiettoria affidabile."
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
        pair_motion = v2.regression_motion(points, rlat, rlon)
        main_motion, track_quality = _main_track_for_candidate(tracking, current)

        trajectory_source = "secondary_three_frame_confirmation"
        confirmed_frames = 3
        motion = pair_motion
        cell_confidence = None
        association = assoc

        if main_motion is not None:
            trajectory_source = "main_track_multi_frame"
            motion = main_motion
            confirmed_frames = int(_num(main_motion.get("frames")) or len(tracking.get("track_history", []) or []) or 2)
            association = tracking.get("association", {}) or assoc
            quality_status = str(track_quality.get("status") or "")
            if motion.get("status") != "tracked" or quality_status == "suspect" or not motion.get("approaching"):
                if pair_motion.get("status") == "tracked" and pair_motion.get("approaching"):
                    base["suppressed_by_main_track"] += 1
                continue
            cell_confidence = _main_track_confidence(motion, track_quality)
        else:
            if pair_motion.get("status") != "tracked" or not pair_motion.get("approaching"):
                continue
            prior = _secondary_three_frame_confirmation(previous_data, previous, pair_motion)
            if prior is None:
                base["unconfirmed_count"] += 1
                base["unconfirmed_cells"].append(_unconfirmed_cell(current, pair_motion, rlat, rlon))
                continue
            current_confidence = _confidence(_num(assoc.get("score")), None)
            prior_confidence = str(prior.get("confidence") or "low")
            cell_confidence = "high" if current_confidence == "high" and prior_confidence == "high" else "medium"

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

        if cell_confidence is None:
            cell_confidence = _confidence(_num(association.get("score")), heading_error)

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
            "confidence": cell_confidence,
            "association": association,
            "trajectory_source": trajectory_source,
            "confirmed_frames": confirmed_frames,
            "track_id": tracking.get("track_id") if trajectory_source == "main_track_multi_frame" else None,
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
        if base["unconfirmed_count"]:
            base["status"] = "unconfirmed"
            base["summary"] = (
                f"{base['unconfirmed_count']} possibile/i cella/e in avvicinamento rilevata/e, "
                "ma la traiettoria non è ancora confermata su tre scansioni coerenti."
            )
        elif base["suppressed_by_main_track"]:
            base["summary"] = (
                "Il confronto fra due scansioni suggeriva un avvicinamento, ma il tracking multi-frame "
                "principale non lo conferma; prevale la traiettoria multi-frame."
            )
        else:
            base["summary"] = "Nessuna delle celle radar confermate risulta in avvicinamento verso Giammoro."
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
        f"{len(approaching)} cella/e radar confermata/e in avvicinamento: la più rilevante arriva da {from_text}, "
        f"si muove verso {toward_text} a ~{main['speed_kmh']:.1f} km/h, ora a ~{main['distance_km']:.1f} km"
        f"{closest_text}{eta_text}."
    )
    return base


def _change_start(change: dict, now: datetime | None) -> datetime | None:
    first_seen = _parse_iso(change.get("first_seen"))
    if first_seen is not None:
        return first_seen
    raw = str(change.get("time") or "")
    try:
        parsed = datetime.strptime(raw, "%d/%m/%Y %H:%M")
    except ValueError:
        return now
    if now is not None and now.tzinfo is not None:
        parsed = parsed.replace(tzinfo=now.tzinfo)
    return parsed


def _radar_state(data: dict) -> str:
    tracking = data.get("nowcast_tracking", {}) or {}
    motion = tracking.get("motion", {}) or {}
    quality = tracking.get("track_quality", {}) or {}
    if quality.get("status") == "suspect" or motion.get("status") == "suspect_association":
        return "unconfirmed"
    if tracking.get("status") != "detected" or motion.get("status") != "tracked":
        return "unavailable"
    return "approaching" if bool(motion.get("approaching")) else "not_approaching"


def _event_id(change: dict, tracking: dict, first_seen: datetime | None) -> str:
    existing = str(change.get("event_id") or "")
    if existing:
        return existing
    track_id = str(change.get("track_id") or tracking.get("track_id") or "radar")
    stamp = first_seen.strftime("%Y%m%dT%H%M") if first_seen is not None else "unknown"
    return f"radar-approach:{track_id}:{stamp}"


def _prepend_history(data: dict, title: str, now: datetime | None) -> None:
    if not title:
        return
    display = now.strftime("%d/%m/%Y %H:%M") if now is not None else str((data.get("meta", {}) or {}).get("last_check") or "—")
    history = [item for item in (data.get("history", []) or []) if isinstance(item, dict)]
    if history and str(history[0].get("text") or "") == title:
        return
    data["history"] = ([{"time": display, "text": title}] + history)[:50]


def _current_motion_evidence(data: dict) -> str:
    tracking = data.get("nowcast_tracking", {}) or {}
    motion = tracking.get("motion", {}) or {}
    cell = tracking.get("tracked_cell") or tracking.get("cell") or {}
    parts = [f"track {tracking.get('track_id') or 'n/d'}"]
    if cell.get("distance_km") is not None:
        parts.append(f"distanza {cell.get('distance_km')} km")
    if motion.get("direction"):
        parts.append(f"direzione {motion.get('direction')}")
    if motion.get("speed_kmh") is not None:
        parts.append(f"velocità {motion.get('speed_kmh')} km/h")
    if motion.get("approach_rate_kmh") is not None:
        parts.append(f"tasso avvicinamento {motion.get('approach_rate_kmh')} km/h")
    return "; ".join(parts) + "."


def sync_latest_radar_change(data: dict, previous_data: dict | None = None) -> None:
    previous_data = previous_data or {}
    change = data.get("latest_change", {}) or {}
    title = str(change.get("title") or "")
    managed_titles = {RADAR_APPROACH_TITLE, RADAR_RESOLVED_TITLE, RADAR_UNCONFIRMED_TITLE}
    if title not in managed_titles:
        return

    now = _parse_iso((data.get("meta", {}) or {}).get("last_check_iso"))
    tracking = data.get("nowcast_tracking", {}) or {}
    state = _radar_state(data)
    first_seen = _change_start(change, now)
    event_id = _event_id(change, tracking, first_seen)
    track_id = change.get("track_id") or tracking.get("track_id")
    confidence = str((data.get("analysis_confidence", {}) or {}).get("label") or change.get("confidence") or "—").lower()

    if title == RADAR_APPROACH_TITLE and state == "approaching":
        change["event_type"] = "radar_approach"
        change["event_id"] = event_id
        change["status"] = "active"
        change["track_id"] = track_id
        change["first_seen"] = first_seen.isoformat(timespec="seconds") if first_seen is not None else None
        change["last_seen"] = now.isoformat(timespec="seconds") if now is not None else None
        change["valid_until"] = (
            (now + timedelta(minutes=RADAR_EVENT_TTL_MINUTES)).isoformat(timespec="seconds")
            if now is not None else None
        )
        data["latest_change"] = change
        return

    if title != RADAR_APPROACH_TITLE:
        return

    if state == "not_approaching":
        resolved_title = RADAR_RESOLVED_TITLE
        status = "resolved"
        text = "Il tracking multi-frame corrente non indica più una traiettoria di avvicinamento verso Giammoro."
    elif state == "unconfirmed":
        resolved_title = RADAR_UNCONFIRMED_TITLE
        status = "unconfirmed"
        text = "La traiettoria di avvicinamento non è confermata perché la qualità dell'associazione radar corrente è insufficiente."
    else:
        resolved_title = RADAR_UNCONFIRMED_TITLE
        status = "pending_confirmation"
        text = "Il ciclo radar corrente non consente di confermare l'avvicinamento indicato in precedenza."

    previous_last_seen = _parse_iso(
        ((previous_data.get("latest_change", {}) or {}).get("last_seen"))
        or ((previous_data.get("meta", {}) or {}).get("last_check_iso"))
    )
    resolved = {
        "time": now.strftime("%d/%m/%Y %H:%M") if now is not None else change.get("time"),
        "title": resolved_title,
        "text": text,
        "window": "situazione corrente",
        "confidence": confidence,
        "evidence": _current_motion_evidence(data),
        "event_type": "radar_approach",
        "event_id": event_id,
        "status": status,
        "track_id": track_id,
        "first_seen": first_seen.isoformat(timespec="seconds") if first_seen is not None else None,
        "last_seen": (
            previous_last_seen.isoformat(timespec="seconds")
            if previous_last_seen is not None
            else (first_seen.isoformat(timespec="seconds") if first_seen is not None else None)
        ),
        "resolved_at": now.isoformat(timespec="seconds") if state == "not_approaching" and now is not None else None,
        "valid_until": (
            (now + timedelta(minutes=RADAR_EVENT_TTL_MINUTES)).isoformat(timespec="seconds")
            if status == "pending_confirmation" and now is not None else None
        ),
    }
    data["latest_change"] = resolved
    _prepend_history(data, resolved_title, now)


def update(data: dict, previous_data: dict, rlat: float, rlon: float) -> dict:
    monitor = build_monitor(data, previous_data, rlat, rlon)
    data["approaching_cells"] = monitor
    data.setdefault("nowcast_evidence", {})["approaching_cells"] = monitor.get("summary")
    sync_latest_radar_change(data, previous_data)
    return monitor
