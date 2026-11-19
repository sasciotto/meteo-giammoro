from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import station_rain_history as r

TZ = ZoneInfo("Europe/Rome")
NOW = datetime(2026, 11, 19, 17, 30, tzinfo=TZ)
NAME = "Archi - San Filippo del Mela (LineaMeteo) Ecowitt WS3900"


def sample(minute, mm, **overrides):
    # Readings are actual source HH:MM, not collector times.
    t = NOW - timedelta(minutes=minute)
    return {
        "name": NAME,
        "display_name": "Pace del Mela / area Giammoro",
        "status": "online",
        "excluded_from_analysis": False,
        "source_quality": "reliable",
        "updated": t.strftime("%H:%M") + f" · {minute} min fa",
        "rain_day": mm,
        **overrides,
    }


def data(station, now=NOW):
    return {"meta": {"last_check_iso": now.isoformat()}, "stations": [station]}


def past(*pairs):
    return {
        "stations": {NAME: [
            {"at": (NOW - timedelta(minutes=minute)).isoformat(timespec="minutes"),
             "rain_day_mm": value}
            for minute, value in pairs
        ]}
    }


def test_no_history_does_not_claim_dry_or_zero():
    out, history = r.update(data(sample(0, 0)))
    assert out["stations"][0]["rain_1h"] is None
    assert out["stations"][0]["rain_30m"] is None
    assert out["stations"][0]["rain_15m"] is None
    assert len(history["stations"][NAME]) == 1
    assert out["nearby_station_rain"]["stations_with_valid_1h"] == 0


def test_full_observations_produce_actual_rain_increments():
    prev = past((60, 1.2), (45, 1.7), (30, 2.0), (15, 2.4))
    out, history = r.update(data(sample(0, 3.4)), prev)
    station = out["stations"][0]
    assert station["rain_15m"] == 1.0
    assert station["rain_30m"] == 1.4
    assert station["rain_1h"] == 2.2
    assert out["nearby_station_rain"]["stations_with_valid_1h"] == 1
    assert len(history["stations"][NAME]) == 5


def test_missing_intermediate_samples_prevent_hourly_claim():
    prev = past((60, 1), (15, 2))
    out, _ = r.update(data(sample(0, 3)), prev)
    assert out["stations"][0]["rain_15m"] == 1
    assert out["stations"][0]["rain_30m"] is None
    assert out["stations"][0]["rain_1h"] is None


def test_unchanged_station_time_is_not_a_new_observation():
    prev = past((60, 1), (45, 1), (30, 1), (15, 1))
    out, history = r.update(data(sample(15, 1)), prev)
    assert out["stations"][0]["rain_15m"] is None
    assert len(history["stations"][NAME]) == 4


def test_stale_fallback_and_primary_station_are_excluded():
    for overrides in (
        {"status": "unknown", "excluded_from_analysis": True, "data_freshness": "previous_cycle"},
        {"status": "test"},
        {"updated": "ultima lettura conservata"},
    ):
        out, history = r.update(data(sample(0, 4, **overrides)), past((60, 1), (45, 1), (30, 1), (15, 1)))
        assert out["stations"][0]["rain_1h"] is None
        assert len(history["stations"][NAME]) == 4
    primary = sample(0, 4, name="MeteoGiammoro", source_quality="primary", status="test")
    out, hist = r.update(data(primary))
    assert out["stations"][0]["rain_1h"] is None
    assert hist["stations"] == {}


def test_daily_reset_and_negative_cumulative_are_not_rainfall():
    prev = past((60, 3.5), (45, 3.7), (30, 0.0), (15, 0.0))
    out, _ = r.update(data(sample(0, 0)), prev)
    assert out["stations"][0]["rain_1h"] is None
    assert out["stations"][0]["rain_30m"] == 0.0
    assert out["stations"][0]["rain_15m"] == 0.0


def test_midnight_crossing_is_never_reported_as_one_hour_rain():
    after = datetime(2026, 11, 20, 0, 10, tzinfo=TZ)
    previous = {
        "stations": {NAME: [
            {"at": "2026-11-19T23:10:00+01:00", "rain_day_mm": 8.0},
            {"at": "2026-11-19T23:25:00+01:00", "rain_day_mm": 9.0},
            {"at": "2026-11-19T23:40:00+01:00", "rain_day_mm": 9.0},
            {"at": "2026-11-19T23:55:00+01:00", "rain_day_mm": 9.0},
        ]}
    }
    station = sample(0, 0, updated="00:10")
    out, _ = r.update(data(station, after), previous)
    assert out["stations"][0]["rain_1h"] is None


def test_revised_measurement_same_timestamp_is_not_recounted():
    prev = past((60, 1), (45, 1.5), (30, 2), (15, 2.2), (0, 2.4))
    out, history = r.update(data(sample(0, 4)), prev)
    assert out["stations"][0]["rain_1h"] is None
    assert len(history["stations"][NAME]) == 4


def test_zero_is_valid_only_when_observed_continuously():
    out, _ = r.update(data(sample(0, 0)), past((60, 0), (45, 0), (30, 0), (15, 0)))
    assert out["stations"][0]["rain_1h"] == 0
    assert out["stations"][0]["rain_30m"] == 0
    assert out["stations"][0]["rain_15m"] == 0


def test_old_samples_pruned_and_station_identity_is_kept():
    prev = {"stations": {"Un'altra stazione": [
        {"at": "2026-11-16T10:00:00+01:00", "rain_day_mm": 3}
    ], NAME: [{"at": "2026-11-16T10:00:00+01:00", "rain_day_mm": 2}]}}
    out, hist = r.update(data(sample(0, 1)), prev)
    assert "Un'altra stazione" not in hist["stations"]
    assert len(hist["stations"][NAME]) == 1
