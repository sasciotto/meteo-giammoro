from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import home_forecast_v2 as h

TZ = ZoneInfo("Europe/Rome")


def base_data():
    return {
        "meta": {"collector_status": "ok", "collector_errors": []},
        "territory": {"metrics": {}},
        "nowcast": {"level": "low"},
        "nowcast_tracking": {"status": "no_cell", "motion": {"status": "unavailable"}},
        "lightning": {"status": "ok", "radii": {"20": {"flash_count": 0}}},
        "model_details": [],
    }


def hour(ts, temp=18, rain=0.0, cloud=50, wind=5, gust=10, code=2):
    return {
        "time": ts,
        "label_time": "vecchio",
        "temperature": temp,
        "precipitation": rain,
        "cloud_cover": cloud,
        "wind_kmh": wind,
        "gust_kmh": gust,
        "weather_code": code,
    }


def test_current_summary_does_not_invent_clear_sky_without_cloud_data():
    out = h.current_summary(base_data(), datetime(2026, 10, 18, 1, 0, tzinfo=TZ))
    assert out["condition_available"] is False
    assert "non disponibili" in out["label"].lower()


def test_apply_reuses_recent_previous_forecast_and_marks_degraded():
    now = datetime(2026, 10, 18, 1, 0, tzinfo=TZ)

    class Collector:
        MODEL_SPECS = [("ItaliaMeteo ICON-2I", "icon", 3)]
        OPEN_METEO = "https://example.invalid"
        @staticmethod
        def now_local(): return now
        @staticmethod
        def model_params(model_id, days): return {"models": model_id}
        @staticmethod
        def fetch_json(*args, **kwargs): raise TimeoutError("timeout")

    previous = {
        "home_summary": {
            "generated_at": (now - timedelta(minutes=25)).isoformat(),
            "source": "ItaliaMeteo ICON-2I",
            "forecast_available": True,
            "hourly": [hour(now.replace(minute=0).isoformat())],
            "days": [{"key": "today"}],
            "multi_model": {"available": True},
            "current": {"label": "vecchio"},
        }
    }
    out = h.apply(base_data(), Collector, previous=previous)
    assert out["meta"]["collector_status"] == "degraded"
    assert out["home_summary"]["forecast_available"] is True
    assert out["home_summary"]["stale"] is True
    assert out["home_summary"]["stale_age_minutes"] == 25
    assert out["home_summary"]["current"]["condition_available"] is False
    assert out["home_summary"]["hourly"][0]["label_time"] == "01:00"


def test_fallback_filters_elapsed_hours_and_relabels_across_midnight():
    now = datetime(2026, 10, 19, 0, 20, tzinfo=TZ)
    previous = {
        "home_summary": {
            "generated_at": datetime(2026, 10, 18, 23, 50, tzinfo=TZ).isoformat(),
            "source": "ItaliaMeteo ICON-2I",
            "forecast_available": True,
            "hourly": [
                hour("2026-10-18T23:00:00+02:00"),
                hour("2026-10-19T00:00:00+02:00"),
                hour("2026-10-19T01:00:00+02:00", cloud=80, code=3),
                hour("2026-10-20T00:00:00+02:00", rain=1.0, cloud=90, code=61),
            ],
            "days": [{"key": "today", "label": "Oggi vecchio"}, {"key": "tomorrow", "label": "Domani vecchio"}],
        }
    }
    out = h._fallback_home(previous, base_data(), now)
    assert [row["time"][:13] for row in out["hourly"]] == [
        "2026-10-19T00", "2026-10-19T01", "2026-10-20T00"
    ]
    assert [day["key"] for day in out["days"]] == ["today", "tomorrow"]
    assert [day["label"] for day in out["days"]] == ["Oggi", "Domani"]
    assert all(day["basis"] == "ItaliaMeteo ICON-2I" for day in out["days"])


def test_fallback_marks_forecast_unavailable_when_future_horizon_is_exhausted():
    now = datetime(2026, 10, 19, 10, 15, tzinfo=TZ)
    previous = {
        "home_summary": {
            "generated_at": datetime(2026, 10, 19, 9, 50, tzinfo=TZ).isoformat(),
            "source": "ItaliaMeteo ICON-2I",
            "forecast_available": True,
            "hourly": [
                hour("2026-10-19T08:00:00+02:00"),
                hour("2026-10-19T09:00:00+02:00"),
            ],
            "days": [{"key": "today", "label": "Oggi"}],
        }
    }
    out = h._fallback_home(previous, base_data(), now)
    assert out["forecast_available"] is False
    assert out["hourly"] == []
    assert out["days"] == []
    assert "esaurita" in out["stale_reason"]


def test_build_keeps_extended_hourly_horizon_for_safe_fallback():
    now = datetime(2026, 10, 19, 10, 8, tzinfo=TZ)
    times = [(now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=i)).isoformat() for i in range(48)]
    raw = {"hourly": {
        "time": times,
        "temperature_2m": [18] * 48,
        "precipitation": [0] * 48,
        "cloud_cover": [50] * 48,
        "wind_speed_10m": [5] * 48,
        "wind_gusts_10m": [10] * 48,
        "weather_code": [2] * 48,
    }}
    out = h.build(base_data(), raw, "ItaliaMeteo ICON-2I", now)
    assert len(out["hourly"]) == 36
