#!/usr/bin/env python3
"""Adattatore opzionale EUMETSAT MTG Lightning Imager (LI L2 Lightning Flashes).

Richiede le variabili d'ambiente:
- EUMETSAT_CONSUMER_KEY
- EUMETSAT_CONSUMER_SECRET

Il modulo non importa eumdac/netCDF4 finché le credenziali non sono presenti.
"""
from __future__ import annotations

import io
import math
import os
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

COLLECTION_ID = "EO:EUM:DAT:0691"
SOURCE = "EUMETSAT MTG Lightning Imager L2 Lightning Flashes"


def haversine_km(a: float, b: float, c: float, d: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(a), math.radians(c)
    dp = math.radians(c - a)
    dl = math.radians(d - b)
    q = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1, math.sqrt(q)))


def summarize_flashes(latitudes, longitudes, rlat: float, rlon: float, radii=(5, 10, 20, 30)) -> dict[str, Any]:
    lats = np.asarray(latitudes, dtype=float)
    lons = np.asarray(longitudes, dtype=float)
    valid = np.isfinite(lats) & np.isfinite(lons) & (lats >= -90) & (lats <= 90) & (lons >= -180) & (lons <= 360)
    lats = lats[valid]
    lons = lons[valid]
    lons = np.where(lons > 180, lons - 360, lons)
    if lats.size == 0:
        return {
            "flash_count_total": 0,
            "nearest_km": None,
            "radii": {str(r): {"flash_count": 0, "frequency_sum": 0.0, "positive_cells": 0} for r in radii},
        }
    dists = np.array([haversine_km(rlat, rlon, float(la), float(lo)) for la, lo in zip(lats, lons)], dtype=float)
    out: dict[str, Any] = {
        "flash_count_total": int(lats.size),
        "nearest_km": round(float(np.min(dists)), 1),
        "radii": {},
    }
    for rad in radii:
        count = int(np.count_nonzero(dists <= rad))
        out["radii"][str(rad)] = {
            "flash_count": count,
            # Compatibilità con il confidence engine esistente: qui è un conteggio flash, non frequenza LAMPINET.
            "frequency_sum": float(count),
            "positive_cells": count,
        }
    return out


def _credentials() -> tuple[str, str] | None:
    key = os.getenv("EUMETSAT_CONSUMER_KEY", "").strip()
    secret = os.getenv("EUMETSAT_CONSUMER_SECRET", "").strip()
    return (key, secret) if key and secret else None


def _choose_body_entry(product) -> str | None:
    entries = list(getattr(product, "entries", []) or [])
    bodies = [e for e in entries if "CHK-BODY" in str(e) and str(e).lower().endswith(".nc")]
    return str(bodies[0]) if bodies else None


def _read_flash_arrays_from_netcdf(raw: bytes) -> tuple[np.ndarray, np.ndarray]:
    from netCDF4 import Dataset

    # I prodotti LI possono essere NetCDF diretti o contenuti in SIP/ZIP.
    nc_bytes = raw
    if raw[:4] == b"PK\x03\x04":
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = [n for n in zf.namelist() if "CHK-BODY" in n and n.lower().endswith(".nc")]
            if not names:
                names = [n for n in zf.namelist() if n.lower().endswith(".nc") and "TRAIL" not in n]
            if not names:
                raise RuntimeError("NetCDF LI body non trovato nel SIP")
            nc_bytes = zf.read(names[0])

    with tempfile.NamedTemporaryFile(suffix=".nc") as tmp:
        tmp.write(nc_bytes)
        tmp.flush()
        with Dataset(tmp.name, "r") as ds:
            if "latitude" not in ds.variables or "longitude" not in ds.variables:
                raise RuntimeError("variabili latitude/longitude non presenti nel prodotto LI")
            lat = np.asarray(ds.variables["latitude"][:], dtype=float)
            lon = np.asarray(ds.variables["longitude"][:], dtype=float)
    return lat, lon


def fetch_lightning(rlat: float, rlon: float, now: datetime | None = None) -> dict[str, Any]:
    creds = _credentials()
    if not creds:
        return {
            "status": "not_configured",
            "source": SOURCE,
            "collection": COLLECTION_ID,
            "note": "Integrazione EUMETSAT pronta; configurare EUMETSAT_CONSUMER_KEY e EUMETSAT_CONSUMER_SECRET nei GitHub Secrets.",
        }

    try:
        import eumdac
    except Exception as exc:
        return {
            "status": "dependency_missing",
            "source": SOURCE,
            "collection": COLLECTION_ID,
            "error": str(exc),
        }

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    end = now.astimezone(timezone.utc).replace(tzinfo=None)
    start = end - timedelta(minutes=35)

    try:
        token = eumdac.AccessToken(creds)
        datastore = eumdac.DataStore(token)
        collection = datastore.get_collection(COLLECTION_ID)
        products = list(collection.search(dtstart=start, dtend=end))
        if not products:
            return {
                "status": "no_recent_product",
                "source": SOURCE,
                "collection": COLLECTION_ID,
                "window_minutes": 35,
            }
        product = max(products, key=lambda p: getattr(p, "sensing_end", datetime.min) or datetime.min)
        sensing_end = getattr(product, "sensing_end", None)
        entry = _choose_body_entry(product)
        if entry:
            with product.open(entry=entry) as src:
                raw = src.read()
        else:
            with product.open() as src:
                raw = src.read()
        lat, lon = _read_flash_arrays_from_netcdf(raw)
        sampled = summarize_flashes(lat, lon, rlat, rlon)
        if sensing_end:
            if sensing_end.tzinfo is None:
                sensing_end = sensing_end.replace(tzinfo=timezone.utc)
            age = max(0, int((now.astimezone(timezone.utc) - sensing_end.astimezone(timezone.utc)).total_seconds() / 60))
            stamp = sensing_end.astimezone(timezone.utc).isoformat(timespec="minutes")
        else:
            age = None
            stamp = None
        return {
            "status": "ok",
            "source": SOURCE,
            "collection": COLLECTION_ID,
            "quality": "satellite_observation",
            "timestamp": stamp,
            "age_minutes": age,
            "product_id": str(product),
            "entry": entry,
            **sampled,
        }
    except Exception as exc:
        return {
            "status": "error",
            "source": SOURCE,
            "collection": COLLECTION_ID,
            "error": str(exc),
        }


def summary(lightning: dict[str, Any]) -> str:
    status = lightning.get("status")
    if status == "ok":
        r = lightning.get("radii", {})
        c5 = int(r.get("5", {}).get("flash_count", 0) or 0)
        c10 = int(r.get("10", {}).get("flash_count", 0) or 0)
        c20 = int(r.get("20", {}).get("flash_count", 0) or 0)
        c30 = int(r.get("30", {}).get("flash_count", 0) or 0)
        nearest = lightning.get("nearest_km")
        if c30 > 0:
            return f"EUMETSAT MTG-LI: flash osservati entro 5/10/20/30 km = {c5}/{c10}/{c20}/{c30}; flash più vicino ~{nearest} km."
        return "EUMETSAT MTG-LI: nessun flash osservato entro 30 km nel granulo recente disponibile."
    if status == "not_configured":
        return "Fulminazioni EUMETSAT MTG-LI predisposte ma non ancora attive: credenziali API non configurate."
    if status == "no_recent_product":
        return "EUMETSAT MTG-LI: nessun granulo recente disponibile nella finestra di ricerca."
    return "Fulminazioni EUMETSAT MTG-LI non disponibili in questo ciclo; nessun dato viene inventato."
