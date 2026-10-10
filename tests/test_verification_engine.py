from datetime import datetime, timezone

import verification_engine as v


def base_data():
    return {
        "nowcast": {"level": "moderato", "label": "Moderato"},
        "risk_48h": {"level": "moderato"},
        "analysis_confidence": {"score": 80, "label": "Alta"},
        "nowcast_tracking": {
            "status": "detected",
            "age_minutes": 5,
            "track_id": "T1",
            "peak_value": 25,
            "cell": {"lat": 38.25, "lon": 15.32, "distance_km": 8},
            "motion": {"status": "tracked", "speed_kmh": 30, "direction_deg": 180, "approaching": True, "closest_approach_km": 3, "closest_approach_minutes": 20, "eta_minutes": 22},
        },
        "lightning": {"status": "ok", "age_minutes": 5, "radii": {"20": {"flash_count": 2}, "30": {"flash_count": 3}}},
        "territory": {"metrics": {"rain_1h": {"value": 3.0}}},
    }


def test_observation_detects_local_event():
    obs = v.observation(base_data())
    assert obs["evaluable"] is True
    assert obs["event"] is True
    assert obs["lightning_20km"] == 2


def test_prediction_uses_eta_and_track():
    now = datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc)
    snap = v.make_snapshot(base_data(), now)
    pred = v.prediction_for_horizon(snap, 30)
    assert pred["event"] is True
    assert pred["eta_minutes"] == 22


def test_classification_matrix():
    assert v.classify(True, {"evaluable": True, "event": True, "nearby_signal": True}) == "correct"
    assert v.classify(False, {"evaluable": True, "event": False, "nearby_signal": False}) == "correct"
    assert v.classify(True, {"evaluable": True, "event": False, "nearby_signal": True}) == "partial"
    assert v.classify(True, {"evaluable": True, "event": False, "nearby_signal": False}) == "false_alarm"
    assert v.classify(False, {"evaluable": True, "event": True, "nearby_signal": True}) == "missed_event"


def test_summary_weighted_accuracy():
    results = [
        {"outcome": "correct", "confidence_score": 80},
        {"outcome": "partial", "confidence_score": 80},
        {"outcome": "false_alarm", "confidence_score": 80},
        {"outcome": "inconclusive", "confidence_score": 80},
    ]
    s = v.build_summary(results)
    assert s["evaluable_results"] == 3
    assert s["accuracy_percent"] == 50.0


def test_event_archive_opens_and_closes():
    now = datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc)
    doc = {"events": [], "active_event": None}
    doc = v.update_events(doc, base_data(), now)
    assert doc["active_event"] is not None
    quiet = base_data()
    quiet["nowcast_tracking"]["cell"]["distance_km"] = 40
    quiet["territory"]["metrics"]["rain_1h"]["value"] = 0
    quiet["lightning"]["radii"]["20"]["flash_count"] = 0
    quiet["lightning"]["radii"]["30"]["flash_count"] = 0
    doc = v.update_events(doc, quiet, now)
    assert doc["active_event"] is None
    assert len(doc["events"]) == 1
