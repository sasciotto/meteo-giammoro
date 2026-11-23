"""Controlli regressione: il meteo live non deve fermarsi per test UI o Pages."""
from pathlib import Path


def test_full_suite_is_independent_from_live_weather_collection():
    weather = Path(".github/workflows/update-weather.yml").read_text(encoding="utf-8")
    ci = Path(".github/workflows/validate-code.yml").read_text(encoding="utf-8")
    assert "python -m pytest -q" not in weather
    assert "python -m py_compile" in weather
    assert "python -m pytest -q" in ci
    assert "pull_request:" in ci
    assert "workflow_dispatch:" in ci
    assert "schedule:" in weather


def test_latest_valid_weather_data_are_persisted_even_if_pages_fails():
    weather = Path(".github/workflows/update-weather.yml").read_text(encoding="utf-8")
    assert "id: weather_data_ready" in weather
    assert "not -5 <= age <= 30" in weather
    assert "collector_status" in weather
    assert "if: always() && steps.weather_data_ready.outcome == 'success'" in weather
    assert weather.index("Convalida dataset pronto") < weather.index("Prepara sito con previsione")
    assert weather.index("Pubblica GitHub Pages") < weather.index("Salva dati aggiornati nel repository")
    assert "git add ${DATA_FILES}" in weather


def test_heartbeat_retries_when_an_old_run_would_otherwise_block_it():
    heartbeat = Path(".github/workflows/weather-heartbeat.yml").read_text(encoding="utf-8")
    assert "25 minutes ago" in heartbeat
    assert "old_active" in heartbeat
    assert "active=${active}" in heartbeat
    assert "Aggiornamento meteo richiesto" in heartbeat
