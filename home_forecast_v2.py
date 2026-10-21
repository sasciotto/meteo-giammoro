#!/usr/bin/env python3
"""Sintesi home v2: fallback all'ultima previsione valida e condizioni conservative."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

import home_forecast as base
import model_outlook

STALE_MAX_MINUTES = 360


def _parse_dt(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def _local_dt(value: str | None, now: datetime) -> datetime | None:
    dt = _parse_dt(value)
    if dt is None:
        return None
    if dt.tzinfo is None and now.tzinfo is not None:
        dt = dt.replace(tzinfo=now.tzinfo)
    elif dt.tzinfo is not None and now.tzinfo is not None:
        dt = dt.astimezone(now.tzinfo)
    return dt


def _lightning_count(data: dict, radius: int) -> int | None:
    lightning = data.get("lightning", {}) or {}
    if lightning.get("status") != "ok":
        return None
    item = (lightning.get("radii", {}) or {}).get(str(radius), {}) or {}
    value = item.get("flash_count", item.get("frequency_sum"))
    number = base.num(value)
    return int(number) if number is not None else 0


def _nearest_radar_km(data: dict) -> float | None:
    tracking = data.get("nowcast_tracking", {}) or {}
    distances: list[float] = []
    for candidate in tracking.get("candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        distance = base.num(candidate.get("distance_km"))
        if distance is not None:
            distances.append(distance)
    if not distances:
        for key in ("hazard_cell", "tracked_cell", "cell"):
            distance = base.num((tracking.get(key, {}) or {}).get("distance_km"))
            if distance is not None:
                distances.append(distance)
                break
    return min(distances) if distances else None


def _trajectory_reliable(data: dict) -> bool:
    reliability = data.get("trajectory_reliability", {}) or {}
    score = base.num(reliability.get("score"))
    if score is not None:
        return score >= 65

    tracking = data.get("nowcast_tracking", {}) or {}
    motion = tracking.get("motion", {}) or {}
    quality = tracking.get("track_quality", {}) or {}
    frames = int(base.num(motion.get("frames")) or 0)
    return quality.get("status") == "good" and frames >= 3


def _incoming_within_three_hours(data: dict) -> bool:
    """Ritorna True solo con una traiettoria confermata e un passaggio locale entro 3 ore."""
    tracking = data.get("nowcast_tracking", {}) or {}
    motion = tracking.get("motion", {}) or {}
    if (
        motion.get("status") == "tracked"
        and motion.get("approaching")
        and _trajectory_reliable(data)
    ):
        eta = base.num(motion.get("eta_minutes"))
        closest = base.num(motion.get("closest_approach_km"))
        closest_minutes = base.num(motion.get("closest_approach_minutes"))
        if eta is not None and 0 <= eta <= 180:
            return True
        if (
            closest is not None
            and closest <= 15
            and closest_minutes is not None
            and 0 <= closest_minutes <= 180
        ):
            return True

    for cell in (data.get("approaching_cells", {}) or {}).get("cells", []) or []:
        if not isinstance(cell, dict) or str(cell.get("confidence") or "").lower() not in {"medium", "high"}:
            continue
        eta = base.num(cell.get("eta_minutes"))
        closest = base.num(cell.get("closest_approach_km"))
        closest_minutes = base.num(cell.get("closest_approach_minutes"))
        if eta is not None and 0 <= eta <= 180:
            return True
        if (
            closest is not None
            and closest <= 15
            and closest_minutes is not None
            and 0 <= closest_minutes <= 180
        ):
            return True
    return False


def simple_nowcast(data: dict) -> dict[str, Any]:
    """Traduce il nowcasting tecnico 0–3 h in quattro stati leggibili dalla home."""
    tracking = data.get("nowcast_tracking", {}) or {}
    lightning = data.get("lightning", {}) or {}
    metrics = ((data.get("territory", {}) or {}).get("metrics", {}) or {})

    radar_age = base.num(tracking.get("age_minutes"))
    radar_fresh = tracking.get("status") in {"detected", "no_cell"} and radar_age is not None and radar_age <= 40
    lightning_age = base.num(lightning.get("age_minutes"))
    lightning_fresh = lightning.get("status") == "ok" and lightning_age is not None and lightning_age <= 35
    rain_1h = base.num((metrics.get("rain_1h", {}) or {}).get("value"))
    rain_available = rain_1h is not None

    nearest_radar = _nearest_radar_km(data) if radar_fresh else None
    flashes20 = _lightning_count(data, 20) if lightning_fresh else None
    flashes30 = _lightning_count(data, 30) if lightning_fresh else None
    technical_level = str((data.get("nowcast", {}) or {}).get("level") or "").lower()

    detail = None
    if nearest_radar is not None and nearest_radar <= 30:
        detail = f"Segnale radar più vicino: circa {nearest_radar:.0f} km."
    elif flashes20 is not None and flashes20 > 0:
        detail = "Fulmini rilevati entro 20 km."
    elif flashes30 is not None and flashes30 > 0:
        detail = "Fulmini rilevati entro 30 km."

    if (
        (rain_available and rain_1h >= 0.5)
        or (nearest_radar is not None and nearest_radar <= 15)
        or (flashes20 is not None and flashes20 > 0)
    ):
        if rain_available and rain_1h >= 0.5:
            text = "Pioggia è già rilevata nell'area di Giammoro. Segui l'evoluzione nelle prossime ore."
        elif flashes20 is not None and flashes20 > 0:
            text = "Attività temporalesca è molto vicina a Giammoro. Segui l'evoluzione nelle prossime ore."
        else:
            text = "Piogge o temporali sono molto vicini a Giammoro. Segui l'evoluzione nelle prossime ore."
        return {
            "window": "0–3 h",
            "status": "active",
            "title": "Fenomeni vicini o in corso",
            "text": text,
            "detail": detail,
            "nearest_signal_km": round(nearest_radar, 1) if nearest_radar is not None and nearest_radar <= 30 else None,
        }

    if _incoming_within_three_hours(data):
        return {
            "window": "0–3 h",
            "status": "incoming",
            "title": "Possibili fenomeni in arrivo",
            "text": "Una zona di pioggia o temporale potrebbe avvicinarsi a Giammoro nelle prossime 3 ore.",
            "detail": detail,
            "nearest_signal_km": round(nearest_radar, 1) if nearest_radar is not None and nearest_radar <= 30 else None,
        }

    nearby = bool(
        (nearest_radar is not None and nearest_radar <= 30)
        or (flashes30 is not None and flashes30 > 0)
        or technical_level not in {"", "low", "basso"}
    )
    if nearby:
        candidates = [c for c in tracking.get("candidates", []) or [] if isinstance(c, dict)]
        motion = tracking.get("motion", {}) or {}
        single_moving_away = (
            len(candidates) == 1
            and motion.get("status") == "tracked"
            and motion.get("approaching") is False
        )
        text = (
            "Piogge o temporali sono presenti nei dintorni, ma al momento non risultano diretti verso Giammoro."
            if single_moving_away
            else "Piogge o temporali sono presenti nei dintorni. Al momento non è confermato un arrivo su Giammoro."
        )
        return {
            "window": "0–3 h",
            "status": "watch",
            "title": "Da monitorare",
            "text": text,
            "detail": detail,
            "nearest_signal_km": round(nearest_radar, 1) if nearest_radar is not None and nearest_radar <= 30 else None,
        }

    if not radar_fresh and not lightning_fresh:
        return {
            "window": "0–3 h",
            "status": "watch",
            "title": "Da monitorare",
            "text": "I principali dati osservativi sono temporaneamente incompleti. La situazione resta da monitorare.",
            "detail": None,
            "nearest_signal_km": None,
        }

    if radar_fresh and lightning_fresh:
        text = "Al momento radar e fulmini non mostrano fenomeni rilevanti vicino a Giammoro."
    elif radar_fresh:
        text = "Il radar non mostra fenomeni rilevanti vicino a Giammoro; i dati sui fulmini sono temporaneamente non disponibili."
    else:
        text = "Non risultano fulmini vicini a Giammoro; i dati radar sono temporaneamente non disponibili."
    return {
        "window": "0–3 h",
        "status": "calm",
        "title": "Tranquillo",
        "text": text,
        "detail": None,
        "nearest_signal_km": None,
    }


def current_summary(data: dict, now: datetime) -> dict[str, Any]:
    """Usa il motore esistente ma non deduce cielo sereno quando la copertura manca."""
    out = base.current_summary(data, now)
    metrics = ((data.get("territory", {}) or {}).get("metrics", {}) or {})
    cloud = base.num((metrics.get("cloud_cover", {}) or {}).get("value"))
    if cloud is None and out.get("kind") == "calm":
        out.update({
            "icon": "◌",
            "kind": "cloudy",
            "label": "Condizioni del cielo temporaneamente non disponibili",
            "condition_available": False,
        })
    else:
        out["condition_available"] = True
    out["description"] = out.get("label") or "Situazione attuale"
    return out


def build(data: dict, raw: dict | None, source_label: str, now: datetime) -> dict[str, Any]:
    current = current_summary(data, now)
    days = base.daily_forecast(raw or {}, now)
    for day in days:
        day["basis"] = source_label
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "source": source_label,
        "current": current,
        "hourly": base.hourly_forecast(raw or {}, now, limit=36),
        "days": days,
        "multi_model": base.multi_model_consensus(data),
        "forecast_available": bool(raw),
        "stale": False,
    }


def _future_hourly(rows: list[dict] | None, now: datetime) -> list[dict]:
    cutoff = now.replace(minute=0, second=0, microsecond=0)
    future: list[dict] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        dt = _local_dt(row.get("time"), now)
        if dt is None or dt < cutoff:
            continue
        item = copy.deepcopy(row)
        item["time"] = dt.isoformat(timespec="minutes")
        item["label_time"] = dt.strftime("%H:%M")
        future.append(item)
    future.sort(key=lambda row: row["time"])
    return future


def _daily_from_hourly(rows: list[dict], now: datetime, source_label: str) -> list[dict]:
    raw_hourly = {
        "time": [],
        "temperature_2m": [],
        "precipitation": [],
        "cloud_cover": [],
        "wind_speed_10m": [],
        "wind_gusts_10m": [],
        "weather_code": [],
    }
    for row in rows:
        raw_hourly["time"].append(row.get("time"))
        raw_hourly["temperature_2m"].append(row.get("temperature"))
        raw_hourly["precipitation"].append(row.get("precipitation"))
        raw_hourly["cloud_cover"].append(row.get("cloud_cover"))
        raw_hourly["wind_speed_10m"].append(row.get("wind_kmh"))
        raw_hourly["wind_gusts_10m"].append(row.get("gust_kmh"))
        raw_hourly["weather_code"].append(row.get("weather_code"))
    days = base.daily_forecast({"hourly": raw_hourly}, now)
    for day in days:
        day["basis"] = source_label
    return days


def _fallback_home(previous: dict | None, data: dict, now: datetime) -> dict | None:
    old = copy.deepcopy((previous or {}).get("home_summary") or {})
    if not old.get("forecast_available"):
        return None
    generated = _local_dt(old.get("generated_at"), now)
    if not generated:
        return None
    try:
        age = max(0, int((now - generated).total_seconds() / 60))
    except TypeError:
        return None
    if age > STALE_MAX_MINUTES:
        return None

    old["current"] = current_summary(data, now)
    old["stale"] = True
    old["stale_age_minutes"] = age
    old["served_at"] = now.isoformat(timespec="seconds")

    future = _future_hourly(old.get("hourly"), now)
    old["hourly"] = future
    old["days"] = _daily_from_hourly(future, now, old.get("source") or "modello precedente")
    if future:
        old["forecast_available"] = True
        old["stale_reason"] = "fonte modellistica temporaneamente non disponibile"
    else:
        old["forecast_available"] = False
        old["stale_reason"] = "previsione precedente esaurita; fonte modellistica temporaneamente non disponibile"
    return old


def apply(data: dict, collector, previous: dict | None = None) -> dict:
    now = collector.now_local()
    raw = None
    source = "ItaliaMeteo ICON-2I"
    error = None
    try:
        label, model_id, days = collector.MODEL_SPECS[0]
        source = label
        raw = collector.fetch_json(collector.OPEN_METEO, collector.model_params(model_id, max(3, days)))
    except Exception as exc:
        error = exc
        meta = data.setdefault("meta", {})
        meta.setdefault("collector_errors", []).append(f"home-forecast: {exc}")
        if meta.get("collector_status") != "offline":
            meta["collector_status"] = "degraded"

    if raw:
        data["home_summary"] = build(data, raw, source, now)
    else:
        fallback = _fallback_home(previous, data, now)
        data["home_summary"] = fallback or build(data, None, source, now)
        if error and fallback:
            data["home_summary"]["fallback_error"] = str(error)

    # Il riepilogo 0–3 h della home viene sempre ricostruito dai dati correnti,
    # anche quando la previsione oraria usa temporaneamente un fallback precedente.
    data["home_summary"]["nowcast_simple"] = simple_nowcast(data)

    # Il 3–48 h descrive una tendenza, non un rischio operativo: separa
    # probabilità di pioggia, incertezza quantitativa e impatto modellistico.
    model_outlook.apply(data)
    return data
