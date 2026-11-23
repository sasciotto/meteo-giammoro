"""Regression tests for P1 meteorological data integrity and station identity."""
from pathlib import Path

import collector


def test_station_matches_only_unique_complete_canonical_name():
    rows = {
        "Messina (SIAS)": {"name": "Messina (SIAS)", "temperature": 18},
        "Messina (DRPC)": {"name": "Messina (DRPC)", "temperature": 16},
        "Merì - Meteo": {"name": "Merì - Meteo", "temperature": 17},
    }
    assert collector._match_cms_station(rows, "Messina - SIAS")["temperature"] == 18
    assert collector._match_cms_station(rows, "Meri Meteo")["temperature"] == 17
    assert collector._match_cms_station(rows, "Messina") is None
    assert collector._match_cms_station(rows, "San Filippo del Mela") is None


def test_station_rejects_ambiguous_instrument_suffixes():
    rows = {
        "Milazzo Piana Sensor A": {"name": "Milazzo Piana Sensor A"},
        "Milazzo Piana Sensor B": {"name": "Milazzo Piana Sensor B"},
    }
    assert collector._match_cms_station(rows, "Milazzo Piana") is None
    assert collector._match_cms_station(rows, "Milazzo Piana Sensor A") == rows["Milazzo Piana Sensor A"]


def test_frontend_missing_cloud_values_are_not_zeros():
    home = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert "value === null || value === undefined || value === ''" in home
    assert "typeof value === 'string' && !value.trim()" in home
    assert "const x = Number(value)" in home
    assert ".map(row => num(row.current.cloud_cover))" in home


def test_source_statuses_are_independent_and_stay_in_footer():
    home = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert "Disponibilità delle fonti meteorologiche" in home
    assert "Radar SRI: non verificabile ora" in home
    assert "Stazioni: dati non recenti" in home
    assert "Fulminazioni: dato non disponibile o non recente" in home
    assert "Allerte ufficiali: livello non verificato" in home
    assert "Date.parse(sri.timestamp || '')" in home
    assert "Date.parse((data?.lightning || {}).observed_at || '')" in home
    assert "strip.appendChild(health)" in home
    assert "const footer = document.querySelector('main .foot')" in home


def test_primary_station_not_implicitly_activated():
    source = Path("collector.py").read_text(encoding="utf-8")
    assert '"excluded_from_analysis": True' in source
    assert '"unmatched_groups"' in source
    assert '"matched_groups"' in source
