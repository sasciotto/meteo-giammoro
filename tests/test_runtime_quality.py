from datetime import datetime
from zoneinfo import ZoneInfo

import runtime_quality as q

TZ = ZoneInfo("Europe/Rome")


def test_alert_domani_is_normalized_to_today_after_midnight():
    data = {
        "alert": {
            "level_class": "warning",
            "level_label": "Gialla (domani)",
            "title": "Avviso Rischio Idrogeologico per il 17-18/10/2026",
            "text": "Zona Nord-Orientale: Gialla (domani). Rischi: temporali.",
            "validity": "domani",
            "national_validation": {
                "level_class": "warning",
                "level_label": "Gialla (domani)",
                "validity": "domani",
                "records": [
                    {"day": "domani", "level_class": "warning", "level_label": "Gialla", "risk": "temporali"}
                ],
            },
        }
    }
    q.normalize_alert_relative_day(data, datetime(2026, 10, 18, 1, 0, tzinfo=TZ))
    alert = data["alert"]
    assert alert["level_label"] == "Gialla (oggi 18/10)"
    assert alert["validity"] == "oggi 18/10"
    assert "Gialla (oggi 18/10)" in alert["text"]
    assert alert["national_validation"]["records"][0]["target_date"] == "2026-10-18"


def test_alert_prefers_current_day_over_earlier_day_with_same_level():
    data = {
        "alert": {
            "level_class": "warning",
            "level_label": "Gialla (20/10)",
            "title": "Avviso Rischio Idrogeologico per il 20-21/10/2026",
            "text": "Zona Nord-Orientale: Gialla (20/10). Rischi: idrogeologico, temporali.",
            "validity": "20/10",
            "national_validation": {
                "records": [
                    {"day": "20/10", "original_day": "oggi", "target_date": "2026-10-20", "level_class": "warning"},
                    {"day": "oggi 21/10", "original_day": "domani", "target_date": "2026-10-21", "level_class": "warning"},
                ]
            },
        }
    }
    q.normalize_alert_relative_day(data, datetime(2026, 10, 21, 15, 0, tzinfo=TZ))
    alert = data["alert"]
    assert alert["level_label"] == "Gialla (oggi 21/10)"
    assert alert["validity"] == "oggi 21/10"
    assert alert["national_validation"]["validity"] == "oggi 21/10"


def test_expired_pending_radar_change_is_closed():
    data = {
        "latest_change": {
            "title": "Traiettoria radar verso Giammoro non confermata",
            "event_type": "radar_approach",
            "status": "pending_confirmation",
            "valid_until": "2026-10-21T14:42:00+02:00",
            "event_id": "radar-test",
        },
        "history": [],
    }
    q.expire_stale_radar_change(data, datetime(2026, 10, 21, 15, 2, tzinfo=TZ))
    change = data["latest_change"]
    assert change["status"] == "expired"
    assert change["title"] == "Segnalazione radar precedente conclusa"
    assert change["resolved_at"] == "2026-10-21T15:02:00+02:00"
    assert data["history"][0]["text"] == "Segnalazione radar precedente conclusa"


def test_home_radar_indicator_distinguishes_area_echo_from_trackable_cell():
    data = {
        "home_summary": {
            "nowcast_simple": {
                "indicators": {"radar": "Fenomeni più lontani", "distance": "~37 km"}
            }
        },
        "dpc_observations": {
            "products": {
                "SRI": {
                    "ok": True,
                    "stats": [
                        {"radius_km": 15, "max": 0.0},
                        {"radius_km": 30, "max": 11.2},
                    ],
                }
            }
        },
        "nowcast_tracking": {
            "candidates": [{"distance_km": 37.2}],
        },
    }
    q.refine_home_nowcast_radar(data)
    indicators = data["home_summary"]["nowcast_simple"]["indicators"]
    assert indicators["radar"] == "Pioggia rilevata entro ~30 km"
    assert indicators["distance"] == "Nucleo tracciabile ~37 km"


