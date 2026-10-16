from datetime import datetime, timezone

import verification_engine_v2 as v2


def data_with_split_cells():
    return {
        "nowcast": {"level": "moderato", "label": "Moderato"},
        "risk_48h": {"level": "moderato"},
        "analysis_confidence": {"score": 80, "label": "Alta"},
        "nowcast_tracking": {
            "status": "detected",
            "age_minutes": 5,
            "track_id": "T1",
            "peak_value": 30,
            "cell": {"lat": 38.30, "lon": 15.55, "distance_km": 32, "peak_value": 30},
            "tracked_cell": {"lat": 38.30, "lon": 15.55, "distance_km": 32, "peak_value": 30},
            "hazard_cell": {"lat": 38.21, "lon": 15.34, "distance_km": 8, "peak_value": 12},
            "motion": {"status": "tracked", "speed_kmh": 30, "direction_deg": 45, "approaching": False},
        },
        "lightning": {"status": "ok", "age_minutes": 5, "radii": {"20": {"flash_count": 0}, "30": {"flash_count": 0}}},
        "territory": {"metrics": {"rain_1h": {"value": 0.0}}},
    }


def test_observation_uses_hazard_cell_for_local_distance():
    obs = v2.observation(data_with_split_cells())
    assert obs["radar_distance_km"] == 8
    assert obs["event"] is True
    assert obs["cell_role"] == "hazard_cell"


def test_base_snapshot_keeps_tracked_cell_for_motion_prediction():
    v2.install()
    now = datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc)
    snap = v2.base.make_snapshot(data_with_split_cells(), now)
    assert snap["prediction"]["radar"]["distance_km"] == 32
    assert snap["prediction"]["radar"]["track_id"] == "T1"


def test_event_metrics_separate_events_from_no_events():
    rows = [
        {"outcome": "correct", "predicted_event": True, "observed_event": True, "confidence_score": 80},
        {"outcome": "correct", "predicted_event": False, "observed_event": False, "confidence_score": 80},
        {"outcome": "false_alarm", "predicted_event": True, "observed_event": False, "confidence_score": 80},
        {"outcome": "missed_event", "predicted_event": False, "observed_event": True, "confidence_score": 80},
    ]
    out = v2.build_summary(rows)
    metrics = out["event_metrics"]
    assert metrics["true_positive"] == 1
    assert metrics["true_negative"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["event_detection_percent"] == 50.0
    assert metrics["false_alarm_ratio_percent"] == 50.0
    assert metrics["balanced_accuracy_percent"] == 50.0
    assert metrics["csi_percent"] == 33.3
