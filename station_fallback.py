"""Fallback prudente per le stazioni quando il feed live non è disponibile."""
from __future__ import annotations

import copy
import json
import re
import subprocess
from datetime import datetime, timedelta
from typing import Any


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def _station_key(station: dict) -> tuple[str, str]:
    return (str(station.get("name") or ""), str(station.get("display_name") or ""))


def _observation_time(station: dict, previous_check: datetime | None, *, allow_legacy_cycle: bool = True) -> datetime | None:
    explicit = _parse_iso(station.get("last_valid_observation_iso"))
    if explicit is None and allow_legacy_cycle:
        explicit = _parse_iso(station.get("last_valid_cycle_iso"))
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


def _reference_observation_times(reference_previous: dict | None) -> dict[tuple[str, str], datetime]:
    if not reference_previous:
        return {}
    check_raw = (reference_previous.get("meta", {}) or {}).get("last_check_iso")
    check = _parse_iso(check_raw)
    out: dict[tuple[str, str], datetime] = {}
    for station in reference_previous.get("stations", []) or []:
        if not isinstance(station, dict):
            continue
        if station.get("data_freshness") == "previous_cycle":
            continue
        observed = _observation_time(station, check, allow_legacy_cycle=False)
        if observed is not None:
            out[_station_key(station)] = observed
    return out


def previous_cycle_stations(
    previous: dict,
    now: datetime,
    reason: str | None = None,
    reference_previous: dict | None = None,
) -> list[dict]:
    """Conserva l'ultimo valore noto solo per consultazione, mai come osservazione corrente.

    ``reference_previous`` può contenere l'ultimo data.json precedente al fallback. Serve
    per migrare in modo corretto i cicli prodotti dalla prima versione del fallback, che
    conservava l'orario del collector invece dell'orario reale dell'osservazione.
    """
    previous_check_raw = (previous.get("meta", {}) or {}).get("last_check_iso")
    previous_check = _parse_iso(previous_check_raw)
    if previous_check is not None and previous_check.tzinfo is None and now.tzinfo is not None:
        previous_check = previous_check.replace(tzinfo=now.tzinfo)

    if reference_previous is None and needs_reference_recovery(previous):
        reference_previous = load_live_reference_from_git()
    reference_times = _reference_observation_times(reference_previous)

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

        last_valid = _parse_iso(item.get("last_valid_observation_iso"))
        if last_valid is None and item.get("data_freshness") == "previous_cycle":
            # Migrazione dalla prima versione: il vecchio last_valid_cycle_iso era
            # l'orario del collector, non quello della stazione. Se possibile usa il
            # vero HH:MM recuperato dall'ultimo data.json non-fallback.
            last_valid = reference_times.get(_station_key(item))
        if last_valid is None:
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
        repeated_note = (
            "Feed stazioni non disponibile nel ciclo corrente: ultimo dato noto conservato solo per riferimento "
            "ed escluso dall'analisi."
        )
        if repeated_note in original_note:
            note = original_note
        else:
            note = f"{original_note} {repeated_note}".strip()
        if reason:
            item["fallback_reason"] = reason
        item["note"] = note
        out.append(item)
    return out


def needs_reference_recovery(previous: dict) -> bool:
    """Indica se sono presenti righe create dal vecchio fallback senza timestamp osservativo."""
    return any(
        isinstance(station, dict)
        and station.get("data_freshness") == "previous_cycle"
        and not station.get("last_valid_observation_iso")
        and bool(station.get("last_valid_cycle_iso"))
        for station in (previous.get("stations", []) or [])
    )


def is_live_reference(data: dict) -> bool:
    """Riconosce un data.json con almeno una vera etichetta HH:MM non-fallback."""
    for station in data.get("stations", []) or []:
        if not isinstance(station, dict) or station.get("data_freshness") == "previous_cycle":
            continue
        if re.match(r"^\s*\d{1,2}:\d{2}\b", str(station.get("updated") or "")):
            return True
    return False


def load_live_reference_from_git(max_commits: int = 24) -> dict:
    """Recupera dall'history Git l'ultimo data.json con stazioni ancora etichettate HH:MM.

    È usato solo per migrare il primo fallback imperfetto; in assenza di Git/history
    restituisce un dizionario vuoto e il chiamante resta comunque in modalità degradata.
    """
    try:
        raw = subprocess.check_output(
            ["git", "rev-list", f"--max-count={max_commits}", "HEAD", "--", "data.json"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return {}

    for sha in [line.strip() for line in raw.splitlines() if line.strip()]:
        try:
            payload = subprocess.check_output(
                ["git", "show", f"{sha}:data.json"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            data = json.loads(payload)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            continue
        if is_live_reference(data):
            return data
    return {}


def metadata(reason: str, now: datetime) -> dict[str, Any]:
    return {
        "source": "fallback ultimo dato noto",
        "rows": 0,
        "status": "degraded",
        "fallback": True,
        "reason": reason,
        "checked_at": now.isoformat(timespec="seconds"),
    }
