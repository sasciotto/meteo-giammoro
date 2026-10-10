from datetime import datetime
from zoneinfo import ZoneInfo

import home_forecast as h

TZ = ZoneInfo("Europe/Rome")


def raw_fixture():
    return {
        "hourly": {
            "time": [
                "2026-10-10T22:00", "2026-10-10T23:00",
                "2026-10-11T00:00", "2026-10-11T01:00", "2026-10-11T12:00"
            ],
            "temperature_2m": [17, 16.5, 16, 15.5, 22],
            "precipitation": [0, 0.2, 1.2, 0.5, 0],
            "cloud_cover": [70, 90, 95, 90, 30],
            "wind_speed_10m": [8, 10, 12, 10, 15],
            "wind_gusts_10m": [15, 18, 25, 20, 30],
            "weather_code": [2, 61, 63, 61, 1],
        }
    }


def base_data():
    return {
        "nowcast": {"level": "moderato"},
        "territory": {"metrics": {"rain_1h": {"value": 0}, "cloud_cover": {"value": 60}}},
        "nowcast_tracking": {
            "status": "detected",
            "product": "SRI",
            "hazard_cell": {"distance_km": 12, "peak_value": 8},
            "cell": {"distance_km": 30, "peak_value": 20},
            "motion": {"status": "tracked", "eta_minutes": None},
        },
        "lightning": {"status": "ok", "radii": {"20": {"flash_count": 0}}},
    }


def test_current_summary_uses_hazard_cell():
    out = h.current_summary(base_data(), datetime(2026, 10, 10, 22, 30, tzinfo=TZ))
    assert out["kind"] == "rain"
    assert out["short_term"]["title"] == "Fenomeni molto vicini"


def test_hourly_forecast_returns_future_hours():
    out = h.hourly_forecast(raw_fixture(), datetime(2026, 10, 10, 22, 30, tzinfo=TZ), limit=3)
    assert len(out) == 3
    assert out[0]["label_time"] == "22:00"
    assert out[1]["kind"] == "rain"


def test_daily_forecast_separates_today_and_tomorrow():
    out = h.daily_forecast(raw_fixture(), datetime(2026, 10, 10, 22, 30, tzinfo=TZ))
    assert [x["key"] for x in out] == ["today", "tomorrow"]
    assert out[0]["precipitation_sum"] == 0.2
    assert out[1]["precipitation_sum"] == 1.7
