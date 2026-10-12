#!/usr/bin/env python3
"""Fallback scheduler esterno per Meteo Giammoro.

Pensato per essere eseguito da un cron job esterno a GitHub Actions.
Controlla il data.json pubblicato su GitHub Pages e avvia il workflow
principale solo quando i dati risultano obsoleti o non verificabili.

Secret richiesto:
    METEO_GITHUB_TOKEN

Il token GitHub fine-grained deve essere limitato al repository
sasciotto/meteo-giammoro con permesso repository Actions: write.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OWNER = os.getenv("METEO_GITHUB_OWNER", "sasciotto")
REPO = os.getenv("METEO_GITHUB_REPO", "meteo-giammoro")
REF = os.getenv("METEO_GITHUB_REF", "main")
WORKFLOW = os.getenv("METEO_GITHUB_WORKFLOW", "update-weather.yml")
DATA_URL = os.getenv(
    "METEO_DATA_URL",
    "https://sasciotto.github.io/meteo-giammoro/data.json",
)
STALE_MINUTES = int(os.getenv("METEO_STALE_MINUTES", "15"))
TIMEOUT_SECONDS = int(os.getenv("METEO_HTTP_TIMEOUT", "20"))
USER_AGENT = "meteo-giammoro-external-scheduler/1.1"


def _request(url: str, *, method: str = "GET", data: bytes | None = None, headers: dict[str, str] | None = None):
    merged = {"User-Agent": USER_AGENT}
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, data=data, headers=merged, method=method)
    return urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def parse_age_minutes(payload: dict, *, now: datetime | None = None) -> int | None:
    raw = (payload.get("meta") or {}).get("last_check_iso")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    seconds = (current.astimezone(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
    return max(0, int(seconds // 60))


def fetch_published_age_minutes() -> int | None:
    # Cache buster: evita di prendere una copia CDN/browser non aggiornata.
    sep = "&" if "?" in DATA_URL else "?"
    url = f"{DATA_URL}{sep}_scheduler_ts={int(time.time())}"
    with _request(url, headers={"Cache-Control": "no-cache"}) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return parse_age_minutes(payload)


def has_active_update(token: str) -> bool:
    workflow = urllib.parse.quote(WORKFLOW, safe="")
    base = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{workflow}/runs"
    for status_name in ("in_progress", "queued"):
        query = urllib.parse.urlencode({"status": status_name, "per_page": 1})
        with _request(f"{base}?{query}", headers=_github_headers(token)) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if int(payload.get("total_count") or 0) > 0:
            return True
    return False


def dispatch_update(token: str) -> None:
    workflow = urllib.parse.quote(WORKFLOW, safe="")
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{workflow}/dispatches"
    body = json.dumps({"ref": REF}).encode("utf-8")
    headers = _github_headers(token)
    headers["Content-Type"] = "application/json"
    with _request(url, method="POST", data=body, headers=headers) as response:
        status = getattr(response, "status", response.getcode())
        if status != 204:
            raise RuntimeError(f"workflow_dispatch inatteso: HTTP {status}")


def main() -> int:
    try:
        age = fetch_published_age_minutes()
    except Exception as exc:  # rete/CDN/JSON: meglio tentare il recupero
        print(f"Controllo freschezza non riuscito: {exc}", file=sys.stderr)
        age = None

    if age is not None and age < STALE_MINUTES:
        print(f"Dati freschi: {age} min (< {STALE_MINUTES}). Nessun dispatch.")
        return 0

    reason = "timestamp non verificabile" if age is None else f"dati vecchi di {age} min"
    token = os.getenv("METEO_GITHUB_TOKEN", "").strip()
    if not token:
        print(
            f"Recupero necessario ({reason}), ma METEO_GITHUB_TOKEN non è configurato.",
            file=sys.stderr,
        )
        return 2

    try:
        if has_active_update(token):
            print(f"Recupero non necessario: {reason}, ma un aggiornamento è già in coda o in corso.")
            return 0
        dispatch_update(token)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        print(f"Controllo/dispatch GitHub fallito: HTTP {exc.code} {detail}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"Controllo/dispatch GitHub fallito: {exc}", file=sys.stderr)
        return 3

    print(f"Recupero avviato: {reason}. Workflow {WORKFLOW} su {REF} inviato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
