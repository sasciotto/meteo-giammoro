from pathlib import Path

import site_prepare as s


def _compact_js() -> tuple[str, str]:
    js = Path("radar_sources_ui.js").read_text(encoding="utf-8")
    return js, "".join(js.split())


def test_radar_sources_ui_contains_requested_external_views_and_is_lazy():
    js, compact = _compact_js()
    assert "maps.weathersicily.it" in js
    assert "meteoeradar.it/radar-meteo/giammoro/9429567" in js
    assert "embed.windy.com/embed.html" in js
    assert "overlay=radar" in js
    assert "modeles20.meteociel.fr/satellite/animsatsandvisirmtgit.gif" in js
    assert "data-radar-src" in js
    assert "mode-radar" in js
    assert "Radar e satellite" in js
    assert "non alimentano il motore di nowcasting" in js
    assert "selectSource(SOURCES[0].id,false)" in compact
    assert "if(shouldLoad)loadSource(valid)" in compact


def test_radar_frames_scale_and_follow_viewport():
    js, compact = _compact_js()
    assert "fit:'desktop'" in compact
    assert "designWidth:1440" in compact
    assert "designWidth:1280" in compact
    assert "height:clamp(480px,74dvh,820px)" in compact
    assert "frameVisualHeight" in js
    assert "functionfitFrame(sourceId)" in compact
    assert "frame.style.transform=`scale(${scale})`" in compact
    assert "requestFullscreen" in js
    assert "fullscreenchange" in js
    assert "window.addEventListener('resize'" in js


def test_radar_loading_is_integrated_without_overlay_patch():
    js, compact = _compact_js()
    assert "radar-frame-loading" in js
    assert "MutationObserver" not in js
    assert "radar_loading_ui.js" not in s._dashboard_scripts()
    assert "<iframeclass=\"radar-source-frame\"" in compact
    assert "hidden></iframe>" not in compact


def test_site_prepare_injects_radar_sources_view():
    scripts = s._dashboard_scripts()
    assert "radarSourcesView" in scripts
    assert "Radar e satellite" in scripts
