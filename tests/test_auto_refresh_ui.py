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
