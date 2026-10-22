from datetime import datetime
from zoneinfo import ZoneInfo

import station_fallback as fallback

TZ = ZoneInfo("Europe/Rome")


def test_previous_station_values_are_kept_but_excluded_from_analysis():
    previous = {
        "meta": {"last_check_iso": "2026-10-22T15:45:00+02:00"},
        "stations": [
            {
                "name": "MeteoGiammoro",
                "source_quality": "primary",
                "status": "maintenance",
                "excluded_from_analysis": True,
            },
            {
                "name": "Santa Lucia del Mela (DRPC)",
                "source_quality": "official",
                "status": "online",
                "status_label": "Online",
                "updated": "15:40 · 5 min fa",
                "temperature": 21.4,
                "rain_day": 3.2,
                "excluded_from_analysis": False,
                "note": "Osservazione di supporto.",
            },
        ],
    }
    now = datetime(2026, 10, 22, 16, 0, tzinfo=TZ)
    stations = fallback.previous_cycle_stations(previous, now, "403 Forbidden")

    assert stations[0]["status"] == "maintenance"
    assert stations[0]["excluded_from_analysis"] is True

    station = stations[1]
    assert station["temperature"] == 21.4
    assert station["rain_day"] == 3.2
    assert station["status"] == "unknown"
    assert station["status_label"] == "Dato precedente · feed non disponibile"
    assert station["excluded_from_analysis"] is True
    assert station["data_freshness"] == "previous_cycle"
    assert station["fallback_age_minutes"] == 15
    assert station["updated"] == "ultimo ciclo valido · 15 min fa"
    assert station["fallback_reason"] == "403 Forbidden"
    assert "escluso dall'analisi" in station["note"]


def test_repeated_fallback_keeps_original_last_valid_cycle():
    previous = {
        "meta": {"last_check_iso": "2026-10-22T16:00:00+02:00"},
        "stations": [
            {
                "name": "Venetico (DRPC)",
                "status": "unknown",
                "status_label": "Dato precedente · feed non disponibile",
                "temperature": 22.0,
                "excluded_from_analysis": True,
                "data_freshness": "previous_cycle",
                "last_valid_cycle_iso": "2026-10-22T15:30:00+02:00",
            }
        ],
    }
    now = datetime(2026, 10, 22, 16, 15, tzinfo=TZ)
    station = fallback.previous_cycle_stations(previous, now, "ancora non disponibile")[0]
    assert station["last_valid_cycle_iso"] == "2026-10-22T15:30:00+02:00"
    assert station["fallback_age_minutes"] == 45


def test_metadata_marks_feed_as_degraded():
    now = datetime(2026, 10, 22, 16, 0, tzinfo=TZ)
    meta = fallback.metadata("403 Forbidden", now)
    assert meta["fallback"] is True
    assert meta["status"] == "degraded"
    assert meta["rows"] == 0
    assert meta["reason"] == "403 Forbidden"
