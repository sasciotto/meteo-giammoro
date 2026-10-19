#!/usr/bin/env python3
"""Normalizza la semantica 3–48 h separando tendenza di pioggia e impatto."""
from __future__ import annotations

import math
import re
from statistics import median
from typing import Any


def _num(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _fmt(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def _rows(data: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model in data.get("model_details", []) or []:
        if not isinstance(model, dict) or not model.get("ok"):
            continue
        period = model.get("next_3_48h", {}) or {}
        rain = _num(period.get("precip_sum"))
        if rain is None:
            continue
        rows.append({
            "label": model.get("label") or model.get("id") or "modello",
            "rain": max(0.0, rain),
            "maxh": max(0.0, _num(period.get("precip_max_h")) or 0.0),
            "gust": max(0.0, _num(period.get("gust_max")) or 0.0),
            "cape": max(0.0, _num(period.get("cape_max")) or 0.0),
            "thunder": bool(period.get("thunder_signal")),
        })
    return rows


def _precipitation_tendency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = [row["rain"] for row in rows]
    count = len(rows)
    wet = sum(1 for amount in amounts if amount >= 0.5)
    ratio = wet / count if count else 0.0

    if wet == 0:
        label = "Pioggia poco probabile"
        level = "low"
    elif ratio >= 0.5:
        label = "Pioggia probabile"
        level = "moderato"
    else:
        label = "Pioggia possibile"
        level = "low"

    spread = max(amounts) - min(amounts)
    if spread <= 1.5:
        uncertainty = "contenuta"
        uncertainty_label = "quantità più coerente"
    elif spread <= 5.0:
        uncertainty = "moderata"
        uncertainty_label = "quantità variabile"
    else:
        uncertainty = "elevata"
        uncertainty_label = "quantità incerta"

    return {
        "label": label,
        "level": level,
        "wet_models": wet,
        "models_count": count,
        "precip_min_mm": round(min(amounts), 1),
        "precip_max_mm": round(max(amounts), 1),
        "precip_median_mm": round(float(median(amounts)), 1),
        "quantity_uncertainty": uncertainty,
        "quantity_uncertainty_label": uncertainty_label,
    }


def _impact(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Stima impatto modellistico: CAPE isolato non basta per alzare il livello."""
    severe = 0
    moderate = 0
    heavy_rain = 0
    strong_gust = 0
    convective_support = 0

    for row in rows:
        rain = row["rain"]
        maxh = row["maxh"]
        gust = row["gust"]
        cape = row["cape"]
        thunder = row["thunder"]

        rain_signal = rain >= 5.0 or maxh >= 3.0
        gust_signal = gust >= 50.0
        convective_signal = thunder or (cape >= 800.0 and rain >= 0.5)
        severe_signal = (
            rain >= 20.0
            or maxh >= 10.0
            or gust >= 70.0
            or (cape >= 1800.0 and (rain >= 5.0 or maxh >= 3.0 or thunder))
        )

        heavy_rain += int(rain_signal)
        strong_gust += int(gust_signal)
        convective_support += int(convective_signal)
        severe += int(severe_signal)
        moderate += int(severe_signal or rain_signal or gust_signal or convective_signal)

    count = len(rows)
    if severe >= 2:
        label, level = "Elevato (modellistico)", "elevato"
    elif moderate >= 2:
        label, level = "Moderato (modellistico)", "moderato"
    elif moderate == 1:
        label, level = "Basso–moderato (modellistico)", "moderato"
    else:
        label, level = "Basso (modellistico)", "low"

    note = (
        f"pioggia intensa {heavy_rain}/{count}, raffiche ≥50 km/h {strong_gust}/{count}, "
        f"instabilità convettiva accompagnata da precipitazione/temporale {convective_support}/{count}"
    )
    return {
        "label": label,
        "level": level,
        "moderate_models": moderate,
        "severe_models": severe,
        "note": note,
    }


def _fix_nowcast_note(data: dict) -> None:
    nowcast = data.get("nowcast", {}) or {}
    note = str(nowcast.get("note") or "")
    note = note.replace(
        "Nessun segnale marcato nel consenso modellistico",
        "Nessun segnale modellistico rilevante nel brevissimo termine 0–3 h",
    )
    note = re.sub(
        r"Segnale forte in (\d+/\d+) modelli",
        r"Segnale modellistico forte nel brevissimo termine 0–3 h in \1 modelli",
        note,
    )
    note = re.sub(
        r"Segnale significativo in (\d+/\d+) modelli",
        r"Segnale modellistico significativo nel brevissimo termine 0–3 h in \1 modelli",
        note,
    )
    note = re.sub(
        r"Segnale isolato in (1/\d+) modelli",
        r"Segnale modellistico isolato nel brevissimo termine 0–3 h in \1 modelli",
        note,
    )
    nowcast["note"] = note
    data["nowcast"] = nowcast


def apply(data: dict) -> dict:
    _fix_nowcast_note(data)
    rows = _rows(data)
    if not rows:
        return data

    tendency = _precipitation_tendency(rows)
    impact = _impact(rows)
    range_text = (
        f"{_fmt(tendency['precip_min_mm'])}–{_fmt(tendency['precip_max_mm'])} mm; "
        f"mediana {_fmt(tendency['precip_median_mm'])} mm"
    )
    note = (
        f"{tendency['wet_models']}/{tendency['models_count']} modelli indicano pioggia ≥0,5 mm nelle 3–48 h. "
        f"{tendency['quantity_uncertainty_label'].capitalize()}: {range_text}. "
        f"Impatto modellistico: {impact['label']}. Segnali d'impatto: {impact['note']}."
    )

    risk = dict(data.get("risk_48h", {}) or {})
    risk.update({
        "label": tendency["label"],
        "level": tendency["level"],
        "note": note,
        "semantic": "model_precipitation_tendency",
        "models_count": tendency["models_count"],
        "wet_models": tendency["wet_models"],
        "precip_min_mm": tendency["precip_min_mm"],
        "precip_max_mm": tendency["precip_max_mm"],
        "precip_median_mm": tendency["precip_median_mm"],
        "quantity_uncertainty": tendency["quantity_uncertainty"],
        "quantity_uncertainty_label": tendency["quantity_uncertainty_label"],
        "impact_label": impact["label"],
        "impact_level": impact["level"],
        "impact_note": impact["note"],
        "impact_moderate_models": impact["moderate_models"],
        "impact_severe_models": impact["severe_models"],
    })
    data["risk_48h"] = risk

    home = data.get("home_summary", {}) or {}
    mm = home.get("multi_model", {}) or {}
    if mm.get("available"):
        mm.update({
            "label": f"{tendency['label']} · {tendency['quantity_uncertainty_label']}",
            "precipitation_tendency": tendency["label"],
            "quantity_uncertainty": tendency["quantity_uncertainty"],
            "impact_label": impact["label"],
            "impact_level": impact["level"],
            "note": note,
        })
        home["multi_model"] = mm
        data["home_summary"] = home

    for model_row in data.get("models", []) or []:
        if not isinstance(model_row, dict) or str(model_row.get("horizon") or "") != "3–48 h":
            continue
        model_row["agreement"] = tendency["quantity_uncertainty_label"]
        model_row["note"] = (
            f"Tendenza: {tendency['label']}. Impatto: {impact['label']}. "
            f"Accumuli {range_text}."
        )

    return data
