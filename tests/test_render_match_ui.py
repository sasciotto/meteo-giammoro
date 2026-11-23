"""Layout fedele al rendering senza radar, avvisi o valori fittizi."""
from pathlib import Path

from site_prepare import transform


def test_rendering_script_injected_after_existing_weather_modules():
    prepared = transform(Path("index.html").read_text(encoding="utf-8"))
    assert 'renderMatchStyles' in prepared
    assert 'homePolishStyles' in prepared
    assert prepared.index('homePolishStyles') < prepared.index('renderMatchStyles')
    assert "const $=id=>document.getElementById(id)" in prepared
    assert prepared.count('id="homePressure"') == 1


def test_reference_layout_sections_and_mobile_breakpoints():
    code = Path("render_match_ui.js").read_text(encoding="utf-8")
    for item in (
        "weather-main-inner{display:grid;grid-template-columns:",
        "home-nowcast-stage{display:grid;grid-template-columns:",
        "render-hourly-panel",
        "render-lower-grid",
        "render-day-panel",
        "render-sources",
        "Fonti e metodologia",
        "@media(max-width:1000px)",
        "@media(max-width:740px)",
        "@media(max-width:430px)",
        "@media(max-width:335px)",
    ):
        assert item in code
    assert "stationSection.appendChild(button)" in code
    assert "Mostra tutte le " in code


def test_radar_preview_is_real_and_falls_back_when_absent_or_stale():
    code = Path("render_match_ui.js").read_text(encoding="utf-8")
    assert "data?.dpc_observations?.products?.SRI" in code
    assert "sri.ok === true" in code
    assert "now - observed < 30 * 60000" in code
    assert "now - check < 35 * 60000" in code
    assert "radar-dpc.png?v=" in code
    assert "img.addEventListener('error', fallback" in code
    assert "Anteprima radar non disponibile o non recente" in code
    assert "https://radar.protezionecivile.it/" in code
    assert "data:image/" not in code
    assert "canvas" not in code


def test_station_wind_is_shown_only_from_current_support_observations():
    forecast = Path("forecast_dashboard.js").read_text(encoding="utf-8")
    layout = Path("render_match_ui.js").read_text(encoding="utf-8")
    assert "const wind = current ? num(s.wind) : null;" in forecast
    assert "home-station-wind" in forecast
    assert "wind === null ? 'Vento —'" in forecast
    assert "home-station-wind{grid-column:3" in layout


def test_pressure_and_cloud_provenance_kept_separate():
    html = Path("index.html").read_text(encoding="utf-8")
    assert 'id="homePressure"' in html
    assert 'id="homePressureTrend"' in html
    assert 'id="homeCloud" hidden' in html
    assert "valueUnit(m.pressure)" in html
    assert 'id="homeGust" hidden' in html
    assert 'id="homeObservationStrip"' in html
