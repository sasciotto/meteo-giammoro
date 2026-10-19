import approaching_cells


RLAT = 38.2018
RLON = 15.31816


def tracking(timestamp, candidates, product="SRI", **extra):
    payload = {
        "status": "detected" if candidates else "no_cell",
        "product": product,
        "unit": "mm/h",
        "timestamp": timestamp,
        "candidates": candidates,
    }
    payload.update(extra)
    return {"nowcast_tracking": payload}


def test_detects_main_tracked_cell_approaching_from_south_and_keeps_motion_direction_separate():
    previous = tracking(
        "2026-10-19T08:40:00+02:00",
        [{"lat": 38.05, "lon": RLON, "distance_km": 16.9, "bearing": "S", "bearing_deg": 180, "peak_value": 8, "pixels": 20}],
    )
    candidate = {"lat": 38.12, "lon": RLON, "distance_km": 9.1, "bearing": "S", "bearing_deg": 180, "peak_value": 10, "pixels": 22}
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [candidate],
        cell=dict(candidate),
        tracked_cell=dict(candidate),
        track_id="SRI-test",
        association={"status": "matched", "score": 2.0},
        track_quality={"status": "good"},
        motion={
            "status": "tracked",
            "frames": 4,
            "speed_kmh": 20.0,
            "direction_deg": 0.0,
            "direction": "N",
            "approach_rate_kmh": 19.0,
            "approaching": True,
            "closest_approach_km": 1.0,
            "closest_approach_minutes": 25,
            "eta_minutes": 20,
        },
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
    assert cell["trajectory_source"] == "main_track_multi_frame"
    assert cell["confirmed_frames"] == 4
    assert cell["confidence"] == "high"


def test_main_multiframe_track_suppresses_conflicting_two_frame_approach():
    previous = tracking(
        "2026-10-19T08:40:00+02:00",
        [{"lat": 38.05, "lon": RLON, "distance_km": 16.9, "peak_value": 8, "pixels": 20}],
    )
    candidate = {"lat": 38.12, "lon": RLON, "distance_km": 9.1, "bearing": "S", "bearing_deg": 180, "peak_value": 10, "pixels": 22}
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [candidate],
        cell=dict(candidate),
        tracked_cell=dict(candidate),
        track_id="SRI-test",
        track_quality={"status": "good"},
        motion={
            "status": "tracked",
            "frames": 4,
            "speed_kmh": 5.4,
            "direction_deg": 194.4,
            "direction": "SSW",
            "approach_rate_kmh": -5.4,
            "approaching": False,
            "closest_approach_km": 9.1,
            "eta_minutes": None,
        },
    )

    monitor = approaching_cells.build_monitor(current, previous, RLAT, RLON)

    assert monitor["status"] == "none"
    assert monitor["cells"] == []
    assert monitor["suppressed_by_main_track"] == 1
    assert "multi-frame" in monitor["summary"]


def test_secondary_cell_requires_three_scans_before_claiming_approach():
    previous = tracking(
        "2026-10-19T08:40:00+02:00",
        [{"lat": 38.05, "lon": RLON, "distance_km": 16.9, "bearing": "S", "bearing_deg": 180, "peak_value": 8, "pixels": 20}],
    )
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [{"lat": 38.12, "lon": RLON, "distance_km": 9.1, "bearing": "S", "bearing_deg": 180, "peak_value": 10, "pixels": 22}],
    )

    monitor = approaching_cells.build_monitor(current, previous, RLAT, RLON)

    assert monitor["status"] == "unconfirmed"
    assert monitor["count"] == 0
    assert monitor["unconfirmed_count"] == 1
    assert monitor["cells"] == []
    assert "tre scansioni" in monitor["summary"]


def test_secondary_cell_is_confirmed_after_three_coherent_scans():
    previous_candidate = {"lat": 38.05, "lon": RLON, "distance_km": 16.9, "bearing": "S", "bearing_deg": 180, "peak_value": 8, "pixels": 20}
    previous = tracking("2026-10-19T08:40:00+02:00", [previous_candidate])
    previous["approaching_cells"] = {
        "cells": [{
            "lat": 38.05,
            "lon": RLON,
            "approach_rate_kmh": 10.0,
            "movement_direction_deg": 0.0,
            "confidence": "high",
        }]
    }
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [{"lat": 38.12, "lon": RLON, "distance_km": 9.1, "bearing": "S", "bearing_deg": 180, "peak_value": 10, "pixels": 22}],
    )

    monitor = approaching_cells.build_monitor(current, previous, RLAT, RLON)

    assert monitor["status"] == "detected"
    assert monitor["count"] == 1
    assert monitor["cells"][0]["trajectory_source"] == "secondary_three_frame_confirmation"
    assert monitor["cells"][0]["confirmed_frames"] == 3


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


