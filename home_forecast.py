#!/usr/bin/env python3
"""Sintesi deterministica per la home di Meteo Giammoro.

La pagina non decide il meteo: questo modulo prepara condizioni attuali,
nowcast leggibile, previsione oraria e riepilogo oggi/domani.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import median
from typing import Any


def num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        x = float(value)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def weather_style(code: int | float | None, night: bool = False) -> dict[str, str]:
    c = int(code) if num(code) is not None else -1
    if c >= 95:
        return {"icon": "⛈", "kind": "storm", "label": "Temporali"}
    if c in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return {"icon": "☂", "kind": "rain", "label": "Pioggia"}
    if c in {71, 73, 75, 77, 85, 86}:
        return {"icon": "❄", "kind": "cloudy", "label": "Neve"}
    if c in {45, 48}:
        return {"icon": "≋", "kind": "cloudy", "label": "Nebbia"}
    if c == 3:
        return {"icon": "☁", "kind": "cloudy", "label": "Molto nuvoloso"}
    if c == 2:
        return {"icon": "☁" if night else "⛅", "kind": "cloudy", "label": "Parzialmente nuvoloso"}
    if c == 1:
        return {"icon": "☾" if night else "🌤", "kind": "calm", "label": "Poco nuvoloso"}
    return {"icon": "☾" if night else "☀", "kind": "calm", "label": "Sereno"}


def _lightning_count(data: dict, radius: int) -> int:
    l = data.get("lightning", {}) or {}
    if l.get("status") != "ok":
        return 0
    item = (l.get("radii", {}) or {}).get(str(radius), {}) or {}
    value = item.get("flash_count", item.get("frequency_sum", 0))
    n = num(value)
    return max(0, int(n or 0))


def current_summary(data: dict, now: datetime) -> dict[str, Any]:
    metrics = ((data.get("territory", {}) or {}).get("metrics", {}) or {})
    tr = data.get("nowcast_tracking", {}) or {}
    hazard = tr.get("hazard_cell") or tr.get("cell") or {}
    motion = tr.get("motion", {}) or {}
    rain = num((metrics.get("rain_1h", {}) or {}).get("value")) or 0.0
    cloud = num((metrics.get("cloud_cover", {}) or {}).get("value"))
    flashes20 = _lightning_count(data, 20)
    hazard_distance = num(hazard.get("distance_km"))
    hazard_peak = num(hazard.get("peak_value")) or 0.0
    product = str(tr.get("product") or "SRI").upper()
    radar_near = hazard_distance is not None and hazard_distance <= 15 and (
        (product == "SRI" and hazard_peak >= 1.0) or (product == "VMI" and hazard_peak >= 30.0)
    )
    night = now.hour >= 19 or now.hour < 7

    if flashes20 > 0:
        style = {"icon": "⛈", "kind": "storm", "label": "Temporali nelle vicinanze"}
    elif rain >= 0.2:
        style = {"icon": "☂", "kind": "rain", "label": "Pioggia in corso o appena rilevata"}
    elif radar_near:
        style = {"icon": "☂", "kind": "rain", "label": "Precipitazioni nelle vicinanze"}
    elif cloud is not None and cloud >= 80:
        style = {"icon": "☁", "kind": "cloudy", "label": "Cielo molto nuvoloso"}
    elif cloud is not None and cloud >= 45:
        style = {"icon": "☁" if night else "⛅", "kind": "cloudy", "label": "Cielo parzialmente nuvoloso"}
    else:
        style = {"icon": "☾" if night else "☀", "kind": "calm", "label": "Cielo poco nuvoloso" if cloud is not None else "Situazione attuale"}

    level = str((data.get("nowcast", {}) or {}).get("level") or "unknown").lower()
    if "elev" in level:
        status_label, status_class = "Attenzione", "elevato"
    elif "moder" in level:
        status_label, status_class = "Da monitorare", "moderato"
    else:
        status_label, status_class = "Tranquillo", "low"

    short = short_term_summary(data, hazard, motion, flashes20)
    storm = storm_summary(data, hazard, motion, flashes20)
    return {**style, "status_label": status_label, "status_class": status_class, "short_term": short, "storm": storm}


def short_term_summary(data: dict, hazard: dict, motion: dict, flashes20: int) -> dict[str, str]:
    dist = num(hazard.get("distance_km"))
    eta = num(motion.get("eta_minutes")) if motion.get("status") == "tracked" else None
    level = str((data.get("nowcast", {}) or {}).get("level") or "").lower()
    if flashes20 > 0:
        return {"title": "Temporali da seguire", "text": f"Osservati {flashes20} flash entro 20 km da Giammoro.", "icon": "⛈"}
    if eta is not None and eta <= 180:
        return {"title": "Possibile arrivo di pioggia", "text": f"La cella tracciata potrebbe raggiungere l'area in circa {int(round(eta))} minuti.", "icon": "☂"}
    if dist is not None and dist <= 15:
        return {"title": "Fenomeni molto vicini", "text": f"La cella radar più rilevante è a circa {dist:g} km da Giammoro.", "icon": "☂"}
    if dist is not None and dist <= 25:
        return {"title": "Fenomeni nelle vicinanze", "text": f"Il radar rileva una cella rilevante a circa {dist:g} km da Giammoro.", "icon": "☂"}
    if "elev" in level:
        return {"title": "Instabilità da monitorare", "text": "Il quadro a brevissimo termine richiede attenzione, ma non implica automaticamente un temporale su Giammoro.", "icon": "⚠"}
    if "moder" in level:
        return {"title": "Situazione da monitorare", "text": "Sono presenti segnali di instabilità nell'area, senza un impatto diretto certo su Giammoro.", "icon": "◷"}
    return {"title": "Nessun fenomeno rilevante", "text": "Non emergono segnali importanti a brevissimo termine.", "icon": "✓"}


def storm_summary(data: dict, hazard: dict, motion: dict, flashes20: int) -> dict[str, str]:
    dist = num(hazard.get("distance_km"))
    eta = num(motion.get("eta_minutes")) if motion.get("status") == "tracked" else None
    if flashes20 > 0:
        return {"title": "Fulmini nelle vicinanze", "text": f"Rilevati {flashes20} flash entro 20 km da Giammoro.", "icon": "⛈"}
    if eta is not None and eta <= 180:
        return {"title": "Cella tracciata in avvicinamento", "text": f"Possibile interessamento dell'area in circa {int(round(eta))} minuti.", "icon": "☂"}
    if dist is not None and dist <= 25:
        return {"title": "Pioggia nelle vicinanze", "text": f"La cella di pericolo locale è a circa {dist:g} km da Giammoro; nessun fulmine entro 20 km nel dato disponibile.", "icon": "☂"}
    if dist is not None:
        return {"title": "Fenomeni lontani da Giammoro", "text": f"La cella radar più rilevante è a circa {dist:g} km; nessun fulmine entro 20 km nel dato disponibile.", "icon": "↗"}
    return {"title": "Nessun temporale vicino", "text": "Non risultano fulmini entro 20 km né celle radar locali rilevanti.", "icon": "☂"}


def _hour_rows(raw: dict, now: datetime, limit: int = 12) -> list[dict[str, Any]]:
    h = raw.get("hourly", {}) or {}
    rows: list[dict[str, Any]] = []
    for i, value in enumerate(h.get("time", []) or []):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=now.tzinfo)
        except (TypeError, ValueError):
            continue
        if dt < now.replace(minute=0, second=0, microsecond=0):
            continue
        row = {"dt": dt}
        for key, vals in h.items():
            if key != "time" and isinstance(vals, list) and i < len(vals):
                row[key] = vals[i]
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def hourly_forecast(raw: dict, now: datetime, limit: int = 12) -> list[dict[str, Any]]:
    result = []
    for row in _hour_rows(raw, now, limit):
        dt = row["dt"]
        style = weather_style(row.get("weather_code"), night=(dt.hour >= 19 or dt.hour < 7))
        result.append({
            "time": dt.isoformat(timespec="minutes"),
            "label_time": dt.strftime("%H:%M"),
            "temperature": num(row.get("temperature_2m")),
            "precipitation": num(row.get("precipitation")),
            "cloud_cover": num(row.get("cloud_cover")),
            "wind_kmh": num(row.get("wind_speed_10m")),
            "gust_kmh": num(row.get("wind_gusts_10m")),
            "weather_code": int(num(row.get("weather_code"))) if num(row.get("weather_code")) is not None else None,
            **style,
        })
    return result


def daily_forecast(raw: dict, now: datetime) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    h = raw.get("hourly", {}) or {}
    for i, value in enumerate(h.get("time", []) or []):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=now.tzinfo)
        except (TypeError, ValueError):
            continue
        delta = (dt.date() - now.date()).days
        if delta not in {0, 1}:
            continue
        row = {"dt": dt}
        for key, vals in h.items():
            if key != "time" and isinstance(vals, list) and i < len(vals):
                row[key] = vals[i]
        groups["today" if delta == 0 else "tomorrow"].append(row)

    out = []
    for key, label in (("today", "Oggi"), ("tomorrow", "Domani")):
        rows = groups.get(key, [])
        if not rows:
            continue
        temps = [num(r.get("temperature_2m")) for r in rows]
        temps = [x for x in temps if x is not None]
        precip = [num(r.get("precipitation")) for r in rows]
        precip_sum = round(sum(x for x in precip if x is not None), 1)
        gusts = [num(r.get("wind_gusts_10m")) for r in rows]
        gusts = [x for x in gusts if x is not None]
        codes = [int(num(r.get("weather_code"))) for r in rows if num(r.get("weather_code")) is not None]
        clouds = [num(r.get("cloud_cover")) for r in rows]
        clouds = [x for x in clouds if x is not None]
        thunder = any(c >= 95 for c in codes)
        rainy = any(c in {51,53,55,56,57,61,63,65,66,67,80,81,82} for c in codes) or precip_sum >= 0.5
        if thunder:
            style = {"icon": "⛈", "kind": "storm", "condition": "Possibili temporali"}
        elif rainy:
            style = {"icon": "☂", "kind": "rain", "condition": "Possibili piogge"}
        elif clouds and sum(clouds) / len(clouds) >= 65:
            style = {"icon": "☁", "kind": "cloudy", "condition": "Prevalentemente nuvoloso"}
        else:
            style = {"icon": "⛅", "kind": "calm", "condition": "Variabile o poco nuvoloso"}
        out.append({
            "key": key, "label": label,
            "temp_min": round(min(temps), 1) if temps else None,
            "temp_max": round(max(temps), 1) if temps else None,
            "precipitation_sum": precip_sum,
            "gust_max_kmh": round(max(gusts), 1) if gusts else None,
            "thunder_signal": thunder,
            **style,
        })
    return out


def multi_model_consensus(data: dict) -> dict[str, Any]:
    """Sintesi 3–48 h dei deterministici già acquisiti dal collector."""
    rows = []
    for model in data.get("model_details", []) or []:
        if not model.get("ok"):
            continue
        period = model.get("next_3_48h", {}) or {}
        precip = num(period.get("precip_sum"))
        gust = num(period.get("gust_max"))
        cape = num(period.get("cape_max"))
        if precip is None:
            continue
        rows.append({
            "label": model.get("label") or model.get("id") or "modello",
            "precip_mm": round(precip, 1),
            "gust_max_kmh": None if gust is None else round(gust, 1),
            "cape_max": None if cape is None else round(cape),
        })

    if not rows:
        return {"available": False, "models": []}

    amounts = [row["precip_mm"] for row in rows]
    wet = sum(1 for value in amounts if value >= 0.5)
    spread = max(amounts) - min(amounts)
    if spread <= 1.5:
        agreement = "alto"
        label = "Buon accordo tra i modelli"
    elif spread <= 5.0:
        agreement = "medio"
        label = "Scenario da monitorare"
    else:
        agreement = "basso"
        label = "Incertezza modellistica elevata"

    return {
        "available": True,
        "horizon": "3–48 h",
        "models_count": len(rows),
        "wet_models": wet,
        "dry_models": len(rows) - wet,
        "precip_min_mm": round(min(amounts), 1),
        "precip_max_mm": round(max(amounts), 1),
        "precip_median_mm": round(float(median(amounts)), 1),
        "agreement": agreement,
        "label": label,
        "models": rows,
        "note": (
            f"{wet}/{len(rows)} modelli indicano almeno 0,5 mm; "
            f"intervallo {min(amounts):.1f}–{max(amounts):.1f} mm, mediana {median(amounts):.1f} mm."
        ),
    }


def build(data: dict, raw: dict | None, source_label: str, now: datetime) -> dict[str, Any]:
    current = current_summary(data, now)
    days = daily_forecast(raw or {}, now)
    for day in days:
        day["basis"] = source_label
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "source": source_label,
        "current": current,
        "hourly": hourly_forecast(raw or {}, now),
        "days": days,
        "multi_model": multi_model_consensus(data),
        "forecast_available": bool(raw),
    }


def apply(data: dict, collector) -> dict:
    now = collector.now_local()
    raw = None
    source = "ItaliaMeteo ICON-2I"
    try:
        label, model_id, days = collector.MODEL_SPECS[0]
        source = label
        raw = collector.fetch_json(collector.OPEN_METEO, collector.model_params(model_id, max(3, days)))
    except Exception as exc:
        data.setdefault("meta", {}).setdefault("collector_errors", []).append(f"home-forecast: {exc}")
    data["home_summary"] = build(data, raw, source, now)
    return data
