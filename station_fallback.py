"""Fallback prudente per le stazioni quando il feed live non è disponibile."""
from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta
from typing import Any


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def _observation_time(station: dict, previous_check: datetime | None) -> datetime | None:
    explicit = _parse_iso(
        station.get("last_valid_observation_iso")
        or station.get("last_valid_cycle_iso")
    )
    if explicit is not None:
        if explicit.tzinfo is None and previous_check is not None and previous_check.tzinfo is not None:
            explicit = explicit.replace(tzinfo=previous_check.tzinfo)
        return explicit

    if previous_check is None:
        return None
    match = re.match(r"^\s*(\d{1,2}):(\d{2})\b", str(station.get("updated") or ""))
    if not match:
        return previous_check
    hour, minute = map(int, match.groups())
    try:
        observed = previous_check.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return previous_check
    if observed > previous_check + timedelta(minutes=10):
        observed -= timedelta(days=1)
    return observed


def previous_cycle_stations(previous: dict, now: datetime, reason: str | None = None) -> list[dict]:
    """Conserva l'ultimo valore noto solo per consultazione, mai come osservazione corrente."""
    previous_check_raw = (previous.get("meta", {}) or {}).get("last_check_iso")
    previous_check = _parse_iso(previous_check_raw)
    if previous_check is not None and previous_check.tzinfo is None and now.tzinfo is not None:
        previous_check = previous_check.replace(tzinfo=now.tzinfo)

    out: list[dict] = []
    for station in previous.get("stations", []) or []:
        if not isinstance(station, dict):
            continue
        item = copy.deepcopy(station)
        is_primary = item.get("name") == "MeteoGiammoro" or item.get("source_quality") == "primary"
        if is_primary:
            item["status"] = "maintenance"
            item["status_label"] = "Manutenzione / test"
            item["updated"] = "esclusa"
            item["excluded_from_analysis"] = True
            out.append(item)
            continue

        last_valid = _observation_time(item, previous_check)
        if last_valid is not None and last_valid.tzinfo is None and now.tzinfo is not None:
            last_valid = last_valid.replace(tzinfo=now.tzinfo)
        age_minutes = None
        if last_valid is not None:
            try:
                age_minutes = max(0, int((now - last_valid.astimezone(now.tzinfo)).total_seconds() / 60))
            except (TypeError, ValueError):
                age_minutes = None

        item["status"] = "unknown"
        item["status_label"] = "Dato precedente · feed non disponibile"
        item["excluded_from_analysis"] = True
        item["data_freshness"] = "previous_cycle"
        item.pop("last_valid_cycle_iso", None)
        item["last_valid_observation_iso"] = last_valid.isoformat(timespec="seconds") if last_valid else None
        item["fallback_age_minutes"] = age_minutes
        item["updated"] = (
            f"ultimo dato noto · {age_minutes} min fa"
            if age_minutes is not None
            else "ultimo dato noto · età non disponibile"
        )
        original_note = str(item.get("note") or "").strip()
        repeated_note = "Feed stazioni non disponibile nel ciclo corrente: ultimo dato noto conservato solo per riferimento ed escluso dall'analisi."
        # Evita di accodare la stessa nota a ogni ciclo consecutivo di fallback.
        if repeated_note in original_note:
            note = original_note
        else:
            note = f"{original_note} {repeated_note}".strip()
        if reason:
            item["fallback_reason"] = reason
        item["note"] = note
        out.append(item)
    return out


def metadata(reason: str, now: datetime) -> dict[str, Any]:
    return {
        "source": "fallback ultimo dato noto",
        "rows": 0,
        "status": "degraded",
        "fallback": True,
        "reason": reason,
        "checked_at": now.isoformat(timespec="seconds"),
    }
