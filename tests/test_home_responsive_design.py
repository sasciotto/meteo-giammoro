"""Regressioni per la home responsive e la separazione osservazioni/previsioni."""
from pathlib import Path

from site_prepare import transform


def test_home_uses_accessible_metric_icons_without_removing_values():
    html = Path("index.html").read_text(encoding="utf-8")
    assert html.count('class="quick-icon"') == 4
    for label in ("Umidità", "Vento", "Pioggia 24 h", "Pressione"):
        assert f"<span>{label}</span>" in html
    assert 'id="homeTemp"' in html
    assert 'id="homeGust" hidden' in html
    assert 'id="homeWind"' in html
    assert 'id="homePressure"' in html
    assert 'id="homeCloud" hidden' in html


def test_forecast_has_distinct_sections_and_missing_rain_is_not_zero():
    script = Path("forecast_dashboard.js").read_text(encoding="utf-8")
    assert 'PREVISIONE MODELLISTICA' in script
    assert 'Prossime ore' in script
    assert 'Oggi e domani' in script
    assert 'const rain = num(h.precipitation);' in script
    assert "rain == null ? '—'" in script
    assert 'previousHourlyScroll' in script
    assert 'aria-label="Previsione oraria, scorrevole"' in script


def test_home_has_one_hourly_timeline_and_preserves_observation_provenance():
    polish = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert 'renderNowcastTimeline(data)' not in polish
    assert '#forecastDetail .hourly-strip{display:grid' in polish
    assert 'Nowcast osservativo 0–3 h · Previsione oraria:' in polish
    assert 'homeObservationStrip' in polish
    assert 'Allerta ufficiale non verificabile' in polish
    assert 'home.insertBefore(card, forecast)' in polish


def test_site_transform_keeps_weather_and_source_footer():
    source = Path("index.html").read_text(encoding="utf-8")
    html = transform(source)
    assert 'id="weatherMain"' in html
    assert 'id="homeObservationStrip"' in html
    assert html.index('id="homeObservationStrip"') < html.index('<footer')
    assert 'homePolishStyles' in html
    assert 'forecast_dashboard.js' in html
