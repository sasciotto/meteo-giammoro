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


def test_hazard_cell_prefers_nearer_relevant_cell_over_tracked_identity():
    data = {
        "nowcast_tracking": {
            "status": "detected",
            "product": "SRI",
            "cell": {"lat": 38.30, "lon": 15.55, "distance_km": 30.0, "peak_value": 35.0, "pixels": 60},
            "candidates": [
                {"lat": 38.30, "lon": 15.55, "distance_km": 30.0, "peak_value": 35.0, "pixels": 60, "relevance": 90},
                {"lat": 38.21, "lon": 15.34, "distance_km": 4.0, "peak_value": 12.0, "pixels": 12, "relevance": 30},
            ],
        }
    }
    nowcast_v4.attach_hazard_cells(data)
    tr = data["nowcast_tracking"]
    assert tr["tracked_cell"]["distance_km"] == 30.0
    assert tr["hazard_cell"]["distance_km"] == 4.0
    assert tr["hazard_same_as_tracked"] is False
    assert tr["hazard_cell"]["hazard_score"] > 0


def test_hazard_score_penalizes_distance_strongly():
    near = {"distance_km": 5, "peak_value": 10, "pixels": 10}
    far = {"distance_km": 30, "peak_value": 25, "pixels": 20}
    assert nowcast_v4.hazard_score(near, "SRI") > nowcast_v4.hazard_score(far, "SRI")
