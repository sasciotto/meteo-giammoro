import nowcast_v4


def test_sanitize_dew_point_when_sources_are_mixed():
    data = {
        "territory": {
            "metrics": {
                "temperature": {"value": 15.3, "quality": "Radar-DPC TEMP (rete termometrica interpolata)"},
                "humidity": {"value": 91.0, "quality": "ItaliaMeteo ICON-2I"},
                "dew_point": {"value": 17.5, "quality": "derivato da T/UR"},
            }
        }
    }
    nowcast_v4.sanitize_territory_metrics(data)
    dew = data["territory"]["metrics"]["dew_point"]
    assert dew["value"] is None
    assert "fonti diverse" in dew["quality"]


def test_sanitize_dew_point_keeps_coherent_same_source_value():
    data = {
        "territory": {
            "metrics": {
                "temperature": {"value": 19.0, "quality": "ItaliaMeteo ICON-2I"},
                "humidity": {"value": 91.0, "quality": "ItaliaMeteo ICON-2I"},
                "dew_point": {"value": 17.5, "quality": "derivato da T/UR"},
            }
        }
    }
    nowcast_v4.sanitize_territory_metrics(data)
    assert data["territory"]["metrics"]["dew_point"]["value"] == 17.5


def test_refresh_runtime_text_mentions_active_sources():
    data = {
        "territory": {},
        "models": [{"horizon": "0–3 h"}],
        "reasoning": {},
        "analysis_confidence": {"note": "vecchia nota"},
        "sources": [],
    }
    nowcast_v4.refresh_runtime_text(data)
    row = data["models"][0]
    assert "Radar-DPC" in row["models"]
    assert "EUMETSAT MTG-LI" in row["models"]
    assert "EUMETSAT MTG-LI" in data["analysis_confidence"]["note"]
