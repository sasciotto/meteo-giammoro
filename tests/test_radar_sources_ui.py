from pathlib import Path

import site_prepare as s


def test_radar_sources_ui_contains_requested_external_views_and_is_lazy():
    js = Path("radar_sources_ui.js").read_text(encoding="utf-8")
    assert "maps.weathersicily.it" in js
    assert "meteoeradar.it/radar-meteo/giammoro/9429567" in js
    assert "embed.windy.com/embed.html" in js
    assert "overlay=radar" in js
    assert "modeles20.meteociel.fr/satellite/animsatsandvisirmtgit.gif" in js
    assert "data-radar-src" in js
    assert "mode-radar" in js
    assert "Radar e satellite" in js
    assert "non alimentano il motore di nowcasting" in js


def test_site_prepare_injects_radar_sources_view():
    scripts = s._dashboard_scripts()
    assert "radarSourcesView" in scripts
    assert "Radar e satellite" in scripts
