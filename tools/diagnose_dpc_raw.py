#!/usr/bin/env python3
"""One-off DPC raw GeoTIFF check. No modifications to live meteo data."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import numpy as np
import requests
from rasterio.io import MemoryFile
from rasterio.warp import transform, transform_bounds
from rasterio.windows import Window, from_bounds

API = "https://radar-api.protezionecivile.it"
ORIGIN = "https://radar.protezionecivile.it"
HEADERS = {"origin": ORIGIN, "referer": ORIGIN + "/", "accept": "application/json, text/plain, */*"}
LON, LAT = 15.31816, 38.2018
PRODUCTS = ("SRI", "SRT1", "VMI", "CUM24")
session = requests.Session()
session.headers.update({"User-Agent": "MeteoGiammoroRadarDiagnostic/1.0", **HEADERS})


def fetch(product: str):
    response = session.get(API + "/findLastProductByType", params={"type": product},
                           timeout=(5, 15))
    response.raise_for_status()
    rows = response.json().get("lastProducts") or []
    if not rows:
        raise ValueError("missing_product")
    stamp = int(rows[0]["time"])
    response = session.post(API + "/downloadProduct",
                            json={"productType": product, "productDate": stamp},
                            headers={"content-type": "application/json"}, timeout=(5, 15))
    response.raise_for_status()
    url = response.json().get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError("missing_download_url")
    # Never print the signed download URL, its token, or any request exception.
    response = session.get(url, timeout=(5, 30))
    response.raise_for_status()
    return stamp, response.content


def top_values(values: np.ndarray, limit: int = 6):
    if values.size == 0:
        return []
    unique, counts = np.unique(values, return_counts=True)
    order = np.argsort(counts)[::-1][:limit]
    return [{"raw_value": float(unique[i]), "count": int(counts[i])} for i in order]


def distribution(array: np.ndarray, mask: np.ndarray):
    v = np.asarray(array).reshape(-1).astype("float64")
    valid_mask = np.asarray(mask).reshape(-1) > 0
    finite = np.isfinite(v)
    readable = valid_mask & finite & (v > -9000)
    raw_finite = v[finite]
    return {
        "pixels": int(v.size),
        "mask_zero_pixels": int((~valid_mask).sum()),
        "finite_pixels": int(finite.sum()),
        "raw_le_minus_9000": int((finite & (v <= -9000)).sum()),
        "raw_eq_minus_9999": int((finite & (v == -9999)).sum()),
        "raw_eq_minus_32768": int((finite & (v == -32768)).sum()),
        "raw_eq_zero": int((finite & (v == 0)).sum()),
        "raw_gt_zero": int((finite & (v > 0)).sum()),
        "readable_count_by_current_filter": int(readable.sum()),
        "raw_min": float(raw_finite.min()) if raw_finite.size else None,
        "raw_max": float(raw_finite.max()) if raw_finite.size else None,
        "most_common_raw": top_values(raw_finite),
    }


def local_window(ds, radius_km: int):
    latdelta = radius_km / 111.32
    londelta = radius_km / (111.32 * math.cos(math.radians(LAT)))
    box = (LON - londelta, LAT - latdelta, LON + londelta, LAT + latdelta)
    if str(ds.crs).upper() not in {"EPSG:4326", "OGC:CRS84"}:
        box = transform_bounds("EPSG:4326", ds.crs, *box, densify_pts=21)
    w = from_bounds(*box, transform=ds.transform)
    c0 = max(0, math.floor(w.col_off))
    r0 = max(0, math.floor(w.row_off))
    c1 = min(ds.width, math.ceil(w.col_off + w.width))
    r1 = min(ds.height, math.ceil(w.row_off + w.height))
    if c1 <= c0 or r1 <= r0:
        return {"outside_raster": True}
    window = Window(c0, r0, c1 - c0, r1 - r0)
    return {
        "outside_raster": False,
        "distribution": distribution(
            ds.read(1, window=window, masked=False), ds.read_masks(1, window=window)
        ),
    }


def inspect(product: str, stamp: int, raw: bytes):
    with MemoryFile(raw) as mem:
        with mem.open() as ds:
            x, y = transform("EPSG:4326", ds.crs, [LON], [LAT])
            x, y = x[0], y[0]
            info = {
                "product": product,
                "product_timestamp_utc": datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat(),
                "raster": {
                    "width": ds.width,
                    "height": ds.height,
                    "crs": str(ds.crs)[:120],
                    "dtype": ds.dtypes[0],
                    "nodata": str(ds.nodata) if ds.nodata is not None else None,
                    "mask_flags": [[flag.name for flag in f] for f in ds.mask_flag_enums],
                    "scales": [float(s) for s in ds.scales],
                    "offsets": [float(s) for s in ds.offsets],
                    "point_inside_bounds": bool(ds.bounds.left <= x < ds.bounds.right and ds.bounds.bottom < y <= ds.bounds.top),
                },
                "local": {str(r): local_window(ds, r) for r in (1, 5, 15, 30)},
                "full_raster": distribution(ds.read(1, masked=False), ds.read_masks(1)),
            }
            return info


def main():
    print("DPC RAW DIAGNOSTICS: start; no thresholds or production data modified.", flush=True)
    for product in PRODUCTS:
        print("FETCH PRODUCT:", product, flush=True)
        try:
            stamp, raw = fetch(product)
            result = inspect(product, stamp, raw)
            print("DIAGNOSTIC_JSON " + json.dumps(result, separators=(",", ":"), allow_nan=False), flush=True)
        except requests.HTTPError as exc:
            # Status code only; never echo signed URL or HTTP response body.
            code = getattr(exc.response, "status_code", None)
            print("DIAGNOSTIC_ERROR " + json.dumps({"product": product, "stage": "http", "status": code}), flush=True)
        except (requests.RequestException, ValueError, OSError, RuntimeError, KeyError) as exc:
            print("DIAGNOSTIC_ERROR " + json.dumps({"product": product, "stage": "fetch_or_decode", "exception_type": type(exc).__name__}), flush=True)
    print("DPC RAW DIAGNOSTICS: complete.", flush=True)


if __name__ == "__main__":
    main()
