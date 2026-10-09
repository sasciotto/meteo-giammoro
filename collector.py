#!/usr/bin/env python3
"""Collector e motore deterministico per Meteo Giammoro.

Principi:
- Giammoro e' sempre il territorio di riferimento.
- MeteoGiammoro resta esclusa finche' e' in manutenzione/test.
- Le stazioni circostanti non vengono rinominate o mediate come dato di Giammoro.
- I valori territoriali durante il guasto della stazione locale derivano dal modello sul punto
  (ItaliaMeteo ICON-2I come prima scelta) e sono esplicitamente etichettati come stima modellistica.
- Le osservazioni circostanti servono come validazione e segnale di contesto.
- Radar/fulmini/satellite sono previsti come fonti nowcasting, ma questa prima pipeline non inventa
  dati se non dispone di API machine-readable verificate.
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import math
import os
import re
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds
from rasterio.warp import transform, transform_bounds
import numpy as np

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config" / "stations.json").read_text(encoding="utf-8"))
OVERRIDES_PATH = ROOT / "config" / "overrides.json"
DATA_PATH = ROOT / "data.json"
HISTORY_PATH = ROOT / "history.json"

REF = CONFIG["reference"]
TZ = ZoneInfo(REF["timezone"])
CMS_URL = "https://www.centrometeosicilia.it/stations/database.php"
DRPC_ALERTS_URL = "https://www.protezionecivilesicilia.it/it/news/default.asp?pageid=75"
DPC_BULLETIN_URL = "https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita/index.html"
DPC_TARGET_ZONE = "Nord-Orientale, versante tirrenico e isole Eolie"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ENSEMBLE = "https://ensemble-api.open-meteo.com/v1/ensemble"
DPC_RADAR_API = "https://radar-api.protezionecivile.it"
DPC_RADAR_ORIGIN = "https://radar.protezionecivile.it"

MODEL_SPECS = [
    ("ItaliaMeteo ICON-2I", "italia_meteo_arpae_icon_2i", 3),
    ("DWD ICON", "dwd_icon_seamless", 7),
    ("ECMWF IFS", "ecmwf_ifs", 8),
    ("NOAA GFS", "ncep_gfs_seamless", 8),
]
ENSEMBLE_SPECS = [
    ("ECMWF ENS", "ecmwf_ifs025_ensemble_mean"),
    ("ICON EPS", "dwd_icon_eps_ensemble_mean_seamless"),
    ("GEFS", "ncep_gefs_ensemble_mean_seamless"),
]

UA = "MeteoGiammoroDashboard/0.3 (+public weather dashboard; respectful polling)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9,en;q=0.5"})


def now_local() -> datetime:
    return datetime.now(TZ)


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", ".")
    if not s or s in {"-", "--", "—", "n/a", "N/A"}:
        return None
    s = re.sub(r"[^0-9+\-.]", "", s)
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def dew_point_c(temp_c: float | None, rh: float | None) -> float | None:
    if temp_c is None or rh is None or rh <= 0 or rh > 100:
        return None
    a, b = 17.625, 243.04
    gamma = math.log(rh / 100.0) + (a * temp_c) / (b + temp_c)
    return round((b * gamma) / (a - gamma), 1)


def network_quality(network: str) -> tuple[str, str]:
    n = (network or "").lower()
    if any(x in n for x in ["protezione civile", "drpc", "sias", "aeronautica"]):
        return "official", "Rete ufficiale"
    if any(x in n for x in ["lineameteo", "cms", "weathersicily", "meteoproject"]):
        return "reliable", "Rete locale affidabile"
    if any(x in n for x in ["weatherlink", "ecowitt", "wunderground", "tempest", "cwop"]):
        return "community", "Rete terza / controllo"
    return "unknown", "Fonte da classificare"


def station_age_status(time_hhmm: str | None, now: datetime | None = None) -> tuple[str, str, int | None]:
    if not time_hhmm or not re.fullmatch(r"\d{1,2}:\d{2}", time_hhmm.strip()):
        return "unknown", "Orario non disponibile", None
    now = now or now_local()
    hh, mm = map(int, time_hhmm.split(":"))
    stamp = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if stamp > now + timedelta(minutes=10):
        stamp -= timedelta(days=1)
    age = max(0, int((now - stamp).total_seconds() / 60))
    if age <= 60:
        return "online", "Online", age
    if age <= 180:
        return "test", "Dato vecchio", age
    return "offline", "Obsoleta", age


def parse_cms_table(html: str) -> dict[str, dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    target = None
    for table in tables:
        headers = [x.get_text(" ", strip=True) for x in table.find_all("th")]
        if headers and "Nome Stazione" in headers and ("Temp" in headers or "Umid" in headers):
            target = table
            break
    if target is None:
        raise RuntimeError("Tabella stazioni CMS non trovata")

    headers = [x.get_text(" ", strip=True) for x in target.find_all("th")]
    out: dict[str, dict[str, Any]] = {}
    for tr in target.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < len(headers):
            continue
        row = {headers[i]: cells[i].get_text(" ", strip=True) for i in range(len(headers))}
        name = row.get("Nome Stazione", "").strip()
        if not name:
            continue
        network = row.get("Rete", "").replace("Image:", "").strip()
        if not network:
            img = cells[-1].find("img")
            network = (img.get("alt") or img.get("title") or "").strip() if img else ""
        out[name] = {
            "name": name,
            "province": row.get("Pr"),
            "altitude_m": safe_float(row.get("Alt")),
            "temperature": safe_float(row.get("Temp")),
            "tmax": safe_float(row.get("Max")),
            "tmin": safe_float(row.get("Min")),
            "humidity": safe_float(row.get("Umid")),
            "wind": safe_float(row.get("Vento")),
            "gust": safe_float(row.get("Raff")),
            "wind_direction": None if row.get("Dir") in {None, "", "-", "--"} else row.get("Dir"),
            "rain_day": safe_float(row.get("P.Day")),
            "rain_month": safe_float(row.get("P.Mese")),
            "rain_year": safe_float(row.get("P.Anno")),
            "pressure": safe_float(row.get("Press")),
            "time": row.get("Ore"),
            "network": network,
        }
    return out


def fetch_text(url: str, timeout: int = 25) -> str:
    r = SESSION.get(url, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    return r.text


def fetch_json(url: str, params: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    r = SESSION.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_stations() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    html = fetch_text(CMS_URL)
    rows = parse_cms_table(html)
    now = now_local()
    stations: list[dict[str, Any]] = [{
        "name": "MeteoGiammoro",
        "display_name": "MeteoGiammoro",
        "network": "stazione locale",
        "source_quality": "primary",
        "status": "maintenance",
        "status_label": "Manutenzione / test",
        "updated": "esclusa",
        "temperature": None, "dew_point": None, "humidity": None, "pressure": None,
        "wind": None, "gust": None, "wind_direction": None, "rain_1h": None, "rain_24h": None,
        "rain_day": None,
        "excluded_from_analysis": True,
        "note": CONFIG["primary_station"]["note"]
    }]
    found: dict[str, Any] = {}

    for group in CONFIG["station_groups"]:
        selected = None
        for candidate in group["candidates"]:
            if candidate in rows:
                selected = rows[candidate]
                break
        if selected is None:
            stations.append({
                "name": group["label"], "display_name": group["label"],
                "network": "nessuna stazione verificata nel feed corrente",
                "source_quality": "unknown", "status": "unknown", "status_label": "Non disponibile",
                "updated": "—", "temperature": None, "dew_point": None, "humidity": None,
                "pressure": None, "wind": None, "gust": None, "wind_direction": None,
                "rain_1h": None, "rain_24h": None, "rain_day": None,
                "excluded_from_analysis": True,
                "note": "Nessun dato viene sostituito con una località diversa senza indicarlo."
            })
            continue

        st = copy.deepcopy(selected)
        status, status_label, age = station_age_status(st.get("time"), now)
        q, q_label = network_quality(st.get("network", ""))
        td = dew_point_c(st.get("temperature"), st.get("humidity"))
        display_name = group["label"]
        note = None
        if selected["name"] != group["label"]:
            note = f"Stazione effettiva: {selected['name']}. Il dato resta attribuito a questa stazione ed è usato solo come supporto per {group['label']}."
        item = {
            "name": selected["name"], "display_name": display_name,
            "network": st.get("network") or "fonte non indicata",
            "source_quality": q, "source_quality_label": q_label,
            "status": status, "status_label": status_label,
            "updated": f"{st.get('time') or '—'}" + (f" · {age} min fa" if age is not None else ""),
            "temperature": st.get("temperature"), "dew_point": td, "humidity": st.get("humidity"),
            "pressure": st.get("pressure"), "wind": st.get("wind"), "gust": st.get("gust"),
            "wind_direction": st.get("wind_direction"), "rain_1h": None, "rain_24h": None,
            "rain_day": st.get("rain_day"), "altitude_m": st.get("altitude_m"),
            "excluded_from_analysis": status not in {"online", "test"}, "note": note,
        }
        stations.append(item)
        found[group["label"]] = item

    # Supporto aggiuntivo senza duplicati
    existing = {s["name"] for s in stations}
    for name in CONFIG.get("additional_support", []):
        if name not in rows or name in existing:
            continue
        st = rows[name]
        status, status_label, age = station_age_status(st.get("time"), now)
        q, q_label = network_quality(st.get("network", ""))
        stations.append({
            "name": name, "display_name": name, "network": st.get("network") or "fonte non indicata",
            "source_quality": q, "source_quality_label": q_label, "status": status, "status_label": status_label,
            "updated": f"{st.get('time') or '—'}" + (f" · {age} min fa" if age is not None else ""),
            "temperature": st.get("temperature"), "dew_point": dew_point_c(st.get("temperature"), st.get("humidity")),
            "humidity": st.get("humidity"), "pressure": st.get("pressure"), "wind": st.get("wind"),
            "gust": st.get("gust"), "wind_direction": st.get("wind_direction"), "rain_1h": None,
            "rain_24h": None, "rain_day": st.get("rain_day"), "altitude_m": st.get("altitude_m"),
            "excluded_from_analysis": status not in {"online", "test"},
            "note": "Stazione aggiuntiva di supporto territoriale."
        })

    meta = {"source": "Centro Meteorologico Siciliano - Database Stazioni Live", "url": CMS_URL, "rows": len(rows)}
    return stations, meta


def model_params(model_id: str, days: int) -> dict[str, Any]:
    hourly = [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation", "showers",
        "weather_code", "pressure_msl", "cloud_cover", "wind_speed_10m", "wind_direction_10m",
        "wind_gusts_10m", "cape"
    ]
    current = [
        "temperature_2m", "relative_humidity_2m", "precipitation", "rain", "showers", "weather_code",
        "cloud_cover", "pressure_msl", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"
    ]
    return {
        "latitude": REF["latitude"], "longitude": REF["longitude"], "elevation": REF["elevation_m"],
        "timezone": REF["timezone"], "forecast_days": days, "models": model_id,
        "hourly": ",".join(hourly), "current": ",".join(current),
        "wind_speed_unit": "kmh", "precipitation_unit": "mm", "temperature_unit": "celsius"
    }


def fetch_models() -> list[dict[str, Any]]:
    results = []
    for label, model_id, days in MODEL_SPECS:
        try:
            raw = fetch_json(OPEN_METEO, model_params(model_id, days))
            results.append({"label": label, "id": model_id, "ok": True, "raw": raw})
        except Exception as exc:
            results.append({"label": label, "id": model_id, "ok": False, "error": str(exc)})
    return results


def hourly_window(raw: dict[str, Any], start_hours: int, end_hours: int, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or now_local()
    h = raw.get("hourly", {})
    times = h.get("time", [])
    rows = []
    for i, t in enumerate(times):
        try:
            dt = datetime.fromisoformat(t)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
        except Exception:
            continue
        dh = (dt - now).total_seconds() / 3600
        if start_hours <= dh <= end_hours:
            row = {"time": dt}
            for key, vals in h.items():
                if key == "time" or not isinstance(vals, list) or i >= len(vals):
                    continue
                row[key] = vals[i]
            rows.append(row)
    return rows


def max_numeric(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [safe_float(r.get(key)) for r in rows]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None


def sum_numeric(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [safe_float(r.get(key)) for r in rows]
    vals = [v for v in vals if v is not None]
    return round(sum(vals), 1) if vals else None


def summarize_model(model: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    if not model.get("ok"):
        return {"label": model["label"], "id": model["id"], "ok": False, "error": model.get("error")}
    raw = model["raw"]
    w03 = hourly_window(raw, -0.5, 3.5, now)
    w348 = hourly_window(raw, 3.0, 48.0, now)
    w27d = hourly_window(raw, 48.0, 168.0, now)
    def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        codes = [int(v) for v in [safe_float(r.get("weather_code")) for r in rows] if v is not None]
        temps = [safe_float(r.get("temperature_2m")) for r in rows]
        temps = [x for x in temps if x is not None]
        return {
            "precip_sum": sum_numeric(rows, "precipitation"),
            "precip_max_h": max_numeric(rows, "precipitation"),
            "gust_max": max_numeric(rows, "wind_gusts_10m"),
            "cape_max": max_numeric(rows, "cape"),
            "thunder_signal": any(c >= 95 for c in codes),
            "temp_min": round(min(temps), 1) if temps else None,
            "temp_max": round(max(temps), 1) if temps else None,
        }
    return {
        "label": model["label"], "id": model["id"], "ok": True,
        "current": raw.get("current", {}),
        "next_0_3h": summary(w03), "next_3_48h": summary(w348), "days_2_7": summary(w27d),
        "grid": {"latitude": raw.get("latitude"), "longitude": raw.get("longitude"), "elevation": raw.get("elevation")}
    }


def fetch_ensembles() -> list[dict[str, Any]]:
    out = []
    variables = [
        "temperature_2m", "temperature_2m_spread", "precipitation", "precipitation_spread",
        "wind_gusts_10m", "wind_gusts_10m_spread", "cape", "cape_spread"
    ]
    for label, model_id in ENSEMBLE_SPECS:
        params = {
            "latitude": REF["latitude"], "longitude": REF["longitude"], "elevation": REF["elevation_m"],
            "timezone": REF["timezone"], "forecast_days": 7, "models": model_id,
            "hourly": ",".join(variables), "wind_speed_unit": "kmh", "precipitation_unit": "mm"
        }
        try:
            raw = fetch_json(OPEN_METEO_ENSEMBLE, params)
            rows = hourly_window(raw, 48, 168)
            out.append({
                "label": label, "id": model_id, "ok": True,
                "temp_spread_max": max_numeric(rows, "temperature_2m_spread"),
                "precip_mean_sum_2_7d": sum_numeric(rows, "precipitation"),
                "precip_spread_max": max_numeric(rows, "precipitation_spread"),
                "gust_mean_max": max_numeric(rows, "wind_gusts_10m"),
                "gust_spread_max": max_numeric(rows, "wind_gusts_10m_spread"),
                "cape_mean_max": max_numeric(rows, "cape"),
                "cape_spread_max": max_numeric(rows, "cape_spread")
            })
        except Exception as exc:
            out.append({"label": label, "id": model_id, "ok": False, "error": str(exc)})
    return out


def normalize_alert_class(value: str | None) -> str:
    """Converte la terminologia italiana dell'allerta nelle classi UI interne."""
    v = (value or "unknown").strip().lower()
    return {
        "verde": "low", "green": "low", "low": "low",
        "gialla": "warning", "giallo": "warning", "yellow": "warning", "warning": "warning",
        "arancione": "orange", "orange": "orange",
        "rossa": "red", "rosso": "red", "red": "red",
    }.get(v, "unknown")


