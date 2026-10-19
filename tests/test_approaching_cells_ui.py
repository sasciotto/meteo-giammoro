from pathlib import Path

import site_prepare


def test_approaching_cells_ui_is_embedded_in_prepared_site():
    html = """<html><body>
<script>
const $=id=>document.getElementById(id);
</script>
</body></html>"""
    out = site_prepare.transform(html)

    assert '<script src="forecast_dashboard.js"></script>' in out
    assert "approachingCellsSection" in out
    assert "Celle in avvicinamento" in out
    assert "approach_from_label" in out
    assert "movement_toward_label" in out


def test_approaching_cells_ui_distinguishes_origin_and_motion():
    js = Path("approaching_cells_ui.js").read_text(encoding="utf-8")

    assert "Da ${esc(from)} → verso ${esc(toward)}" in js
    assert "closest_approach_km" in js
    assert "eta_minutes" in js
