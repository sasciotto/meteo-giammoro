from nowcast_calibration import build_report, update


def _row(snapshot, horizon, predicted, observed, watch=False, reason=None, driver=None):
    return {
        "snapshot_id": snapshot,
        "issued_at": "2026-10-31T08:00:00+00:00",
        "verified_at": "2026-10-31T10:00:00+00:00",
        "horizon_minutes": horizon,
        "outcome": "correct",
        "predicted_event": predicted,
        "predicted_watch": watch,
        "observed_event": observed,
        "prediction_reasons": [reason] if reason else [],
        "watch_reasons": ["watch radar"] if watch else [],
        "observation": {"event_drivers": [driver] if driver else [], "radar_distance_km": 10.0},
    }


def test_update_deduplicates_snapshot_horizon_and_preserves_history():
    verification = {"updated_at": "2026-10-31T10:00:00+00:00", "results": [_row("a", 30, True, True, reason="radar")]}
    history = {"rows": [{"key": "old:60", "snapshot_id": "old", "verified_at": "2026-10-30T10:00:00+00:00", "horizon_minutes": 60, "predicted_event": False, "predicted_watch": False, "observed_event": False, "prediction_reasons": [], "watch_reasons": [], "event_drivers": []}]}
    payload, report = update(verification, history)
    assert len(payload["rows"]) == 2
    assert report["overall"]["true_positive"] == 1
    assert report["overall"]["true_negative"] == 1


def test_report_keeps_probability_uncalibrated_and_exposes_diagnostics():
    rows = []
    for i in range(20):
        rows.append({"key": f"tp{i}:30", "horizon_minutes": 30, "predicted_event": True, "predicted_watch": True, "observed_event": True, "prediction_reasons": ["radar vicino"], "watch_reasons": ["watch radar"], "event_drivers": ["radar_15km"]})
    rows.append({"key": "fp:30", "horizon_minutes": 30, "predicted_event": True, "predicted_watch": True, "observed_event": False, "prediction_reasons": ["radar vicino"], "watch_reasons": ["watch radar"], "event_drivers": []})
    report = build_report(rows, "2026-10-31T10:00:00+00:00")
    assert report["status"] == "calibration_ready"
    assert "probabilita' calibrata" in report["note"]
    assert report["diagnostics"]["prediction_reasons_true_positive"]["radar vicino"] == 20
    assert report["diagnostics"]["watch"]["false_positive_samples"] == 1
