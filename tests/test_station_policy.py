import json
from pathlib import Path

import station_policy


def test_substitutes_enabled_are_appended():
    config = {
        "station_groups": [
            {
                "label": "Area A",
                "candidates": ["Primary"],
                "substitutes": ["Fallback 1", "Fallback 2"],
                "allow_substitute": True,
            }
        ]
    }
    effective = station_policy.effective_config(config)
    assert effective["station_groups"][0]["candidates"] == ["Primary", "Fallback 1", "Fallback 2"]


def test_substitutes_disabled_are_not_used():
    config = {
        "station_groups": [
            {
                "label": "Area A",
                "candidates": ["Primary"],
                "substitutes": ["Other town"],
                "allow_substitute": False,
            }
        ]
    }
    effective = station_policy.effective_config(config)
    assert effective["station_groups"][0]["candidates"] == ["Primary"]


def test_network_is_inferred_from_explicit_suffix_when_missing():
    station = {
        "name": "Santa Lucia del Mela (DRPC)",
        "network": "fonte non indicata",
        "source_quality": "unknown",
        "source_quality_label": "Fonte da classificare",
    }
    out = station_policy.normalize_station(station)
    assert out["network"] == "DRPC Sicilia / Protezione Civile"
    assert out["source_quality"] == "official"
    assert out["network_inferred"] is True


def test_existing_network_is_never_overwritten():
    station = {
        "name": "Santa Lucia del Mela (DRPC)",
        "network": "Rete dichiarata dal feed",
        "source_quality": "unknown",
    }
    out = station_policy.normalize_station(station)
    assert out["network"] == "Rete dichiarata dal feed"
    assert "network_inferred" not in out


def test_lineameteo_suffix_is_reliable_not_official():
    station = {
        "name": "San Filippo del Mela (LineaMeteo)",
        "network": "",
        "source_quality": "unknown",
    }
    out = station_policy.normalize_station(station)
    assert out["network"] == "LineaMeteo"
    assert out["source_quality"] == "reliable"


def test_real_config_has_no_substitutes_on_forbidden_groups():
    config = json.loads(Path("config/stations.json").read_text(encoding="utf-8"))
    for group in config["station_groups"]:
        substitutes = set(group.get("substitutes") or [])
        candidates = set(group.get("candidates") or [])
        if not group.get("allow_substitute", False):
            assert not substitutes
        else:
            assert substitutes.issubset(candidates)


def test_normalize_data_records_policy_without_relabeling_station():
    config = {
        "station_groups": [
            {
                "label": "Santa Lucia del Mela",
                "candidates": ["Santa Lucia del Mela (DRPC)"],
                "substitutes": [],
                "allow_substitute": False,
            }
        ]
    }
    data = {
        "stations": [
            {
                "name": "Santa Lucia del Mela (DRPC)",
                "display_name": "Santa Lucia del Mela",
                "network": "fonte non indicata",
                "source_quality": "unknown",
            }
        ]
    }
    out = station_policy.normalize_data(data, config)
    assert out["stations"][0]["name"] == "Santa Lucia del Mela (DRPC)"
    assert out["stations"][0]["display_name"] == "Santa Lucia del Mela"
    assert out["station_selection_policy"]["groups"][0]["allow_substitute"] is False