def local_product(point=0.0, p90_1=0.0, mean_1=0.0, max_1=0.0, p90_3=0.0, mean_3=0.0, max_3=0.0):
    return {
        "ok": True,
        "timestamp": "2026-10-22T16:00+02:00",
        "age_minutes": 5,
        "stats": [
            {"radius_km": 1, "point": point, "p90": p90_1, "mean": mean_1, "max": max_1},
            {"radius_km": 3, "point": point, "p90": p90_3, "mean": mean_3, "max": max_3},
            {"radius_km": 5, "point": point, "p90": p90_3, "mean": mean_3, "max": max_3},
        ],
    }


def test_local_radar_area_can_detect_rain_without_claiming_point_accumulation(monkeypatch):
    sri = local_product(point=0.0, p90_1=0.4, mean_1=0.2, max_1=0.9)
    srt = local_product(point=0.0, p90_1=0.2, mean_1=0.1, max_1=0.4)
    monkeypatch.setattr(q, "_fetch_local_product", lambda data, name: (sri if name == "SRI" else srt, None))
    data = {
        "nowcast": {"level": "low"},
        "model_details": [],
        "home_summary": {"nowcast_simple": {"status": "calm", "title": "Tranquillo", "text": "", "indicators": {}}},
    }
    q.update_local_precipitation(data, previous={}, now=datetime(2026, 10, 22, 16, 5, tzinfo=TZ))
    local = data["local_precipitation"]
    assert local["status"] == "active"
    assert local["area_values_are_not_point_measurements"] is True
    assert local["radar"]["sri"]["1"]["point"] == 0.0
    assert "entro ~1 km" in local["current_detection_basis"]
    assert data["home_summary"]["nowcast_simple"]["status"] == "active"


def test_recent_local_rain_is_kept_after_current_radar_turns_dry(monkeypatch):
    dry = local_product()
    monkeypatch.setattr(q, "_fetch_local_product", lambda data, name: (dry, None))
    previous = {
        "local_precipitation": {
            "history": [
                {
                    "timestamp": "2026-10-22T15:30:00+02:00",
                    "rain_detected": True,
                    "recent_accumulation": True,
                    "basis": "segnale radar coerente entro ~1 km",
                }
            ]
        }
    }
    data = {
        "nowcast": {"level": "low"},
        "model_details": [],
        "home_summary": {"nowcast_simple": {"status": "calm", "title": "Tranquillo", "text": "", "indicators": {}}},
    }
    q.update_local_precipitation(data, previous=previous, now=datetime(2026, 10, 22, 16, 10, tzinfo=TZ))
    assert data["local_precipitation"]["status"] == "recent"
    assert data["home_summary"]["nowcast_simple"]["status"] == "watch"
    assert "recentemente" in data["home_summary"]["nowcast_simple"]["text"].lower()


def test_weak_model_rain_signal_is_separate_from_impact_level(monkeypatch):
    dry = local_product()
    monkeypatch.setattr(q, "_fetch_local_product", lambda data, name: (dry, None))
    data = {
        "nowcast": {"level": "low"},
        "model_details": [
            {"label": "ICON-2I", "ok": True, "next_0_3h": {"precip_sum": 0.0}},
            {"label": "ICON", "ok": True, "next_0_3h": {"precip_sum": 0.0}},
            {"label": "ECMWF", "ok": True, "next_0_3h": {"precip_sum": 0.1}},
            {"label": "GFS", "ok": True, "next_0_3h": {"precip_sum": 0.9}},
        ],
        "home_summary": {"nowcast_simple": {"status": "calm", "title": "Tranquillo", "text": "", "indicators": {}}},
    }
    q.update_local_precipitation(data, previous={}, now=datetime(2026, 10, 22, 16, 10, tzinfo=TZ))
    local = data["local_precipitation"]
    assert local["forecast_0_3h"]["status"] == "weak"
    assert local["impact_level"] == "low"
    assert data["home_summary"]["nowcast_simple"]["status"] == "watch"
    assert "piovaschi" in data["home_summary"]["nowcast_simple"]["text"].lower()
