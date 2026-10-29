from datetime import datetime, timezone

import ground_solar


def test_parse_cumulus_gauges_reads_solar_and_uv():
    text = '{"SolarRad":"512","UV":"3.4","date":"29/10/26","time":"12:15:00"}'
    result = ground_solar.parse_cumulus_gauges(text, now_utc=datetime(2026, 10, 29, 11, 16, tzinfo=timezone.utc))
    assert result['solar_wm2'] == 512.0
    assert result['uv_index'] == 3.4
    assert result['observed_at'] == '2026-10-29T11:15:00Z'


def test_parse_cumulus_realtime_standard_fields():
    fields = ['0'] * 46
    fields[0] = '29/10/26'
    fields[1] = '12:15:00'
    fields[43] = '2.7'
    fields[45] = '488'
    result = ground_solar.parse_cumulus_realtime(' '.join(fields), now_utc=datetime(2026, 10, 29, 11, 16, tzinfo=timezone.utc))
    assert result['solar_wm2'] == 488.0
    assert result['uv_index'] == 2.7


def test_parse_wunderground_station_html_reads_uv_and_radiation():
    html = '<html><body><div>UV 2.4 Moderate</div><div>Radiation 411.7</div></body></html>'
    result = ground_solar.parse_wunderground_station_html(html, now_utc=datetime(2026, 10, 29, 11, 0, tzinfo=timezone.utc))
    assert result['solar_wm2'] == 411.7
    assert result['uv_index'] == 2.4


def test_parse_meteonetwork_station_html_reads_labels():
    html = '<html><body><div>Radiazione solare 325 W/m²</div><div>Radiazione UV 1,8</div></body></html>'
    result = ground_solar.parse_meteonetwork_station_html(html, now_utc=datetime(2026, 10, 29, 11, 0, tzinfo=timezone.utc))
    assert result['solar_wm2'] == 325.0
    assert result['uv_index'] == 1.8


def test_haversine_archi_distance_is_about_four_km_from_giammoro():
    distance = ground_solar.haversine_km(38.2018, 15.31816, ground_solar.ARCHI_LAT, ground_solar.ARCHI_LON)
    assert 3.5 < distance < 4.5


def test_haversine_scl087_distance_is_about_ten_km_from_giammoro():
    distance = ground_solar.haversine_km(38.2018, 15.31816, ground_solar.SCL087_LAT, ground_solar.SCL087_LON)
    assert 9.0 < distance < 11.0
