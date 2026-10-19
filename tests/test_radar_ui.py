from pathlib import Path


def test_radar_ui_uses_official_dpc_wms_and_local_overlays():
    js = Path("radar_ui.js").read_text(encoding="utf-8")

    assert "radar-geowebcache.protezionecivile.it/service/wms" in js
    assert "radar:sri" in js
    assert "radar:vmi" in js
    assert "Giammoro" in js
    assert "nowcast_tracking" in js
    assert "direction_deg" in js
    assert "track_id" in js
    assert "time" in js


def test_radar_ui_stays_in_detailed_analysis():
    js = Path("radar_ui.js").read_text(encoding="utf-8")

    assert "trackingStatus" in js
    assert "expertRoot" in js
    assert "radarViewerSection" in js


def test_site_prepare_injects_radar_ui():
    import site_prepare

    scripts = site_prepare._dashboard_scripts()
    assert "radarViewerSection" in scripts
    assert "radar-geowebcache.protezionecivile.it/service/wms" in scripts
