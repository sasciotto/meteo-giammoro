from pathlib import Path

import site_prepare as s


def test_auto_refresh_checks_data_without_cache_and_preserves_view():
    js = Path("auto_refresh_ui.js").read_text(encoding="utf-8")
    compact = "".join(js.split())
    assert "CHECK_INTERVAL_MS=60_000" in compact
    assert "fetch(`data.json?_=${Date.now()}`" in compact
    assert "cache:'no-store'" in compact
    assert "last_check_iso" in js
    assert "sessionStorage" in js
    assert "mode-radar" in js
    assert "radarSource" in js
    assert "visibilitychange" in js
    assert "window.location.replace" in js


def test_site_prepare_injects_auto_refresh():
    scripts = s._dashboard_scripts()
    assert "CHECK_INTERVAL_MS" in scripts
    assert "auto-refresh-state" in scripts


def test_weather_auto_refresh_tracks_actually_rendered_data():
    refresh = Path("auto_refresh_ui.js").read_text(encoding="utf-8")
    html = Path("index.html").read_text(encoding="utf-8")
    assert "window.meteoRenderedStamp || null" in refresh
    assert "nextTime <= currentTime" in refresh
    assert "await window.applyMeteoData(data)" in refresh
    assert "if (initial || !knownStamp)" not in refresh
    assert "window.meteoRenderedStamp=nextStamp" in html
    assert "Date.parse(nextStamp)<=Date.parse(currentStamp)" in html


def test_published_html_keeps_auxiliary_renderers_before_stamping_freshness():
    published = s.transform(Path("index.html").read_text(encoding="utf-8"))
    main = published.index("window.renderForecastDashboard?.(d);window.renderSolarMonitoring?.(d);")
    stamp = published.index("window.meteoRenderedStamp=nextStamp", main)
    assert main < stamp
    assert published.count("window.meteoRenderedStamp=nextStamp") == 1