def parse_alert_level_from_text(text: str) -> tuple[str | None, str | None, str]:
    clean = re.sub(r"\s+", " ", text or " ")
    patterns = [
        r"(?:ZONA|zona)\s*A.{0,500}?\b(ROSSA|ARANCIONE|GIALLA|VERDE)\b",
        r"\bA\b.{0,250}?\b(ROSSA|ARANCIONE|GIALLA|VERDE)\b",
    ]
    for pat in patterns:
        m = re.search(pat, clean, flags=re.I)
        if m:
            word = m.group(1).upper()
            return normalize_alert_class(word), word.title(), "estrazione automatica zona A"
    return  None, None, "livello zona A non estratto con sufficiente confidenza"


def parse_national_bulletin_text(text: str, target_zone: str = DPC_TARGET_ZONE) -> list[dict[str, str]]:
    """Estrae dal bollettino nazionale le allerte che includono la zona di Giammoro."""
    lines = [re.sub(r"\s+", " ", x).strip() for x in (text or "").splitlines()]
    lines = [x for x in lines if x]
    day = "non specificato"
    level = None
    risk = None
    records: list[dict[str, str]] = []
    for line in lines:
        low = line.lower()
        if low.startswith("per la giornata di oggi"):
            day = "oggi"
            continue
        if low.startswith("per la giornata di domani"):
            day = "domani"
            continue
        hm = re.search(r"(ALLERTA\s+(ROSSA|ARANCIONE|GIALLA))", line, flags=re.I)
        if hm:
            level = hm.group(2).lower()
            rm = re.search(r"RISCHIO\s+([A-ZÀ-Ù ]+?)\s*/", line, flags=re.I)
            risk = rm.group(1).strip().lower() if rm else "non specificato"
            continue
        if line.startswith("Sicilia:") and target_zone.lower() in line.lower() and level:
            records.append({
                "day": day,
                "level_class": normalize_alert_class(level),
                "level_label": level.title(),
                "risk": risk or "non specificato",
                "evidence": line,
            })
    return records


