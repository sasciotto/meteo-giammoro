from datetime import datetime, timezone

import solar_monitoring


def test_product_url_uses_quarter_hour_timestamp():
    stamp = datetime(2026, 10, 29, 7, 45, tzinfo=timezone.utc)
    url = solar_monitoring.product_url(stamp)
    assert url.endswith('/2026/10/29/NETCDF4_LSASAF_MSG_MDSSFTD_MSG-Disk_202610290745.nc')


def test_candidate_times_are_latest_first():
    now = datetime(2026, 10, 29, 8, 7, tzinfo=timezone.utc)
    values = list(solar_monitoring.candidate_product_times(now, lookback_hours=1))
    assert values[0] == datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc)
    assert values[-1] == datetime(2026, 10, 29, 7, 0, tzinfo=timezone.utc)
    assert len(values) == 5


def test_daily_energy_integrates_only_new_short_gap():
    previous = {
        'observation': {
            'observed_at': '2026-10-29T08:00:00Z',
            'total_shortwave_wm2': 400.0,
        },
        'daily': {
            'local_date': '2026-10-29',
            'energy_kwh_m2': 1.0,
            'coverage_minutes': 60,
            'samples': 4,
            'first_observed_at': '2026-10-29T07:00:00Z',
            'last_observed_at': '2026-10-29T08:00:00Z',
        },
    }
    observation = {
        'observed_at': '2026-10-29T08:15:00Z',
        'total_shortwave_wm2': 600.0,
    }
    daily = solar_monitoring.update_daily_summary(previous, observation, 'Europe/Rome')
    assert daily['energy_kwh_m2'] == 1.125
    assert daily['coverage_minutes'] == 75
    assert daily['samples'] == 5


def test_update_data_without_credentials_is_explicit_and_nonfatal(tmp_path, monkeypatch):
    data_path = tmp_path / 'data.json'
    data_path.write_text('{"meta":{"collector_status":"ok"}}\n', encoding='utf-8')
    monkeypatch.delenv('LSASAF_USERNAME', raising=False)
    monkeypatch.delenv('LSASAF_PASSWORD', raising=False)

    payload = solar_monitoring.update_data(
        data_path,
        now_utc=datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc),
    )

    assert payload['status'] == 'credentials_missing'
    assert payload['observation'] is None
    assert payload['reference']['name'] == 'Giammoro'
    text = data_path.read_text(encoding='utf-8')
    assert 'solar_monitoring' in text
    assert 'collector_status' in text


def test_update_data_can_reuse_previous_cycle_solar_state(tmp_path, monkeypatch):
    current = tmp_path / 'data.json'
    previous = tmp_path / 'previous.json'
    current.write_text('{"meta":{"collector_status":"ok"}}\n', encoding='utf-8')
    previous.write_text(
        '{"solar_monitoring":{"observation":{"observed_at":"2026-10-29T07:45:00Z","total_shortwave_wm2":300,"age_minutes":15},"daily":{"local_date":"2026-10-29","energy_kwh_m2":0.5,"coverage_minutes":60,"samples":4}}}\n',
        encoding='utf-8',
    )
    monkeypatch.delenv('LSASAF_USERNAME', raising=False)
    monkeypatch.delenv('LSASAF_PASSWORD', raising=False)

    payload = solar_monitoring.update_data(
        current,
        now_utc=datetime(2026, 10, 29, 8, 0, tzinfo=timezone.utc),
        previous_path=previous,
    )

    assert payload['status'] == 'credentials_missing'
    assert payload['observation']['total_shortwave_wm2'] == 300
    assert payload['daily']['energy_kwh_m2'] == 0.5
