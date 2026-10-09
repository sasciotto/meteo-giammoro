from datetime import datetime
from zoneinfo import ZoneInfo

import collector


def test_dew_point():
    td = collector.dew_point_c(20.0, 50.0)
    assert 9.0 < td < 10.0


def test_parse_cms_table():
    html = """
    <table><thead><tr>
      <th>Nome Stazione</th><th>Pr</th><th>Alt</th><th>Temp</th><th>Max</th><th>Min</th><th>Umid</th><th>Vento</th><th>Raff</th><th>Dir</th><th>P.Day</th><th>P.Mese</th><th>P.Anno</th><th>Press</th><th>Ore</th><th>Rete</th>
    </tr></thead><tbody><tr>
      <td>Santa Lucia del Mela (DRPC)</td><td>ME</td><td>418</td><td>22.1</td><td>27.7</td><td>20.8</td><td>75</td><td>-</td><td>-</td><td>-</td><td>0</td><td>4.2</td><td>503.5</td><td>-</td><td>19:20</td><td>Protezione Civile</td>
    </tr></tbody></table>
    """
    rows = collector.parse_cms_table(html)
    assert rows["Santa Lucia del Mela (DRPC)"]["temperature"] == 22.1
    assert rows["Santa Lucia del Mela (DRPC)"]["rain_day"] == 0


def test_station_age():
    tz = ZoneInfo("Europe/Rome")
    now = datetime(2026, 10, 9, 20, 0, tzinfo=tz)
    status, _, age = collector.station_age_status("19:30", now)
    assert status == "online"
    assert age == 30


def test_alert_parser():
    text = "ZONA A RISCHIO IDROGEOLOGICO ARANCIONE per la giornata successiva"
    level, label, note = collector.parse_alert_level_from_text(text)
    assert level == "orange"
    assert label == "Arancione"
    assert "zona A" in note


def test_alert_class_normalization():
    assert collector.normalize_alert_class("GIALLA") == "warning"
    assert collector.normalize_alert_class("arancione") == "orange"
    assert collector.normalize_alert_class("ROSSA") == "red"
    assert collector.normalize_alert_class("verde") == "low"

def test_parse_national_bulletin_target():
    text = """
    Per la giornata di domani, sabato 10 ottobre 2026:
    MODERATA CRITICITA' PER RISCHIO TEMPORALI / ALLERTA ARANCIONE:
    Sicilia: Nord-Orientale, versante ionico, Nord-Orientale, versante tirrenico e isole Eolie
    ORDINARIA CRITICITA' PER RISCHIO IDRAULICO / ALLERTA GIALLA:
    Sicilia: Nord-Orientale, versante tirrenico e isole Eolie
    """
    rows = collector.parse_national_bulletin_text(text)
    assert len(rows) == 2
    assert rows[0]["level_class"] == "orange"
    assert rows[0]["day"] == "domani"

def test_significant_change_gust_threshold():
    previous = {
        "alert": {"level_class": "warning", "level_label": "Gialla"},
        "nowcast": {"level": "low", "label": "Basso"},
        "territory": {"metrics": {"gust": {"value": 25}}},
    }
    current = {
        "alert": {"level_class": "warning", "level_label": "Gialla"},
        "nowcast": {"level": "low", "label": "Basso"},
        "territory": {"metrics": {"gust": {"value": 55}}},
    }
    change = collector.significant_change(previous, current)
    assert change is not None
    assert "raffiche" in change["title"].lower()
