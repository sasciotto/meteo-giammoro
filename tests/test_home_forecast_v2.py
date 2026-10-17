from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import home_forecast_v2 as h

TZ = ZoneInfo("Europe/Rome")


def test_current_summary_does_not_invent_clear_sky_without_cloud_data():
    data = {
        "territory": {"metrics": {}},
        "nowcast": {"level": "low"},
        "nowcast_tracking": {"status": "no_cell", "motion": {"status": "unavailable"}},
        "lightning": {"status": "ok", "radii": {"20": {"flash_count": 0}}},
    }
    out = h.current_summary(data, datetime(2026, 10, 18, 1, 0, tzinfo=TZ))
    assert out["condition_available"] is False
    assert "non disponibili" in out["label"].lower()


def test_apply_reuses_recent_previous_forecast_and_marks_degraded():
    now = datetime(2026, 10, 18, 1, 0, tzinfo=TZ)

    class Collector:
        MODEL_SPECS = [("ItaliaMeteo ICON-2I", "icon", 3)]
        OPEN_METEO = "https://example.invalid"

        @staticmethod
        def now_local():
            return now

        @staticmethod
        def model_params(model_id, days):
            return {"models": model_id}

        @staticmethod
        def fetch_json(*args, **kwargs):
            raise TimeoutError("timeout")

    previous = {
        "home_summary": {
            "generated_at": (now - timedelta(minutes=25)).isoformat(),
            "source": "ItaliaMeteo ICON-2I",
            "forecast_available": True,
            "hourly": [{"label_time": "01:00"}],
            "days": [{"key": "today"}],
            "multi_model": {"available": True},
            "current": {"label": "vecchio"},
        }
    }
    data = {
        "meta": {"collector_status": "ok", "collector_errors": []},
        "territory": {"metrics": {}},
        "nowcast": {"level": "low"},
        "nowcast_tracking": {"status": "no_cell", "motion": {"status": "unavailable"}},
        "lightning": {"status": "ok", "radii": {"20": {"flash_count": 0}}},
        "model_details": [],
    }
    out = h.apply(data, Collector, previous=previous)
    assert out["meta"]["collector_status"] == "degraded"
    assert out["home_summary"]["forecast_available"] is True
    assert out["home_summary"]["stale"] is True
    assert out["home_summary"]["stale_age_minutes"] == 25
    assert out["home_summary"]["current"]["condition_available"] is False
