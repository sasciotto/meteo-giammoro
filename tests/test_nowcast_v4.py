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
    assert "LTG/LAMPINET DPC" in row["models"]
    assert "EUMETSAT MTG-LI" not in row["models"]
    external = nowcast_v4.external_lightning_map()
    assert external["role"] == "external_view_only"
    assert external["used_for_nowcast"] is False
    assert external["url"].startswith("https://maps.blitzortung.org/")


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


def test_suspect_short_interval_jump_invalidates_projection():
    data = {
        "nowcast": {"note": "Nucleo radar a circa 36 km E di Giammoro, picco 31.5 dBZ; movimento WSW a ~22.5 km/h. In avvicinamento; minima distanza proiettata ~8.7 km."},
        "nowcast_tracking": {
            "status": "detected",
            "association": {"status": "matched", "score": 12.2, "predicted_error_km": 10.5, "implied_speed_kmh": 110.3},
            "track_history": [
                {"timestamp": "2026-10-16T13:55+02:00", "lat": 38.17759, "lon": 15.83344},
                {"timestamp": "2026-10-16T14:00+02:00", "lat": 38.19325, "lon": 15.73013},
            ],
            "motion": {
                "status": "tracked",
                "speed_kmh": 22.5,
                "approaching": True,
                "eta_minutes": 90,
                "closest_approach_km": 8.7,
                "closest_approach_minutes": 93,
                "fit_residual_km": 3.2,
            },
        },
    }
    quality = nowcast_v4.assess_tracking_quality(data)
    motion = data["nowcast_tracking"]["motion"]
    assert quality["status"] == "suspect"
    assert motion["status"] == "suspect_association"
    assert motion["approaching"] is False
    assert motion["eta_minutes"] is None
    assert "traiettoria non validata" in data["nowcast"]["note"]


def test_confidence_is_capped_when_tracking_is_suspect():
    data = {
        "analysis_confidence": {"score": 100, "components": {}},
        "nowcast_tracking": {"track_quality": {"status": "suspect", "penalty_points": 18}},
    }
    nowcast_v4.calibrate_confidence(data)
    assert data["analysis_confidence"]["score"] <= 75
    assert data["analysis_confidence"]["components"]["tracking_quality_adjustment"] == -18


def test_tracking_quality_is_unavailable_without_cell():
    data = {
        "nowcast_tracking": {
            "status": "no_cell",
            "association": {"status": "no_candidate"},
            "motion": {"status": "unavailable"},
        }
    }
    quality = nowcast_v4.assess_tracking_quality(data)
    assert quality["status"] == "unavailable"
    assert data["nowcast_evidence"]["tracking_quality"].startswith("Tracking radar non disponibile")




def test_blitzortung_is_embedded_for_viewing_only():
    from pathlib import Path

    html = Path("index.html").read_text(encoding="utf-8")
    assert "https://map.blitzortung.org/index.php?" in html
    assert "Blitzortung.org" in html
    assert "non è una fonte per allerte" in html
    assert "EUMETSAT MTG-LI" not in Path("nowcast_v4.py").read_text(encoding="utf-8")


def test_workflow_has_no_eumetsat_lightning_keys_but_keeps_solar():
    from pathlib import Path

    workflow = Path(".github/workflows/update-weather.yml").read_text(encoding="utf-8")
    assert "EUMETSAT_CONSUMER_KEY" not in workflow
    assert "EUMETSAT_CONSUMER_SECRET" not in workflow
    assert "LSASAF_USERNAME" in workflow
    assert "LSASAF_PASSWORD" in workflow
