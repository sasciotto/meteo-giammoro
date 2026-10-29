#!/usr/bin/env python3
"""Best-effort ground solar observations near Giammoro.

Sources are intentionally independent from the main meteorological collector:
- Pace del Mela: standard Cumulus MX machine-readable files, when publicly exposed.
- Archi / San Filippo del Mela (ISANFI5): Weather Underground public PWS dashboard.
- Barcellona P.G. NE (SCL087): official MeteoNetwork public station page.

Any failure is represented explicitly as unavailable; no value is fabricated.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

PACE_SITE = "https://meteopacedelmela.altervista.org/"
PACE_GAUGES_URL = f"{PACE_SITE}realtimegauges.txt"
PACE_REALTIME_URL = f"{PACE_SITE}realtime.txt"
ARCHI_URL = "https://www.wunderground.com/dashboard/pws/ISANFI5"
ARCHI_LAT = 38.189
ARCHI_LON = 15.275
SCL087_URL = "https://www.meteonetwork.eu/it/weather-station/scl087-stazione-meteorologica-di-zona-nord-est"
SCL087_LAT = 38.15593
SCL087_LON = 15.22328

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "MeteoGiammoroDashboard/0.5 (+public weather dashboard; respectful polling)",
})


def _number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_local_datetime(date_text: str | None, time_text: str | None, timezone_name: str = "Europe/Rome") -> str | None:
    if not date_text or not time_text:
        return None
    value = f"{date_text.strip()} {time_text.strip()}"
    formats = (
        "%d/%m/%y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    )
    for fmt in formats:
        try:
            local = datetime.strptime(value, fmt).replace(tzinfo=ZoneInfo(timezone_name))
            return _iso(local)
        except ValueError:
            continue
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_case_insensitive(payload: dict[str, Any], *keys: str) -> Any:
    lowered = {str(key).lower(): value for key, value in payload.items()}
    for key in keys:
        if key.lower() in lowered:
            return lowered[key.lower()]
    return None


def parse_cumulus_gauges(text: str, now_utc: datetime | None = None) -> dict[str, Any]:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("realtimegauges.txt non contiene un oggetto JSON")

    solar = _number(_get_case_insensitive(payload, "SolarRad", "solar", "solarRadiation", "radiation"))
    uv = _number(_get_case_insensitive(payload, "UV", "uvindex", "uv_index"))
    date_text = _get_case_insensitive(payload, "date", "Date")
    time_text = _get_case_insensitive(payload, "time", "Time")
    observed_at = _parse_local_datetime(str(date_text) if date_text is not None else None, str(time_text) if time_text is not None else None)
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)

    if solar is None and uv is None:
        raise ValueError("Radiazione/UV non presenti in realtimegauges.txt")

    return {
        "solar_wm2": round(solar, 1) if solar is not None else None,
        "uv_index": round(uv, 2) if uv is not None else None,
        "observed_at": observed_at,
        "retrieved_at": _iso(now_utc),
        "method": "cumulus-realtimegauges",
    }


def parse_cumulus_realtime(text: str, now_utc: datetime | None = None) -> dict[str, Any]:
    fields = text.strip().split()
    # Cumulus realtime.txt standard: UV at field 43, Solar Radiation at field 45.
    if len(fields) <= 45:
        raise ValueError("realtime.txt Cumulus incompleto")
    uv = _number(fields[43])
    solar = _number(fields[45])
    observed_at = _parse_local_datetime(fields[0], fields[1])
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if solar is None and uv is None:
        raise ValueError("Radiazione/UV non presenti in realtime.txt")
    return {
        "solar_wm2": round(solar, 1) if solar is not None else None,
        "uv_index": round(uv, 2) if uv is not None else None,
        "observed_at": observed_at,
        "retrieved_at": _iso(now_utc),
        "method": "cumulus-realtime",
    }


def collect_pace_del_mela(now_utc: datetime | None = None) -> dict[str, Any]:
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    errors: list[str] = []
    attempts = (
        (PACE_GAUGES_URL, parse_cumulus_gauges),
        (PACE_REALTIME_URL, parse_cumulus_realtime),
    )
    for url, parser in attempts:
        try:
            response = SESSION.get(url, timeout=15)
            if response.status_code == 404:
                errors.append(f"{url.rsplit('/', 1)[-1]}: 404")
                continue
            response.raise_for_status()
            parsed = parser(response.text, now_utc=now_utc)
            return {
                "id": "pace-del-mela",
                "name": "Pace del Mela · Pace Alta",
                "source": "Meteo Pace del Mela / Cumulus MX",
                "source_url": PACE_SITE,
                "status": "ok",
                **parsed,
                "note": "Lettura da file standard Cumulus MX pubblicamente esposto dalla stazione.",
            }
        except Exception as exc:
            errors.append(f"{url.rsplit('/', 1)[-1]}: {exc}")

    return {
        "id": "pace-del-mela",
        "name": "Pace del Mela · Pace Alta",
        "source": "Meteo Pace del Mela / Cumulus MX",
        "source_url": PACE_SITE,
        "status": "unavailable",
        "solar_wm2": None,
        "uv_index": None,
        "observed_at": None,
        "retrieved_at": _iso(now_utc),
        "method": "cumulus-discovery",
        "note": "Sensore Solare/UV noto, ma i file standard Cumulus MX non sono risultati leggibili in questo ciclo.",
        "diagnostic": "; ".join(errors)[:500],
    }


def parse_wunderground_station_html(html: str, now_utc: datetime | None = None) -> dict[str, Any]:
    text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)
    # The public PWS dashboard exposes labelled UV and Radiation values. Keep the
    # patterns strict enough not to confuse forecast UV/radiation text with the
    # current-station observation block.
    uv_match = re.search(r"(?:^|\s)UV\s+([-+]?\d+(?:[\.,]\d+)?)\b", text, flags=re.IGNORECASE)
    solar_match = re.search(r"Radiation\s+([-+]?\d+(?:[\.,]\d+)?)\b", text, flags=re.IGNORECASE)
    uv = _number(uv_match.group(1)) if uv_match else None
    solar = _number(solar_match.group(1)) if solar_match else None
    if solar is None and uv is None:
        raise ValueError("Campi UV/Radiation non trovati nella dashboard Weather Underground")
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "solar_wm2": round(solar, 1) if solar is not None else None,
        "uv_index": round(uv, 2) if uv is not None else None,
        "observed_at": None,
        "retrieved_at": _iso(now_utc),
        "method": "wunderground-public-pws-page",
    }


def collect_archi(reference: dict[str, Any], now_utc: datetime | None = None) -> dict[str, Any]:
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    base = {
        "id": "archi-isanfi5",
        "name": "Archi · San Filippo del Mela · ISANFI5",
        "source": "Weather Underground PWS",
        "source_url": ARCHI_URL,
        "latitude": ARCHI_LAT,
        "longitude": ARCHI_LON,
        "distance_km": round(haversine_km(float(reference["latitude"]), float(reference["longitude"]), ARCHI_LAT, ARCHI_LON), 1),
    }
    try:
        response = SESSION.get(ARCHI_URL, timeout=15)
        response.raise_for_status()
        parsed = parse_wunderground_station_html(response.text, now_utc=now_utc)
        return {
            **base,
            "status": "ok",
            **parsed,
            "note": "Valori UV e radiazione letti dalla dashboard pubblica della PWS Archi; acquisizione best-effort e indipendente dalle altre fonti.",
        }
    except Exception as exc:
        return {
            **base,
            "status": "unavailable",
            "solar_wm2": None,
            "uv_index": None,
            "observed_at": None,
            "retrieved_at": _iso(now_utc),
            "method": "wunderground-public-pws-page",
            "note": "Stazione Archi con UV/radiazione verificati sulla pagina pubblica, ma lettura automatica non disponibile in questo ciclo.",
            "diagnostic": str(exc)[:500],
        }


def parse_meteonetwork_station_html(html: str, now_utc: datetime | None = None) -> dict[str, Any]:
    text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)
    solar_match = re.search(r"Radiazione\s+solare\s+([-+]?\d+(?:[\.,]\d+)?)\s*W\s*/?\s*m(?:2|²)", text, flags=re.IGNORECASE)
    uv_match = re.search(r"Radiazione\s+UV\s+([-+]?\d+(?:[\.,]\d+)?)", text, flags=re.IGNORECASE)
    solar = _number(solar_match.group(1)) if solar_match else None
    uv = _number(uv_match.group(1)) if uv_match else None
    if solar is None and uv is None:
        raise ValueError("Campi Radiazione solare/UV non trovati nella pagina MeteoNetwork")
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "solar_wm2": round(solar, 1) if solar is not None else None,
        "uv_index": round(uv, 2) if uv is not None else None,
        "observed_at": None,
        "retrieved_at": _iso(now_utc),
        "method": "meteonetwork-public-page",
    }


def collect_scl087(reference: dict[str, Any], now_utc: datetime | None = None) -> dict[str, Any]:
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    base = {
        "id": "scl087",
        "name": "Barcellona P.G. NE · SCL087",
        "source": "MeteoNetwork",
        "source_url": SCL087_URL,
        "latitude": SCL087_LAT,
        "longitude": SCL087_LON,
        "distance_km": round(haversine_km(float(reference["latitude"]), float(reference["longitude"]), SCL087_LAT, SCL087_LON), 1),
    }
    try:
        response = SESSION.get(SCL087_URL, timeout=15)
        response.raise_for_status()
        parsed = parse_meteonetwork_station_html(response.text, now_utc=now_utc)
        return {
            **base,
            "status": "ok",
            **parsed,
            "note": "Valore letto dalla pagina pubblica ufficiale MeteoNetwork; il timestamp della misura non è esposto in modo affidabile dal parser, quindi viene mostrato il tempo di acquisizione.",
        }
    except Exception as exc:
        return {
            **base,
            "status": "unavailable",
            "solar_wm2": None,
            "uv_index": None,
            "observed_at": None,
            "retrieved_at": _iso(now_utc),
            "method": "meteonetwork-public-page",
            "note": "Stazione con sensori solare/UV verificati, ma lettura automatica non disponibile in questo ciclo.",
            "diagnostic": str(exc)[:500],
        }


def collect_ground_observations(reference: dict[str, Any], now_utc: datetime | None = None) -> list[dict[str, Any]]:
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return [
        collect_pace_del_mela(now_utc=now_utc),
        collect_archi(reference, now_utc=now_utc),
        collect_scl087(reference, now_utc=now_utc),
    ]
