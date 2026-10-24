#!/usr/bin/env python3
"""Separa qualità dei dati, affidabilità della traiettoria e confidenza previsionale."""
from __future__ import annotations

import math
from typing import Any

MIN_EVENT_SAMPLES_FOR_CALIBRATION = 20


def _num(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _score_label(score: float) -> str:
    if score < 40:
        return "Bassa"
    if score < 65:
        return "Media"
    if score < 85:
        return "Alta"
    return "Molto alta"


def _quality_status(score: float) -> str:
    if score >= 85:
        return "good"
    if score >= 65:
        return "fair"
    if score >= 40:
        return "degraded"
    return "poor"


def _radar_freshness_score(tracking: dict) -> int:
    if tracking.get("status") not in {"detected", "no_cell"}:
        return 0
    age = _num(tracking.get("age_minutes"))
    if age is None:
        return 0
    if age <= 10:
        return 30
    if age <= 20:
        return 27
    if age <= 35:
        return 22
    if age <= 60:
        return 12
    return 4


def _radar_crosscheck_score(data: dict) -> int:
    products = ((data.get("dpc_observations", {}) or {}).get("products", {}) or {})
    available = sum(1 for name in ("SRI", "VMI") if (products.get(name, {}) or {}).get("ok"))
    return 15 if available == 2 else 8 if available == 1 else 0


def _station_support_score(data: dict) -> int:
    stations = [
        row for row in (data.get("stations", []) or [])
        if isinstance(row, dict)
        and row.get("status") == "online"
        and row.get("source_quality") in {"official", "reliable"}
        and not row.get("excluded_from_analysis")
    ]
    return min(20, len(stations) * 4)


def _model_support_score(data: dict) -> int:
    available = sum(1 for row in (data.get("model_details", []) or []) if isinstance(row, dict) and row.get("ok"))
    return 15 if available >= 4 else 12 if available == 3 else 8 if available == 2 else 4 if available == 1 else 0


def _lightning_support_score(data: dict) -> int:
    lightning = data.get("lightning", {}) or {}
    if lightning.get("status") != "ok":
        return 0
    age = _num(lightning.get("age_minutes"))
    if age is None:
        return 0
    if age <= 20:
        return 20
    if age <= 35:
        return 16
    if age <= 60:
        return 8
    return 4


def data_quality(data: dict) -> dict:
    """Misura disponibilità e freschezza delle fonti, non probabilità di previsione corretta."""
    tracking = data.get("nowcast_tracking", {}) or {}
    components = {
        "radar_freshness": _radar_freshness_score(tracking),
        "radar_crosscheck": _radar_crosscheck_score(data),
        "station_support": _station_support_score(data),
        "model_availability": _model_support_score(data),
        "lightning_support": _lightning_support_score(data),
    }
    score = int(sum(components.values()))
    return {
        "score": score,
        "label": _score_label(score),
        "status": _quality_status(score),
        "semantic": "data_quality",
        "components": components,
        "note": (
            "Punteggio di qualità dell'analisi: misura freschezza e disponibilità di radar, cross-check, "
            "stazioni, modelli e fulminazioni. Non è una probabilità di previsione corretta."
        ),
    }


def _association_score(association: dict) -> int:
    if association.get("status") != "matched":
        return 4 if association.get("status") == "new_track" else 0
    score = _num(association.get("score"))
    if score is None:
        return 8
    if score <= 7:
        return 20
    if score <= 14:
        return 14
    if score <= 22:
        return 8
    return 4


def _residual_score(motion: dict, frames: int) -> int:
    residual = _num(motion.get("fit_residual_km"))
    if residual is None:
        return 8 if frames <= 2 else 5
    if residual <= 2:
        return 20
    if residual <= 4:
        return 16
    if residual <= 6:
        return 10
    return 4


def trajectory_reliability(data: dict) -> dict:
    """Valuta la robustezza geometrica del track corrente, separata dalla qualità delle fonti."""
    tracking = data.get("nowcast_tracking", {}) or {}
    motion = tracking.get("motion", {}) or {}
    track_quality = tracking.get("track_quality", {}) or {}

    if tracking.get("status") == "no_cell":
        return {
            "score": None,
            "label": "Non applicabile",
            "status": "not_applicable",
            "semantic": "trajectory_reliability",
            "components": {},
            "note": "Nessuna cella significativa da tracciare: l'affidabilità della traiettoria non è applicabile.",
        }
    if tracking.get("status") != "detected":
        return {
            "score": None,
            "label": "Non disponibile",
            "status": "unavailable",
            "semantic": "trajectory_reliability",
            "components": {},
            "note": "Tracking radar non disponibile in questo ciclo.",
        }
    if motion.get("status") != "tracked":
        return {
            "score": None,
            "label": "In acquisizione",
            "status": "collecting",
            "semantic": "trajectory_reliability",
            "components": {},
            "note": "La cella è rilevata, ma non ci sono ancora abbastanza frame coerenti per una traiettoria affidabile.",
        }

    frames = int(_num(motion.get("frames")) or len(tracking.get("track_history", []) or []) or 0)
    frame_score = 30 if frames >= 4 else 24 if frames == 3 else 12 if frames == 2 else 0
    track_status = str(track_quality.get("status") or "unknown")
    quality_score = {"good": 30, "degraded": 18, "suspect": 5}.get(track_status, 10)
    association_score = _association_score(tracking.get("association", {}) or {})
    residual_score = _residual_score(motion, frames)
    conflict_penalty = 8 if int((data.get("approaching_cells", {}) or {}).get("suppressed_by_main_track") or 0) > 0 else 0

    score = max(0, min(100, frame_score + quality_score + association_score + residual_score - conflict_penalty))
    if frames <= 2 or str(motion.get("method") or "") == "two_frame":
        score = min(score, 64)
    if track_status == "suspect":
        score = min(score, 39)
    elif track_status == "degraded":
        score = min(score, 69)

    status = "suspect" if track_status == "suspect" else "degraded" if track_status == "degraded" else _quality_status(score)
    reasons = []
    if frames <= 2 or str(motion.get("method") or "") == "two_frame":
        reasons.append("solo due frame coerenti: affidabilità operativa limitata")
    if conflict_penalty:
        reasons.append("ultimo confronto a due frame in disaccordo con il fit multi-frame")
    reasons.extend(str(x) for x in (track_quality.get("reasons", []) or []) if x)
    detail = "; ".join(reasons)

    return {
        "score": int(score),
        "label": _score_label(score),
        "status": status,
        "semantic": "trajectory_reliability",
        "frames": frames,
        "method": motion.get("method"),
        "components": {
            "frame_continuity": frame_score,
            "track_quality": quality_score,
            "association": association_score,
            "fit_residual": residual_score,
            "two_frame_conflict_adjustment": -conflict_penalty,
        },
        "note": (
            "Affidabilità geometrica della traiettoria radar corrente"
            + (f": {detail}." if detail else ".")
            + " Non rappresenta la probabilità che un evento colpisca Giammoro."
        ),
    }


def predictive_confidence(data: dict) -> dict:
    """Non inventa una probabilità finché il sistema non dispone di una calibrazione probabilistica."""
    summary = ((data.get("verification", {}) or {}).get("summary", {}) or {})
    event_metrics = summary.get("event_metrics", {}) or {}
    event_samples = int(_num(event_metrics.get("event_samples")) or 0)
    progress = min(100, int(round(100 * event_samples / MIN_EVENT_SAMPLES_FOR_CALIBRATION)))
    ready = event_samples >= MIN_EVENT_SAMPLES_FOR_CALIBRATION
    return {
        "score": None,
        "label": "Non calibrata",
        "status": "calibration_ready" if ready else "uncalibrated",
        "semantic": "predictive_probability",
        "event_samples": event_samples,
        "minimum_event_samples": MIN_EVENT_SAMPLES_FOR_CALIBRATION,
        "calibration_progress_percent": progress,
        "note": (
            "Confidenza previsionale non espressa in percentuale: il progetto non dispone ancora di una "
            "calibrazione probabilistica affidabile. "
            f"Campioni evento disponibili: {event_samples}/{MIN_EVENT_SAMPLES_FOR_CALIBRATION} come soglia minima di studio."
        ),
    }


def apply(data: dict) -> dict:
    quality = data_quality(data)
    trajectory = trajectory_reliability(data)
    predictive = predictive_confidence(data)

    data["analysis_quality"] = quality
    data["trajectory_reliability"] = trajectory
    data["predictive_confidence"] = predictive

    legacy = dict(quality)
    legacy["deprecated_alias"] = True
    legacy["note"] = quality["note"] + " Campo legacy analysis_confidence mantenuto solo per compatibilità."
    data["analysis_confidence"] = legacy

    change = data.get("latest_change", {}) or {}
    if change.get("event_type") == "radar_approach" and trajectory.get("score") is not None:
        change["confidence"] = str(trajectory.get("label") or "—").lower()
        change["confidence_basis"] = "affidabilità traiettoria radar"
        data["latest_change"] = change

    return data
