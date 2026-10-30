#!/usr/bin/env python3
"""Policy esplicita per selezione e classificazione delle stazioni.

Il collector storico usa ``station_groups[].candidates`` in ordine. Questo modulo
prepara una configurazione effettiva in cui i sostituti vengono aggiunti solo se
``allow_substitute`` è vero e normalizza la rete sorgente quando il feed CMS non
la espone ma il nome stazione contiene un suffisso inequivocabile.

Principi:
- un alias della stessa stazione può restare tra ``candidates``;
- una stazione alternativa va in ``substitutes``;
- ``allow_substitute: false`` impedisce che ``substitutes`` entri nel collector;
- l'inferenza della rete non modifica il nome reale della stazione e viene
  dichiarata esplicitamente nell'output.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

GENERIC_NETWORKS = {
    "",
    "fonte non indicata",
    "fonte da classificare",
    "nessuna stazione verificata nel feed corrente",
}

NETWORK_PATTERNS: tuple[tuple[re.Pattern[str], str, str, str], ...] = (
    (re.compile(r"\(\s*DRPC\s*\)", re.I), "DRPC Sicilia / Protezione Civile", "official", "Rete ufficiale"),
    (re.compile(r"\(\s*SIAS\s*\)", re.I), "SIAS Regione Siciliana", "official", "Rete ufficiale"),
    (re.compile(r"\(\s*LineaMeteo\s*\)", re.I), "LineaMeteo", "reliable", "Rete locale affidabile"),
    (re.compile(r"\bMeteoNetwork\b", re.I), "MeteoNetwork", "community", "Rete terza / controllo"),
    (re.compile(r"\bWeather Underground\b|\bWunderground\b", re.I), "Weather Underground", "community", "Rete terza / controllo"),
)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def effective_config(config: dict[str, Any]) -> dict[str, Any]:
    """Restituisce la configurazione che il collector può realmente usare.

    ``candidates`` contiene stazioni/alias ammessi sempre. ``substitutes`` viene
    aggiunto solo quando ``allow_substitute`` è esplicitamente true.
    """
    result = copy.deepcopy(config)
    for group in result.get("station_groups", []):
        primary = _dedupe(list(group.get("candidates") or []))
        substitutes = _dedupe(list(group.get("substitutes") or []))
        if bool(group.get("allow_substitute", False)):
            group["candidates"] = _dedupe(primary + substitutes)
        else:
            group["candidates"] = primary
    return result


def infer_network(station_name: str | None, current_network: str | None) -> tuple[str | None, str | None, str | None, bool]:
    """Determina rete e qualità solo quando il feed non fornisce una rete utile."""
    current = (current_network or "").strip()
    if current.lower() not in GENERIC_NETWORKS:
        return current, None, None, False

    name = station_name or ""
    for pattern, network, quality, label in NETWORK_PATTERNS:
        if pattern.search(name):
            return network, quality, label, True
    return current_network, None, None, False


def normalize_station(station: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(station)
    network, quality, quality_label, inferred = infer_network(item.get("name"), item.get("network"))
    if inferred:
        item["network"] = network
        if item.get("source_quality") not in {"primary"}:
            item["source_quality"] = quality
            item["source_quality_label"] = quality_label
        item["network_inferred"] = True
        item["network_inference_note"] = "Rete inferita dal suffisso esplicito del nome stazione nel feed CMS."
    return item


def normalize_data(data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(data)
    result["stations"] = [normalize_station(x) for x in (result.get("stations") or []) if isinstance(x, dict)]
    result["station_selection_policy"] = {
        "version": "1.0",
        "rule": "candidates sempre ammessi; substitutes solo con allow_substitute=true",
        "groups": [
            {
                "label": group.get("label"),
                "allow_substitute": bool(group.get("allow_substitute", False)),
                "candidates": list(group.get("candidates") or []),
                "substitutes": list(group.get("substitutes") or []),
            }
            for group in config.get("station_groups", [])
        ],
    }
    return result


def normalize_file(data_path: Path, config: dict[str, Any]) -> None:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    normalized = normalize_data(data, config)
    data_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data.json")
    parser.add_argument("--config", default="config/stations.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    normalize_file(Path(args.data), config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
