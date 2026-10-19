from nowcast_v2 import choose_candidate, regression_motion, _raster_values, significant_lightning_change, lightning_summary
import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds


def previous_track():
    return {
        "status":"detected",
        "product":"SRI",
        "timestamp":"2026-10-10T12:00+00:00",
        "peak_value":20.0,
        "track_id":"SRI-test",
        "cell":{"lat":38.2,"lon":15.10,"pixels":20},
        "motion":{"status":"tracked","speed_kmh":20.0,"direction_deg":90.0},
        "track_history":[
            {"track_id":"SRI-test","timestamp":"2026-10-10T11:30+00:00","lat":38.2,"lon":14.99,"peak_value":18,"pixels":18},
            {"track_id":"SRI-test","timestamp":"2026-10-10T12:00+00:00","lat":38.2,"lon":15.10,"peak_value":20,"pixels":20},
        ],
    }


def test_multicell_prefers_plausible_match_over_stronger_new_cell():
    prev=previous_track()
    candidates=[
        {"lat":38.35,"lon":15.55,"distance_km":30,"bearing":"E","pixels":40,"peak_value":50,"relevance":99},
        {"lat":38.2,"lon":15.21,"distance_km":9,"bearing":"W","pixels":22,"peak_value":22,"relevance":20},
    ]
    chosen,assoc=choose_candidate(candidates,prev,"2026-10-10T12:30+00:00")
    assert assoc["status"]=="matched"
    assert abs(chosen["lon"]-15.21)<0.001


def test_multiframe_regression_smooths_motion():
    points=[
        {"timestamp":"2026-10-10T11:30+00:00","lat":38.2,"lon":14.99},
        {"timestamp":"2026-10-10T12:00+00:00","lat":38.2,"lon":15.10},
        {"timestamp":"2026-10-10T12:30+00:00","lat":38.2,"lon":15.21},
    ]
    m=regression_motion(points,38.2,15.318)
    assert m["status"]=="tracked"
    assert m["method"]=="multi_frame_linear_fit"
    assert m["frames"]==3
    assert m["direction"] in {"E","ENE","ESE"}
    assert 15 < m["speed_kmh"] < 25


def make_tif():
    arr=np.zeros((20,20),dtype="float32")
    arr[10,10]=2
    arr[10,11]=1
    transform=from_bounds(15.0,38.0,15.4,38.4,20,20)
    with MemoryFile() as mem:
        with mem.open(driver="GTiff",height=20,width=20,count=1,dtype="float32",crs="EPSG:4326",transform=transform) as ds:
            ds.write(arr,1)
        return mem.read()


def test_ltg_raw_raster_sampling_counts_positive_frequency():
    out=_raster_values(make_tif(),38.2,15.2,radii=(5,10,20))
    assert out["positive_cells"]==2
    assert out["nearest_km"] is not None
    assert out["radii"]["20"]["frequency_sum"]==3.0


def test_significant_lightning_change_uses_eumetsat_source_and_flash_counts():
    source="EUMETSAT MTG Lightning Imager L2 Lightning Flashes"
    unchanged={"time":"precedente","title":"Situazione invariata"}
    previous={
        "latest_change":unchanged.copy(),
        "lightning":{
            "status":"ok",
            "source":source,
            "nearest_km":8.0,
            "radii":{
                "5":{"flash_count":0,"frequency_sum":0.0},
                "10":{"flash_count":1,"frequency_sum":1.0},
                "20":{"flash_count":1,"frequency_sum":1.0},
                "30":{"flash_count":1,"frequency_sum":1.0},
            },
        },
    }
    data={
        "meta":{"last_check":"18/10/2026 14:46 CEST"},
        "latest_change":unchanged.copy(),
        "analysis_confidence":{"label":"Alta"},
        "history":[],
    }
    lightning={
        "status":"ok",
        "source":source,
        "nearest_km":3.2,
        "radii":{
            "5":{"flash_count":1,"frequency_sum":1.0},
            "10":{"flash_count":4,"frequency_sum":4.0},
            "20":{"flash_count":5,"frequency_sum":5.0},
            "30":{"flash_count":6,"frequency_sum":6.0},
        },
    }

    significant_lightning_change(data,previous,lightning)

    change=data["latest_change"]
    assert change["title"]=="Aumento dell'attività elettrica vicino a Giammoro"
    assert "EUMETSAT MTG Lightning Imager" in change["evidence"]
    assert "flash osservati entro 10 km 1 → 4" in change["evidence"]
    assert "LAMPINET" not in change["evidence"]
    assert change["text"].startswith("EUMETSAT MTG-LI")


def test_significant_lightning_change_does_not_compare_different_sources():
    unchanged={"time":"precedente","title":"Situazione invariata"}
    previous={
        "latest_change":unchanged.copy(),
        "lightning":{
            "status":"ok",
            "source":"Radar-DPC LTG / LAMPINET",
            "radii":{"10":{"frequency_sum":1.0}},
        },
    }
    data={
        "meta":{"last_check":"18/10/2026 14:46 CEST"},
        "latest_change":unchanged.copy(),
        "analysis_confidence":{"label":"Alta"},
        "history":[],
    }
    lightning={
        "status":"ok",
        "source":"EUMETSAT MTG Lightning Imager L2 Lightning Flashes",
        "nearest_km":2.0,
        "radii":{"10":{"flash_count":8,"frequency_sum":8.0}},
    }

    significant_lightning_change(data,previous,lightning)

    assert data["latest_change"]==unchanged
    assert data["history"]==[]


def test_legacy_unavailable_summary_keeps_v4_cleanup_marker():
    text=lightning_summary({
        "status":"unavailable",
        "source":"Radar-DPC LTG / LAMPINET",
    })
    assert text=="LTG/LAMPINET non disponibile in questo ciclo; nessun dato di fulminazione viene inventato."
