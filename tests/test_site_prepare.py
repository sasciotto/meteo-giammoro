import site_prepare as s


def test_prepare_removes_visible_legacy_card_and_wires_single_data_render():
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
    assert 'class=\"grid two section\"' in out
    assert 'id=\"homeForecastLegacy\" hidden' in out
    assert 'd.home_summary?.current||homeWeather' in out
    assert "window.renderForecastDashboard?.(d)" in out
    assert '<script src=\"forecast_dashboard.js\"></script>' in out
