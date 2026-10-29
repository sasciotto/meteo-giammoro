from datetime import datetime, timezone

import solar_history


def test_build_sample_keeps_ground_and_satellite_sources():
    solar = {
        'updated_at': '2026-10-29T16:00:00Z',
        'status': 'credentials_missing',
        'source': 'LSA SAF',
        'observation': None,
        'ground_observations': [
            {'id': 'pace-del-mela', 'name': 'Pace del Mela', 'source': 'Cumulus MX', 'status': 'ok', 'solar_wm2': 220, 'uv_index': 1.2}
        ],
    }
    sample = solar_history.build_sample(solar)
    assert sample['sources']['pace-del-mela']['solar_wm2'] == 220.0
    assert sample['sources']['pace-del-mela']['uv_index'] == 1.2
    assert sample['sources']['lsa-saf']['solar_wm2'] is None


def test_summarize_day_integrates_only_short_valid_gaps():
    samples = [
        {'timestamp':'2026-10-29T08:00:00Z','sources':{'pace':{'name':'Pace','status':'ok','solar_wm2':400,'uv_index':1}}},
        {'timestamp':'2026-10-29T08:15:00Z','sources':{'pace':{'name':'Pace','status':'ok','solar_wm2':600,'uv_index':2}}},
        {'timestamp':'2026-10-29T10:00:00Z','sources':{'pace':{'name':'Pace','status':'ok','solar_wm2':800,'uv_index':3}}},
    ]
    day = solar_history.summarize_day(samples, '2026-10-29')
    pace = day['sources']['pace']
    assert pace['energy_kwh_m2'] == 0.125
    assert pace['coverage_minutes'] == 15
    assert pace['solar_max_wm2'] == 800.0
    assert pace['uv_max'] == 3.0


def test_update_history_deduplicates_timestamp(tmp_path):
    data = tmp_path / 'data.json'
    history = tmp_path / 'solar_history.json'
    payload = {
        'solar_monitoring': {
            'updated_at': '2026-10-29T16:00:00Z',
            'status': 'credentials_missing',
            'ground_observations': [
                {'id':'pace','name':'Pace','status':'ok','solar_wm2':100,'uv_index':0.4,'source':'test'}
            ],
            'observation': None,
        }
    }
    import json
    data.write_text(json.dumps(payload), encoding='utf-8')
    now = datetime(2026,10,29,16,0,tzinfo=timezone.utc)
    solar_history.update_history(data, history, now)
    solar_history.update_history(data, history, now)
    saved = json.loads(history.read_text(encoding='utf-8'))
    assert len(saved['samples']) == 1
    assert saved['daily'][0]['sources']['pace']['solar_max_wm2'] == 100.0