def test_requires_coherent_previous_scan_before_estimating_approach():
    current = tracking(
        "2026-10-19T08:55:00+02:00",
        [{"lat": 38.12, "lon": RLON, "distance_km": 9.1, "bearing": "S", "bearing_deg": 180, "peak_value": 10, "pixels": 22}],
    )

    monitor = approaching_cells.build_monitor(current, {}, RLAT, RLON)

    assert monitor["status"] == "insufficient_history"
    assert monitor["count"] == 0
    assert "scansioni coerenti" in monitor["summary"]


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


def test_latest_radar_change_is_resolved_when_main_track_no_longer_approaches():
    previous = {
        "meta": {"last_check_iso": "2026-10-19T09:45:00+02:00"},
        "latest_change": {"title": approaching_cells.RADAR_APPROACH_TITLE},
    }
    data = {
        "meta": {"last_check_iso": "2026-10-19T10:00:00+02:00"},
        "latest_change": {
            "time": "19/10/2026 09:44",
            "title": approaching_cells.RADAR_APPROACH_TITLE,
            "text": "vecchio avvicinamento",
        },
        "nowcast_tracking": {
            "status": "detected",
            "track_id": "SRI-test",
            "cell": {"distance_km": 42.8},
            "motion": {
                "status": "tracked",
                "approaching": False,
                "direction": "SSW",
                "speed_kmh": 5.4,
                "approach_rate_kmh": -5.4,
            },
            "track_quality": {"status": "good"},
        },
        "analysis_confidence": {"label": "Molto alta"},
        "history": [],
    }

    approaching_cells.sync_latest_radar_change(data, previous)

    change = data["latest_change"]
    assert change["title"] == approaching_cells.RADAR_RESOLVED_TITLE
    assert change["status"] == "resolved"
    assert change["resolved_at"] == "2026-10-19T10:00:00+02:00"
    assert change["event_type"] == "radar_approach"
    assert data["history"][0]["text"] == approaching_cells.RADAR_RESOLVED_TITLE


def test_active_radar_change_gets_lifecycle_metadata():
    data = {
        "meta": {"last_check_iso": "2026-10-19T10:00:00+02:00"},
        "latest_change": {
            "time": "19/10/2026 09:44",
            "title": approaching_cells.RADAR_APPROACH_TITLE,
        },
        "nowcast_tracking": {
            "status": "detected",
            "track_id": "SRI-test",
            "motion": {"status": "tracked", "approaching": True},
            "track_quality": {"status": "good"},
        },
    }

    approaching_cells.sync_latest_radar_change(data, {})

    change = data["latest_change"]
    assert change["status"] == "active"
    assert change["event_type"] == "radar_approach"
    assert change["track_id"] == "SRI-test"
    assert change["valid_until"] == "2026-10-19T10:45:00+02:00"


def test_suspect_tracking_downgrades_active_approach_to_unconfirmed():
    data = {
        "meta": {"last_check_iso": "2026-10-19T10:00:00+02:00"},
        "latest_change": {
            "time": "19/10/2026 09:44",
            "title": approaching_cells.RADAR_APPROACH_TITLE,
        },
        "nowcast_tracking": {
            "status": "detected",
            "track_id": "SRI-test",
            "motion": {"status": "suspect_association", "approaching": False},
            "track_quality": {"status": "suspect"},
        },
        "history": [],
    }

    approaching_cells.sync_latest_radar_change(data, {})

    assert data["latest_change"]["title"] == approaching_cells.RADAR_UNCONFIRMED_TITLE
    assert data["latest_change"]["status"] == "unconfirmed"


def test_update_exposes_monitor_in_data_and_evidence():
    data = tracking("2026-10-19T08:55:00+02:00", [])
    monitor = approaching_cells.update(data, {}, RLAT, RLON)

    assert data["approaching_cells"] is monitor
    assert data["nowcast_evidence"]["approaching_cells"] == monitor["summary"]
