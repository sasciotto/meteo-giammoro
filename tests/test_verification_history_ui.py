from pathlib import Path

import site_prepare


def test_verification_history_ui_uses_cumulative_v2_metrics_and_keeps_legacy_separate():
    js = Path("verification_history_ui.js").read_text(encoding="utf-8")
    assert "verificationHistoryEnhancer" in js
    assert "cumulative_event_metrics" in js
    assert "cumulative_by_horizon" in js
    assert "legacy_baseline" in js
    assert "non indica un miglioramento dimostrato" in js
    for label in ("POD 30 min", "POD 60 min", "POD 120 min", "FN 30 min", "FN 60 min", "FN 120 min"):
        assert label in js


def test_site_prepare_embeds_verification_history_enhancer():
    scripts = site_prepare._dashboard_scripts()
    assert "verificationHistoryEnhancer" in scripts
    assert "verification_history_ui.js" not in scripts
