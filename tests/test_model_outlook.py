import model_outlook
import site_prepare


def _current_case():
    return {
        "nowcast": {"note": "Radar-DPC senza segnali; Nessun segnale marcato nel consenso modellistico."},
        "risk_48h": {"label": "Elevato (modellistico)", "level": "elevato", "note": "Segnale forte in 3/4 modelli"},
        "model_details": [
            {"label": "ItaliaMeteo ICON-2I", "ok": True, "next_3_48h": {"precip_sum": 0.1, "precip_max_h": 0.1, "gust_max": 64.8, "cape_max": 1980, "thunder_signal": False}},
            {"label": "DWD ICON", "ok": True, "next_3_48h": {"precip_sum": 4.1, "precip_max_h": 1.9, "gust_max": 31.3, "cape_max": 1770, "thunder_signal": True}},
            {"label": "ECMWF IFS", "ok": True, "next_3_48h": {"precip_sum": 7.7, "precip_max_h": 4.0, "gust_max": 46.4, "cape_max": 1910, "thunder_signal": False}},
            {"label": "NOAA GFS", "ok": True, "next_3_48h": {"precip_sum": 4.0, "precip_max_h": 1.0, "gust_max": 39.2, "cape_max": 1270, "thunder_signal": False}},
        ],
        "home_summary": {"multi_model": {"available": True, "label": "Incertezza modellistica elevata", "agreement": "basso"}},
        "models": [{"horizon": "3–48 h", "agreement": "medio", "note": "Differenze rilevanti"}],
    }


def test_current_case_becomes_precipitation_tendency_not_high_risk():
    data = model_outlook.apply(_current_case())
    risk = data["risk_48h"]
    assert risk["semantic"] == "model_precipitation_tendency"
    assert risk["label"] == "Pioggia probabile"
    assert risk["level"] == "moderato"
    assert risk["wet_models"] == 3
    assert risk["precip_min_mm"] == 0.1
    assert risk["precip_max_mm"] == 7.7
    assert risk["precip_median_mm"] == 4.0
    assert risk["quantity_uncertainty"] == "elevata"
    assert risk["impact_label"] == "Moderato (modellistico)"
    assert "Quantità incerta" in risk["note"]
    assert "Nessun segnale modellistico rilevante nel brevissimo termine 0–3 h" in data["nowcast"]["note"]


def test_high_cape_without_rain_or_thunder_does_not_create_high_impact():
    data = {
        "risk_48h": {},
        "model_details": [
            {"label": "A", "ok": True, "next_3_48h": {"precip_sum": 0.0, "precip_max_h": 0.0, "gust_max": 25, "cape_max": 2500, "thunder_signal": False}},
            {"label": "B", "ok": True, "next_3_48h": {"precip_sum": 0.0, "precip_max_h": 0.0, "gust_max": 30, "cape_max": 2200, "thunder_signal": False}},
        ],
    }
    model_outlook.apply(data)
    assert data["risk_48h"]["label"] == "Pioggia poco probabile"
    assert data["risk_48h"]["impact_label"] == "Basso (modellistico)"
    assert data["risk_48h"]["impact_severe_models"] == 0


def test_home_multi_model_exposes_tendency_and_impact_separately():
    data = model_outlook.apply(_current_case())
    mm = data["home_summary"]["multi_model"]
    assert mm["label"] == "Pioggia probabile · quantità incerta"
    assert mm["precipitation_tendency"] == "Pioggia probabile"
    assert mm["impact_label"] == "Moderato (modellistico)"


def test_site_preparation_renames_risk_card_to_tendency():
    html = '<html><body><div class="k">Rischio 3–48 h</div><script>\nconst $=id=>id;</script></body></html>'
    out = site_prepare.transform(html)
    assert "Tendenza 3–48 h" in out
    assert "Rischio 3–48 h" not in out
