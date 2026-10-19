#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import analysis_quality


def run(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    analysis_quality.apply(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data.json")
    args = parser.parse_args()
    run(Path(args.data))
    print("Qualità dati, affidabilità traiettoria e confidenza previsionale aggiornate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
