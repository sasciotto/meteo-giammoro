#!/usr/bin/env python3
"""Prepara l'HTML pubblico: una sola pipeline dati e nessuna card duplicata."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


LEGACY_CARD = re.compile(
    r'<article class="card forecast-card">(?:(?!</article>).)*?'
    r'<div class="k">OGGI E DOMANI</div>(?:(?!</article>).)*?</article>',
    flags=re.S,
)
APPROACH_UI_PATH = Path(__file__).with_name("approaching_cells_ui.js")
QUALITY_UI_PATH = Path(__file__).with_name("analysis_quality_ui.js")
RADAR_UI_PATH = Path(__file__).with_name("radar_ui.js")


def _dashboard_scripts() -> str:
    scripts = ['<script src="forecast_dashboard.js"></script>']
    for path in (APPROACH_UI_PATH, QUALITY_UI_PATH, RADAR_UI_PATH):
        if path.exists():
            scripts.append("<script>\n" + path.read_text(encoding="utf-8").strip() + "\n</script>")
    return "\n".join(scripts)


def transform(html: str) -> str:
    placeholder = '<div id="homeForecastLegacy" hidden><span id="homeForecastTitle"></span><span id="homeForecastText"></span></div>'
    html, count = LEGACY_CARD.subn(placeholder, html, count=1)
    if count:
        html = html.replace('<div class="grid three section">', '<div class="grid two section">', 1)

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
