#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import analysis_quality
import home_hourly_consensus
import station_policy


ROOT = Path(__file__).resolve().parent
STATIONS_CONFIG = ROOT / "config" / "stations.json"


def run(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    config = json.loads(STATIONS_CONFIG.read_text(encoding="utf-8"))
    data = station_policy.normalize_data(data, config)
    analysis_quality.apply(data)
    home_hourly_consensus.apply_from_cache(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data.json")
    args = parser.parse_args()
    run(Path(args.data))
    print("Policy stazioni, qualità dati, affidabilità traiettoria, confidenza previsionale e consenso orario aggiornati")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
