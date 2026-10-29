#!/usr/bin/env python3
"""Archivio storico compatto del monitoraggio solare.

Conserva campioni grezzi per 31 giorni, sufficienti per i grafici 24 h / 7 d / 30 d,
e riepiloghi giornalieri per 10 anni. I buchi superiori a 45 minuti non vengono
interpolati e i dati non disponibili restano esplicitamente mancanti.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data.json"
HISTORY_PATH = ROOT / "solar_history.json"
SCHEMA_VERSION = "1.0"
RAW_RETENTION_DAYS = 31
DAILY_RETENTION_DAYS = 3660
MAX_INTEGRATION_GAP_MINUTES = 45
TIMEZONE_NAME = "Europe/Rome"


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def finite_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _ground_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name") or item.get("id") or "Stazione",
        "source": item.get("source"),
        "status": item.get("status") or "unknown",
        "solar_wm2": finite_number(item.get("solar_wm2")),
        "uv_index": finite_number(item.get("uv_index")),
        "observed_at": item.get("observed_at"),
        "retrieved_at": item.get("retrieved_at"),
    }


def _satellite_snapshot(solar: dict[str, Any]) -> dict[str, Any]:
    observation = solar.get("observation") or {}
    return {
        "name": "Giammoro · LSA SAF",
        "source": observation.get("source") or solar.get("source") or "EUMETSAT LSA SAF",
        "status": solar.get("status") or "unknown",
        "solar_wm2": finite_number(observation.get("total_shortwave_wm2")),
        "uv_index": None,
        "direct_wm2": finite_number(observation.get("direct_horizontal_wm2")),
        "diffuse_wm2": finite_number(observation.get("diffuse_wm2")),
        "direct_fraction": finite_number(observation.get("direct_fraction")),
        "observed_at": observation.get("observed_at"),
        "retrieved_at": solar.get("updated_at"),
    }


def build_sample(solar: dict[str, Any], now_utc: datetime | None = None) -> dict[str, Any]:
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stamp = parse_dt(solar.get("updated_at")) or now_utc
    sources: dict[str, dict[str, Any]] = {}
    for item in solar.get("ground_observations") or []:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("id") or "").strip()
        if source_id:
            sources[source_id] = _ground_snapshot(item)
    sources["lsa-saf"] = _satellite_snapshot(solar)
    return {"timestamp": iso_utc(stamp), "sources": sources}


def empty_history() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "started_at": None,
        "timezone": TIMEZONE_NAME,
        "raw_retention_days": RAW_RETENTION_DAYS,
        "daily_retention_days": DAILY_RETENTION_DAYS,
        "integration_gap_max_minutes": MAX_INTEGRATION_GAP_MINUTES,
        "catalog": {},
        "samples": [],
        "daily": [],
    }


def load_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_history()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return empty_history()
    if not isinstance(raw, dict):
        return empty_history()
    result = empty_history()
    result.update(raw)
    result["samples"] = list(raw.get("samples") or [])
    result["daily"] = list(raw.get("daily") or [])
    result["catalog"] = dict(raw.get("catalog") or {})
    return result


def _local_date(timestamp: str, timezone_name: str = TIMEZONE_NAME) -> str | None:
    dt = parse_dt(timestamp)
    if not dt:
        return None
    return dt.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def _valid_source_point(source: dict[str, Any] | None) -> bool:
    return isinstance(source, dict) and source.get("status") == "ok"


def summarize_day(samples: list[dict[str, Any]], local_day: str, timezone_name: str = TIMEZONE_NAME) -> dict[str, Any]:
    day_samples = [sample for sample in samples if _local_date(str(sample.get("timestamp") or ""), timezone_name) == local_day]
    source_ids: set[str] = set()
    for sample in day_samples:
        source_ids.update((sample.get("sources") or {}).keys())

    summaries: dict[str, Any] = {}
    for source_id in sorted(source_ids):
        solar_points: list[tuple[datetime, float]] = []
        uv_values: list[float] = []
        source_name = source_id
        source_label = None
        valid_sample_times: list[datetime] = []

        for sample in day_samples:
            stamp = parse_dt(sample.get("timestamp"))
            source = (sample.get("sources") or {}).get(source_id)
            if not stamp or not _valid_source_point(source):
                continue
            source_name = str(source.get("name") or source_name)
            source_label = source.get("source") or source_label
            solar = finite_number(source.get("solar_wm2"))
            uv = finite_number(source.get("uv_index"))
            if solar is not None:
                solar_points.append((stamp, max(0.0, solar)))
            if uv is not None:
                uv_values.append(max(0.0, uv))
            if solar is not None or uv is not None:
                valid_sample_times.append(stamp)

        solar_points.sort(key=lambda item: item[0])
        energy = 0.0
        coverage = 0
        for (prev_dt, prev_value), (curr_dt, curr_value) in zip(solar_points, solar_points[1:]):
            delta_minutes = int((curr_dt - prev_dt).total_seconds() / 60)
            if 0 < delta_minutes <= MAX_INTEGRATION_GAP_MINUTES:
                energy += ((prev_value + curr_value) / 2.0) * (delta_minutes / 60.0) / 1000.0
                coverage += delta_minutes

        solar_values = [value for _, value in solar_points]
        summaries[source_id] = {
            "name": source_name,
            "source": source_label,
            "samples": len(valid_sample_times),
            "solar_samples": len(solar_values),
            "uv_samples": len(uv_values),
            "solar_max_wm2": round(max(solar_values), 1) if solar_values else None,
            "solar_mean_wm2": round(sum(solar_values) / len(solar_values), 1) if solar_values else None,
            "uv_max": round(max(uv_values), 2) if uv_values else None,
            "energy_kwh_m2": round(energy, 4) if solar_values else None,
            "coverage_minutes": coverage,
            "first_sample_at": iso_utc(min(valid_sample_times)) if valid_sample_times else None,
            "last_sample_at": iso_utc(max(valid_sample_times)) if valid_sample_times else None,
        }

    return {"date": local_day, "sources": summaries}


def _catalog_from_samples(samples: list[dict[str, Any]], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    catalog = dict(existing or {})
    for sample in samples:
        for source_id, source in (sample.get("sources") or {}).items():
            if not isinstance(source, dict):
                continue
            catalog[source_id] = {
                "name": source.get("name") or source_id,
                "source": source.get("source"),
            }
    return catalog


def update_history(data_path: Path = DATA_PATH, history_path: Path = HISTORY_PATH, now_utc: datetime | None = None) -> dict[str, Any]:
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    solar = data.get("solar_monitoring") or {}
    sample = build_sample(solar, now_utc=now_utc)
    history = load_history(history_path)

    samples_by_timestamp: dict[str, dict[str, Any]] = {}
    for existing in history.get("samples") or []:
        stamp = str(existing.get("timestamp") or "")
        if parse_dt(stamp):
            samples_by_timestamp[stamp] = existing
    samples_by_timestamp[sample["timestamp"]] = sample
    all_samples = sorted(samples_by_timestamp.values(), key=lambda item: parse_dt(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc))

    daily_by_date = {str(item.get("date")): item for item in history.get("daily") or [] if isinstance(item, dict) and item.get("date")}
    affected_days = sorted({_local_date(str(item.get("timestamp") or ""), TIMEZONE_NAME) for item in all_samples} - {None})
    for local_day in affected_days:
        daily_by_date[str(local_day)] = summarize_day(all_samples, str(local_day), TIMEZONE_NAME)

    raw_cutoff = now_utc - timedelta(days=RAW_RETENTION_DAYS)
    retained_samples = [item for item in all_samples if (parse_dt(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc)) >= raw_cutoff]

    local_today = now_utc.astimezone(ZoneInfo(TIMEZONE_NAME)).date()
    daily_cutoff = local_today - timedelta(days=DAILY_RETENTION_DAYS)
    retained_daily: list[dict[str, Any]] = []
    for day_key, item in daily_by_date.items():
        try:
            parsed_day = date.fromisoformat(day_key)
        except ValueError:
            continue
        if parsed_day >= daily_cutoff:
            retained_daily.append(item)
    retained_daily.sort(key=lambda item: item["date"])

    started_at = history.get("started_at") or (all_samples[0]["timestamp"] if all_samples else sample["timestamp"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": iso_utc(now_utc),
        "started_at": started_at,
        "timezone": TIMEZONE_NAME,
        "raw_retention_days": RAW_RETENTION_DAYS,
        "daily_retention_days": DAILY_RETENTION_DAYS,
        "integration_gap_max_minutes": MAX_INTEGRATION_GAP_MINUTES,
        "catalog": _catalog_from_samples(all_samples, history.get("catalog")),
        "samples": retained_samples,
        "daily": retained_daily,
    }

    tmp = history_path.with_suffix(history_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(history_path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument("--history", default=str(HISTORY_PATH))
    args = parser.parse_args()
    payload = update_history(Path(args.data), Path(args.history))
    print(
        "Storico solare: "
        f"{len(payload['samples'])} campioni grezzi, {len(payload['daily'])} giorni, "
        f"fonti={len(payload['catalog'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
