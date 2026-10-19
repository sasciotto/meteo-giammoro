from datetime import datetime, timezone

import verification_engine_v2 as v2


def test_snapshot_does_not_store_data_quality_as_predictive_confidence():
    data = {
        "analysis_quality": {"score": 96, "label": "Molto alta"},
        "trajectory_reliability": {"score": 91, "label": "Molto alta"},
        "predictive_confidence": {"score": None, "label": "Non calibrata", "status": "uncalibrated"},
        "analysis_confidence": {"score": 96, "label": "Molto alta", "semantic": "data_quality"},
        "nowcast": {"level": "basso", "label": "Basso"},
        "risk_48h": {"level": "moderato"},
        "nowcast_tracking": {
            "status": "no_cell",
            "motion": {"status": "unavailable"},
        },
        "lightning": {"status": "ok", "radii": {"20": {"flash_count": 0}, "30": {"flash_count": 0}}},
    }

    v2.install()
    snap = v2.base.make_snapshot(data, datetime(2026, 10, 19, 9, 30, tzinfo=timezone.utc))
    prediction = snap["prediction"]

    assert prediction["confidence_score"] is None
    assert prediction["confidence_label"] == "Non calibrata"
    assert prediction["data_quality_score"] == 96
    assert prediction["trajectory_reliability_score"] == 91
    assert prediction["predictive_confidence_status"] == "uncalibrated"


def test_summary_marks_old_confidence_buckets_disabled():
    out = v2.build_summary([
        {"outcome": "correct", "predicted_event": False, "observed_event": False, "confidence_score": 99},
    ])

    assert out["by_confidence"]["status"] == "disabled_until_probabilistic_calibration"
    assert "qualità tecnica" in out["by_confidence"]["note"]
