#!/usr/bin/env python3
"""Orchestra lo storico solare recuperando i timeslot LSA SAF intermedi.

LSA-207 e' un prodotto a 15 minuti ma la pubblicazione NRT puo' arrivare in
ritardo. Se il prodotto piu' recente avanza di piu' di 15 minuti rispetto al
ciclo precedente, questo script prova a recuperare i timeslot intermedi e li
inserisce nello storico prima del campione corrente.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import solar_history
import solar_monitoring

MAX_BACKFILL_HOURS = 4


def parse_dt(value: Any) -> datetime | None:
    return solar_monitoring.parse_dt(value) if value else None


def missing_quarter_hours(previous_at: str | None, current_at: str | None, max_hours: int = MAX_BACKFILL_HOURS) -> list[datetime]:
    previous = parse_dt(previous_at)
    current = parse_dt(current_at)
    if previous is None or current is None or current <= previous + timedelta(minutes=15):
        return []
    earliest = max(previous + timedelta(minutes=15), current - timedelta(hours=max_hours))
    # allinea in avanti al quarto d'ora successivo se necessario
    minute = (earliest.minute // 15) * 15
    stamp = earliest.replace(minute=minute, second=0, microsecond=0)
    if stamp < earliest:
        stamp += timedelta(minutes=15)
    output: list[datetime] = []
    while stamp < current:
        output.append(stamp.astimezone(timezone.utc))
        stamp += timedelta(minutes=15)
    return output


def fetch_intermediate_observations(
    reference: dict[str, Any],
    previous_at: str | None,
    current_at: str | None,
    username: str,
    password: str,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for stamp in missing_quarter_hours(previous_at, current_at):
        url = solar_monitoring.product_url(stamp)
        response = solar_monitoring.SESSION.get(url, auth=(username, password), timeout=45)
        if response.status_code == 401:
            raise solar_monitoring.AuthenticationError("Credenziali LSA SAF non accettate")
        if response.status_code == 404:
            continue
        response.raise_for_status()
        if not response.content:
            continue
        observations.append(
            solar_monitoring.decode_netcdf(
                response.content,
                stamp,
                url,
                float(reference["latitude"]),
                float(reference["longitude"]),
            )
        )
    return observations


def _read(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _write_temp_payload(data: dict[str, Any], observation: dict[str, Any]) -> Path:
    payload = copy.deepcopy(data)
    solar = dict(payload.get("solar_monitoring") or {})
    solar["status"] = "ok"
    solar["observation"] = observation
    solar["ground_observations"] = []
    solar["updated_at"] = observation.get("observed_at")
    payload["solar_monitoring"] = solar
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False)
    try:
        json.dump(payload, handle, ensure_ascii=False)
        handle.write("\n")
        return Path(handle.name)
    finally:
        handle.close()


def update_history_with_backfill(data_path: Path, previous_path: Path, history_path: Path) -> tuple[dict[str, Any], int]:
    data = _read(data_path)
    previous_data = _read(previous_path)
    solar = data.get("solar_monitoring") or {}
    previous_solar = previous_data.get("solar_monitoring") or {}
    current_obs = solar.get("observation") or {}
    previous_obs = previous_solar.get("observation") or {}

    username = os.getenv("LSASAF_USERNAME", "").strip()
    password = os.getenv("LSASAF_PASSWORD", "").strip()
    backfilled: list[dict[str, Any]] = []
    if username and password and current_obs.get("observed_at") and previous_obs.get("observed_at"):
        reference = solar.get("reference") or solar_monitoring.load_reference()
        backfilled = fetch_intermediate_observations(
            reference,
            previous_obs.get("observed_at"),
            current_obs.get("observed_at"),
            username,
            password,
        )

    for observation in backfilled:
        temp_path = _write_temp_payload(data, observation)
        try:
            solar_history.update_history(temp_path, history_path, parse_dt(observation.get("observed_at")))
        finally:
            temp_path.unlink(missing_ok=True)

    result = solar_history.update_history(data_path, history_path)
    return result, len(backfilled)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data.json")
    parser.add_argument("--previous", required=True)
    parser.add_argument("--history", default="solar_history.json")
    args = parser.parse_args()
    payload, count = update_history_with_backfill(Path(args.data), Path(args.previous), Path(args.history))
    print(
        f"Storico solare aggiornato: backfill LSA={count}, "
        f"campioni grezzi={len(payload.get('samples') or [])}, giorni={len(payload.get('daily') or [])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
