from pathlib import Path


def test_radar_ui_uses_local_official_screenshot_not_browser_wms():
    js = Path("radar_ui.js").read_text(encoding="utf-8")

    assert "radar-dpc.png" in js
    assert "radar.protezionecivile.it/#/pages/dashboard?zoom=6" in js
    assert "radar-geowebcache.protezionecivile.it/service/wms" not in js
    assert "Screenshot della piattaforma Radar-DPC ufficiale" in js
    assert "SRI · precipitazione" in js
    assert "VMI · riflettività" in js
    assert "nowcast_tracking" in js


def test_radar_ui_stays_in_detailed_analysis():
    js = Path("radar_ui.js").read_text(encoding="utf-8")

    assert "trackingStatus" in js
    assert "expertRoot" in js
    assert "radarViewerSection" in js


def test_site_prepare_injects_radar_ui_and_captures_official_app():
    import site_prepare

    scripts = site_prepare._dashboard_scripts()
    source = Path("site_prepare.py").read_text(encoding="utf-8")
    assert "radarViewerSection" in scripts
    assert "radar-dpc.png" in scripts
    assert "capture_official_radar_snapshot" in source
    assert "--screenshot=" in source
    assert "radar.protezionecivile.it/#/pages/dashboard?zoom=6" in source


def test_radar_snapshot_is_optional_when_browser_is_missing(monkeypatch, tmp_path):
    import site_prepare

    monkeypatch.setattr(site_prepare.shutil, "which", lambda _name: None)
    output = tmp_path / "radar-dpc.png"
    assert site_prepare.capture_official_radar_snapshot(output) is False
    assert not output.exists()
