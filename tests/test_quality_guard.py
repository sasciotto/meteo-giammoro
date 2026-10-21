from datetime import datetime, timedelta, timezone

import quality_guard


def test_unvalidated_regional_alert_is_not_presented_as_certain():
    data = {
        "alert": {
            "level_label": "Rossa",
            "level_class": "red",
            "title": "Avviso Rischio Idrogeologico per il 15-16/10/2026",
            "validity": "dalle ore fino alle ore 24:00 del 16-ott-2026 PER IL RISCHIO ROSSA ALLARME",
            "parser_note": "estrazione automatica zona A",
            "national_validation": {"error": "zona DPC nazionale non trovata nel bollettino corrente"},
        }
    }
    quality_guard.guard_alert_quality(data)
    alert = data["alert"]
    assert alert["level_label"] == "Da verificare"
    assert alert["level_class"] == "unknown"
    assert alert["regional_candidate"]["level_label"] == "Rossa"
    assert "15–16/10/2026" in alert["validity"]


def test_validated_alert_keeps_level():
    data = {
        "alert": {
            "level_label": "Gialla",
            "level_class": "warning",
            "title": "Avviso Rischio Idrogeologico per il 15-16/10/2026",
            "validity": "fino alle ore 24:00 del 16/10/2026",
            "parser_note": "livello zona A validato dal bollettino nazionale DPC",
            "national_validation": {"level_label": "Gialla"},
        }
    }
    quality_guard.guard_alert_quality(data)
    assert data["alert"]["level_label"] == "Gialla"
    assert data["alert"]["level_class"] == "warning"


def test_latest_change_removes_obsolete_lightning_message():
    data = {
        "latest_change": {
            "evidence": "Radar presente. Fulminazioni non ancora acquisite automaticamente."
        }
    }
    quality_guard.sanitize_latest_change(data)
    evidence = data["latest_change"]["evidence"]
    assert "non ancora acquisite" not in evidence
    assert "EUMETSAT MTG-LI" in evidence


def test_unvalidated_alert_does_not_create_fake_change_loop():
    previous = {
        "alert": {
            "level_label": "Da verificare",
            "regional_candidate": {"level_label": "Verde", "status": "unvalidated"},
        },
        "latest_change": {
            "title": "Variazione allerta ufficiale: Da verificare → Verde",
            "window": "testo sporco",
        },
    }
    data = {
        "meta": {"last_check": "16/10/2026 10:00 CEST"},
        "alert": {
            "level_label": "Da verificare",
            "validity": "Validità avviso: 15–16/10/2026; orari da verificare nel PDF ufficiale.",
            "source": "CFD/DRPC Sicilia + DPC nazionale",
            "regional_candidate": {"level_label": "Verde", "status": "unvalidated"},
        },
        "latest_change": {
            "title": "Variazione allerta ufficiale: Da verificare → Verde",
            "window": "ROSSA ALLARME PER IL RISCHIO",
        },
        "history": [
            {"time": "ora", "text": "Variazione allerta ufficiale: Da verificare → Verde"},
            {"time": "prima", "text": "Nucleo radar in avvicinamento verso Giammoro"},
        ],
    }
    quality_guard.sanitize_latest_change(data, previous)
    change = data["latest_change"]
    assert change["title"] == "Nuovo avviso ufficiale pubblicato — livello in verifica"
    assert change["status"] == "unvalidated"
    assert change["event_type"] == "official_alert_validation"
    assert data["history"][0]["text"] == change["title"]
    assert all("Da verificare → Verde" not in row["text"] for row in data["history"])


def test_unvalidated_candidate_is_not_announced_as_official_level_change():
    data = {
        "meta": {"last_check": "21/10/2026 15:48 CEST"},
        "alert": {
            "level_label": "Da verificare",
            "validity": "Validità avviso: 20–21/10/2026; orari da verificare nel PDF ufficiale.",
            "source": "CFD/DRPC Sicilia + DPC nazionale",
            "regional_candidate": {"level_label": "Verde", "level_class": "low", "status": "unvalidated"},
        },
        "latest_change": {
            "time": "21/10/2026 15:44",
            "title": "Variazione allerta ufficiale: Gialla (20/10) → Verde",
            "confidence": "alta",
        },
        "history": [
            {"time": "21/10/2026 15:44", "text": "Variazione allerta ufficiale: Gialla (20/10) → Verde"},
            {"time": "21/10/2026 13:57", "text": "Traiettoria radar verso Giammoro non confermata"},
        ],
    }
    quality_guard.sanitize_latest_change(data)
    change = data["latest_change"]
    assert change["title"] == "Nuovo avviso ufficiale pubblicato — livello in verifica"
    assert change["confidence"] == "da verificare"
    assert "non è stato validato automaticamente" in change["text"]
    assert all("Gialla (20/10) → Verde" not in row["text"] for row in data["history"])


def test_real_alert_change_gets_clean_validity_window():
    data = {
        "alert": {
            "level_label": "Gialla",
            "validity": "Validità avviso: 16–17/10/2026; orari da verificare nel PDF ufficiale.",
        },
        "latest_change": {
            "title": "Variazione allerta ufficiale: Verde → Gialla",
            "window": "ROSSA ALLARME PER IL RISCHIO IDROGEOLOGICO",
        },
    }
    quality_guard.sanitize_latest_change(data)
    assert data["latest_change"]["window"].startswith("Validità avviso:")


def test_pressure_trend_computes_one_hour_delta():
    now = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
    previous = {
        "pressure_history": [
            {"timestamp": (now - timedelta(hours=1)).isoformat(), "hpa": 1022.0},
            {"timestamp": (now - timedelta(minutes=15)).isoformat(), "hpa": 1021.4},
        ]
    }
    data = {
        "meta": {"last_check_iso": now.isoformat()},
        "territory": {"metrics": {"pressure": {"value": 1021.0, "unit": " hPa"}}},
    }
    quality_guard.update_pressure_trend(data, previous)
    trend = data["pressure_trend"]
    assert trend["status"] == "ready"
    assert trend["delta_1h_hpa"] == -1.0
    assert trend["tendency"] == "in calo"
    assert "Δ1h -1.0 hPa" in data["territory"]["metrics"]["pressure"]["trend"]


def test_pressure_trend_seeds_previous_cycle_when_history_missing():
    now = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
    previous = {
        "meta": {"last_check_iso": (now - timedelta(minutes=15)).isoformat()},
        "territory": {"metrics": {"pressure": {"value": 1021.5}}},
    }
    data = {
        "meta": {"last_check_iso": now.isoformat()},
        "territory": {"metrics": {"pressure": {"value": 1021.4}}},
    }
    quality_guard.update_pressure_trend(data, previous)
    assert data["pressure_trend"]["status"] == "collecting"
    assert data["pressure_trend"]["samples"] == 2


def test_pressure_evidence_marks_modelled_source():
    data = {
        "pressure_trend": {
            "tendency": "stabile",
            "delta_1h_hpa": 0.1,
            "delta_3h_hpa": -0.2,
        }
    }
    quality_guard.refresh_pressure_evidence(data)
    text = data["nowcast_evidence"]["wind_pressure"]
    assert "Trend modellistico" in text
    assert "Δ1h +0.1 hPa" in text
