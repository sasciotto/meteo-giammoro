"""Regressioni sugli orari pubblicati dalle reti osservative."""
from datetime import datetime
from zoneinfo import ZoneInfo

import collector


def test_station_age_rejects_out_of_range_times_without_raising():
    now = datetime(2026, 11, 21, 14, 0, tzinfo=ZoneInfo("Europe/Rome"))
    for observed in ("24:00", "25:70", "12:60", "99:99"):
        status, label, age = collector.station_age_status(observed, now)
        assert (status, label, age) == ("unknown", "Orario non valido", None)


def test_station_age_preserves_valid_timestamp_behavior():
    now = datetime(2026, 11, 21, 14, 0, tzinfo=ZoneInfo("Europe/Rome"))
    assert collector.station_age_status("13:45", now) == ("online", "Online", 15)
    assert collector.station_age_status("13:00", now) == ("online", "Online", 60)
    assert collector.station_age_status("12:59", now) == ("test", "Dato vecchio", 61)


def test_station_age_rejects_missing_or_malformed_time():
    now = datetime(2026, 11, 21, 14, 0, tzinfo=ZoneInfo("Europe/Rome"))
    for observed in (None, "", "—", "12:0", "12:30 extra"):
        assert collector.station_age_status(observed, now) == ("unknown", "Orario non disponibile", None)
