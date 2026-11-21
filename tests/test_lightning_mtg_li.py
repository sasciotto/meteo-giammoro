import json
from datetime import datetime, timedelta, timezone

import lightning_mtg_li as li


NOW = datetime(2026, 11, 18, 2, 0, tzinfo=timezone.utc)


def raw_snapshot(minutes_old=10, status="ok"):
    return {
        "status": status,
        "observed_at": (NOW - timedelta(minutes=minutes_old)).isoformat(),
        "retrieved_at": NOW.isoformat(),
        "radii": {
            "5": {"flash_count": 1},
            "10": {"flash_count": 2},
            "20": {"flash_count": 3},
            "30": {"flash_count": 4},
        },
        "nearest_km": 2.5,
        "product_id": "test-only",
    }


def test_recent_validated_snapshot_is_observation_not_ground_strike():
    result = li.usable_snapshot(raw_snapshot(), now=NOW)
    assert result["status"] == "ok"
    assert result["age_minutes"] == 10
    assert result["radii"]["20"]["flash_count"] == 3
    assert "non cumulata" in li.snapshot_note(result)
    assert "impatto al suolo" in li.snapshot_note(result)


def test_stale_snapshot_never_exposes_reused_flash_counts():
    result = li.usable_snapshot(raw_snapshot(minutes_old=46), now=NOW)
    assert result["status"] == "stale"
    assert "radii" not in result
    assert "vecchio" in li.snapshot_note(result)


def test_missing_timestamp_cannot_be_treated_as_zero():
    raw = raw_snapshot()
    raw.pop("observed_at")
    result = li.usable_snapshot(raw, now=NOW)
    assert result["status"] == "unavailable"
    assert "radii" not in result


def test_invalid_monotonic_counts_are_rejected():
    raw = raw_snapshot()
    raw["radii"]["20"]["flash_count"] = 1
    assert li.usable_snapshot(raw, now=NOW)["status"] == "unavailable"


def test_zero_is_valid_only_with_verified_fresh_product():
    raw = raw_snapshot()
    raw["radii"] = {r: {"flash_count": 0} for r in ("5", "10", "20", "30")}
    result = li.usable_snapshot(raw, now=NOW)
    assert result["status"] == "ok"
    assert result["radii"]["30"]["flash_count"] == 0


def test_missing_cache_is_nonfatal(tmp_path):
    out = li.read_snapshot(tmp_path / "missing.json", now=NOW)
    assert out["status"] == "unavailable"


def test_not_configured_has_no_fake_flash_count(tmp_path):
    snapshot = li.write_snapshot(tmp_path / "mtg.json", {"status": "not_configured"}, now=NOW)
    assert snapshot["status"] == "not_configured"
    assert "radii" not in snapshot
    assert json.loads((tmp_path / "mtg.json").read_text())["status"] == "not_configured"


def test_timeout_does_not_use_previous_data(tmp_path):
    path = tmp_path / "mtg.json"
    li.write_snapshot(path, raw_snapshot(), now=NOW)
    snapshot = li.write_snapshot(path, {"status": "timeout"}, now=NOW)
    assert snapshot["status"] == "timeout"
    assert "radii" not in snapshot


def test_no_credentials_does_not_trigger_network(monkeypatch):
    monkeypatch.delenv("EUMETSAT_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("EUMETSAT_CONSUMER_SECRET", raising=False)
    assert li.fetch_lightning(38.2018, 15.31816)["status"] == "not_configured"


def test_blitzortung_only_external_and_independent_workflow():
    from pathlib import Path
    weather = Path(".github/workflows/update-weather.yml").read_text(encoding="utf-8")
    li_workflow = Path(".github/workflows/update-mtg-li.yml").read_text(encoding="utf-8")
    assert "EUMETSAT_CONSUMER_KEY" not in weather
    assert "EUMETSAT_CONSUMER_SECRET" not in weather
    assert "timeout --signal=TERM" in li_workflow
    assert "lightning_mtg_li.py" in li_workflow
    assert "Blitzortung" not in li_workflow


def test_timeout_snapshot_records_only_safe_phase(tmp_path):
    snapshot = li.write_snapshot(
        tmp_path / "li.json", {"status": "timeout", "phase": "download"}, now=NOW
    )
    assert snapshot["status"] == "timeout"
    assert snapshot["phase"] == "download"
    assert "radii" not in snapshot


def test_untrusted_phase_does_not_enter_public_json(tmp_path):
    snapshot = li.write_snapshot(
        tmp_path / "li.json",
        {"status": "unavailable", "phase": "Bearer secret http://example.invalid"},
        now=NOW,
    )
    assert snapshot["phase"] == "unknown"
    assert "Bearer" not in (tmp_path / "li.json").read_text(encoding="utf-8")


def test_phase_marker_is_whitelisted_and_newline_terminated(monkeypatch, tmp_path):
    monkeypatch.setattr(li, "STAGE_FILE", tmp_path / "stage.txt")
    li._stage("search")
    assert li.STAGE_FILE.read_text(encoding="utf-8") == "search\n"
    li._stage("untrusted-token")
    assert li.STAGE_FILE.read_text(encoding="utf-8") == "unknown\n"


def test_workflow_has_safe_error_categorization():
    from pathlib import Path
    workflow = Path(".github/workflows/update-mtg-li.yml").read_text(encoding="utf-8")
    assert "--phase \"$phase\"" in workflow
    assert "state=timeout" in workflow
    assert "state=unavailable" in workflow


def test_lfl_netcdf_flashes_group_is_decoded(tmp_path):
    import numpy as np
    from netCDF4 import Dataset

    path = tmp_path / "lightning.nc"
    with Dataset(str(path), "w", format="NETCDF4") as ds:
        group = ds.createGroup("flashes")
        group.createDimension("flashes", 2)
        lat = group.createVariable("latitude", "f4", ("flashes",))
        lon = group.createVariable("longitude", "f4", ("flashes",))
        lat[:] = [38.2, 38.3]
        lon[:] = [15.3, 15.4]
    latitudes, longitudes = li._read_flash_arrays_from_netcdf(path.read_bytes())
    assert np.allclose(latitudes, [38.2, 38.3])
    assert np.allclose(longitudes, [15.3, 15.4])
