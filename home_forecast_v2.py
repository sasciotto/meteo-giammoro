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

    # Il 3–48 h descrive una tendenza, non un rischio operativo: separa
    # probabilità di pioggia, incertezza quantitativa e impatto modellistico.
    model_outlook.apply(data)
    return data