def fetch_national_alert_target() -> dict[str, Any]:
    html = fetch_text(DPC_BULLETIN_URL)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    records = parse_national_bulletin_text(text)
    if not records:
        raise RuntimeError("zona DPC nazionale non trovata nel bollettino corrente")
    rank = {"low": 0, "warning": 1, "orange": 2, "red": 3, "unknown": -1}
    highest = max(records, key=lambda r: rank.get(r["level_class"], -1))
    same = [r for r in records if r["level_class"] == highest["level_class"]]
    risks = sorted({r["risk"] for r in same})
    days = sorted({r["day"] for r in same}, key=lambda d: {"oggi": 0, "domani": 1}.get(d, 2))
    return {
        "level_class": highest["level_class"],
        "level_label": highest["level_label"] + (f" ({'/'.join(days)})" if days else ""),
        "validity": ", ".join(days) if days else "—",
        "risks": risks,
        "records": records,
        "source": "DPC nazionale - Bollettino di criticità/allerta",
        "url": DPC_BULLETIN_URL,
    }


def fetch_alert() -> dict[str, Any]:
    html = fetch_text(DRPC_ALERTS_URL)
    soup = BeautifulSoup(html, "html.parser")
    link = None
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if "Avviso Rischio Idrogeologico" in title:
            link = a
            break
    if link is None:
        raise RuntimeError("Ultimo avviso DRPC non trovato")
    title = link.get_text(" ", strip=True)
    href = urljoin(DRPC_ALERTS_URL, link["href"])
    if href.lower().endswith(".pdf"):
        pdf_url = href
    else:
        page = fetch_text(href)
        psoup = BeautifulSoup(page, "html.parser")
        pdf_link = next((a for a in psoup.find_all("a", href=True) if ".pdf" in a["href"].lower()), None)
        pdf_url = urljoin(href, pdf_link["href"]) if pdf_link else None

    level_class = level_label = None
    parser_note = "PDF non disponibile"
    validity = "—"
    text_excerpt = ""
    if pdf_url:
        r = SESSION.get(pdf_url, timeout=35)
        r.raise_for_status()
        reader = PdfReader(io.BytesIO(r.content))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        level_class, level_label, parser_note = parse_alert_level_from_text(text)
        vm = re.search(r"VALIDIT[ÀA]'?\s*:?\s*(.{0,180})", re.sub(r"\s+", " ", text), flags=re.I)
        if vm:
            validity = vm.group(1).strip(" :-")[:170]
        pm = re.search(r"(precipitazioni.{0,500})", re.sub(r"\s+", " ", text), flags=re.I)
        if pm:
            text_excerpt = pm.group(1)[:600]

    national = None
    try:
        national = fetch_national_alert_target()
        # Per il codice colore automatico usiamo la sintesi testuale ufficiale nazionale:
        # evita di inferire colori da una mappa raster del PDF regionale.
        level_class = national["level_class"]
        level_label = national["level_label"]
        validity = national["validity"]
        parser_note = "livello zona A validato dal bollettino nazionale DPC; avviso regionale mantenuto come fonte primaria di dettaglio"
        risks = ", ".join(national.get("risks", []))
        text_excerpt = f"Zona {DPC_TARGET_ZONE}: {level_label}. Rischi: {risks}."
    except Exception as exc:
        national = {"error": str(exc)}

    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8")) if OVERRIDES_PATH.exists() else {}
    if overrides.get("alert_zone_a_level"):
        raw_level = overrides["alert_zone_a_level"]
        level_class = normalize_alert_class(str(raw_level))
        level_label = overrides.get("alert_zone_a_label") or str(raw_level).title()
        parser_note = "override manuale zona A"

    return {
        "level_label": level_label or "Da verificare",
        "level_class": level_class or "unknown",
        "title": title,
        "text": text_excerpt or "Avviso ufficiale individuato; livello specifico della zona A da validare se la tabella PDF non è parsabile automaticamente.",
        "validity": validity,
        "source": "CFD/DRPC Sicilia + DPC nazionale",
        "url": pdf_url or href,
        "parser_note": parser_note,
        "retrieved_at": now_local().isoformat(timespec="minutes"),
        "national_validation": national,
    }


