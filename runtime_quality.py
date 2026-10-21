#!/usr/bin/env python3
"""Correzioni runtime conservative per testi relativi e stato dati."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")


def _title_dates(title: str) -> tuple[date, date] | None:
    m = re.search(r"(\d{1,2})\s*[-–]\s*(\d{1,2})/(\d{1,2})/(\d{4})", title or "")
    if m:
        d1, d2, month, year = map(int, m.groups())
        try:
            return date(year, month, d1), date(year, month, d2)
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})/(\d{1,2})\s*[-–]\s*(\d{1,2})/(\d{1,2})/(\d{4})", title or "")
    if m:
        d1, m1, d2, m2, year = map(int, m.groups())
        try:
            return date(year, m1, d1), date(year, m2, d2)
        except ValueError:
            return None
    return None


def _display_day(target: date, today: date) -> str:
    if target == today:
        return f"oggi {target:%d/%m}"
    if target == today + timedelta(days=1):
        return f"domani {target:%d/%m}"
    return target.strftime("%d/%m")


def _parse_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def _parse_datetime(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def normalize_alert_relative_day(data: dict, now: datetime | None = None) -> None:
    """Mostra il giorno corrente dell'avviso quando è presente, non il primo giorno storico."""
    alert = data.get("alert", {}) or {}
    national = alert.get("national_validation", {}) or {}
    records = national.get("records", []) or []
    dates = _title_dates(str(alert.get("title") or ""))
    if not dates or not records:
        return

    now = now or datetime.now(TZ)
    today = now.astimezone(TZ).date() if now.tzinfo else now.date()
    mapping = {"oggi": dates[0], "domani": dates[1]}
    target_dates: list[date] = []

    for row in records:
        if not isinstance(row, dict):
            continue
        original = str(row.get("original_day") or row.get("day") or "").lower().strip()
        target = _parse_date(row.get("target_date"))
        if target is None:
            if original.startswith("oggi"):
                target = mapping["oggi"]
            elif original.startswith("domani"):
                target = mapping["domani"]
        if target is None:
            continue
        if not row.get("original_day"):
            row["original_day"] = original
        row["target_date"] = target.isoformat()
        row["day"] = _display_day(target, today)
        if row.get("level_class") == alert.get("level_class"):
            target_dates.append(target)

    if not target_dates:
        return

    unique_dates = sorted(set(target_dates))
    if today in unique_dates:
        target = today
    else:
        future = [item for item in unique_dates if item > today]
        target = min(future) if future else max(unique_dates)

    display = _display_day(target, today)
    old_label = str(alert.get("level_label") or "")
    base_label = re.sub(r"\s*\([^)]*\)\s*$", "", old_label).strip() or "Allerta"
    new_label = f"{base_label} ({display})"
    alert["level_label"] = new_label
    alert["validity"] = display
    text = str(alert.get("text") or "")
    if old_label and old_label in text:
        alert["text"] = text.replace(old_label, new_label)
    national["level_label"] = new_label
    national["validity"] = display
    alert["national_validation"] = national


def expire_stale_radar_change(data: dict, now: datetime | None = None) -> None:
    """Chiude una segnalazione radar che ha superato valid_until senza riconferma."""
    change = data.get("latest_change", {}) or {}
    if change.get("event_type") != "radar_approach":
        return
    if str(change.get("status") or "") not in {"active", "pending_confirmation"}:
        return

    valid_until = _parse_datetime(change.get("valid_until"))
    if valid_until is None:
        return
    now = now or datetime.now(TZ)
    if now.tzinfo is None and valid_until.tzinfo is not None:
        now = now.replace(tzinfo=TZ)
    elif now.tzinfo is not None and valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=now.tzinfo)
    if now <= valid_until:
        return

    title = "Segnalazione radar precedente conclusa"
    change["title"] = title
    change["text"] = "La precedente indicazione di avvicinamento non è stata confermata entro la finestra di validità."
    change["window"] = "evento concluso"
    change["status"] = "expired"
    change["resolved_at"] = now.isoformat(timespec="seconds")
    data["latest_change"] = change

    history = [item for item in (data.get("history", []) or []) if isinstance(item, dict)]
    if not history or str(history[0].get("text") or "") != title:
        data["history"] = ([{"time": now.strftime("%d/%m/%Y %H:%M"), "text": title}] + history)[:50]


def _radar_stat_max(data: dict, product: str, radius: int) -> float | None:
    row = (((data.get("dpc_observations", {}) or {}).get("products", {}) or {}).get(product, {}) or {})
    if not row.get("ok"):
        return None
    for stat in row.get("stats", []) or []:
        try:
            if int(stat.get("radius_km", -1)) != radius:
                continue
            value = float(stat.get("max"))
            return value if value == value else None
        except (TypeError, ValueError):
            continue
    return None


def refine_home_nowcast_radar(data: dict) -> None:
    """Distingue eco radar nell'area vasta dalla distanza del nucleo strutturato/tracciabile."""
    simple = ((data.get("home_summary", {}) or {}).get("nowcast_simple", {}) or {})
    indicators = simple.get("indicators", {}) or {}
    if not simple or not indicators:
        return

    sri15 = _radar_stat_max(data, "SRI", 15)
    sri30 = _radar_stat_max(data, "SRI", 30)
    vmi15 = _radar_stat_max(data, "VMI", 15)
    vmi30 = _radar_stat_max(data, "VMI", 30)

    if (sri15 or 0) >= 5 or (vmi15 or 0) >= 40:
        indicators["radar"] = "Pioggia significativa entro ~15 km"
    elif (sri30 or 0) >= 3 or (vmi30 or 0) >= 35:
        indicators["radar"] = "Pioggia rilevata entro ~30 km"
    elif (sri30 or 0) > 0.2 or (vmi30 or 0) >= 20:
        indicators["radar"] = "Segnale debole entro ~30 km"

    tracking = data.get("nowcast_tracking", {}) or {}
    distances = []
    for candidate in tracking.get("candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        try:
            distances.append(float(candidate.get("distance_km")))
        except (TypeError, ValueError):
            pass
    if distances:
        nearest_trackable = min(distances)
        if nearest_trackable <= 50:
            indicators["distance"] = f"Nucleo tracciabile ~{nearest_trackable:.0f} km"

    simple["indicators"] = indicators
    data.setdefault("home_summary", {})["nowcast_simple"] = simple


def apply(data: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(TZ)
    normalize_alert_relative_day(data, now)
    expire_stale_radar_change(data, now)
    refine_home_nowcast_radar(data)
    return data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data.json")
    args = p.parse_args()
    path = Path(args.data)
    data = json.loads(path.read_text(encoding="utf-8"))
    apply(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
