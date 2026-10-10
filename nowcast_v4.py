#!/usr/bin/env python3
"""Nowcasting v4: radar multi-cella/multi-frame + fulminazioni EUMETSAT MTG-LI opzionali."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import lightning_eumetsat as eum_li
import nowcast_v2 as v2


def run(data_path: Path, previous_path: Path | None = None, history_path: Path | None = None):
    import collector

    # Prima esegue la pipeline radar stabile v2.
    data = v2.run(data_path, previous_path, history_path)
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path and previous_path.exists() else {}
    rlat = float(collector.REF["latitude"])
    rlon = float(collector.REF["longitude"])

    # Se le credenziali EUMETSAT esistono, sostituisce il placeholder fulmini con osservazioni MTG-LI.
    lightning = eum_li.fetch_lightning(rlat, rlon)
    data["lightning"] = lightning
    data.setdefault("nowcast_evidence", {})["lightning"] = eum_li.summary(lightning)

    tr = data.get("nowcast_tracking", {})
    if lightning.get("status") == "ok":
        data["analysis_confidence"] = v2.enhanced_confidence(data, tr, lightning)
        v2.significant_lightning_change(data, previous, lightning)

    # Mantiene il testo leggibile e non duplica messaggi delle vecchie sorgenti.
    note = str(data.get("nowcast", {}).get("note", "")).strip()
    markers = [
        "LTG/LAMPINET non disponibile in questo ciclo; nessun dato di fulminazione viene inventato.",
        "Fulminazioni non ancora acquisite automaticamente.",
    ]
    for marker in markers:
        note = note.replace(marker, "").strip()
    li_text = eum_li.summary(lightning)
    if li_text not in note:
        note = (note + " " + li_text).strip()
    data.setdefault("nowcast", {})["note"] = note

    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if history_path:
        history_path.write_text(json.dumps(data.get("history", []), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data.json")
    p.add_argument("--previous")
    p.add_argument("--history", default="history.json")
    a = p.parse_args()
    run(Path(a.data), Path(a.previous) if a.previous else None, Path(a.history) if a.history else None)
    print("Nowcast v4: radar multi-frame + EUMETSAT MTG-LI opzionale aggiornato")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
