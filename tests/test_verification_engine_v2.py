from datetime import datetime, timezone

import verification_engine_v2 as v2


def multi_cell_data():
    return {
        "nowcast": {"level": "moderato", "label": "Moderato"},
        "risk_48h": {"level": "moderato"},
        "analysis_confidence": {"score": 80, "label": "Alta"},
        "home_summary": {"nowcast_simple": {"status": "watch"}},
        "nowcast_tracking": {
            "status": "detected",
            "age_minutes": 5,
            "track_id": "T1",
            "peak_value": 30,
            "cell": {"lat": 38.30, "lon": 15.55, "distance_km": 32.0, "peak_value": 30},
            "tracked_cell": {"lat": 38.30, "lon": 15.55, "distance_km": 32.0, "peak_value": 30},
            "hazard_cell": {"lat": 38.30, "lon": 15.55, "distance_km": 32.0, "peak_value": 30},
            "candidates": [
                {"lat": 38.30, "lon": 15.55, "distance_km": 32.0, "peak_value": 30},
                {"lat": 38.22, "lon": 15.34, "distance_km": 10.0, "peak_value": 8},
            ],
            "motion": {
                "status": "tracked",
                "speed_kmh": 0.0,
                "direction_deg": 45.0,
                "approaching": False,
                "closest_approach_km": 32.0,
                "closest_approach_minutes": None,
                "eta_minutes": None,
            },
        },
        "lightning": {
            "status": "ok",
            "age_minutes": 5,
            "radii": {"20": {"flash_count": 0}, "30": {"flash_count": 0}},
        },
        "territory": {"metrics": {"rain_1h": {"value": 0.0}}},
    }


def test_observation_uses_nearest_significant_candidate_not_far_hazard_cell():
    obs = v2.observation(multi_cell_data())
    assert obs["radar_distance_km"] == 10.0
    assert obs["cell_role"] == "nearest_candidate"
    assert obs["radar_candidate_count"] == 2
    assert obs["event"] is True
    assert "radar_15km" in obs["event_drivers"]
    assert obs["tracked_cell_lat"] == 38.30
    assert obs["tracked_cell_lon"] == 15.55


def test_snapshot_keeps_main_track_and_archives_nearest_local_candidate():
    snap = v2.make_snapshot(multi_cell_data(), datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc))
    radar = snap["prediction"]["radar"]
    assert radar["distance_km"] == 32.0
    assert radar["local_nearest_distance_km"] == 10.0
    assert radar["local_candidate_count"] == 2
    assert snap["prediction"]["watch_status"] == "watch"


def test_prediction_uses_local_candidate_for_event_without_relabeling_main_track():
    snap = v2.make_snapshot(multi_cell_data(), datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc))
    pred60 = v2.prediction_for_horizon(snap, 60)
    pred120 = v2.prediction_for_horizon(snap, 120)
    assert pred60["event"] is True
    assert "nucleo radar locale già entro 15 km" in pred60["reasons"]
    assert pred120["event"] is False


def test_watch_is_diagnostic_and_does_not_become_strict_event():
    data = multi_cell_data()
    data["nowcast_tracking"]["candidates"][1]["distance_km"] = 22.0
    data["lightning"]["radii"]["30"]["flash_count"] = 2
    snap = v2.make_snapshot(data, datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc))
    pred = v2.prediction_for_horizon(snap, 60)
    assert pred["event"] is False
    assert pred["watch"] is True
    assert pred["watch_reasons"]


def test_trajectory_error_uses_tracked_cell_not_nearest_secondary_cell():
    data = multi_cell_data()
    snap = v2.make_snapshot(data, datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc))
    obs = v2.observation(data)
    assert obs["cell_lat"] != obs["tracked_cell_lat"]
    assert v2.trajectory_error(snap, obs, 30) == 0.0


def test_missing_lightning_age_is_not_treated_as_fresh():
    data = multi_cell_data()
    data["nowcast_tracking"] = {"status": "no_cell", "age_minutes": 5}
    data["lightning"] = {
        "status": "ok",
        "age_minutes": None,
        "radii": {"20": {"flash_count": 4}, "30": {"flash_count": 5}},
    }
    obs = v2.observation(data)
    assert obs["lightning_fresh"] is False
    assert "lightning_20km" not in obs["event_drivers"]
    assert obs["event"] is False


def test_summary_exposes_horizon_metrics_and_miss_drivers():
    rows = [
        {
            "horizon_minutes": 30,
            "outcome": "correct",
            "predicted_event": True,
            "predicted_watch": True,
            "observed_event": True,
            "observation": {"event_drivers": ["lightning_20km"]},
        },
        {
            "horizon_minutes": 30,
            "outcome": "correct",
            "predicted_event": False,
            "predicted_watch": False,
            "observed_event": False,
            "observation": {},
        },
        {
            "horizon_minutes": 60,
            "outcome": "missed_event",
            "predicted_event": False,
            "predicted_watch": True,
            "observed_event": True,
            "observation": {"event_drivers": ["lightning_20km"]},
        },
        {
            "horizon_minutes": 120,
            "outcome": "missed_event",
            "predicted_event": False,
            "predicted_watch": False,
            "observed_event": True,
            "observation": {"event_drivers": ["radar_15km", "lightning_20km"]},
        },
    ]
    summary = v2.build_summary(rows)
    assert summary["by_horizon"]["30"]["event_detection_percent"] == 100.0
    assert summary["by_horizon"]["60"]["false_negative"] == 1
    assert summary["by_horizon"]["120"]["false_negative"] == 1
    assert summary["miss_diagnostics"]["by_horizon"] == {"30": 0, "60": 1, "120": 1}
    assert summary["miss_diagnostics"]["by_event_driver"]["lightning_20km"] == 2
    assert summary["miss_diagnostics"]["by_event_driver"]["multiple"] == 1
    assert summary["watch_metrics"]["event_coverage_percent"] == 66.7
