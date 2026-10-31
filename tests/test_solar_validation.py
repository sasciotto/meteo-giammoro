from solar_validation import build_report


def test_solar_validation_matches_nearest_ground_sample_within_window():
    history = {
        "updated_at": "2026-10-31T10:00:00Z",
        "samples": [
            {"timestamp": "2026-10-31T09:00:00Z", "sources": {"lsa-saf": {"status": "ok", "solar_wm2": 500, "observed_at": "2026-10-31T09:00:00Z"}, "pace-del-mela": {"status": "ok", "solar_wm2": 450, "observed_at": "2026-10-31T09:05:00Z"}}},
            {"timestamp": "2026-10-31T09:15:00Z", "sources": {"lsa-saf": {"status": "ok", "solar_wm2": 520, "observed_at": "2026-10-31T09:15:00Z"}, "pace-del-mela": {"status": "ok", "solar_wm2": 500, "observed_at": "2026-10-31T09:17:00Z"}}},
            {"timestamp": "2026-10-31T09:30:00Z", "sources": {"lsa-saf": {"status": "ok", "solar_wm2": 540, "observed_at": "2026-10-31T09:30:00Z"}, "pace-del-mela": {"status": "ok", "solar_wm2": 530, "observed_at": "2026-10-31T09:31:00Z"}}},
        ],
    }
    report = build_report(history, 20)
    pace = report["ground_comparisons"]["pace-del-mela"]
    assert pace["matched_pairs"] == 3
    assert pace["mean_bias_satellite_minus_ground_wm2"] == 26.7
    assert report["lsa_cadence"]["median_gap_minutes"] == 15.0
    assert pace["correlation"] is not None


def test_solar_validation_does_not_match_stale_ground_point():
    history = {"samples": [
        {"timestamp": "2026-10-31T09:00:00Z", "sources": {"lsa-saf": {"status": "ok", "solar_wm2": 500, "observed_at": "2026-10-31T09:00:00Z"}}},
        {"timestamp": "2026-10-31T10:00:00Z", "sources": {"pace-del-mela": {"status": "ok", "solar_wm2": 450, "observed_at": "2026-10-31T10:00:00Z"}}},
    ]}
    report = build_report(history, 20)
    assert report["ground_comparisons"]["pace-del-mela"]["matched_pairs"] == 0
