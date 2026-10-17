#!/usr/bin/env python3
"""Sintesi home v2: fallback all'ultima previsione valida e condizioni conservative."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

import home_forecast as base

STALE_MAX_MINUTES = 360


def _parse_dt(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


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
        "hourly": base.hourly_forecast(raw or {}, now),
        "days": days,
        "multi_model": base.multi_model_consensus(data),
        "forecast_available": bool(raw),
        "stale": False,
    }


def _fallback_home(previous: dict | None, data: dict, now: datetime) -> dict | None:
    old = copy.deepcopy((previous or {}).get("home_summary") or {})
    if not old.get("forecast_available"):
        return None
    generated = _parse_dt(old.get("generated_at"))
    if not generated:
        return None
    if generated.tzinfo is None and now.tzinfo is not None:
        generated = generated.replace(tzinfo=now.tzinfo)
    try:
        age = max(0, int((now - generated).total_seconds() / 60))
    except TypeError:
        return None
    if age > STALE_MAX_MINUTES:
        return None

    old["current"] = current_summary(data, now)
    old["stale"] = True
    old["stale_age_minutes"] = age
    old["stale_reason"] = "fonte modellistica temporaneamente non disponibile"
    old["served_at"] = now.isoformat(timespec="seconds")
    old["forecast_available"] = True
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
    return data
