from datetime import datetime, timezone

import precipitation_verification as p


def test_prediction_separates_30_60_120_minute_rain_presence():
    data = {
        "local_precipitation": {
            "status": "dry",
            "forecast_0_3h": {
                "status": "weak",
                "wet_models": 1,
                "notable_models": 1,
                "current_wet_models": 0,
                "max_precip_0_3h_mm": 0.9,
            },
        }
    }
    pred = p._prediction(data)
    assert pred["by_horizon"] == {"30": False, "60": False, "120": True}


def test_observation_uses_persisted_local_radar_history():
    history = [
        {"timestamp": "2026-10-22T14:00:00+00:00", "rain_detected": False, "observation_valid": True},
        {"timestamp": "2026-10-22T14:20:00+00:00", "rain_detected": True, "observation_valid": True},
        {"timestamp": "2026-10-22T14:40:00+00:00", "rain_detected": False, "observation_valid": True},
    ]
    start = datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc)
    assert p._observed_between(history, start, start.replace(minute=30)) is True
    assert p._observed_between(history, start.replace(minute=30), start.replace(minute=50)) is False


def test_apply_counts_a_missed_local_rain_event():
    events = {
        "precipitation_verification": {
            "metric_version": p.METRIC_VERSION,
            "pending": [
                {
                    "id": "snap",
                    "issued_at": "2026-10-22T14:00:00+00:00",
                    "prediction": {
                        "by_horizon": {"30": False, "60": False, "120": False},
                        "forecast_status": "low",
                        "wet_models": 0,
                        "current_wet_models": 0,
                    },
                    "evaluated_horizons": [],
                }
            ],
            "results": [],
            "counts": p._empty_counts(),
            "by_horizon": {str(h): p._empty_counts() for h in p.HORIZONS},
            "processed_keys": [],
        }
    }
    data = {
        "meta": {"last_check_iso": "2026-10-22T14:31:00+00:00"},
        "local_precipitation": {
            "status": "dry",
            "history": [
                {"timestamp": "2026-10-22T14:20:00+00:00", "rain_detected": True, "observation_valid": True},
            ],
            "forecast_0_3h": {"status": "low", "wet_models": 0, "notable_models": 0},
        },
    }
    data, verification, events = p.apply(
        data,
        {"summary": {}},
        events,
        now=datetime(2026, 10, 22, 14, 31, tzinfo=timezone.utc),
    )
    metrics = verification["summary"]["precipitation_presence"]["cumulative"]
    assert metrics["samples"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["rain_detection_percent"] == 0.0
    assert events["precipitation_verification"]["results"][-1]["outcome"] == "false_negative"


def test_area_signal_is_not_exposed_as_point_accumulation_metric():
    summary = p._metrics({"true_positive": 1, "true_negative": 2, "false_positive": 0, "false_negative": 1})
    assert summary["rain_samples"] == 2
    assert summary["rain_detection_percent"] == 50.0
    assert summary["precision_percent"] == 100.0


def test_unknown_radar_cannot_count_as_dry():
    from datetime import timedelta
    start = datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc)
    history = [
        {"timestamp": start.isoformat(), "rain_detected": False, "observation_valid": False},
        {"timestamp": (start + timedelta(minutes=15)).isoformat(), "rain_detected": None, "observation_valid": False},
        {"timestamp": (start + timedelta(minutes=30)).isoformat(), "rain_detected": False, "observation_valid": False},
    ]
    assert p._observed_between(history, start, start + timedelta(minutes=30)) is None


def test_verified_dry_window_is_negative():
    from datetime import timedelta
    start = datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc)
    history = [
        {"timestamp": (start + timedelta(minutes=m)).isoformat(), "rain_detected": False, "observation_valid": True}
        for m in (0, 15, 30)
    ]
    assert p._observed_between(history, start, start + timedelta(minutes=30)) is False


def test_v1_metrics_archived_and_unverifiable_forecasts_skipped():
    now = datetime(2026, 10, 22, 14, 31, tzinfo=timezone.utc)
    legacy = {
        "metric_version": "local-precipitation-v1",
        "counts": {"true_positive": 3, "true_negative": 200, "false_positive": 4, "false_negative": 5},
    }
    state = p._initial_state()
    state["pending"] = [{
        "id": "unknown", "issued_at": "2026-10-22T14:00:00+00:00",
        "prediction": {"by_horizon": {"30": False, "60": False, "120": False}},
        "evaluated_horizons": [],
    }]
    data = {"local_precipitation": {"status": "unavailable", "history": [
        {"timestamp": "2026-10-22T14:15:00+00:00", "rain_detected": None, "observation_valid": False}
    ]}}
    # v1 migration does not reuse old pending forecasts because coverage semantics changed.
    _, report, events = p.apply(data, {"summary": {}}, {"precipitation_verification": legacy}, now=now)
    assert events["precipitation_verification_legacy_v1"] == legacy
    assert report["summary"]["precipitation_presence"]["cumulative"]["samples"] == 0
    _, report, events = p.apply(data, report, {
        **events, "precipitation_verification": {**state, "skipped_unverifiable": 0}
    }, now=now)
    assert report["summary"]["precipitation_presence"]["skipped_unverifiable"] == 1
    assert report["summary"]["precipitation_presence"]["cumulative"]["samples"] == 0
    assert events["precipitation_verification"]["results"] == []
