"""Storico prudente delle letture di pioggia delle stazioni vicine.

I cumulati giornalieri sono osservazioni *delle stazioni*, mai di Giammoro.
Nessuna differenza viene stimata se mancano i campioni del periodo, se
l'orario della stazione non avanza o se il cumulato si azzera.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")
KEEP_HOURS = 48
MAX_SAMPLE_AGE_MINUTES = 60
MAX_GAP_MINUTES = 25
TARGET_TOLERANCE_MINUTES = 8
WINDOWS = (15, 30, 60)


def _num(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def _time(value):
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.astimezone(TZ) if dt.tzinfo else dt.replace(tzinfo=TZ)
    except (ValueError, TypeError):
        return None


def _actual_time(station: dict, now: datetime):
    # No inferred timestamp based only on the collector cycle; source HH:MM
    # must be present and not more than 10 min in the future.
    label = str(station.get("updated") or "")
    match = re.match(r"^\s*(\d{1,2}):(\d{2})\b", label)
    if not match:
        return None
    hh, mm = map(int, match.groups())
    if hh > 23 or mm > 59:
        return None
    stamp = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if stamp > now + timedelta(minutes=10):
        stamp -= timedelta(days=1)
    age = (now - stamp).total_seconds() / 60
    return stamp if -10 <= age <= MAX_SAMPLE_AGE_MINUTES else None


def _identity(station: dict):
    # Explicit original station name: no label substitution, even if grouped.
    name = str(station.get("name") or "").strip()
    if not name or name == "MeteoGiammoro" or station.get("source_quality") == "primary":
        return None
    return name


def _valid_station(station: dict):
    if station.get("status") != "online" or station.get("excluded_from_analysis"):
        return False
    if station.get("data_freshness") == "previous_cycle":
        return False
    return _identity(station) is not None


def _interval(rows: list[dict], current: dict, minutes: int):
    """Return an observed increment only for full, same-day, dense coverage."""
    current_time = _time(current["at"])
    if current_time is None:
        return None
    beginning = current_time - timedelta(minutes=minutes)
    if beginning.date() != current_time.date():
        return None
    todays = sorted(
        (r for r in rows if _time(r.get("at")) is not None
         and _time(r["at"]).date() == current_time.date()
         and _time(r["at"]) <= current_time),
        key=lambda row: row["at"],
    )
    if len(todays) < 2:
        return None
    anchors = [
        row for row in todays[:-1]
        if abs((_time(row["at"]) - beginning).total_seconds()) <= TARGET_TOLERANCE_MINUTES * 60
    ]
    if not anchors:
        return None
    start = min(anchors, key=lambda row: abs((_time(row["at"]) - beginning).total_seconds()))
    segment = [row for row in todays if _time(row["at"]) >= _time(start["at"])]
    if len(segment) < 2:
        return None
    times = [_time(row["at"]) for row in segment]
    if any((b - a).total_seconds() > MAX_GAP_MINUTES * 60 for a, b in zip(times, times[1:])):
        return None
    amounts = [_num(row.get("rain_day_mm")) for row in segment]
    if any(a is None for a in amounts):
        return None
    if any(b + 1e-6 < a for a, b in zip(amounts, amounts[1:])):
        return None
    return round(max(0.0, amounts[-1] - amounts[0]), 2)


def update(data: dict, previous: dict | None = None):
    meta = data.get("meta") or {}
    now = _time(meta.get("last_check_iso"))
    if now is None:
        # collector.py fills human-readable last_check before runtime_quality.py
        # adds last_check_iso. Parse that actual cycle timestamp rather than
        # using the runner clock or inventing a station observation.
        match = re.match(r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2})\b", str(meta.get("last_check") or ""))
        if match:
            try:
                now = datetime.strptime(match.group(1), "%d/%m/%Y %H:%M").replace(tzinfo=TZ)
            except ValueError:
                now = None
    if now is None:
        raise ValueError("data.json missing a valid collector timestamp")
    previous = previous or {}
    prev = (previous.get("stations") or {})
    if not isinstance(prev, dict):
        prev = {}
    output = {}
    for station in data.get("stations") or []:
        if not isinstance(station, dict):
            continue
        station["rain_15m"] = None
        station["rain_30m"] = None
        station["rain_1h"] = None
        name = _identity(station)
        if name is None:
            continue
        last = prev.get(name) or []
        rows = {}
        for reading in last if isinstance(last, list) else []:
            if not isinstance(reading, dict):
                continue
            stamp = _time(reading.get("at"))
            amount = _num(reading.get("rain_day_mm"))
            if stamp and amount is not None and timedelta(0) <= now - stamp <= timedelta(hours=KEEP_HOURS):
                rows[stamp.isoformat(timespec="minutes")] = {
                    "at": stamp.isoformat(timespec="minutes"), "rain_day_mm": amount,
                }
        stamp = _actual_time(station, now) if _valid_station(station) else None
        amount = _num(station.get("rain_day"))
        is_new = False
        if stamp is not None and amount is not None:
            key = stamp.isoformat(timespec="minutes")
            if key in rows and rows[key]["rain_day_mm"] != amount:
                # A revised value for the same observation invalidates
                # that observation instead of inventing a new time step.
                rows.pop(key)
            elif key not in rows:
                rows[key] = {"at": key, "rain_day_mm": amount}
                is_new = True
        ordered = [rows[key] for key in sorted(rows)]
        output[name] = ordered
        if stamp is None or amount is None or not is_new:
            continue
        current = rows.get(stamp.isoformat(timespec="minutes"))
        if not current:
            continue
        for minutes, field in ((15, "rain_15m"), (30, "rain_30m"), (60, "rain_1h")):
            station[field] = _interval(ordered, current, minutes)

    valid_count = sum(
        1 for station in data.get("stations") or []
        if station.get("rain_1h") is not None
    )
    data["nearby_station_rain"] = {
        "source": "CMS - cumulati giornalieri delle singole stazioni",
        "updated_at": now.isoformat(timespec="seconds"),
        "window_minutes": list(WINDOWS),
        "stations_with_valid_1h": valid_count,
        "note": (
            "Differenze osservate fra letture con orario valido della stessa stazione. "
            "Nessuna misura equivale a pioggia osservata su Giammoro; "
            "intervalli mancanti, stazioni obsolete e azzeramenti restano non verificabili."
        ),
    }
    return data, {"schema_version": "1.0", "updated_at": now.isoformat(timespec="seconds"), "stations": output}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data.json")
    parser.add_argument("--history", default="station_rain_history.json")
    args = parser.parse_args()
    data_path = Path(args.data)
    hist_path = Path(args.history)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else {}
    current, next_hist = update(data, hist)
    data_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hist_path.write_text(json.dumps(next_hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Campioni stazioni:", len(next_hist["stations"]), "intervalli 1h validi:",
          current["nearby_station_rain"]["stations_with_valid_1h"])


if __name__ == "__main__":
    main()