def dpc_api_headers() -> dict[str, str]:
    return {
        "origin": DPC_RADAR_ORIGIN,
        "referer": DPC_RADAR_ORIGIN + "/",
        "accept": "application/json, text/plain, */*",
    }


def dpc_last_product(product_type: str) -> dict[str, Any]:
    r = SESSION.get(
        f"{DPC_RADAR_API}/findLastProductByType",
        params={"type": product_type}, headers=dpc_api_headers(), timeout=20,
    )
    r.raise_for_status()
    payload = r.json()
    products = payload.get("lastProducts") or []
    if not products:
        raise RuntimeError(f"nessun prodotto DPC {product_type}")
    return products[0]


def dpc_download_product(product_type: str, timestamp_ms: int) -> bytes:
    headers = dpc_api_headers() | {"content-type": "application/json"}
    r = SESSION.post(
        f"{DPC_RADAR_API}/downloadProduct",
        json={"productType": product_type, "productDate": int(timestamp_ms)},
        headers=headers, timeout=25,
    )
    r.raise_for_status()
    payload = r.json()
    url = payload.get("url")
    if not url:
        raise RuntimeError(f"URL download DPC assente per {product_type}")
    raw = SESSION.get(url, timeout=35)
    raw.raise_for_status()
    return raw.content


def _radius_bbox(lon: float, lat: float, radius_km: float) -> tuple[float, float, float, float]:
    lat_delta = radius_km / 111.32
    lon_delta = radius_km / max(1.0, 111.32 * math.cos(math.radians(lat)))
    return lon - lon_delta, lat - lat_delta, lon + lon_delta, lat + lat_delta


def sample_geotiff_neighborhood(content: bytes, lon: float, lat: float, radius_km: float) -> dict[str, Any]:
    """Restituisce statistiche sul raster in un intorno del punto senza assumere unità del prodotto."""
    with MemoryFile(content) as mem:
        with mem.open() as ds:
            if not ds.crs:
                raise RuntimeError("GeoTIFF DPC senza CRS")
            point_value = None
            try:
                px, py = lon, lat
                if str(ds.crs).upper() not in {"EPSG:4326", "OGC:CRS84"}:
                    xs, ys = transform("EPSG:4326", ds.crs, [lon], [lat])
                    px, py = xs[0], ys[0]
                sampled = next(ds.sample([(px, py)], indexes=1, masked=True))
                if len(sampled) and not np.ma.is_masked(sampled[0]):
                    candidate = float(sampled[0])
                    if math.isfinite(candidate) and candidate > -9000:
                        point_value = round(candidate, 2)
            except Exception:
                point_value = None

            left, bottom, right, top = _radius_bbox(lon, lat, radius_km)
            if str(ds.crs).upper() not in {"EPSG:4326", "OGC:CRS84"}:
                left, bottom, right, top = transform_bounds("EPSG:4326", ds.crs, left, bottom, right, top, densify_pts=21)
            win = from_bounds(left, bottom, right, top, transform=ds.transform)
            win = win.round_offsets().round_lengths()
            arr = ds.read(1, window=win, boundless=True, masked=True)
            vals = np.asarray(arr.compressed(), dtype=float)
            vals = vals[np.isfinite(vals)]
            # Numerosi prodotti usano valori negativi come nodata/fuori dominio.
            vals = vals[vals > -9000]
            if vals.size == 0:
                return {"radius_km": radius_km, "count": 0, "point": point_value, "max": None, "mean": None, "p90": None}
            return {
                "radius_km": radius_km,
                "count": int(vals.size),
                "point": point_value,
                "max": round(float(np.nanmax(vals)), 2),
                "mean": round(float(np.nanmean(vals)), 2),
                "p90": round(float(np.nanpercentile(vals, 90)), 2),
            }


