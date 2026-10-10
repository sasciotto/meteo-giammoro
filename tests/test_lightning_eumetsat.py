import os

from lightning_eumetsat import fetch_lightning, summarize_flashes, summary


def test_summarize_flashes_counts_radii():
    rlat, rlon = 38.2018, 15.31816
    lats = [38.2018, 38.2018, 38.2018, 38.2018]
    lons = [15.31816, 15.35, 15.45, 15.70]
    out = summarize_flashes(lats, lons, rlat, rlon)
    assert out["flash_count_total"] == 4
    assert out["radii"]["5"]["flash_count"] >= 1
    assert out["radii"]["10"]["flash_count"] >= out["radii"]["5"]["flash_count"]
    assert out["radii"]["30"]["flash_count"] >= out["radii"]["20"]["flash_count"]


def test_no_credentials_is_non_fatal(monkeypatch):
    monkeypatch.delenv("EUMETSAT_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("EUMETSAT_CONSUMER_SECRET", raising=False)
    out = fetch_lightning(38.2018, 15.31816)
    assert out["status"] == "not_configured"
    assert "non ancora attive" in summary(out)
