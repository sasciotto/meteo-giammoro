from pathlib import Path

import site_prepare


def test_quality_ui_is_embedded_in_prepared_site():
    html = """<html><body>
<script>
const $=id=>document.getElementById(id);
</script>
</body></html>"""
    out = site_prepare.transform(html)

    assert "Qualità dell’analisi" in out
    assert "analysis_quality" in out
    assert "trajectory_reliability" in out
    assert "predictive_confidence" in out
    assert "Confidenza previsionale" in out


def test_quality_ui_never_labels_data_quality_as_probability():
    js = Path("analysis_quality_ui.js").read_text(encoding="utf-8")

    assert "Qualità dell’analisi" in js
    assert "non è una probabilità previsionale" in js
    assert "Affidabilità traiettoria" in js
    assert "Confidenza previsionale" in js
    assert "Calibrazione eventi" in js
