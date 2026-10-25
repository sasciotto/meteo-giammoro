#!/usr/bin/env python3
"""Raccoglie eventi sismici INGV per la pagina Eventi di Meteo Giammoro.

Il modulo e' deliberatamente separato da data.json e dalla pipeline meteo.
Non produce previsioni sismiche e non deduce allerte tsunami.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import requests


GIAMMORO_LAT = 38.2018
GIAMMORO_LON = 15.31816
LOCAL_RADIUS_KM = 150.0
REGIONAL_RADIUS_KM = 500.0
DEFAULT_DAYS = 7
MIN_MAGNITUDE = 1.0
INGV_FDSN_URL = "https://webservices.ingv.it/fdsnws/event/1/query"
INGV_PORTAL_URL = "https://terremoti.ingv.it/"
CAT_INGV_URL = "https://cat.ingv.it/"
DPC_EARTHQUAKE_URL = "https://www.protezionecivile.gov.it/it/approfondimento/se-arriva-il-terremoto/"
ROME = ZoneInfo("Europe/Rome")


def _float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _field(row: dict[str, Any], *names: str) -> Any:
    normalized = {str(key).strip().lower(): value for key, value in row.items() if key is not None}
    for name in names:
        key = name.strip().lower()
        if key in normalized:
            return normalized[key]
    return None


def _parse_utc(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def compass_label(degrees: float) -> str:
    labels = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]
    return labels[int((degrees + 11.25) // 22.5) % 16]


def parse_fdsn_text(text: str) -> list[dict[str, Any]]:
    """Converte l'output FDSN ``format=text`` in record normalizzati."""
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return []

    header_index = next((i for i, line in enumerate(lines) if "EventID" in line and "Latitude" in line), None)
    if header_index is None:
        raise ValueError("intestazione FDSN INGV non riconosciuta")

    header = lines[header_index].lstrip("#\ufeff")
    rows = [header] + [line for line in lines[header_index + 1 :] if not line.startswith("#")]
    reader = csv.DictReader(io.StringIO("\n".join(rows)), delimiter="|")
    events: list[dict[str, Any]] = []

    for row in reader:
        lat = _float(_field(row, "Latitude"))
        lon = _float(_field(row, "Longitude"))
        origin = _parse_utc(str(_field(row, "Time") or ""))
        if lat is None or lon is None or origin is None:
            continue

        event_type = str(_field(row, "EventType") or "").strip().lower()
        if event_type and event_type != "earthquake":
            continue

        event_id = str(_field(row, "EventID") or "").strip()
        magnitude = _float(_field(row, "Magnitude"))
        distance = haversine_km(GIAMMORO_LAT, GIAMMORO_LON, lat, lon)
        bearing = bearing_degrees(GIAMMORO_LAT, GIAMMORO_LON, lat, lon)
        local_time = origin.astimezone(ROME)

        events.append(
            {
                "event_id": event_id,
                "time_utc": origin.isoformat(timespec="seconds"),
                "time_local": local_time.isoformat(timespec="seconds"),
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "depth_km": _float(_field(row, "Depth/km", "Depth/Km", "Depth/KM")),
                "magnitude": magnitude,
                "magnitude_type": str(_field(row, "MagType") or "").strip() or None,
                "location": str(_field(row, "EventLocationName") or "").strip() or "Area non specificata",
                "author": str(_field(row, "Author") or "").strip() or None,
                "event_type": event_type or "earthquake",
                "distance_km": round(distance, 1),
                "bearing_deg": round(bearing),
                "direction": compass_label(bearing),
                "source_url": f"https://terremoti.ingv.it/event/{event_id}" if event_id else INGV_PORTAL_URL,
            }
        )

    events.sort(key=lambda item: item["time_utc"], reverse=True)
    return events


