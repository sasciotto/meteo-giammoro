from pathlib import Path

import site_prepare as s


def test_home_polish_is_injected_and_keeps_single_data_pipeline():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    scripts = s._dashboard_scripts()
    assert "homePolishStyles" in js
    assert "Radar live" in js
    assert "Nowcast osservativo 0–3 h" in js
    assert "Aggiornamento automatico" in js
    assert "homeObservationStrip" in js
    assert "homeSummaryCards" in js
    assert "home_polish_ui.js" not in scripts  # iniettato inline da site_prepare
    assert "homePolishStyles" in scripts
    assert "fetch('data.json" not in js
    assert "fetch(`data.json" not in js


def test_home_polish_keeps_observation_separate_from_model_timeline():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    forecast = Path("forecast_dashboard.js").read_text(encoding="utf-8")
    compact = "".join(js.split())
    assert "renderForecastDashboard" in js
    assert "home-alert-compact" in js
    assert "['warning','orange','red']" in compact
    assert "Nowcast osservativo 0–3 h" in js
    assert "homeObservationStrip" in js
    assert "homeNowcastSimple" in forecast
    assert "PREVISIONE MODELLISTICA" in forecast
    assert "const hourly = Array.isArray(home.hourly)" in forecast
    assert "renderNowcastTimeline(data)" not in js


def test_home_hourly_cards_use_consensus_weather_icons_without_duplicates():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    forecast = Path("forecast_dashboard.js").read_text(encoding="utf-8")
    assert 'class="hour-icon"' in forecast
    assert "esc(h.icon || '•')" in forecast
    assert 'aria-hidden="true"' in forecast
    assert 'aria-label="Previsione oraria, scorrevole"' in forecast
    assert "home-nowcast-step-icon" in js  # legacy CSS is harmless, but not rendered
    assert "renderNowcastTimeline(data)" not in js


def test_home_polish_emphasizes_operational_nowcast_message():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert "body.mode-home #forecastDetail .home-nowcast-title" in js
    assert "body.mode-home #forecastDetail .home-nowcast-text" in js
    assert "@media(max-width:650px)" in js


def test_home_polish_keeps_support_station_identity_explicit():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert "station.display_name || station.name" in js
    assert "coordinate di Giammoro" in js
    assert "Stazioni circostanti usate come controllo" in js


def test_home_polish_uses_model_consensus_for_current_sky():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    compact = "".join(js.split())
    assert "functioncurrentSkyConsensus(data)" in compact
    assert "data?.model_details" in js
    assert "row.current.cloud_cover" in js
    assert "spread>=35" in compact
    assert "label:'Cielo variabile'" in js
    assert "Consenso modellistico corrente" in js
    assert "forte variabilità" in js


def test_home_polish_does_not_override_rain_or_storm_with_sky_consensus():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    compact = "".join(js.split())
    assert "functionrenderCurrentSky(data)" in compact
    assert "card.classList.contains('rain')||card.classList.contains('storm')" in compact
