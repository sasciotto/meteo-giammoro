"""UI readability and emergency restore invariants."""
from pathlib import Path


def test_emergency_graphics_restore_documented_in_repository():
    guide = Path("GRAPHICS_RECOVERY.md").read_text(encoding="utf-8")
    assert "backup/graphics-original-emergency-20261123" in guide
    assert "backup/main-20261123-before-readable-home" in guide
    assert "git restore --source origin/backup/graphics-original-emergency-20261123" in guide
    assert "data.json" in guide


def test_header_and_metrics_have_readable_mobile_layout():
    html = Path("index.html").read_text(encoding="utf-8")
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    assert '<h1>Meteo Giammoro</h1>' in html
    assert 'id="freshness"' in html
    assert "@media(max-width:650px)" in js
    assert "@media(max-width:365px)" in js
    assert "body.mode-home .hero-meta strong{font-size:12px}" in js
    assert "body.mode-home .quick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}" in js
    assert "body.mode-home .mode-switch{width:100%;display:grid;grid-template-columns:repeat(5,minmax(0,1fr))" in js


def test_nowcast_fields_are_readable_and_not_suppressed():
    js = Path("home_polish_ui.js").read_text(encoding="utf-8")
    forecast = Path("forecast_dashboard.js").read_text(encoding="utf-8")
    assert "body.mode-home #forecastDetail .home-nowcast-signals{grid-template-columns:1fr}" in js
    assert "body.mode-home #forecastDetail .home-nowcast-signal b{font-size:13px}" in js
    assert "body.mode-home #forecastDetail .hourly-strip{grid-auto-columns:minmax(133px,65%)" in js
    assert "homeNowcastSimple" in forecast
    assert "home-stations-grid" in js
