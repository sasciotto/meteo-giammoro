from datetime import datetime, timezone
from pathlib import Path

import seismic_collector as s


SAMPLE = """#EventID|Time|Latitude|Longitude|Depth/km|Author|Catalog|Contributor|ContributorID|MagType|Magnitude|MagAuthor|EventLocationName|EventType
123456|2026-10-25T10:15:00.000000|38.2500|15.4000|12.3|SURVEY-INGV|INGV|INGV|123456|ML|2.4|SURVEY-INGV|4 km NE Giammoro (ME)|earthquake
123457|2026-10-24T08:00:00.000000|37.5000|14.0000|8.0|SURVEY-INGV|INGV|INGV|123457|ML|3.1|SURVEY-INGV|Sicilia centrale|earthquake
"""


def test_parse_fdsn_text_adds_giammoro_distance_and_source():
    rows = s.parse_fdsn_text(SAMPLE)
    assert len(rows) == 2
    first = rows[0]
    assert first["event_id"] == "123456"
    assert first["magnitude"] == 2.4
    assert first["magnitude_type"] == "ML"
    assert first["depth_km"] == 12.3
    assert first["distance_km"] < 20
    assert first["direction"] in {"NE", "ENE", "E", "NNE"}
    assert first["source_url"].endswith("/event/123456")
    assert "+00:00" in first["time_utc"]
    assert "+01:00" in first["time_local"]


def test_build_payload_separates_local_and_regional_without_risk_score():
    rows = s.parse_fdsn_text(SAMPLE)
    payload = s.build_payload(rows, datetime(2026, 10, 25, 12, tzinfo=timezone.utc))
    assert payload["meta"]["source"].startswith("INGV")
    assert payload["summary"]["local_radius_km"] == 150.0
    assert payload["summary"]["regional_radius_km"] == 500.0
    assert payload["summary"]["latest_local"]["event_id"] == "123456"
    assert payload["tsunami"]["mode"] == "official_only"
    assert payload["tsunami"]["status"] == "not_evaluated"
    assert "risk" not in payload
    assert "probability" not in payload


def test_collect_keeps_previous_dataset_when_ingv_fails(tmp_path: Path):
    output = tmp_path / "seismic_events.json"
    previous = s.build_payload(s.parse_fdsn_text(SAMPLE), datetime(2026, 10, 25, 10, tzinfo=timezone.utc))
    output.write_text(__import__("json").dumps(previous), encoding="utf-8")

    def fail(_params):
        raise RuntimeError("INGV non raggiungibile")

    payload = s.collect(
        output,
        now=datetime(2026, 10, 25, 11, tzinfo=timezone.utc),
        fetcher=fail,
    )
    assert payload["meta"]["status"] == "stale"
    assert payload["summary"]["latest_local"]["event_id"] == "123456"
    assert "INGV non raggiungibile" in payload["meta"]["error"]


def test_query_is_centered_on_giammoro_and_bounded():
    params = s.query_params(datetime(2026, 10, 25, 12, tzinfo=timezone.utc))
    assert params["latitude"] == s.GIAMMORO_LAT
    assert params["longitude"] == s.GIAMMORO_LON
    assert params["maxradiuskm"] == 500
    assert params["minmagnitude"] == 1.0
    assert params["format"] == "text"
    assert params["limit"] == 500
