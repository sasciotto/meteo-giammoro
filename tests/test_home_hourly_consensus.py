from datetime import datetime
from zoneinfo import ZoneInfo

import home_hourly_consensus as h

TZ = ZoneInfo('Europe/Rome')
NOW = datetime(2026, 10, 27, 10, 5, tzinfo=TZ)


def raw(clouds, codes=None, precip=None, temps=None):
    times = [f'2026-10-27T{hour:02d}:00' for hour in range(10, 14)]
    return {
        'hourly': {
            'time': times,
            'temperature_2m': temps or [20, 21, 22, 22],
            'precipitation': precip or [0, 0, 0, 0],
            'cloud_cover': clouds,
            'wind_speed_10m': [10, 10, 11, 11],
            'wind_gusts_10m': [20, 20, 21, 21],
            'weather_code': codes or [3, 3, 0, 0],
        }
    }


def test_hourly_consensus_avoids_false_clear_sky_when_models_disagree():
    cache = {
        'italia_meteo_arpae_icon_2i': raw([100, 95, 5, 5]),
        'dwd_icon_seamless': raw([80, 75, 55, 45]),
        'ecmwf_ifs': raw([45, 40, 35, 30]),
        'ncep_gfs_seamless': raw([30, 25, 20, 15]),
    }
    rows, labels = h.consensus_hourly(cache, NOW, limit=4)
    assert len(labels) == 4
    assert [row['label'] for row in rows] == [
        'Cielo variabile',
        'Cielo variabile',
        'Cielo variabile',
        'Cielo variabile',
    ]
    assert all(row['label'] != 'Sereno' for row in rows)
    assert rows[2]['cloud_spread'] == 50.0


def test_hourly_consensus_allows_clear_only_with_strong_agreement():
    cache = {
        'italia_meteo_arpae_icon_2i': raw([10, 10, 10, 10], codes=[0, 0, 0, 0]),
        'dwd_icon_seamless': raw([15, 15, 15, 15], codes=[0, 0, 0, 0]),
        'ecmwf_ifs': raw([8, 8, 8, 8], codes=[0, 0, 0, 0]),
        'ncep_gfs_seamless': raw([12, 12, 12, 12], codes=[1, 1, 1, 1]),
    }
    rows, _ = h.consensus_hourly(cache, NOW, limit=4)
    assert rows
    assert all(row['label'] == 'Sereno' for row in rows)
    assert all(row['cloud_spread'] <= 20 for row in rows)


def test_hourly_consensus_uses_majority_for_rain_signal():
    cache = {
        'italia_meteo_arpae_icon_2i': raw([90]*4, codes=[61]*4, precip=[0.5]*4),
        'dwd_icon_seamless': raw([90]*4, codes=[61]*4, precip=[0.4]*4),
        'ecmwf_ifs': raw([60]*4, codes=[61]*4, precip=[0.3]*4),
        'ncep_gfs_seamless': raw([20]*4, codes=[1]*4, precip=[0.0]*4),
    }
    rows, _ = h.consensus_hourly(cache, NOW, limit=4)
    assert rows
    assert all(row['label'] == 'Possibili piogge' for row in rows)
    assert all(row['kind'] == 'rain' for row in rows)


def test_apply_replaces_single_model_hourly_source_with_consensus():
    data = {
        'home_summary': {
            'forecast_available': True,
            'generated_at': NOW.isoformat(),
            'source': 'ItaliaMeteo ICON-2I',
            'hourly': [{'label': 'Sereno'}],
        }
    }
    cache = {
        'italia_meteo_arpae_icon_2i': raw([100, 95, 5, 5]),
        'dwd_icon_seamless': raw([80, 75, 55, 45]),
        'ecmwf_ifs': raw([45, 40, 35, 30]),
        'ncep_gfs_seamless': raw([30, 25, 20, 15]),
    }
    changed = h.apply(data, cache, NOW)
    assert changed is True
    assert data['home_summary']['source'].startswith('Consenso multi-modello')
    assert data['home_summary']['hourly'][0]['consensus'] is True
    assert data['home_summary']['hourly_consensus']['model_count'] == 4


def test_wind_gust_consensus_never_displays_gust_below_wind():
    cache = {
        'italia_meteo_arpae_icon_2i': raw([10]*4),
        'dwd_icon_seamless': raw([10]*4),
        'ecmwf_ifs': raw([10]*4),
        'ncep_gfs_seamless': raw([10]*4),
    }
    # Three internally consistent model pairs but a fourth invalid gust.
    cache['italia_meteo_arpae_icon_2i']['hourly']['wind_speed_10m'] = [7]*4
    cache['italia_meteo_arpae_icon_2i']['hourly']['wind_gusts_10m'] = [6]*4
    cache['dwd_icon_seamless']['hourly']['wind_speed_10m'] = [9]*4
    cache['dwd_icon_seamless']['hourly']['wind_gusts_10m'] = [15]*4
    cache['ecmwf_ifs']['hourly']['wind_speed_10m'] = [8]*4
    cache['ecmwf_ifs']['hourly']['wind_gusts_10m'] = [12]*4
    cache['ncep_gfs_seamless']['hourly']['wind_speed_10m'] = [10]*4
    cache['ncep_gfs_seamless']['hourly']['wind_gusts_10m'] = [11]*4
    rows, _ = h.consensus_hourly(cache, NOW)
    assert rows
    assert all(row['gust_kmh'] >= row['wind_kmh'] for row in rows if row['gust_kmh'] is not None)
    assert rows[0]['wind_kmh'] == 9.0
    assert rows[0]['gust_kmh'] == 12.0


def test_invalid_model_gusts_are_not_fabricated():
    a = raw([10]*4)
    b = raw([12]*4)
    a['hourly']['wind_speed_10m'] = [12]*4
    a['hourly']['wind_gusts_10m'] = [6]*4
    b['hourly']['wind_speed_10m'] = [14]*4
    b['hourly']['wind_gusts_10m'] = [7]*4
    rows, _ = h.consensus_hourly({
        'italia_meteo_arpae_icon_2i': a,
        'dwd_icon_seamless': b,
    }, NOW)
    assert rows[0]['gust_kmh'] is None
    assert rows[0]['wind_kmh'] == 13.0