def _strongest(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not events:
        return None
    return max(events, key=lambda item: ((_float(item.get("magnitude")) or -999.0), item.get("time_utc") or ""))


def build_payload(events: list[dict[str, Any]], now: datetime, *, days: int = DEFAULT_DAYS) -> dict[str, Any]:
    regional = [event for event in events if (_float(event.get("distance_km")) or 99999) <= REGIONAL_RADIUS_KM]
    local = [event for event in regional if (_float(event.get("distance_km")) or 99999) <= LOCAL_RADIUS_KM]

    return {
        "meta": {
            "schema_version": "1.0",
            "status": "ok",
            "generated_at": now.astimezone(ROME).isoformat(timespec="seconds"),
            "source": "INGV · FDSN Event Web Service",
            "source_url": INGV_FDSN_URL,
            "portal_url": INGV_PORTAL_URL,
            "period_days": int(days),
            "min_magnitude": MIN_MAGNITUDE,
            "query_radius_km": REGIONAL_RADIUS_KM,
            "reference": {
                "name": "Giammoro, Pace del Mela (ME)",
                "latitude": GIAMMORO_LAT,
                "longitude": GIAMMORO_LON,
            },
            "events_count": len(regional),
            "error": None,
        },
        "summary": {
            "local_radius_km": LOCAL_RADIUS_KM,
            "regional_radius_km": REGIONAL_RADIUS_KM,
            "local_count": len(local),
            "regional_count": len(regional),
            "latest_local": local[0] if local else None,
            "strongest_local": _strongest(local),
            "strongest_regional": _strongest(regional),
        },
        "local": local,
        "regional": regional,
        "tsunami": {
            "mode": "official_only",
            "status": "not_evaluated",
            "title": "Maremoti: solo informazioni ufficiali",
            "text": "Meteo Giammoro non calcola il rischio tsunami a partire dai terremoti. Per eventuali messaggi di informazione, allerta, conferma o revoca fanno fede CAT-INGV, Protezione Civile e autorita competenti.",
            "cat_url": CAT_INGV_URL,
        },
        "safety": {
            "title": "In caso di terremoto",
            "text": "Per comportamenti e indicazioni di protezione civile consulta la guida ufficiale.",
            "url": DPC_EARTHQUAKE_URL,
        },
    }


def query_params(now: datetime, *, days: int = DEFAULT_DAYS) -> dict[str, Any]:
    end = now.astimezone(timezone.utc)
    start = end - timedelta(days=days)
    fmt = "%Y-%m-%dT%H:%M:%S"
    return {
        "starttime": start.strftime(fmt),
        "endtime": end.strftime(fmt),
        "latitude": GIAMMORO_LAT,
        "longitude": GIAMMORO_LON,
        "maxradiuskm": int(REGIONAL_RADIUS_KM),
        "minmagnitude": MIN_MAGNITUDE,
        "format": "text",
        "orderby": "time",
        "limit": 500,
    }


def fetch_text(params: dict[str, Any], timeout: int = 30) -> str:
    response = requests.get(
        INGV_FDSN_URL,
        params=params,
        timeout=timeout,
        headers={"User-Agent": "MeteoGiammoro/1.0 seismic-events"},
    )
    if response.status_code == 204:
        return ""
    response.raise_for_status()
    return response.text


def _empty_payload(now: datetime, *, days: int, error: str) -> dict[str, Any]:
    payload = build_payload([], now, days=days)
    payload["meta"]["status"] = "error"
    payload["meta"]["error"] = error
    payload["meta"]["last_attempt"] = now.astimezone(ROME).isoformat(timespec="seconds")
    return payload


def collect(
    output: Path,
    *,
    days: int = DEFAULT_DAYS,
    now: datetime | None = None,
    fetcher: Callable[[dict[str, Any]], str] = fetch_text,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    try:
        text = fetcher(query_params(now, days=days))
        payload = build_payload(parse_fdsn_text(text), now, days=days)
    except Exception as exc:  # Il meteo non deve dipendere dalla disponibilita INGV.
        message = f"{type(exc).__name__}: {exc}"
        previous: dict[str, Any] | None = None
        if output.exists():
            try:
                previous = json.loads(output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                previous = None
        if previous and isinstance(previous, dict):
            payload = previous
            meta = payload.setdefault("meta", {})
            meta["status"] = "stale"
            meta["error"] = message
            meta["last_attempt"] = now.astimezone(ROME).isoformat(timespec="seconds")
        else:
            payload = _empty_payload(now, days=days, error=message)

    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="seismic_events.json")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    args = parser.parse_args()
    payload = collect(Path(args.output), days=max(1, min(30, args.days)))
    meta = payload.get("meta", {})
    print(
        f"Eventi sismici: stato={meta.get('status')} · "
        f"eventi={meta.get('events_count', 0)} · fonte=INGV"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
