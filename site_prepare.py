#!/usr/bin/env python3
"""Prepara l'HTML pubblico: una sola pipeline dati e nessuna card duplicata."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path


LEGACY_CARD = re.compile(
    r'<article class="card forecast-card">(?:(?!</article>).)*?'
    r'<div class="k">OGGI E DOMANI</div>(?:(?!</article>).)*?</article>',
    flags=re.S,
)
APPROACH_UI_PATH = Path(__file__).with_name("approaching_cells_ui.js")
QUALITY_UI_PATH = Path(__file__).with_name("analysis_quality_ui.js")
VERIFICATION_HISTORY_UI_PATH = Path(__file__).with_name("verification_history_ui.js")
RADAR_UI_PATH = Path(__file__).with_name("radar_ui.js")
RADAR_SOURCES_UI_PATH = Path(__file__).with_name("radar_sources_ui.js")
RADAR_APP_URL = "https://radar.protezionecivile.it/#/pages/dashboard?zoom=6"


def _dashboard_scripts() -> str:
    scripts = ['<script src="forecast_dashboard.js"></script>']
    for path in (
        APPROACH_UI_PATH,
        QUALITY_UI_PATH,
        VERIFICATION_HISTORY_UI_PATH,
        RADAR_UI_PATH,
        RADAR_SOURCES_UI_PATH,
    ):
        if path.exists():
            scripts.append("<script>\n" + path.read_text(encoding="utf-8").strip() + "\n</script>")
    return "\n".join(scripts)


def capture_official_radar_snapshot(output: Path) -> bool:
    """Cattura la web app Radar-DPC reale senza rendere il deploy dipendente dal browser."""
    browser = next(
        (path for name in ("google-chrome", "chromium", "chromium-browser") if (path := shutil.which(name))),
        None,
    )
    if not browser:
        return False

    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--hide-scrollbars",
        "--window-size=1400,900",
        "--virtual-time-budget=12000",
        f"--screenshot={output}",
        RADAR_APP_URL,
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=40,
            check=False,
        )
        valid = result.returncode == 0 and output.exists() and output.stat().st_size >= 20_000
    except (OSError, subprocess.SubprocessError):
        valid = False

    if not valid:
        output.unlink(missing_ok=True)
    return valid


def transform(html: str) -> str:
    placeholder = '<div id="homeForecastLegacy" hidden><span id="homeForecastTitle"></span><span id="homeForecastText"></span></div>'
    html, count = LEGACY_CARD.subn(placeholder, html, count=1)
    if count:
        html = html.replace('<div class="grid three section">', '<div class="grid two section">', 1)
        html = html.replace(
            '<div class="grid two section">',
            '<div class="grid two section" id="homeSummaryCards">',
            1,
        )

    html = html.replace(
        '<div class="k">Rischio 3–48 h</div>',
        '<div class="k">Tendenza 3–48 h</div>',
        1,
    )
    html = html.replace(
        "const wx=homeWeather(m,d,tr,flashes20);",
        "const wx=d.home_summary?.current||homeWeather(m,d,tr,flashes20);",
        1,
    )
    html = html.replace(
        "}).catch(err=>{$('homeDescription').textContent='Dati temporaneamente non disponibili';",
        ";window.renderForecastDashboard?.(d)}).catch(err=>{$('homeDescription').textContent='Dati temporaneamente non disponibili';",
        1,
    )

    forecast_tag = '<script src="forecast_dashboard.js"></script>'
    if forecast_tag not in html:
        marker = "<script>\nconst $="
        if marker not in html:
            raise RuntimeError("script principale dashboard non trovato")
        html = html.replace(marker, _dashboard_scripts() + "\n" + marker, 1)
    return html


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="index.html")
    p.add_argument("--dest", default="_site/index.html")
    args = p.parse_args()
    source = Path(args.source)
    dest = Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(transform(source.read_text(encoding="utf-8")), encoding="utf-8")
    captured = capture_official_radar_snapshot(dest.parent / "radar-dpc.png")
    print("Screenshot Radar-DPC acquisito" if captured else "Screenshot Radar-DPC non disponibile: uso fallback con link ufficiale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
