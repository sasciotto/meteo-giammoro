#!/usr/bin/env python3
"""Nowcasting v3: tracking multi-cella/multi-frame + LTG diretto via downloadProduct.

LTG non dipende da findLastProductByType: il motore prova timestamp recenti a passi di 10 minuti,
seguendo il flusso ufficiale downloadProduct documentato dal client Radar-DPC.
"""
from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

import nowcast_v2 as v2


def fetch_lightning_direct(collector, rlat: float, rlon: float) -> dict:
    errors=[]
    now=collector.now_local()
    base=now.replace(second=0,microsecond=0,minute=(now.minute//10)*10)
    # Il prodotto LTG è indicato a cadenza 10 min. Si tenta il presente e fino a 90 min indietro.
    for i in range(10):
        stamp=base-timedelta(minutes=10*i)
        ms=int(stamp.timestamp()*1000)
        try:
            raw=collector.dpc_download_product("LTG",ms)
            sampled=v2._raster_values(raw,rlat,rlon)
            return {
                "status":"ok",
                "source":"Radar-DPC LTG / LAMPINET (Aeronautica Militare - CNMCA)",
                "quality":"raw_product_direct_probe",
                "timestamp":stamp.isoformat(timespec="minutes"),
                "age_minutes":max(0,int((now-stamp).total_seconds()/60)),
                "retrieval":"downloadProduct diretto su timestamp a cadenza 10 minuti",
                **sampled,
            }
        except Exception as exc:
            errors.append(f"{stamp.isoformat(timespec='minutes')}: {exc}")
    return {
        "status":"unavailable",
        "source":"Radar-DPC LTG / LAMPINET",
        "retrieval":"downloadProduct diretto su ultimi 10 timestamp",
        "errors":errors[-4:],
    }


def run(data_path: Path, previous_path: Path|None=None, history_path: Path|None=None):
    import collector
    data=json.loads(data_path.read_text(encoding="utf-8"))
    prev=json.loads(previous_path.read_text(encoding="utf-8")) if previous_path and previous_path.exists() else {}
    rlat,rlon=float(collector.REF["latitude"]),float(collector.REF["longitude"])

    # Riutilizza tutta la pipeline radar v2, ma intercetta temporaneamente la sorgente LTG.
    original=v2.fetch_lightning
    v2.fetch_lightning=lambda _collector,_rlat,_rlon: fetch_lightning_direct(_collector,_rlat,_rlon)
    try:
        result=v2.run(data_path,previous_path,history_path)
    finally:
        v2.fetch_lightning=original
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="data.json")
    p.add_argument("--previous")
    p.add_argument("--history",default="history.json")
    a=p.parse_args()
    run(Path(a.data),Path(a.previous) if a.previous else None,Path(a.history) if a.history else None)
    print("Nowcast v3: multi-frame + LTG direct probe aggiornato")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
