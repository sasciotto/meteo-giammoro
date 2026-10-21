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
