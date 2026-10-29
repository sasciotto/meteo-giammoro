#!/usr/bin/env python3
"""Monitoraggio solare per Giammoro tramite EUMETSAT LSA SAF MDSSFTD.

Il modulo aggiorna ``data.json`` senza rendere la pipeline meteo dipendente
alla disponibilita' del servizio solare. Se le credenziali LSA SAF non sono
configurate o il prodotto non e' disponibile, conserva l'ultima osservazione
nota e marca esplicitamente lo stato come non disponibile/stale.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np
import requests
from netCDF4 import Dataset

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "stations.json"
DATA_PATH = ROOT / "data.json"
BASE_URL = "https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MSG/MDSSFTD/NETCDF"
SOURCE_NAME = "EUMETSAT LSA SAF MDSSFTD (LSA-207)"
SOURCE_PAGE = "https://lsa-saf.eumetsat.int/en/data/products/radiation/"
METRIC_VERSION = "solar-observation-v1"
SCHEMA_VERSION = "1.0"
MAX_LOOKBACK_HOURS = 4
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "MeteoGiammoroDashboard/0.3 (+public weather dashboard; respectful polling)",
})


class CredentialsMissing(RuntimeError):
    pass


class AuthenticationError(RuntimeError):
    pass


def load_reference() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    ref = config["reference"]
    return {
        "name": ref["name"],
        "latitude": float(ref["latitude"]),
        "longitude": float(ref["longitude"]),
        "timezone": str(ref["timezone"]),
    }


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def rounded_quarter_hour(now_utc: datetime | None = None) -> datetime:
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    minute = (now_utc.minute // 15) * 15
    return now_utc.replace(minute=minute, second=0, microsecond=0)


def candidate_product_times(now_utc: datetime | None = None, lookback_hours: int = MAX_LOOKBACK_HOURS) -> Iterable[datetime]:
    current = rounded_quarter_hour(now_utc)
    for step in range(lookback_hours * 4 + 1):
        yield current - timedelta(minutes=15 * step)


def product_url(stamp: datetime) -> str:
    stamp = stamp.astimezone(timezone.utc)
    name = f"NETCDF4_LSASAF_MSG_MDSSFTD_MSG-Disk_{stamp:%Y%m%d%H%M}.nc"
    return f"{BASE_URL}/{stamp:%Y/%m/%d}/{name}"


def download_latest(username: str, password: str, now_utc: datetime | None = None) -> tuple[bytes, datetime, str]:
    for stamp in candidate_product_times(now_utc):
        url = product_url(stamp)
        response = SESSION.get(url, auth=(username, password), timeout=45)
        if response.status_code == 401:
            raise AuthenticationError("Credenziali LSA SAF non accettate")
        if response.status_code == 404:
            continue
        response.raise_for_status()
        if not response.content:
            continue
        return response.content, stamp, url
    raise RuntimeError("Nessun prodotto MDSSFTD disponibile nelle ultime 4 ore")


def _find_variable(dataset: Dataset, names: tuple[str, ...]) -> str | None:
    available = {name.lower(): name for name in dataset.variables}
    for candidate in names:
        if candidate.lower() in available:
            return available[candidate.lower()]
    return None


def _nearest_index(dataset: Dataset, latitude: float, longitude: float) -> tuple[int, int, float, float]:
    lat_name = _find_variable(dataset, ("lat", "latitude"))
    lon_name = _find_variable(dataset, ("lon", "longitude"))
    if not lat_name or not lon_name:
        raise RuntimeError("Coordinate latitude/longitude non trovate nel NetCDF MDSSFTD")

    lats = np.asarray(dataset.variables[lat_name][:], dtype=float)
    lons = np.asarray(dataset.variables[lon_name][:], dtype=float)

    if lats.ndim == 1 and lons.ndim == 1:
        i = int(np.nanargmin(np.abs(lats - latitude)))
        j = int(np.nanargmin(np.abs(lons - longitude)))
        return i, j, float(lats[i]), float(lons[j])

    if lats.shape != lons.shape or lats.ndim != 2:
        raise RuntimeError("Griglia coordinate MDSSFTD non supportata")

    distance2 = (lats - latitude) ** 2 + (lons - longitude) ** 2
    flat = int(np.nanargmin(distance2))
    i, j = np.unravel_index(flat, lats.shape)
    return int(i), int(j), float(lats[i, j]), float(lons[i, j])


def _point_value(dataset: Dataset, variable: str, i: int, j: int) -> float | None:
    if variable not in dataset.variables:
        return None
    arr = dataset.variables[variable][:]
    while getattr(arr, "ndim", 0) > 2:
        arr = arr[0]
    if getattr(arr, "ndim", 0) != 2:
        return None
    value = arr[i, j]
    if np.ma.is_masked(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def decode_netcdf(content: bytes, stamp: datetime, source_url: str, latitude: float, longitude: float) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".nc") as tmp:
        tmp.write(content)
        tmp.flush()
        with Dataset(tmp.name, "r") as dataset:
            i, j, grid_lat, grid_lon = _nearest_index(dataset, latitude, longitude)
            total = _point_value(dataset, "DSSF_TOT", i, j)
            diffuse_fraction = _point_value(dataset, "FRACTION_DIFFUSE", i, j)
            aod = _point_value(dataset, "AOD", i, j)
            opacity = _point_value(dataset, "OPACITY_INDEX", i, j)
            q_flag = _point_value(dataset, "Q_FLAG", i, j)

    if total is None:
        raise RuntimeError("DSSF_TOT non disponibile sul punto di Giammoro")

    if diffuse_fraction is not None and not 0 <= diffuse_fraction <= 1:
        diffuse_fraction = None

    diffuse = round(total * diffuse_fraction, 1) if diffuse_fraction is not None else None
    direct = round(total * (1 - diffuse_fraction), 1) if diffuse_fraction is not None else None
    direct_fraction = round(1 - diffuse_fraction, 4) if diffuse_fraction is not None else None

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_PAGE,
        "product_url": source_url,
        "observed_at": stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "grid_point": {"latitude": round(grid_lat, 4), "longitude": round(grid_lon, 4)},
        "total_shortwave_wm2": round(total, 1),
        "diffuse_fraction": round(diffuse_fraction, 4) if diffuse_fraction is not None else None,
        "diffuse_wm2": diffuse,
        "direct_horizontal_wm2": direct,
        "direct_fraction": direct_fraction,
        "aod_550nm": round(aod, 4) if aod is not None else None,
        "opacity_index": round(opacity, 4) if opacity is not None else None,
        "quality_flag": int(q_flag) if q_flag is not None and float(q_flag).is_integer() else q_flag,
    }


def collect_observation(reference: dict[str, Any], now_utc: datetime | None = None) -> dict[str, Any]:
    username = os.getenv("LSASAF_USERNAME", "").strip()
    password = os.getenv("LSASAF_PASSWORD", "").strip()
    if not username or not password:
        raise CredentialsMissing("Credenziali LSA SAF non configurate")
    content, stamp, url = download_latest(username, password, now_utc=now_utc)
    return decode_netcdf(content, stamp, url, reference["latitude"], reference["longitude"])


def observation_age_minutes(observation: dict[str, Any] | None, now_utc: datetime | None = None) -> int | None:
    if not observation:
        return None
    observed = parse_dt(observation.get("observed_at"))
    if not observed:
        return None
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return max(0, int((now_utc - observed.astimezone(timezone.utc)).total_seconds() / 60))


def update_daily_summary(previous: dict[str, Any] | None, observation: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    tz = ZoneInfo(timezone_name)
    observed = parse_dt(observation.get("observed_at"))
    if not observed:
        raise RuntimeError("Timestamp osservazione solare non valido")
    local_day = observed.astimezone(tz).date().isoformat()
    prev_daily = dict((previous or {}).get("daily") or {})
    prev_obs = (previous or {}).get("observation") or {}
    prev_dt = parse_dt(prev_obs.get("observed_at"))

    if prev_daily.get("local_date") != local_day:
        daily = {
            "local_date": local_day,
            "energy_kwh_m2": 0.0,
            "coverage_minutes": 0,
            "samples": 1,
            "first_observed_at": observation["observed_at"],
            "last_observed_at": observation["observed_at"],
        }
        return daily

    daily = {
        "local_date": local_day,
        "energy_kwh_m2": float(prev_daily.get("energy_kwh_m2") or 0.0),
        "coverage_minutes": int(prev_daily.get("coverage_minutes") or 0),
        "samples": int(prev_daily.get("samples") or 0),
        "first_observed_at": prev_daily.get("first_observed_at") or observation["observed_at"],
        "last_observed_at": prev_daily.get("last_observed_at") or observation["observed_at"],
    }

    if prev_dt and observed > prev_dt:
        delta_minutes = int((observed - prev_dt).total_seconds() / 60)
        prev_total = prev_obs.get("total_shortwave_wm2")
        curr_total = observation.get("total_shortwave_wm2")
        if 0 < delta_minutes <= 45 and prev_total is not None and curr_total is not None:
            increment = ((float(prev_total) + float(curr_total)) / 2.0) * (delta_minutes / 60.0) / 1000.0
            daily["energy_kwh_m2"] = round(daily["energy_kwh_m2"] + increment, 4)
            daily["coverage_minutes"] += delta_minutes
        daily["samples"] += 1
        daily["last_observed_at"] = observation["observed_at"]

    return daily


def update_data(
    path: Path = DATA_PATH,
    now_utc: datetime | None = None,
    previous_path: Path | None = None,
) -> dict[str, Any]:
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    data = json.loads(path.read_text(encoding="utf-8"))
    reference = load_reference()
    previous = data.get("solar_monitoring") or {}
    if previous_path and previous_path.exists():
        try:
            previous_data = json.loads(previous_path.read_text(encoding="utf-8"))
            previous = previous_data.get("solar_monitoring") or previous
        except (OSError, ValueError, TypeError):
            pass
    previous_observation = previous.get("observation") or None

    base = {
        "schema_version": SCHEMA_VERSION,
        "metric_version": METRIC_VERSION,
        "reference": {
            "name": reference["name"],
            "latitude": reference["latitude"],
            "longitude": reference["longitude"],
        },
        "source": SOURCE_NAME,
        "source_url": SOURCE_PAGE,
        "ground_support": {
            "source": "Stazione meteo Pace del Mela",
            "status": "endpoint_unverified",
            "solar_wm2": None,
            "uv_index": None,
            "note": "Sensore Solare/UV noto, ma nessun endpoint machine-readable stabile e verificato e' ancora integrato.",
        },
    }

    try:
        observation = collect_observation(reference, now_utc=now_utc)
        age = observation_age_minutes(observation, now_utc=now_utc)
        observation["age_minutes"] = age
        daily = update_daily_summary(previous, observation, reference["timezone"])
        status = "ok" if age is not None and age <= 180 else "stale"
        message = "Osservazione satellitare LSA SAF disponibile." if status == "ok" else "Ultima osservazione LSA SAF oltre 180 minuti."
    except CredentialsMissing as exc:
        observation = previous_observation
        if observation:
            observation = dict(observation)
            observation["age_minutes"] = observation_age_minutes(observation, now_utc=now_utc)
        daily = previous.get("daily") or None
        status = "credentials_missing"
        message = str(exc)
    except Exception as exc:
        observation = previous_observation
        if observation:
            observation = dict(observation)
            observation["age_minutes"] = observation_age_minutes(observation, now_utc=now_utc)
        daily = previous.get("daily") or None
        status = "stale" if observation else "unavailable"
        message = f"Monitoraggio solare non aggiornato: {exc}"

    payload = {
        **base,
        "status": status,
        "message": message,
        "updated_at": now_utc.isoformat().replace("+00:00", "Z"),
        "observation": observation,
        "daily": daily,
    }
    data["solar_monitoring"] = payload
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--previous", default=None)
    args = parser.parse_args()
    previous_path = Path(args.previous) if args.previous else None
    payload = update_data(Path(args.data), previous_path=previous_path)
    print(f"Monitoraggio solare: {payload['status']} - {payload['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
