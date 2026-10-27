#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

import home_forecast as base

CACHE_PATH = Path('/tmp/open-meteo-model-cache.json')
TZ = ZoneInfo('Europe/Rome')
MODEL_LABELS = {
    'italia_meteo_arpae_icon_2i': 'ICON-2I',
    'dwd_icon_seamless': 'DWD ICON',
    'ecmwf_ifs': 'ECMWF IFS',
    'ncep_gfs_seamless': 'NOAA GFS',
}
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
THUNDER_CODES = {95, 96, 99}


def _num(value: Any) -> float | None:
    return base.num(value)


def _median(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def _reference_now(data: dict) -> datetime:
    for raw in (
        ((data.get('home_summary') or {}).get('generated_at')),
        ((data.get('meta') or {}).get('last_check_iso')),
    ):
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw))
            return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)
        except (TypeError, ValueError):
            pass
    return datetime.now(TZ)


def _style(rows: list[dict], cloud: float | None, spread: float | None, rain: float | None, night: bool) -> dict[str, Any]:
    count = len(rows)
    majority = count // 2 + 1
    codes = [int(v) for v in (_num(row.get('weather_code')) for row in rows) if v is not None]
    rain_votes = sum(
        1
        for row in rows
        if (_num(row.get('precipitation')) or 0.0) >= 0.2
        or (int(_num(row.get('weather_code'))) if _num(row.get('weather_code')) is not None else -1) in RAIN_CODES
    )
    thunder_votes = sum(1 for code in codes if code in THUNDER_CODES or code >= 95)

    if thunder_votes >= majority:
        return {'icon': '⛈', 'kind': 'storm', 'label': 'Possibili temporali', 'weather_code': 95}
    if rain_votes >= majority or (rain is not None and rain >= 0.2):
        return {'icon': '☂', 'kind': 'rain', 'label': 'Possibili piogge', 'weather_code': 61}

    if cloud is None:
        return {'icon': '◌', 'kind': 'cloudy', 'label': 'Condizioni del cielo incerte', 'weather_code': 2}

    if spread is not None and spread >= 35:
        return {
            'icon': '☁' if night or cloud >= 70 else '⛅',
            'kind': 'cloudy',
            'label': 'Nuvoloso variabile' if cloud >= 70 else 'Cielo variabile',
            'weather_code': 3 if cloud >= 70 else 2,
        }

    if cloud >= 85:
        return {'icon': '☁', 'kind': 'cloudy', 'label': 'Molto nuvoloso', 'weather_code': 3}
    if cloud >= 60:
        return {'icon': '☁', 'kind': 'cloudy', 'label': 'Nuvoloso', 'weather_code': 3}
    if cloud >= 35:
        return {'icon': '☁' if night else '⛅', 'kind': 'cloudy', 'label': 'Parzialmente nuvoloso', 'weather_code': 2}
    if cloud >= 20:
        return {'icon': '☁' if night else '⛅', 'kind': 'cloudy', 'label': 'Poco nuvoloso', 'weather_code': 1}

    clear_votes = sum(1 for row in rows if (_num(row.get('cloud_cover')) is not None and _num(row.get('cloud_cover')) <= 20))
    strong_clear = count >= 3 and clear_votes >= max(3, math.ceil(count * 0.75)) and (spread or 0) <= 20
    if strong_clear:
        return {'icon': '☾' if night else '☀', 'kind': 'calm', 'label': 'Sereno', 'weather_code': 0}
    return {'icon': '☾' if night else '⛅', 'kind': 'cloudy', 'label': 'Poco nuvoloso', 'weather_code': 1}


def consensus_hourly(cache: dict[str, dict], now: datetime, limit: int = 36) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    labels: list[str] = []

    for model_id, raw in cache.items():
        if not isinstance(raw, dict) or not isinstance(raw.get('hourly'), dict):
            continue
        label = MODEL_LABELS.get(model_id, model_id)
        rows = base.hourly_forecast(raw, now, limit=max(limit, 48))
        if not rows:
            continue
        labels.append(label)
        for row in rows:
            grouped.setdefault(str(row.get('time')), []).append(row)

    if len(labels) < 2:
        return [], labels

    output: list[dict[str, Any]] = []
    for timestamp in sorted(grouped):
        rows = grouped[timestamp]
        if len(rows) < 2:
            continue
        try:
            dt = datetime.fromisoformat(timestamp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            else:
                dt = dt.astimezone(TZ)
        except (TypeError, ValueError):
            continue

        clouds = [v for v in (_num(row.get('cloud_cover')) for row in rows) if v is not None]
        precip = [v for v in (_num(row.get('precipitation')) for row in rows) if v is not None]
        temps = [v for v in (_num(row.get('temperature')) for row in rows) if v is not None]
        winds = [v for v in (_num(row.get('wind_kmh')) for row in rows) if v is not None]
        gusts = [v for v in (_num(row.get('gust_kmh')) for row in rows) if v is not None]

        cloud = _median(clouds)
        cloud_spread = (max(clouds) - min(clouds)) if len(clouds) >= 2 else 0.0 if clouds else None
        rain = _median(precip)
        style = _style(rows, cloud, cloud_spread, rain, night=(dt.hour >= 19 or dt.hour < 7))

        output.append({
            'time': dt.isoformat(timespec='minutes'),
            'label_time': dt.strftime('%H:%M'),
            'temperature': None if not temps else round(_median(temps), 1),
            'precipitation': None if rain is None else round(rain, 1),
            'precipitation_min': None if not precip else round(min(precip), 1),
            'precipitation_max': None if not precip else round(max(precip), 1),
            'cloud_cover': None if cloud is None else round(cloud, 1),
            'cloud_spread': None if cloud_spread is None else round(cloud_spread, 1),
            'wind_kmh': None if not winds else round(_median(winds), 1),
            'gust_kmh': None if not gusts else round(_median(gusts), 1),
            'model_count': len(rows),
            'consensus': True,
            **style,
        })
        if len(output) >= limit:
            break

    return output, labels


def apply(data: dict, cache: dict[str, dict], now: datetime | None = None) -> bool:
    home = data.get('home_summary')
    if not isinstance(home, dict) or not home.get('forecast_available'):
        return False

    rows, labels = consensus_hourly(cache, now or _reference_now(data), limit=36)
    if not rows or len(labels) < 2:
        return False

    home['hourly'] = rows
    home['source'] = f"Consenso multi-modello ({' · '.join(labels)})"
    home['hourly_consensus'] = {
        'available': True,
        'models': labels,
        'model_count': len(labels),
        'method': 'mediana per ora; condizioni del cielo conservative quando i modelli divergono',
        'clear_sky_rule': 'Sereno solo con almeno 3 modelli concordi e spread di nuvolosità <= 20 punti',
    }
    return True


def apply_from_cache(data: dict, cache_path: Path = CACHE_PATH) -> bool:
    if not cache_path.exists():
        return False
    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return False
    return apply(data, cache)
