"""Quality guard per l'output pubblico di Meteo Giammoro.

Corregge/smarca come non validate informazioni derivate da parsing euristico,
ripulisce testi storici non più coerenti e mantiene un trend pressorio breve.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta


def _safe_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _parse_iso(value):
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def _clean_alert_validity(alert: dict) -> None:
    """Sostituisce testo PDF contaminato da legenda con una validità prudente."""
    raw = str(alert.get("validity") or "").strip()
    noisy = (
        len(raw) > 120
        or any(token in raw.upper() for token in ("ROSSA ALLARME", "ARANCIONE", "GIALLA", "PER IL RISCHIO"))
        or raw.count("fino alle ore") > 1
    )
    if not noisy:
        return

    title = str(alert.get("title") or "")
    match = re.search(r"(\d{1,2})-(\d{1,2})/(\d{1,2})/(\d{4})", title)
    if match:
        day_from, day_to, month, year = match.groups()
        alert["validity"] = (
            f"Validità avviso: {int(day_from):02d}–{int(day_to):02d}/{int(month):02d}/{year}; "
            "orari da verificare nel PDF ufficiale."
        )
    else:
        alert["validity"] = "Validità/orari da verificare nel PDF ufficiale."


def guard_alert_quality(data: dict) -> None:
    """Evita di presentare come certo un livello regionale non cross-validato.

    Se il livello proviene dal parser euristico della zona A e il controllo con
    il bollettino DPC nazionale fallisce, il candidato regionale viene conservato
    per l'analisi tecnica ma il livello pubblico diventa ``Da verificare``.
    """
    alert = data.get("alert", {}) or {}
    if not alert:
        return

    _clean_alert_validity(alert)
    national = alert.get("national_validation")
    parser_note = str(alert.get("parser_note") or "")
    national_error = isinstance(national, dict) and bool(national.get("error"))
    heuristic_regional = "estrazione automatica zona a" in parser_note.lower()

    if national_error and heuristic_regional:
        regional_label = alert.get("level_label")
        regional_class = alert.get("level_class")
        alert["regional_candidate"] = {
            "level_label": regional_label,
            "level_class": regional_class,
            "status": "unvalidated",
        }
        alert["level_label"] = "Da verificare"
        alert["level_class"] = "unknown"
        alert["parser_note"] = (
            "livello zona A estratto dal PDF regionale ma non validato automaticamente; "
            "consultare l'avviso ufficiale"
        )
        if regional_label and regional_label != "Da verificare":
            alert["text"] = (
                f"Livello regionale candidato: {regional_label}. "
                "La validazione incrociata con il bollettino DPC nazionale non è riuscita; "
                "consultare il PDF ufficiale prima di considerare definitivo il livello."
            )

    data["alert"] = alert


def sanitize_latest_change(data: dict) -> None:
    """Rimuove dai cambiamenti storici riferimenti ormai falsi alle fulminazioni."""
    change = data.get("latest_change", {}) or {}
    evidence = str(change.get("evidence") or "")
    markers = (
        "Fulminazioni non ancora acquisite automaticamente.",
        "LTG/LAMPINET non disponibile in questo ciclo; nessun dato di fulminazione viene inventato.",
    )
    changed = False
    for marker in markers:
        if marker in evidence:
            evidence = evidence.replace(marker, "").strip()
            changed = True

    if changed:
        evidence = re.sub(r"\s{2,}", " ", evidence).strip(" ;.")
        suffix = "Fulminazioni EUMETSAT MTG-LI integrate nel sistema."
        change["evidence"] = f"{evidence}. {suffix}" if evidence else suffix
        data["latest_change"] = change


def update_pressure_trend(data: dict, previous: dict) -> None:
    """Mantiene fino a 6 h di storico e calcola ΔP 1h/3h.

    La pressione territoriale deriva dal modello sul punto: il trend viene quindi
    etichettato come modellistico e non come osservazione barometrica locale.
    """
    metrics = ((data.get("territory", {}) or {}).get("metrics", {}) or {})
    pressure = metrics.get("pressure", {}) or {}
    current_hpa = _safe_float(pressure.get("value"))
    current_ts = _parse_iso((data.get("meta", {}) or {}).get("last_check_iso"))
    if current_hpa is None or current_ts is None:
        pressure["trend"] = "non disponibile"
        return

    history = []
    for item in (previous.get("pressure_history", []) or []):
        if not isinstance(item, dict):
            continue
        ts = _parse_iso(item.get("timestamp"))
        val = _safe_float(item.get("hpa"))
        if ts is not None and val is not None:
            history.append({"timestamp": ts.isoformat(timespec="seconds"), "hpa": round(val, 1)})

    if not history:
        prev_ts = _parse_iso((previous.get("meta", {}) or {}).get("last_check_iso"))
        prev_pressure = _safe_float(
            (((previous.get("territory", {}) or {}).get("metrics", {}) or {}).get("pressure", {}) or {}).get("value")
        )
        if prev_ts is not None and prev_pressure is not None:
            history.append({"timestamp": prev_ts.isoformat(timespec="seconds"), "hpa": round(prev_pressure, 1)})

    floor = current_ts - timedelta(hours=6)
    history = [item for item in history if (_parse_iso(item["timestamp"]) or current_ts) >= floor]
    stamp = current_ts.isoformat(timespec="seconds")
    if not history or history[-1]["timestamp"] != stamp:
        history.append({"timestamp": stamp, "hpa": round(current_hpa, 1)})
    history = history[-32:]
    data["pressure_history"] = history

    def delta_for(hours: int, tolerance_minutes: int):
        target = current_ts - timedelta(hours=hours)
        candidates = []
        for item in history[:-1]:
            ts = _parse_iso(item["timestamp"])
            if ts is None:
                continue
            distance = abs((ts - target).total_seconds()) / 60.0
            if distance <= tolerance_minutes:
                candidates.append((distance, item))
        if not candidates:
            return None
        _, best = min(candidates, key=lambda row: row[0])
        return round(current_hpa - float(best["hpa"]), 1)

    delta_1h = delta_for(1, 22)
    delta_3h = delta_for(3, 40)
    basis = delta_1h if delta_1h is not None else (round(delta_3h / 3.0, 1) if delta_3h is not None else None)

    if basis is None:
        tendency = "storico in raccolta"
    elif basis <= -1.5:
        tendency = "in forte calo"
    elif basis <= -0.5:
        tendency = "in calo"
    elif basis >= 1.5:
        tendency = "in forte aumento"
    elif basis >= 0.5:
        tendency = "in aumento"
    else:
        tendency = "stabile"

    parts = [tendency]
    if delta_1h is not None:
        parts.append(f"Δ1h {delta_1h:+.1f} hPa")
    if delta_3h is not None:
        parts.append(f"Δ3h {delta_3h:+.1f} hPa")
    if delta_1h is None and delta_3h is None:
        parts.append(f"{len(history)} campioni")

    pressure["trend"] = " · ".join(parts)
    pressure["trend_quality"] = "trend modellistico sul punto"
    data["pressure_trend"] = {
        "status": "ready" if (delta_1h is not None or delta_3h is not None) else "collecting",
        "tendency": tendency,
        "delta_1h_hpa": delta_1h,
        "delta_3h_hpa": delta_3h,
        "samples": len(history),
        "source": "pressione sul punto da modello; non misura barometrica locale",
    }


def refresh_pressure_evidence(data: dict) -> None:
    trend = data.get("pressure_trend", {}) or {}
    if not trend:
        return
    d1 = trend.get("delta_1h_hpa")
    d3 = trend.get("delta_3h_hpa")
    d1_text = "n/d" if d1 is None else f"{d1:+.1f} hPa"
    d3_text = "n/d" if d3 is None else f"{d3:+.1f} hPa"
    data.setdefault("nowcast_evidence", {})["wind_pressure"] = (
        f"Pressione sul punto: {trend.get('tendency', '—')}; Δ1h {d1_text}; Δ3h {d3_text}. "
        "Trend modellistico, non misura barometrica locale."
    )
