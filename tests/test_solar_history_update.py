from datetime import datetime, timezone

import solar_history_update


def test_missing_quarter_hours_recovers_intermediate_slots():
    values = solar_history_update.missing_quarter_hours(
        "2026-10-31T08:00:00Z",
        "2026-10-31T09:00:00Z",
    )
    assert values == [
        datetime(2026, 10, 31, 8, 15, tzinfo=timezone.utc),
        datetime(2026, 10, 31, 8, 30, tzinfo=timezone.utc),
        datetime(2026, 10, 31, 8, 45, tzinfo=timezone.utc),
    ]


def test_missing_quarter_hours_does_nothing_for_normal_15_minute_advance():
    assert solar_history_update.missing_quarter_hours(
        "2026-10-31T08:00:00Z",
        "2026-10-31T08:15:00Z",
    ) == []


def test_missing_quarter_hours_caps_large_gap_to_four_hours():
    values = solar_history_update.missing_quarter_hours(
        "2026-10-30T20:00:00Z",
        "2026-10-31T09:00:00Z",
    )
    assert values[0] == datetime(2026, 10, 31, 5, 0, tzinfo=timezone.utc)
    assert values[-1] == datetime(2026, 10, 31, 8, 45, tzinfo=timezone.utc)
    assert len(values) == 16


def test_fetch_intermediate_skips_404_and_decodes_available(monkeypatch):
    class Response:
        def __init__(self, status_code, content=b""):
            self.status_code = status_code
            self.content = content
        def raise_for_status(self):
            assert self.status_code < 400

    responses = iter([Response(404), Response(200, b"netcdf"), Response(404)])
    monkeypatch.setattr(solar_history_update.solar_monitoring.SESSION, "get", lambda *a, **k: next(responses))
    monkeypatch.setattr(
        solar_history_update.solar_monitoring,
        "decode_netcdf",
        lambda content, stamp, url, latitude, longitude: {
            "observed_at": stamp.isoformat().replace("+00:00", "Z"),
            "total_shortwave_wm2": 500.0,
        },
    )
    result = solar_history_update.fetch_intermediate_observations(
        {"latitude": 38.2, "longitude": 15.3},
        "2026-10-31T08:00:00Z",
        "2026-10-31T09:00:00Z",
        "u",
        "p",
    )
    assert len(result) == 1
    assert result[0]["observed_at"] == "2026-10-31T08:30:00Z"
