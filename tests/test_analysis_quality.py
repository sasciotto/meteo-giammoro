import analysis_quality


def test_data_quality_is_not_predictive_confidence():
    data = {
        "nowcast_tracking": {"status": "detected", "age_minutes": 5},
        "dpc_observations": {"products": {"SRI": {"ok": True}, "VMI": {"ok": True}}},
        "stations": [
            {"status": "online", "source_quality": "official", "excluded_from_analysis": False},
            {"status": "online", "source_quality": "reliable", "excluded_from_analysis": False},
        ],
        "model_details": [{"ok": True}, {"ok": True}, {"ok": True}, {"ok": True}],
        "lightning": {"status": "ok", "age_minutes": 5},
        "verification": {"summary": {"event_metrics": {"event_samples": 0}}},
    }

    analysis_quality.apply(data)

    assert data["analysis_quality"]["score"] > 0
    assert data["analysis_quality"]["semantic"] == "data_quality"
    assert data["predictive_confidence"]["score"] is None
    assert data["predictive_confidence"]["label"] == "Non calibrata"
    assert "Non è una probabilità" in data["analysis_quality"]["note"]


def test_no_cell_makes_trajectory_not_applicable_not_low_quality():
    data = {
        "nowcast_tracking": {"status": "no_cell", "age_minutes": 4},
        "verification": {"summary": {"event_metrics": {"event_samples": 0}}},
    }

    analysis_quality.apply(data)

    trajectory = data["trajectory_reliability"]
    assert trajectory["score"] is None
    assert trajectory["status"] == "not_applicable"
    assert trajectory["label"] == "Non applicabile"


def test_multiframe_good_track_gets_high_trajectory_reliability():
    data = {
        "nowcast_tracking": {
            "status": "detected",
            "motion": {"status": "tracked", "frames": 4, "method": "multi_frame_linear_fit", "fit_residual_km": 1.4},
            "association": {"status": "matched", "score": 5.8},
            "track_quality": {"status": "good", "reasons": []},
        },
        "approaching_cells": {"suppressed_by_main_track": 0},
        "verification": {"summary": {"event_metrics": {"event_samples": 0}}},
    }

    analysis_quality.apply(data)

    trajectory = data["trajectory_reliability"]
    assert trajectory["score"] >= 85
    assert trajectory["label"] == "Molto alta"
    assert trajectory["frames"] == 4


def test_conflicting_two_frame_signal_reduces_trajectory_score():
    base = {
        "nowcast_tracking": {
            "status": "detected",
            "motion": {"status": "tracked", "frames": 4, "method": "multi_frame_linear_fit", "fit_residual_km": 1.4},
            "association": {"status": "matched", "score": 5.8},
            "track_quality": {"status": "good", "reasons": []},
        },
        "verification": {"summary": {"event_metrics": {"event_samples": 0}}},
    }
    clean = dict(base)
    clean["approaching_cells"] = {"suppressed_by_main_track": 0}
    conflict = dict(base)
    conflict["approaching_cells"] = {"suppressed_by_main_track": 1}

    clean_score = analysis_quality.trajectory_reliability(clean)["score"]
    conflict_score = analysis_quality.trajectory_reliability(conflict)["score"]

    assert conflict_score == clean_score - 8


def test_predictive_confidence_uses_event_samples_only_as_calibration_progress():
    data = {"verification": {"summary": {"event_metrics": {"event_samples": 5}}}}

    predictive = analysis_quality.predictive_confidence(data)

    assert predictive["score"] is None
    assert predictive["status"] == "uncalibrated"
    assert predictive["calibration_progress_percent"] == 25
    assert predictive["event_samples"] == 5
    assert predictive["event_samples_source"] == "event_metrics"


def test_predictive_confidence_prefers_cumulative_v2_metrics():
    data = {
        "verification": {
            "summary": {
                "event_metrics": {"event_samples": 0},
                "cumulative_event_metrics": {"event_samples": 42},
            }
        }
    }

    predictive = analysis_quality.predictive_confidence(data)

    assert predictive["score"] is None
    assert predictive["status"] == "calibration_ready"
    assert predictive["calibration_progress_percent"] == 100
    assert predictive["event_samples"] == 42
    assert predictive["event_samples_source"] == "cumulative_event_metrics"
    assert "non equivale" in predictive["note"]


def test_legacy_alias_is_explicitly_deprecated():
    data = {
        "nowcast_tracking": {"status": "no_cell", "age_minutes": 5},
        "verification": {"summary": {"event_metrics": {"event_samples": 0}}},
    }

    analysis_quality.apply(data)

    assert data["analysis_confidence"]["deprecated_alias"] is True
    assert data["analysis_confidence"]["semantic"] == "data_quality"