def fetch_dpc_product_point(product_type: str, radii_km: tuple[int, ...] = (5, 15, 30)) -> dict[str, Any]:
    latest = dpc_last_product(product_type)
    ts = int(latest["time"])
    raw = dpc_download_product(product_type, ts)
    stats = [sample_geotiff_neighborhood(raw, REF["longitude"], REF["latitude"], r) for r in radii_km]
    stamp = datetime.fromtimestamp(ts / 1000, tz=ZoneInfo("UTC")).astimezone(TZ)
    return {
        "product": product_type,
        "ok": True,
        "timestamp": stamp.isoformat(timespec="minutes"),
        "age_minutes": max(0, int((now_local() - stamp).total_seconds() / 60)),
        "period": latest.get("period"),
        "stats": stats,
    }


def fetch_dpc_observations() -> dict[str, Any]:
    """Scarica prodotti ufficiali DPC utili a Giammoro. Ogni prodotto fallisce in modo indipendente."""
    products: dict[str, Any] = {}
    errors: list[str] = []
    # SRI=intensità istantanea, SRT1=cumulata 1h radar+pluviometri, CUM24=rete a terra interpolata,
    # TEMP=rete termometrica interpolata, VMI=riflettività massima, IR_108=satellite.
    for product, radii in [
        ("SRI", (5, 15, 30)), ("SRT1", (5, 15, 30)), ("CUM24", (5,)),
        ("TEMP", (5,)), ("VMI", (5, 15, 30)), ("IR_108", (5,)),
    ]:
        try:
            products[product] = fetch_dpc_product_point(product, radii)
        except Exception as exc:
            products[product] = {"product": product, "ok": False, "error": str(exc)}
            errors.append(f"{product}: {exc}")
    return {"products": products, "errors": errors, "source": "Radar-DPC / Dipartimento Protezione Civile"}


def _stat_max(product: dict[str, Any] | None, radius: int) -> float | None:
    if not product or not product.get("ok"):
        return None
    for s in product.get("stats", []):
        if int(s.get("radius_km", -1)) == radius:
            return safe_float(s.get("max"))
    return None


def _stat_point(product: dict[str, Any] | None) -> float | None:
    if not product or not product.get("ok"):
        return None
    for s in product.get("stats", []):
        value = safe_float(s.get("point"))
        if value is not None:
            return value
    return None


def nowcast_from_dpc_and_models(dpc: dict[str, Any] | None, model_label: str, model_level: str, model_note: str) -> tuple[str, str, str]:
    """Dà precedenza alle osservazioni radar DPC; non attribuisce una traiettoria senza HRD/animazione."""
    products = (dpc or {}).get("products", {})
    sri = products.get("SRI", {})
    vmi = products.get("VMI", {})
    srt = products.get("SRT1", {})
    sri5, sri15, sri30 = (_stat_max(sri, r) for r in (5, 15, 30))
    vmi15, vmi30 = (_stat_max(vmi, r) for r in (15, 30))
    rain1_5 = _stat_max(srt, 5)
    radar_available = any(v is not None for v in [sri5, sri15, sri30, vmi15, vmi30, rain1_5])
    if not radar_available:
        return model_label, model_level, model_note + ". Radar-DPC non disponibile nel ciclo corrente."

    evidence = []
    if sri5 is not None: evidence.append(f"SRI max 5 km {sri5:.1f} mm/h")
    if sri15 is not None: evidence.append(f"SRI max 15 km {sri15:.1f} mm/h")
    if sri30 is not None: evidence.append(f"SRI max 30 km {sri30:.1f} mm/h")
    if vmi15 is not None: evidence.append(f"VMI max 15 km {vmi15:.0f} dBZ")
    if rain1_5 is not None: evidence.append(f"SRT1 max 5 km {rain1_5:.1f} mm")

    if (sri5 or 0) >= 10 or (vmi15 or 0) >= 50 or (rain1_5 or 0) >= 15:
        return "Elevato (osservato)", "elevato", "Fenomeni intensi rilevati nell'area di Giammoro: " + ", ".join(evidence)
    if (sri15 or 0) >= 5 or (vmi15 or 0) >= 40 or (rain1_5 or 0) >= 5:
        return "Moderato–elevato (osservato)", "elevato", "Precipitazioni/eco radar significativi nelle immediate vicinanze: " + ", ".join(evidence)
    if (sri30 or 0) >= 3 or (vmi30 or 0) >= 35:
        return "Moderato (radar vicino)", "moderato", "Eco/precipitazioni rilevati entro ~30 km; traiettoria non dedotta automaticamente: " + ", ".join(evidence)
    if (sri30 or 0) > 0.2 or (vmi30 or 0) >= 20:
        return "Basso–moderato", "moderato", "Segnale radar debole o periferico nell'area vasta: " + ", ".join(evidence)
    return "Basso (radar)", "low", "Radar-DPC senza segnali precipitativi rilevanti entro ~30 km; " + model_note


