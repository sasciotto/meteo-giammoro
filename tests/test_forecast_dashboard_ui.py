from pathlib import Path


def test_verification_ui_prioritizes_event_metrics_over_global_accuracy():
    js = Path("forecast_dashboard.js").read_text(encoding="utf-8")

    assert "event_metrics" in js
    for label in (
        "Campioni evento",
        "TP",
        "FP",
        "FN",
        "POD",
        "FAR",
        "CSI",
        "Balanced accuracy",
        "Campioni ETA",
        "Campioni traiettoria",
    ):
        assert label in js

    assert "Accuracy globale" in js
    assert "metrica secondaria" in js
    assert js.index("Campioni evento") < js.index("Accuracy globale")
    assert "nessun evento osservato finora" in js


def test_numeric_formatter_keeps_missing_values_unavailable():
    js = Path("forecast_dashboard.js").read_text(encoding="utf-8")

    assert "value === null || value === undefined || value === ''" in js
    assert "return null;" in js


def test_home_shows_simple_nowcast_before_hourly_forecast_with_indicators():
    js = Path("forecast_dashboard.js").read_text(encoding="utf-8")

    assert "nowcast_simple" in js
    assert "Prossime 3 ore" in js
    assert "homeNowcastSimple" in js
    assert "home-nowcast-title" in js
    assert "home-nowcast-text" in js
    assert "home-nowcast-signals" in js
    assert "home-nowcast-signal" in js
    for label in ("Radar", "Traiettoria", "Fulmini", "Distanza"):
        assert f"['{label}'," in js
    assert "${nowcastHtml}\n      ${staleHtml}\n      <div class=\"hourly-strip\"" in js
    assert "${nowcastHtml}\n        <div class=\"forecast-unavailable\"" in js


def test_home_does_not_render_technical_multi_model_consensus_block():
    js = Path("forecast_dashboard.js").read_text(encoding="utf-8")

    assert "consensusHtml" not in js
    assert "consenso multi-modello 3–48 h" not in js
    assert "modelli indicano pioggia ≥0,5 mm" not in js
    assert "model-values" not in js
    assert "home?.multi_model" not in js


def test_detailed_analysis_keeps_multi_model_technical_section():
    html = Path("index.html").read_text(encoding="utf-8")

    assert "Previsione multi-modello" in html
    assert 'id="models"' in html
    assert 'id="riskNote"' in html
    assert "3–48 h e 2–7+ giorni" in html
