import verification_history as h


def row(snapshot, horizon, verified, predicted, observed, outcome="correct"):
    return {
        "snapshot_id": snapshot,
        "horizon_minutes": horizon,
        "verified_at": verified,
        "outcome": outcome,
        "predicted_event": predicted,
        "observed_event": observed,
    }


def test_legacy_baseline_is_preserved_but_not_summed_into_v2():
    data = {"verification": {}}
    verification = {
        "updated_at": "2026-10-22T14:00:00+00:00",
        "summary": {"event_metrics": {"event_samples": 0}},
        "results": [
            row("quiet", 30, "2026-10-22T13:50:00+00:00", False, False),
        ],
    }
    data, verification, events = h.apply(data, verification, {})
    summary = verification["summary"]
    assert summary["metric_version"] == "local-event-v2"
    assert summary["cumulative_event_metrics"]["samples"] == 1
    assert summary["cumulative_event_metrics"]["event_samples"] == 0
    assert summary["legacy_baseline"]["event_metrics"]["event_samples"] == 57
    assert summary["legacy_baseline"]["event_metrics"]["false_negative"] == 43
    assert "non viene sommata" in summary["retention_note"].lower()
    assert data["verification"]["summary"] is summary
    assert events["verification_cumulative"]["metric_version"] == "local-event-v2"


def test_cumulative_metrics_do_not_double_count_and_keep_event_rows():
    verification = {
        "updated_at": "2026-10-22T14:10:00+00:00",
        "summary": {},
        "results": [
            row("tn", 30, "2026-10-22T13:50:00+00:00", False, False),
            row("tp", 30, "2026-10-22T13:51:00+00:00", True, True),
            row("fn", 60, "2026-10-22T13:52:00+00:00", False, True, "missed_event"),
            row("fp", 120, "2026-10-22T13:53:00+00:00", True, False, "false_alarm"),
        ],
    }
    data, verification, events = h.apply({}, verification, {})
    metrics = verification["summary"]["cumulative_event_metrics"]
    assert metrics["samples"] == 4
    assert metrics["true_positive"] == 1
    assert metrics["true_negative"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["event_detection_percent"] == 50.0
    assert metrics["csi_percent"] == 33.3
    assert len(events["verification_event_archive"]) == 3

    _, verification2, events2 = h.apply(data, verification, events)
    assert verification2["summary"]["cumulative_event_metrics"] == metrics
    assert len(events2["verification_event_archive"]) == 3


def test_rows_before_v2_semantics_start_are_not_mixed_with_new_metric():
    verification = {
        "summary": {},
        "results": [
            row("old", 30, "2026-10-22T13:40:00+00:00", False, True, "missed_event"),
            row("new", 30, "2026-10-22T13:50:00+00:00", True, True),
        ],
    }
    _, verification, events = h.apply({}, verification, {})
    metrics = verification["summary"]["cumulative_event_metrics"]
    assert metrics["samples"] == 1
    assert metrics["true_positive"] == 1
    assert metrics["false_negative"] == 0
    assert len(events["verification_event_archive"]) == 1


def test_cumulative_metrics_are_available_by_horizon():
    verification = {
        "summary": {},
        "results": [
            row("a", 30, "2026-10-22T13:50:00+00:00", True, True),
            row("b", 60, "2026-10-22T13:51:00+00:00", False, True, "missed_event"),
            row("c", 120, "2026-10-22T13:52:00+00:00", False, False),
        ],
    }
    _, verification, _ = h.apply({}, verification, {})
    by_horizon = verification["summary"]["cumulative_by_horizon"]
    assert by_horizon["30"]["event_detection_percent"] == 100.0
    assert by_horizon["60"]["false_negative"] == 1
    assert by_horizon["120"]["true_negative"] == 1
