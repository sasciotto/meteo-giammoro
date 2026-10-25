from pathlib import Path

import site_prepare as s


def test_home_polish_is_injected_and_keeps_single_data_pipeline():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    scripts = s._dashboard_scripts()
    assert "homePolishStyles" in js
    assert "Radar live" in js
    assert "Nowcast 0–3 h" in js
    assert "Aggiornamento automatico" in js
    assert "homeObservationStrip" in js
    assert "homeSummaryCards" in js
    assert "home_polish_ui.js" not in scripts  # iniettato inline da site_prepare
    assert "homePolishStyles" in scripts
    assert "fetch('data.json" not in js
    assert "fetch(`data.json" not in js


def test_home_polish_reuses_backend_nowcast_and_marks_model_timeline():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    compact = "".join(js.split())
    assert "data?.home_summary?.hourly" in js
    assert "Pioggia modello" in js
    assert "homeNowcastSimple" in js
    assert "renderForecastDashboard" in js
    assert "home-alert-compact" in js
    assert "['warning','orange','red']" in compact


def test_home_polish_keeps_support_station_identity_explicit():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert "station.display_name || station.name" in js
    assert "coordinate di Giammoro" in js
    assert "Stazioni circostanti usate come controllo" in js
