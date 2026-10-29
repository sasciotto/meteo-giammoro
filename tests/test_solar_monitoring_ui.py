from pathlib import Path


def test_solar_ui_exposes_mode_and_renderer():
    text = Path('solar_monitoring_ui.js').read_text(encoding='utf-8')
    assert 'mode-solar' in text
    assert 'solarBtn' in text
    assert 'window.renderSolarMonitoring' in text
    assert 'Quota diretta' in text
    assert 'non è una percentuale meteorologica' in text
    assert 'RETE DI CONTROLLO AL SUOLO' in text
    assert 'ground_observations' in text
    assert 'Pace del Mela' not in text  # station names come from data, not hard-coded UI labels
