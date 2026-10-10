#!/usr/bin/env python3
"""Nowcasting v4: radar multi-cella/multi-frame + fulminazioni EUMETSAT MTG-LI opzionali."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import lightning_eumetsat as eum_li
import nowcast_v2 as v2


def sanitize_territory_metrics(data: dict) -> None:
    """Evita di presentare un dew point incoerente con la temperatura mostrata.

    Quando TEMP DPC sostituisce la temperatura modellistica ma l'umidità resta
    modellistica, T e UR non appartengono alla stessa sorgente: in quel caso il
    dew point non viene pubblicato come dato coerente.
    """
    metrics = ((data.get("territory", {}) or {}).get("metrics", {}) or {})
    temp = metrics.get("temperature", {}) or {}
    humidity = metrics.get("humidity", {}) or {}
    dew = metrics.get("dew_point", {}) or {}

    temp_source = str(temp.get("quality") or "").strip()
    humidity_source = str(humidity.get("quality") or "").strip()
    try:
        temp_value = float(temp.get("value")) if temp.get("value") is not None else None
        dew_value = float(dew.get("value")) if dew.get("value") is not None else None
    except (TypeError, ValueError):
        temp_value = dew_value = None

    mixed_sources = bool(temp_source and humidity_source and temp_source != humidity_source)
    physically_invalid = bool(temp_value is not None and dew_value is not None and dew_value > temp_value + 0.05)
    if mixed_sources or physically_invalid:
        dew["value"] = None
        dew["quality"] = "non disponibile: temperatura e umidità da fonti diverse" if mixed_sources else "scartato: valore incoerente con la temperatura"
        metrics["dew_point"] = dew


def refresh_runtime_text(data: dict) -> None:
    """Allinea le descrizioni tecniche alle sorgenti realmente operative."""
    territory = data.get("territory", {}) or {}
    territory["summary"] = (
        "Stima territoriale automatica; nel nowcasting hanno priorità Radar-DPC, "
        "fulminazioni EUMETSAT MTG-LI e osservazioni disponibili."
    )

    for row in data.get("models", []) or []:
        if row.get("horizon") == "0–3 h":
            row["models"] = "Radar-DPC · EUMETSAT MTG-LI · stazioni locali · modelli sul punto"
            row["signal"] = "Osservazioni prioritarie; modelli a supporto"
            row["agreement"] = "nowcasting osservativo"
            row["note"] = "Radar e fulminazioni sono acquisiti automaticamente; il tracking radar usa più celle e più frame quando disponibili."

    reasoning = data.get("reasoning", {}) or {}
    reasoning["description"] = (
        "Il backend acquisisce stazioni, modelli, prodotti Radar-DPC, fulminazioni EUMETSAT MTG-LI "
        "e allerte ufficiali. Giammoro resta il punto di riferimento; le stazioni vicine sono supporto separato. "
        "Nel 0–3 h hanno priorità osservazioni, radar, fulmini e tracking; oltre il brevissimo termine vengono confrontati modelli ed ensemble."
    )

    confidence = data.get("analysis_confidence", {}) or {}
    if confidence:
        confidence["note"] = "Confidenza nowcasting da freschezza radar, rilevamento/track delle celle, cross-check radar, stazioni, modelli e fulminazioni EUMETSAT MTG-LI."

    sources = data.setdefault("sources", [])
    eum_source = "EUMETSAT MTG Lightning Imager L2 Lightning Flashes"
    if eum_source not in sources:
        sources.append(eum_source)


def run(data_path: Path, previous_path: Path | None = None, history_path: Path | None = None):
    import collector

    # Prima esegue la pipeline radar stabile v2.
    data = v2.run(data_path, previous_path, history_path)
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path and previous_path.exists() else {}
    rlat = float(collector.REF["latitude"])
    rlon = float(collector.REF["longitude"])

    # Timestamp machine-readable per la pagina: permette di mostrare la freschezza reale dei dati.
    data.setdefault("meta", {})["last_check_iso"] = collector.now_local().isoformat(timespec="seconds")

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

    sanitize_territory_metrics(data)
    refresh_runtime_text(data)

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
