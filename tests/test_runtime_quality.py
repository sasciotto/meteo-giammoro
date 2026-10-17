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
