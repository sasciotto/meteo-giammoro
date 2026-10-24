from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import analysis_quality
import precipitation_verification as precipitation
import runtime_quality

TZ = ZoneInfo("Europe/Rome")


def test_obsolete_nowcast_change_closes_but_current_target_stays():
    stale = {
        "nowcast": {"label": "Basso (radar)"},
        "latest_change": {"title": "Aumento del segnale 0–3 h: Basso (radar) → Basso–moderato"},
        "history": [],
    }
    runtime_quality.resolve_obsolete_nowcast_change(stale, datetime(2026, 10, 24, 9, 42, tzinfo=TZ))
    assert stale["latest_change"]["status"] == "resolved"
    assert stale["latest_change"]["event_type"] == "nowcast_change"

    current = {
        "nowcast": {"label": "Basso–moderato"},
        "latest_change": {"title": "Aumento del segnale 0–3 h: Basso (radar) → Basso–moderato"},
    }
    runtime_quality.resolve_obsolete_nowcast_change(current, datetime(2026, 10, 24, 10, 18, tzinfo=TZ))
    assert "status" not in current["latest_change"]


def test_current_model_precipitation_drives_30_minute_signal():
    signal = runtime_quality._model_precipitation_signal({
        "model_details": [
            {"label": "ICON-2I", "ok": True, "current": {"precipitation": 0.2}, "next_0_3h": {"precip_sum": 0.4}},
            {"label": "ICON", "ok": True, "current": {"rain": 0.1, "showers": 0.1}, "next_0_3h": {"precip_sum": 0.3}},
            {"label": "ECMWF", "ok": True, "current": {"precipitation": 0.0}, "next_0_3h": {"precip_sum": 0.0}},
        ]
    })
    assert signal["current_wet_models"] == 2
    pred = precipitation._prediction({"local_precipitation": {"status": "dry", "forecast_0_3h": signal}})
    assert pred["by_horizon"]["30"] is True


def test_missing_lightning_age_scores_zero_and_two_frames_are_capped():
    assert analysis_quality._lightning_support_score({"lightning": {"status": "ok", "age_minutes": None}}) == 0
    trajectory = analysis_quality.trajectory_reliability({
        "nowcast_tracking": {
            "status": "detected",
            "motion": {"status": "tracked", "frames": 2, "method": "two_frame", "fit_residual_km": None},
            "association": {"status": "matched", "score": 3.0},
            "track_quality": {"status": "good", "reasons": []},
        },
        "approaching_cells": {"suppressed_by_main_track": 0},
    })
    assert trajectory["score"] <= 64
    assert trajectory["label"] == "Media"


def test_forecast_dashboard_overrides_legacy_summary_cards_from_backend():
    js = Path("forecast_dashboard.js").read_text(encoding="utf-8")
    assert "function renderSummaryCards(data)" in js
    assert "homeHoursTitle" in js and "homeHoursText" in js
    assert "local_precipitation" in js and "homeStormTitle" in js
    assert "Pioggia terminata o attenuata" in js
    assert "renderSummaryCards(data);" in js