def choose_reference_model(summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    for preferred in ["ItaliaMeteo ICON-2I", "ECMWF IFS", "DWD ICON", "NOAA GFS"]:
        for s in summaries:
            if s.get("ok") and s.get("label") == preferred and s.get("current"):
                return s
    return next((s for s in summaries if s.get("ok") and s.get("current")), None)


def risk_from_models(summaries: list[dict[str, Any]], key: str) -> tuple[str, str, str]:
    available = [s for s in summaries if s.get("ok")]
    if not available:
        return "Da verificare", "unknown", "Modelli non disponibili"
    severe = 0
    moderate = 0
    signals = []
    for s in available:
        x = s.get(key, {})
        rain = x.get("precip_sum") or 0
        maxh = x.get("precip_max_h") or 0
        gust = x.get("gust_max") or 0
        cape = x.get("cape_max") or 0
        thunder = bool(x.get("thunder_signal"))
        if thunder or rain >= 20 or maxh >= 10 or gust >= 70 or cape >= 1800:
            severe += 1
        if rain >= 5 or maxh >= 3 or gust >= 50 or cape >= 800:
            moderate += 1
        if rain >= 1:
            signals.append(f"{s['label']}: {rain:.1f} mm")
    n = len(available)
    if severe >= 2:
        return "Elevato (modellistico)", "elevato", f"Segnale forte in {severe}/{n} modelli"
    if moderate >= 2:
        return "Moderato", "moderato", f"Segnale significativo in {moderate}/{n} modelli"
    if moderate == 1:
        return "Basso–moderato", "moderato", f"Segnale isolato in 1/{n} modelli"
    return "Basso", "low", "Nessun segnale marcato nel consenso modellistico"


def model_agreement(summaries: list[dict[str, Any]], key: str) -> tuple[str, str]:
    vals = []
    for s in summaries:
        if not s.get("ok"):
            continue
        p = s.get(key, {}).get("precip_sum")
        if p is not None:
            vals.append(float(p))
    if len(vals) < 2:
        return "insufficiente", "Pochi modelli disponibili"
    mean = statistics.fmean(vals)
    spread = max(vals) - min(vals)
    if spread <= max(2.0, mean * 0.5):
        return "alto", f"Pioggia prevista abbastanza coerente ({min(vals):.1f}–{max(vals):.1f} mm)"
    if spread <= max(8.0, mean * 1.2):
        return "medio", f"Differenze rilevanti ({min(vals):.1f}–{max(vals):.1f} mm)"
    return "basso", f"Forte divergenza ({min(vals):.1f}–{max(vals):.1f} mm)"


def territory_from_reference_model(ref_model: dict[str, Any] | None, dpc: dict[str, Any] | None = None) -> dict[str, Any]:
    if not ref_model:
        return {
            "title": "Giammoro — situazione territoriale", "quality": "unknown", "quality_label": "Dato non disponibile",
            "basis": "Nessun modello sul punto disponibile e MeteoGiammoro è esclusa.", "metrics": {},
            "summary": "Impossibile stimare il quadro territoriale senza inventare dati."
        }
    c = ref_model.get("current", {})
    products = (dpc or {}).get("products", {})
    dpc_temp = _stat_point(products.get("TEMP"))
    dpc_rain1 = _stat_point(products.get("SRT1"))
    dpc_rain24 = _stat_point(products.get("CUM24"))
    temp_value = dpc_temp if dpc_temp is not None else safe_float(c.get("temperature_2m"))
    temp_source = "Radar-DPC TEMP (rete termometrica interpolata)" if dpc_temp is not None else ref_model["label"]
    td = None
    # il current endpoint non espone sempre dewpoint: usa prima ora hourly se necessario, altrimenti formula da T/RH
    td = dew_point_c(safe_float(c.get("temperature_2m")), safe_float(c.get("relative_humidity_2m")))
    return {
        "title": "Giammoro — situazione territoriale",
        "quality": "test", "quality_label": "Stima sul punto",
        "basis": f"Valori riferiti alle coordinate di Giammoro da {ref_model['label']}; le stazioni circostanti sono usate separatamente per controllo e contesto, non come sostituzione diretta.",
        "metrics": {
            "temperature": {"value": temp_value, "unit": " °C", "quality": temp_source},
            "dew_point": {"value": td, "unit": " °C", "quality": "derivato da T/UR"},
            "humidity": {"value": safe_float(c.get("relative_humidity_2m")), "unit": " %", "quality": f"{ref_model['label']}"},
            "pressure": {"value": safe_float(c.get("pressure_msl")), "unit": " hPa", "trend": "trend calcolato nei prossimi step"},
            "wind": {"value": safe_float(c.get("wind_speed_10m")), "unit": " km/h", "direction": c.get("wind_direction_10m")},
            "gust": {"value": safe_float(c.get("wind_gusts_10m")), "unit": " km/h"},
            "rain_1h": {"value": dpc_rain1, "unit": " mm", "quality": "Radar-DPC SRT1" if dpc_rain1 is not None else "n/d"},
            "rain_24h": {"value": dpc_rain24, "unit": " mm", "quality": "Radar-DPC CUM24" if dpc_rain24 is not None else "n/d"},
            "cloud_cover": {"value": safe_float(c.get("cloud_cover")), "unit": " %"}
        },
        "summary": "Stima territoriale automatica; per il nowcasting severo hanno priorità osservazioni reali, radar e fulminazioni quando integrati."
    }


def build_model_rows(summaries: list[dict[str, Any]], ensembles: list[dict[str, Any]]) -> list[dict[str, str]]:
    agree48, note48 = model_agreement(summaries, "next_3_48h")
    signals = []
    for s in summaries:
        if not s.get("ok"):
            signals.append(f"{s['label']}: n/d")
            continue
        x = s["next_3_48h"]
        signals.append(f"{s['label']}: pioggia {x.get('precip_sum') or 0:.1f} mm, raff {x.get('gust_max') or 0:.0f} km/h")
    ens_ok = [e for e in ensembles if e.get("ok")]
    if ens_ok:
        spreads = [e.get("temp_spread_max") for e in ens_ok if e.get("temp_spread_max") is not None]
        spread_text = f"spread T max {max(spreads):.1f} °C" if spreads else "spread T n/d"
        ens_signal = " · ".join(f"{e['label']}: precip media 2–7g {e.get('precip_mean_sum_2_7d') or 0:.1f} mm" for e in ens_ok)
    else:
        spread_text = "ensemble non disponibili"
        ens_signal = "n/d"
    return [
        {
            "horizon": "0–3 h", "models": "osservazioni locali + modelli sul punto (radar/fulmini da integrare)",
            "signal": "Il modello non sostituisce il radar", "agreement": "nowcasting incompleto",
            "note": "Le stazioni circostanti sono già raccolte; radar e fulminazioni restano il prossimo connettore prioritario."
        },
        {
            "horizon": "3–48 h", "models": "ICON-2I · ICON · ECMWF IFS · GFS",
            "signal": " | ".join(signals), "agreement": agree48,
            "note": note48
        },
        {
            "horizon": "2–7 giorni", "models": "ECMWF ENS · ICON EPS · GEFS",
            "signal": ens_signal, "agreement": spread_text,
            "note": "Media e spread ensemble; serve a rappresentare l'incertezza, non a produrre una previsione puntuale deterministica."
        }
    ]


def dpc_radar_evidence(dpc: dict[str, Any] | None) -> str:
    products = (dpc or {}).get("products", {})
    sri = products.get("SRI", {})
    srt = products.get("SRT1", {})
    vmi = products.get("VMI", {})
    parts = []
    for label, product, radius, unit in [
        ("SRI", sri, 5, "mm/h"), ("SRI", sri, 15, "mm/h"), ("SRI", sri, 30, "mm/h"),
        ("SRT1", srt, 5, "mm"), ("VMI", vmi, 15, "dBZ"),
    ]:
        value = _stat_max(product, radius)
        if value is not None:
            parts.append(f"{label} max {radius} km: {value:g} {unit}")
    ts = sri.get("timestamp") or srt.get("timestamp") or vmi.get("timestamp")
    if parts:
        return "Radar-DPC: " + "; ".join(parts) + (f" · aggiornamento {ts}" if ts else "")
    return "Radar-DPC non acquisito nel ciclo corrente; nessun valore radar viene inventato."


def dpc_satellite_evidence(dpc: dict[str, Any] | None) -> str:
    ir = (dpc or {}).get("products", {}).get("IR_108", {})
    if ir.get("ok"):
        return f"Prodotto satellitare DPC IR10.8 disponibile · aggiornamento {ir.get('timestamp', '—')}. Il valore raw non viene trasformato in copertura percentuale senza una conversione validata."
    return "Prodotto satellitare DPC IR10.8 non acquisito nel ciclo corrente."


def significant_change(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any] | None:
    rank = {"unknown": -1, "low": 0, "verde": 0, "moderato": 1, "gialla": 1, "warning": 1, "orange": 2, "arancione": 2, "elevato": 2, "red": 3, "rossa": 3}
    pa = str(previous.get("alert", {}).get("level_class", "unknown")).lower()
    ca = str(current.get("alert", {}).get("level_class", "unknown")).lower()
    if ca != "unknown" and rank.get(ca, -1) != rank.get(pa, -1):
        return {
            "time": now_local().strftime("%d/%m/%Y %H:%M"),
            "title": f"Variazione allerta ufficiale: {previous.get('alert', {}).get('level_label', '—')} → {current['alert']['level_label']}",
            "text": "Il livello ufficiale associato al settore di Giammoro è cambiato rispetto al controllo precedente.",
            "window": current["alert"].get("validity", "—"), "confidence": "alta",
            "evidence": f"CFD/DRPC Sicilia + DPC nazionale · {current['alert'].get('title', '')}"
        }

    pn = str(previous.get("nowcast", {}).get("level", "unknown")).lower()
    cn = str(current.get("nowcast", {}).get("level", "unknown")).lower()
    if cn != pn and rank.get(cn, -1) > rank.get(pn, -1):
        confidence = "alta" if "osserv" in str(current.get("nowcast", {}).get("label", "")).lower() else "media"
        return {
            "time": now_local().strftime("%d/%m/%Y %H:%M"),
            "title": f"Aumento del segnale 0–3 h: {previous.get('nowcast', {}).get('label', '—')} → {current['nowcast']['label']}",
            "text": "Il rischio a brevissimo termine è aumentato rispetto al controllo precedente.",
            "window": "prossime 0–3 ore", "confidence": confidence,
            "evidence": current["nowcast"].get("note", "")
        }

    pm = previous.get("territory", {}).get("metrics", {})
    cm = current.get("territory", {}).get("metrics", {})

    def val(metrics: dict[str, Any], key: str) -> float | None:
        return safe_float(metrics.get(key, {}).get("value"))

    # Pioggia dell'ultima ora: privilegia SRT1 DPC quando presente.
    pr, cr = val(pm, "rain_1h"), val(cm, "rain_1h")
    if cr is not None and cr >= 5 and (pr is None or pr < 2 or cr - pr >= 5):
        return {
            "time": now_local().strftime("%d/%m/%Y %H:%M"),
            "title": "Aumento significativo delle precipitazioni su Giammoro",
            "text": f"La cumulata riferita all'ultima ora sul punto/area di Giammoro è salita a circa {cr:.1f} mm.",
            "window": "ultima ora / prossime 0–3 ore", "confidence": "alta" if "Radar-DPC" in str(cm.get("rain_1h", {}).get("quality", "")) else "media",
            "evidence": str(cm.get("rain_1h", {}).get("quality", "fonte territoriale"))
        }

    pg, cg = val(pm, "gust"), val(cm, "gust")
    if cg is not None and cg >= 50 and (pg is None or pg < 50 or cg - pg >= 20):
        return {
            "time": now_local().strftime("%d/%m/%Y %H:%M"),
            "title": "Aumento marcato delle raffiche previste/stimate su Giammoro",
            "text": f"La raffica di riferimento è salita a circa {cg:.0f} km/h.",
            "window": "brevissimo termine", "confidence": "media",
            "evidence": "metrica territoriale sul punto di Giammoro; verificare osservazioni locali quando disponibili"
        }

    pt, ct = val(pm, "temperature"), val(cm, "temperature")
    if pt is not None and ct is not None and abs(ct - pt) >= 4:
        direction = "aumento" if ct > pt else "calo"
        return {
            "time": now_local().strftime("%d/%m/%Y %H:%M"),
            "title": f"{direction.title()} marcato della temperatura su Giammoro",
            "text": f"Temperatura di riferimento: {pt:.1f} → {ct:.1f} °C.",
            "window": "dal controllo precedente", "confidence": "media-alta" if "Radar-DPC" in str(cm.get("temperature", {}).get("quality", "")) else "media",
            "evidence": str(cm.get("temperature", {}).get("quality", "metrica territoriale"))
        }

    pp, cp = val(pm, "pressure"), val(cm, "pressure")
    if pp is not None and cp is not None and abs(cp - pp) >= 3:
        direction = "aumento" if cp > pp else "calo"
        return {
            "time": now_local().strftime("%d/%m/%Y %H:%M"),
            "title": f"Rapido {direction} della pressione di riferimento",
            "text": f"Pressione: {pp:.1f} → {cp:.1f} hPa dal controllo precedente.",
            "window": "dal controllo precedente", "confidence": "media",
            "evidence": "stima sul punto; richiede conferma osservativa se la stazione locale è indisponibile"
        }
    return None


def load_previous() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {}
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def run(offline: bool = False) -> dict[str, Any]:
    previous = load_previous()
    errors: list[str] = []

    try:
        stations, station_meta = fetch_stations() if not offline else (previous.get("stations", []), {"source": "offline", "rows": 0})
    except Exception as exc:
        errors.append(f"stazioni: {exc}")
        stations = previous.get("stations", [])
        station_meta = {"source": "errore", "rows": 0}

    try:
        model_raw = fetch_models() if not offline else []
        model_summaries = [summarize_model(x) for x in model_raw]
    except Exception as exc:
        errors.append(f"modelli: {exc}")
        model_summaries = []

    try:
        ensembles = fetch_ensembles() if not offline else []
    except Exception as exc:
        errors.append(f"ensemble: {exc}")
        ensembles = []

    try:
        dpc_obs = fetch_dpc_observations() if not offline else previous.get("dpc_observations", {})
        if dpc_obs.get("errors"):
            errors.extend(f"radar-dpc: {e}" for e in dpc_obs["errors"])
    except Exception as exc:
        errors.append(f"radar-dpc: {exc}")
        dpc_obs = previous.get("dpc_observations", {})

    try:
        alert = fetch_alert() if not offline else previous.get("alert", {})
    except Exception as exc:
        errors.append(f"allerta: {exc}")
        alert = previous.get("alert", {
            "level_label": "Da verificare", "level_class": "unknown", "title": "Avviso ufficiale non acquisito",
            "text": "Errore di acquisizione; consultare direttamente DRPC Sicilia.", "validity": "—", "source": "DRPC Sicilia"
        })

    ref_model = choose_reference_model(model_summaries)
    territory = territory_from_reference_model(ref_model, dpc_obs) if model_summaries else previous.get("territory", territory_from_reference_model(None, dpc_obs))

    now_label, now_level, now_note = risk_from_models(model_summaries, "next_0_3h") if model_summaries else (
        previous.get("nowcast", {}).get("label", "Da verificare"), previous.get("nowcast", {}).get("level", "unknown"), "Modelli non aggiornati"
    )
    risk_label, risk_level, risk_note = risk_from_models(model_summaries, "next_3_48h") if model_summaries else (
        previous.get("risk_48h", {}).get("label", "Da verificare"), previous.get("risk_48h", {}).get("level", "unknown"), "Modelli non aggiornati"
    )

    now_label, now_level, now_note = nowcast_from_dpc_and_models(dpc_obs, now_label, now_level, now_note)

    current = {
        "meta": {
            "schema_version": "2.1", "last_check": now_local().strftime("%d/%m/%Y %H:%M %Z"),
            "analysis_engine": "collector Python + regole deterministiche", "reference_area": "Giammoro, Pace del Mela (ME)",
            "coordinates": [REF["latitude"], REF["longitude"]], "collector_status": "offline" if offline else ("degraded" if errors else "ok"),
            "collector_errors": errors
        },
        "primary_station": {
            "name": "MeteoGiammoro", "status": "maintenance", "status_label": "Fuori servizio",
            "excluded_from_analysis": True,
            "note": "Stazione esclusa dai calcoli perché in manutenzione, risoluzione guasto e test. Rientro previsto prima in TEST e poi ONLINE dopo validazione."
        },
        "nowcast": {"label": now_label, "level": now_level, "note": now_note + ". Fulminazioni non ancora acquisite automaticamente."},
        "risk_48h": {"label": risk_label, "level": risk_level, "note": risk_note},
        "territory": territory,
        "alert": alert,
        "latest_change": previous.get("latest_change", {
            "time": "—", "title": "Nessun cambiamento registrato", "text": "—", "window": "—", "confidence": "—", "evidence": "—"
        }),
        "stations": stations,
        "dpc_observations": dpc_obs,
        "nowcast_evidence": {
            "radar": dpc_radar_evidence(dpc_obs),
            "rain_gauges": f"Stazioni/pluviometri raccolti dal feed locale: {station_meta.get('rows', 0)} righe disponibili; vengono mostrate solo le stazioni selezionate e la rete originaria.",
            "lightning": "Connettore fulminazioni non ancora attivo: nessuna inferenza viene inventata in sua assenza.",
            "satellite": dpc_satellite_evidence(dpc_obs),
            "wind_pressure": "Il motore confronta vento/raffiche e pressione tra stazioni disponibili e modelli; i trend osservativi richiederanno la persistenza dello storico.",
            "local_effects": "Giammoro viene valutata come area costiera della Valle del Mela, con possibili differenze rispetto a Milazzo, rilievi di Santa Lucia/Monforte e Stretto di Messina."
        },
        "models": build_model_rows(model_summaries, ensembles) if model_summaries else previous.get("models", []),
        "model_details": model_summaries,
        "ensemble_details": ensembles,
        "reasoning": {
            "location": "Backend / GitHub Actions",
            "description": "Il collector acquisisce stazioni, modelli e avviso ufficiale, normalizza i valori e produce una stima riferita esclusivamente alle coordinate di Giammoro. Le stazioni vicine restano osservazioni separate. Le regole deterministiche danno priorità a Radar-DPC nel 0–3 h, segnalano variazioni e confrontano i modelli. L'analisi meteorologica esperta/AI resta un livello successivo per traiettorie complesse, fulminazioni non ancora integrate, convergenze e interpretazione sinottica."
        },
        "sources": [
            "DRPC Sicilia / CFD + bollettino nazionale DPC", "Radar-DPC (SRI/VMI/SRT1/CUM24/TEMP/IR10.8)", "Centro Meteorologico Siciliano - Database Stazioni Live",
            "SIAS / DRPC / reti originarie riportate dal feed", "ItaliaMeteo ICON-2I via Open-Meteo",
            "DWD ICON via Open-Meteo", "ECMWF IFS/ENS via Open-Meteo", "NOAA GFS/GEFS via Open-Meteo"
        ],
        "history": previous.get("history", [])[-50:]
    }

    change = significant_change(previous, current) if previous else None
    if change:
        current["latest_change"] = change
        current["history"] = ([{"time": change["time"], "text": change["title"]}] + current["history"])[:50]

    return current


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Non effettua richieste di rete; valida solo la pipeline sui dati esistenti")
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()
    data = run(offline=args.offline)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.stdout:
        sys.stdout.write(payload)
    else:
        DATA_PATH.write_text(payload, encoding="utf-8")
        HISTORY_PATH.write_text(json.dumps(data.get("history", []), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Aggiornato {DATA_PATH}")
        if data.get("meta", {}).get("collector_errors"):
            print("Avvisi:", " | ".join(data["meta"]["collector_errors"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
