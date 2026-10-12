from datetime import datetime, timezone

import external_scheduler as es


def test_parse_age_minutes():
    payload = {"meta": {"last_check_iso": "2026-10-12T10:00:00+00:00"}}
    now = datetime(2026, 10, 12, 10, 17, tzinfo=timezone.utc)
    assert es.parse_age_minutes(payload, now=now) == 17


def test_parse_age_minutes_missing_or_invalid():
    assert es.parse_age_minutes({}) is None
    assert es.parse_age_minutes({"meta": {"last_check_iso": "non-data"}}) is None


def test_main_does_nothing_when_data_are_fresh(monkeypatch):
    called = []
    monkeypatch.setattr(es, "STALE_MINUTES", 15)
    monkeypatch.setattr(es, "fetch_published_age_minutes", lambda: 4)
    monkeypatch.setattr(es, "dispatch_update", lambda token: called.append(token))
    monkeypatch.delenv("METEO_GITHUB_TOKEN", raising=False)

    assert es.main() == 0
    assert called == []


def test_main_dispatches_when_data_are_stale(monkeypatch):
    called = []
    monkeypatch.setattr(es, "STALE_MINUTES", 15)
    monkeypatch.setattr(es, "fetch_published_age_minutes", lambda: 27)
    monkeypatch.setattr(es, "dispatch_update", lambda token: called.append(token))
    monkeypatch.setenv("METEO_GITHUB_TOKEN", "secret-token")

    assert es.main() == 0
    assert called == ["secret-token"]


def test_main_requires_token_only_when_recovery_is_needed(monkeypatch):
    monkeypatch.setattr(es, "STALE_MINUTES", 15)
    monkeypatch.setattr(es, "fetch_published_age_minutes", lambda: None)
    monkeypatch.delenv("METEO_GITHUB_TOKEN", raising=False)

    assert es.main() == 2
