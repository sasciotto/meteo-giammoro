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


def normalize_alert_relative_day(data: dict, now: datetime | None = None) -> None:
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
        raw_day = str(row.get("day") or "").lower()
        target = mapping.get(raw_day)
        if not target:
            continue
        row.setdefault("original_day", raw_day)
        row["target_date"] = target.isoformat()
        row["day"] = _display_day(target, today)
        if row.get("level_class") == alert.get("level_class"):
            target_dates.append(target)

    if not target_dates:
        return

    target = min(target_dates)
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


def apply(data: dict, now: datetime | None = None) -> dict:
    normalize_alert_relative_day(data, now)
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
