"""Regression checks for blue mobile UI without coastline artwork."""
from pathlib import Path

from site_prepare import transform


def test_mobile_header_has_only_project_name():
    html = Path("index.html").read_text(encoding="utf-8")
    assert '<header class="hero"><div><h1>Meteo Giammoro</h1></div>' in html
    assert '<div class="sub">Giammoro · Pace del Mela (ME)</div>' not in html
    assert 'id="checked"' in html
    assert 'id="freshness"' in html


def test_blue_theme_uses_gradients_not_coastal_background_image():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert 'body.mode-home .hero{background:linear-gradient(' in js
    assert 'body.mode-home{background:linear-gradient(' in js
    assert 'body.mode-home .weather-main.calm:before' in js
    assert 'background-image:url(' not in js
    assert 'coast.jpg' not in js


def test_compact_breakpoints_and_two_column_metrics():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert '@media(max-width:760px)' in js
    assert '@media(max-width:440px)' in js
    assert '@media(max-width:330px)' in js
    assert 'body.mode-home .quick-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))' in js
    assert 'body.mode-home .home-stations-grid{grid-template-columns:1fr}' in js
    assert 'body.mode-home #forecastDetail .hourly-strip{display:grid;' in js
    assert 'body.mode-home #forecastDetail .day-grid{grid-template-columns:1fr}' in js


def test_site_build_keeps_weather_sources_and_navigation():
    html = transform(Path("index.html").read_text(encoding="utf-8"))
    assert 'Meteo Giammoro</h1>' in html
    assert 'id="weatherMain"' in html
    assert 'id="homeGust" hidden' in html
    assert 'id="homeObservationStrip"' in html
    assert 'id="expertBtn"' in html
    assert 'homePolishStyles' in html
