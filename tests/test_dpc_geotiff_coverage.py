import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

import collector


def make_raster(values, nodata=-9999.0):
    arr = np.asarray(values, dtype="float32")
    with MemoryFile() as mem:
        with mem.open(
            driver="GTiff", height=arr.shape[0], width=arr.shape[1],
            count=1, dtype="float32", crs="EPSG:4326",
            transform=from_origin(15.0, 38.30, 0.01, 0.01),
            nodata=nodata,
        ) as ds:
            ds.write(arr, 1)
        return mem.read()


def test_geotiff_valid_zero_is_real_observation():
    raw = make_raster(np.zeros((10, 10)))
    result = collector.sample_geotiff_neighborhood(raw, 15.05, 38.25, 1)
    assert result["coverage"] == "valid_pixels"
    assert result["count"] > 0
    assert result["max"] == 0.0
    assert result["diagnostics"]["valid_pixels"] == result["count"]


def test_geotiff_masked_pixels_are_unknown_not_zero():
    raw = make_raster(np.full((10, 10), -9999.0))
    result = collector.sample_geotiff_neighborhood(raw, 15.05, 38.25, 1)
    assert result["coverage"] == "no_valid_pixels"
    assert result["count"] == 0
    assert result["max"] is None
    assert result["diagnostics"]["raster_nodata_defined"] is True


def test_geotiff_outside_extent_is_not_dry():
    raw = make_raster(np.zeros((10, 10)))
    result = collector.sample_geotiff_neighborhood(raw, 16.0, 39.0, 1)
    assert result["coverage"] == "outside_raster"
    assert result["count"] == 0
    assert result["max"] is None
    assert result["diagnostics"]["window_pixels"] == 0


def test_geotiff_partial_edge_uses_only_real_pixels():
    raw = make_raster(np.ones((10, 10)))
    result = collector.sample_geotiff_neighborhood(raw, 15.099, 38.25, 1)
    assert result["coverage"] == "valid_pixels"
    assert result["count"] > 0
    assert result["max"] == 1.0
    assert result["diagnostics"]["window_pixels"] <= 20
    assert result["count"] == result["diagnostics"]["valid_pixels"]


def test_geotiff_mixed_valid_and_masked_pixel_count():
    arr = np.full((10, 10), -9999.0)
    arr[5, 5] = 0
    raw = make_raster(arr)
    result = collector.sample_geotiff_neighborhood(raw, 15.055, 38.245, 1)
    assert result["coverage"] == "valid_pixels"
    assert result["count"] == 1
    assert result["max"] == 0.0
