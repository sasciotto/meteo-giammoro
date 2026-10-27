from pathlib import Path

import site_prepare as s


def test_prepare_keeps_quick_home_cards_visible_below_full_forecast():
    html = """<html><body>
<div class=\"grid three section\">
<article class=\"card forecast-card\"><div class=\"k\">PROSSIME ORE</div></article>
<article class=\"card forecast-card\"><div><div class=\"k\">OGGI E DOMANI</div><div id=\"homeForecastTitle\"></div></div><div id=\"homeForecastText\"></div></article>
<article class=\"card forecast-card\"><div class=\"k\">PIOGGIA E TEMPORALI</div></article>
</div>
<script>
const $=id=>document.getElementById(id);
function x(){const wx=homeWeather(m,d,tr,flashes20);$('sources').innerHTML='x'}).catch(err=>{$('homeDescription').textContent='Dati temporaneamente non disponibili';}
</script></body></html>"""
    out = s.transform(html)
    assert "OGGI E DOMANI" not in out
    assert '<div class=\"grid two section\" id=\"homeSummaryCards\">' in out
    assert 'id=\"homeSummaryCards\" hidden' not in out
    assert "PROSSIME ORE" in out
    assert "PIOGGIA E TEMPORALI" in out
    assert 'id=\"homeForecastLegacy\" hidden' in out
    assert 'd.home_summary?.current||homeWeather' in out
    assert "window.renderForecastDashboard?.(d)" in out
    assert '<script src=\"forecast_dashboard.js\"></script>' in out


def test_forecast_dashboard_inserts_full_forecast_before_quick_cards():
    js = Path("forecast_dashboard.js").read_text(encoding="utf-8")
    assert "const summaryCards = byId('homeSummaryCards');" in js
    assert "summaryCards.parentElement.insertBefore(section, summaryCards);" in js
    assert js.index("homeSummaryCards") < js.index("homeAlertCard")


def test_seismic_persistence_is_explicitly_managed_by_workflow():
    site_prepare = Path("site_prepare.py").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/update-weather.yml").read_text(encoding="utf-8")

    assert "stage_seismic_events" not in site_prepare
    assert "seismic_events.json" in workflow
    assert 'DATA_FILES="data.json history.json verification.json events.json seismic_events.json"' in workflow
    assert "git diff --cached --quiet -- ${DATA_FILES}" in workflow
    assert "git add ${DATA_FILES}" in workflow
