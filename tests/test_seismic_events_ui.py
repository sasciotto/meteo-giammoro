from pathlib import Path

import site_prepare as s


def test_seismic_ui_is_injected_and_lazy_loads_separate_dataset():
    js = Path("seismic_events_ui.js").read_text(encoding="utf-8")
    scripts = s._dashboard_scripts()
    assert "seismicEventsStyles" in js
    assert "eventsBtn" in js
    assert "mode-events" in js
    assert "seismic_events.json" in js
    assert "loadEvents" in js
    assert "fetch(`${DATA_URL}?_=${Date.now()}`" in js
    assert "cache:'no-store'" in js
    assert "seismicEventsStyles" in scripts
    assert "fetch('data.json" not in js
    assert "fetch(`data.json" not in js


def test_seismic_ui_keeps_official_only_tsunami_language_and_ingv_links():
    js = Path("seismic_events_ui.js").read_text(encoding="utf-8")
    assert "non prevede terremoti" in js
    assert "non calcola autonomamente allerte tsunami" in js
    assert "CAT-INGV" in js
    assert "Scheda INGV" in js
    assert "Protezione Civile" in js
    assert "Mappa radiale" in js


def test_seismic_ui_emphasizes_dates_and_times():
    js = Path("seismic_events_ui.js").read_text(encoding="utf-8")
    assert "events-datetime" in js
    assert "events-status-time" in js
    assert "font-variant-numeric:tabular-nums" in js
    assert 'font-weight:780' in js
    assert '<span class=\"events-datetime\">${esc(localTime(event.time_local || event.time_utc))}</span>' in js


def test_site_prepare_updates_and_copies_seismic_dataset():
    source = Path("site_prepare.py").read_text(encoding="utf-8")
    assert "SEISMIC_EVENTS_UI_PATH" in source
    assert "update_seismic_events()" in source
    assert "copy_seismic_events(dest.parent)" in source
    assert "seismic_collector.collect" in source


def test_auto_refresh_preserves_events_mode():
    js = Path("auto_refresh_ui.js").read_text(encoding="utf-8")
    assert "mode-events" in js
    assert "state.mode === 'events'" in js
    assert "eventsBtn" in js
