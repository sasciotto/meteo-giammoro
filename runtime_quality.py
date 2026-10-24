#!/usr/bin/env python3
"""Correzioni runtime conservative per testi relativi, stato dati e pioggia locale."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import collector

TZ = ZoneInfo("Europe/Rome")
PREVIOUS_PATH = Path("/tmp/data-previous.json")
LOCAL_HISTORY_MINUTES = 180


def _num(value) -> float | None:
    try:
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return None


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


def _normalized_signal_label(value) -> str:
    text = str(value or "").lower().replace("–", "-").replace("—", "-")
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def resolve_obsolete_nowcast_change(data: dict, now: datetime | None = None) -> None:
    """Chiude una variazione 0–3 h quando il livello corrente non coincide più con il target annunciato."""
    change = data.get("latest_change", {}) or {}
    if str(change.get("status") or "") in {"expired", "resolved"}:
        return
    title = str(change.get("title") or "")
    if "→" not in title or not re.match(r"^(Aumento|Riduzione) del segnale 0[–-]3 h:", title):
        return

    target = title.rsplit("→", 1)[-1].strip()
    current = str((data.get("nowcast", {}) or {}).get("label") or "").strip()
    if not target or not current or _normalized_signal_label(target) == _normalized_signal_label(current):
        return

    now = now or datetime.now(TZ)
    previous_title = title
    closed_title = "Segnalazione 0–3 h precedente conclusa"
    data["latest_change"] = {
        **change,
        "title": closed_title,
        "text": f"La variazione precedente non rappresenta più il quadro corrente, ora {current}.",
        "window": "evento concluso",
        "confidence": "—",
        "evidence": f"Segnalazione precedente: {previous_title}. Stato 0–3 h corrente: {current}.",
        "event_type": "nowcast_change",
        "status": "resolved",
        "resolved_at": now.isoformat(timespec="seconds"),
    }
    history = [item for item in (data.get("history", []) or []) if isinstance(item, dict)]
    if not history or str(history[0].get("text") or "") != closed_title:
        data["history"] = ([{"time": now.strftime("%d/%m/%Y %H:%M"), "text": closed_title}] + history)[:50]


def _radar_stat_max(data: dict, product: str, radius: int) -> float | None:
    row = (((data.get("dpc_observations", {}) or {}).get("products", {}) or {}).get(product, {}) or {})
    if not row.get("ok"):
        return None
    for stat in row.get("stats", []) or []:
        try:
            if int(stat.get("radius_km", -1)) != radius:
                continue
            return _num(stat.get("max"))
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
        value = _num(candidate.get("distance_km"))
        if value is not None:
            distances.append(value)
    if distances:
        nearest_trackable = min(distances)
        if nearest_trackable <= 50:
            indicators["distance"] = f"Nucleo tracciabile ~{nearest_trackable:.0f} km"

    simple["indicators"] = indicators
    data.setdefault("home_summary", {})["nowcast_simple"] = simple


def _load_previous(path: Path = PREVIOUS_PATH) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _stat(product: dict, radius: int) -> dict:
    if not isinstance(product, dict) or not product.get("ok"):
        return {}
    for row in product.get("stats", []) or []:
        try:
            if int(row.get("radius_km", -1)) == radius:
                return row if isinstance(row, dict) else {}
        except (TypeError, ValueError):
            continue
    return {}


def _compact_radar_context(product: dict) -> dict:
    out = {"timestamp": product.get("timestamp"), "age_minutes": product.get("age_minutes")}
    for radius in (1, 3, 5):
        row = _stat(product, radius)
        out[str(radius)] = {
            "point": _num(row.get("point")),
            "max": _num(row.get("max")),
            "mean": _num(row.get("mean")),
            "p90": _num(row.get("p90")),
        }
    return out


def _fetch_local_product(data: dict, product_name: str) -> tuple[dict, str | None]:
    try:
        return collector.fetch_dpc_product_point(product_name, (1, 3, 5)), None
    except Exception as exc:
        fallback = (((data.get("dpc_observations", {}) or {}).get("products", {}) or {}).get(product_name, {}) or {})
        return fallback, str(exc)


def _current_precipitation(row: dict) -> float | None:
    current = row.get("current", {}) or {}
    precipitation = _num(current.get("precipitation"))
    if precipitation is not None:
        return max(0.0, precipitation)
    rain = _num(current.get("rain"))
    showers = _num(current.get("showers"))
    parts = [value for value in (rain, showers) if value is not None]
    return max(0.0, sum(parts)) if parts else None


def _model_precipitation_signal(data: dict) -> dict:
    amounts: list[tuple[str, float]] = []
    current_amounts: list[tuple[str, float]] = []
    for row in data.get("model_details", []) or []:
        if not isinstance(row, dict) or not row.get("ok"):
            continue
        label = str(row.get("label") or "modello")
        amount = _num(((row.get("next_0_3h", {}) or {}).get("precip_sum")))
        if amount is not None:
            amounts.append((label, amount))
        current_amount = _current_precipitation(row)
        if current_amount is not None:
            current_amounts.append((label, current_amount))

    wet = [(label, amount) for label, amount in amounts if amount >= 0.2]
    notable = [(label, amount) for label, amount in amounts if amount >= 0.5]
    current_wet = [(label, amount) for label, amount in current_amounts if amount >= 0.1]
    if len(wet) >= 3:
        status = "supported"
        label = "Pioggia possibile"
    elif notable or len(wet) >= 2:
        status = "weak"
        label = "Possibili piovaschi"
    else:
        status = "low"
        label = "Segnale modellistico basso"

    return {
        "status": status,
        "label": label,
        "available_models": len(amounts),
        "wet_models": len(wet),
        "notable_models": len(notable),
        "current_available_models": len(current_amounts),
        "current_wet_models": len(current_wet),
        "max_current_precip_mm": round(max((amount for _, amount in current_amounts), default=0.0), 2),
        "max_precip_0_3h_mm": round(max((amount for _, amount in amounts), default=0.0), 1),
        "current_signals": [{"model": model, "current_precip_mm": round(amount, 2)} for model, amount in current_wet],
        "signals": [{"model": model, "precip_0_3h_mm": round(amount, 1)} for model, amount in wet],
        "semantic": "precipitation_presence_not_impact",
    }


def _radar_local_detected(sri: dict) -> tuple[bool, str]:
    r1 = _stat(sri, 1)
    r3 = _stat(sri, 3)
    point = _num(r1.get("point"))
    p90_1 = _num(r1.get("p90")) or 0.0
    mean_1 = _num(r1.get("mean")) or 0.0
    max_1 = _num(r1.get("max")) or 0.0
    p90_3 = _num(r3.get("p90")) or 0.0
    mean_3 = _num(r3.get("mean")) or 0.0
    max_3 = _num(r3.get("max")) or 0.0

    if point is not None and point >= 0.2:
        return True, "pixel radar sul punto"
    if p90_1 >= 0.2 or (mean_1 >= 0.1 and max_1 >= 0.5):
        return True, "segnale radar coerente entro ~1 km"
    if p90_3 >= 0.5 and mean_3 >= 0.1 and max_3 >= 1.0:
        return True, "segnale radar diffuso entro ~3 km"
    return False, "nessun segnale radar locale coerente"


def _recent_accumulation_signal(srt1: dict) -> bool:
    r1 = _stat(srt1, 1)
    r3 = _stat(srt1, 3)
    point = _num(r1.get("point"))
    if point is not None and point >= 0.2:
        return True
    p90_1 = _num(r1.get("p90")) or 0.0
    mean_1 = _num(r1.get("mean")) or 0.0
    max_1 = _num(r1.get("max")) or 0.0
    p90_3 = _num(r3.get("p90")) or 0.0
    mean_3 = _num(r3.get("mean")) or 0.0
    max_3 = _num(r3.get("max")) or 0.0
    return bool(
        p90_1 >= 0.1
        or (mean_1 >= 0.05 and max_1 >= 0.2)
        or (p90_3 >= 0.2 and mean_3 >= 0.05 and max_3 >= 0.5)
    )


def _merge_local_history(previous: dict, snapshot: dict, now: datetime) -> list[dict]:
    old = (((previous.get("local_precipitation", {}) or {}).get("history", [])) or [])
    rows = [row for row in old if isinstance(row, dict)]
    rows.append(snapshot)
    cutoff = now - timedelta(minutes=LOCAL_HISTORY_MINUTES)
    merged: dict[str, dict] = {}
    for row in rows:
        stamp = _parse_datetime(row.get("timestamp"))
        if stamp is None:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=TZ)
        if stamp < cutoff:
            continue
        merged[stamp.isoformat(timespec="minutes")] = row
    return [merged[key] for key in sorted(merged)]


def update_local_precipitation(data: dict, previous: dict | None = None, now: datetime | None = None) -> None:
    """Costruisce un contesto pioggia locale multi-raggio senza spacciare l'area per misura sul punto."""
    now = now or datetime.now(TZ)
    previous = previous or {}
    sri, sri_error = _fetch_local_product(data, "SRI")
    srt1, srt_error = _fetch_local_product(data, "SRT1")
    detected, detection_basis = _radar_local_detected(sri)
    recent_accumulation = _recent_accumulation_signal(srt1)

    snapshot = {
        "timestamp": now.isoformat(timespec="minutes"),
        "rain_detected": detected,
        "recent_accumulation": recent_accumulation,
        "basis": detection_basis,
        "sri": _compact_radar_context(sri),
        "srt1": _compact_radar_context(srt1),
    }
    history = _merge_local_history(previous, snapshot, now)
    recent_detected_rows = []
    for row in history:
        stamp = _parse_datetime(row.get("timestamp"))
        if stamp is None:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=TZ)
        if now - stamp <= timedelta(minutes=75) and bool(row.get("rain_detected")):
            recent_detected_rows.append(row)

    if detected:
        observation_status = "active"
        observation_label = "Pioggia rilevata nell'area di Giammoro"
    elif recent_detected_rows or recent_accumulation:
        observation_status = "recent"
        observation_label = "Pioggia rilevata recentemente nell'area"
    else:
        observation_status = "dry"
        observation_label = "Nessuna pioggia locale rilevata ora"

    last_detected_at = None
    if recent_detected_rows:
        last_detected_at = recent_detected_rows[-1].get("timestamp")
    elif detected:
        last_detected_at = snapshot["timestamp"]

    model_signal = _model_precipitation_signal(data)
    data["local_precipitation"] = {
        "generated_at": now.isoformat(timespec="seconds"),
        "status": observation_status,
        "label": observation_label,
        "observation_basis": "Radar-DPC multi-raggio 1/3/5 km + persistenza temporale",
        "point_measurement_available": bool(_num(_stat(srt1, 1).get("point")) is not None),
        "area_values_are_not_point_measurements": True,
        "last_detected_at": last_detected_at,
        "current_detection_basis": detection_basis,
        "recent_accumulation_signal": recent_accumulation,
        "radar": {"sri": _compact_radar_context(sri), "srt1": _compact_radar_context(srt1)},
        "forecast_0_3h": model_signal,
        "impact_level": (data.get("nowcast", {}) or {}).get("level"),
        "history": history,
        "errors": [item for item in (sri_error, srt_error) if item],
        "note": (
            "La presenza di pioggia e l'impatto sono separati. I valori areali entro 1/3/5 km servono a riconoscere "
            "rovesci locali che possono sfuggire al singolo pixel e non vengono presentati come accumulo esatto su Giammoro."
        ),
    }

    simple = ((data.get("home_summary", {}) or {}).get("nowcast_simple", {}) or {})
    if not simple:
        return
    indicators = simple.setdefault("indicators", {})
    if observation_status == "active":
        simple["status"] = "active"
        simple["title"] = "Fenomeni vicini o in corso"
        simple["text"] = "Pioggia rilevata nell'area di Giammoro. Il segnale radar locale ha priorità sui modelli nel brevissimo termine."
        simple["detail"] = "Rilevamento areale entro pochi chilometri; non è una misura pluviometrica puntuale."
        indicators["radar"] = "Pioggia locale rilevata"
    elif observation_status == "recent":
        simple["status"] = "watch"
        simple["title"] = "Da monitorare"
        simple["text"] = "Pioggia rilevata recentemente nell'area di Giammoro; al momento il segnale radar locale è cessato o attenuato."
        if model_signal["status"] in {"weak", "supported"}:
            simple["text"] += " Restano possibili altri piovaschi nelle prossime 3 ore."
        indicators["radar"] = "Pioggia recente nell'area"
    elif model_signal["status"] in {"weak", "supported"} and simple.get("status") == "calm":
        simple["status"] = "watch"
        simple["title"] = "Da monitorare"
        simple["text"] = "Il radar è attualmente asciutto, ma i modelli mostrano un segnale di possibili piovaschi nelle prossime 3 ore."
        simple["detail"] = (
            f"Segnale modellistico di presenza: {model_signal['wet_models']}/{model_signal['available_models']} modelli; "
            "impatto previsto basso se non emergono nuovi segnali osservativi."
        )

    indicators["pioggia_locale"] = observation_label
    indicators["modelli_0_3h"] = model_signal["label"]
    simple["indicators"] = indicators
    data.setdefault("home_summary", {})["nowcast_simple"] = simple


def apply(data: dict, now: datetime | None = None, previous: dict | None = None, update_local: bool = True) -> dict:
    now = now or datetime.now(TZ)
    normalize_alert_relative_day(data, now)
    expire_stale_radar_change(data, now)
    resolve_obsolete_nowcast_change(data, now)
    refine_home_nowcast_radar(data)
    if update_local:
        update_local_precipitation(data, previous=previous or {}, now=now)
    return data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data.json")
    p.add_argument("--previous", default=str(PREVIOUS_PATH))
    args = p.parse_args()
    path = Path(args.data)
    data = json.loads(path.read_text(encoding="utf-8"))
    previous = _load_previous(Path(args.previous))
    apply(data, previous=previous)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
