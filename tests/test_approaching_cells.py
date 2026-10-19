import approaching_cells


RLAT = 38.2018
RLON = 15.31816


def tracking(timestamp, candidates, product="SRI"):
    return {
        "nowcast_tracking": {
            "status": "detected" if candidates else "no_cell",
            "product": product,
            "unit": "mm/h",
            "timestamp": timestamp,
            "candidates": candidates,
        }
    }


def test_detects_cell_approaching_from_south_and_keeps_motion_direction_separate():
    previous = tracking(
        "2026-10-19T08:40:00+02:00",
        [{"lat": 38.05, "lon": RLON, "distance_km": 16.9, "bearing": "S", "bearing_deg": 180, "peak_value": 8, "pixels": 20}],
    )
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [{"lat": 38.12, "lon": RLON, "distance_km": 9.1, "bearing": "S", "bearing_deg": 180, "peak_value": 10, "pixels": 22}],
    )

    monitor = approaching_cells.build_monitor(current, previous, RLAT, RLON)

    assert monitor["status"] == "detected"
    assert monitor["count"] == 1
    cell = monitor["cells"][0]
    assert cell["approach_from"] == "S"
    assert cell["approach_from_label"] == "sud"
    assert cell["movement_toward"] == "N"
    assert cell["distance_change_km"] < 0
    assert cell["approach_rate_kmh"] > 3
    assert cell["closest_approach_km"] <= 5


def test_does_not_report_cell_moving_away():
    previous = tracking(
        "2026-10-19T08:40:00+02:00",
        [{"lat": RLAT, "lon": 15.40, "distance_km": 7.1, "bearing": "E", "bearing_deg": 90, "peak_value": 8, "pixels": 20}],
    )
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [{"lat": RLAT, "lon": 15.46, "distance_km": 12.4, "bearing": "E", "bearing_deg": 90, "peak_value": 8, "pixels": 20}],
    )

    monitor = approaching_cells.build_monitor(current, previous, RLAT, RLON)

    assert monitor["status"] == "none"
    assert monitor["matched_cells"] == 1
    assert monitor["cells"] == []


def test_requires_two_coherent_scans_before_claiming_approach():
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [{"lat": 38.12, "lon": RLON, "distance_km": 9.1, "bearing": "S", "bearing_deg": 180, "peak_value": 10, "pixels": 22}],
    )

    monitor = approaching_cells.build_monitor(current, {}, RLAT, RLON)

    assert monitor["status"] == "insufficient_history"
    assert monitor["count"] == 0
    assert "almeno due scansioni" in monitor["summary"]


def test_rejects_implausible_candidate_jump():
    previous = tracking(
        "2026-10-19T08:40:00+02:00",
        [{"lat": 38.05, "lon": RLON, "distance_km": 16.9, "bearing": "S", "peak_value": 8, "pixels": 20}],
    )
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [{"lat": 38.35, "lon": RLON, "distance_km": 16.5, "bearing": "N", "peak_value": 8, "pixels": 20}],
    )

    monitor = approaching_cells.build_monitor(current, previous, RLAT, RLON)

    assert monitor["status"] == "none"
    assert monitor["matched_cells"] == 0


def test_update_exposes_monitor_in_data_and_evidence():
    data = tracking("2026-10-19T08:55:00+02:00", [])
    monitor = approaching_cells.update(data, {}, RLAT, RLON)

    assert data["approaching_cells"] is monitor
    assert data["nowcast_evidence"]["approaching_cells"] == monitor["summary"]
