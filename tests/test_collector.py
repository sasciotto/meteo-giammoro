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


def test_parse_cms_current_headers_and_instrument_suffix():
    html = """
    <table><thead><tr>
      <th>Nome Stazione</th><th>Pr</th><th>Quota</th><th>Temp</th><th>Max</th>
      <th>Min</th><th>Umidità</th><th>Rugiada</th><th>Vento</th><th>Raffica</th>
      <th>Dir</th><th>Pioggia</th><th>Mese</th><th>Pressione</th>
      <th>Ora</th><th>Rete</th><th>Dettagli</th>
    </tr></thead><tbody>
      <tr>
        <td>Milazzo - Piana Ecowitt WS2910 - Schermatura Originaria</td>
        <td>ME</td><td>14</td><td>22.5</td><td>25.2</td><td>18.1</td>
        <td>63</td><td>15</td><td>12</td><td>20</td><td>NE</td>
        <td>2.4</td><td>51.0</td><td>1016.2</td><td>13:20</td><td>Ecowitt</td><td>Dettagli</td>
      </tr>
      <tr>
        <td>Messina (SIAS) Campbell CR1000 + MTX + Gill</td>
        <td>ME</td><td>55</td><td>21.0</td><td>23</td><td>19</td>
        <td>67</td><td>14</td><td>5</td><td>9</td><td>E</td>
        <td>0</td><td>15</td><td>1015.0</td><td>13:15</td><td>SIAS</td><td>Dettagli</td>
      </tr>
    </tbody></table>
    """
    rows = collector.parse_cms_table(html)
    selected = collector._match_cms_station(rows, "Milazzo - Piana")
    assert selected["name"] == "Milazzo - Piana Ecowitt WS2910 - Schermatura Originaria"
    assert selected["temperature"] == 22.5
    assert selected["humidity"] == 63
    assert selected["rain_day"] == 2.4
    assert selected["rain_month"] == 51.0
    assert selected["rain_year"] is None  # Current source does not include year.
    assert selected["pressure"] == 1016.2
    assert selected["time"] == "13:20"
    assert selected["altitude_m"] == 14
    assert collector._match_cms_station(rows, "Messina (SIAS)")["name"].startswith("Messina (SIAS)")


def test_cms_matching_never_substitutes_different_stations():
    rows = {
        "Milazzo - Piana Ecowitt WS2910": {"name": "Milazzo - Piana Ecowitt WS2910"},
        "Milazzo - Piana Davis VP2": {"name": "Milazzo - Piana Davis VP2"},
        "Messina (LineaMeteo) Sainlogic": {"name": "Messina (LineaMeteo) Sainlogic"},
    }
    assert collector._match_cms_station(rows, "Milazzo - Piana") is None
    assert collector._match_cms_station(rows, "Messina (SIAS)") is None
    assert collector._match_cms_station(rows, "Merì") is None


def test_cms_repeated_footer_headers_do_not_discard_all_rows():
    headers = "<tr><th>Nome Stazione</th><th>Temp</th><th>Ora</th></tr>"
    html = (
        "<table><thead>" + headers + "</thead>"
        "<tbody><tr><td>Milazzo - Piana Ecowitt WS2910</td><td>24.1</td>"
        "<td>13:40</td></tr></tbody>"
        "<tfoot>" + headers + "</tfoot></table>"
    )
    rows = collector.parse_cms_table(html)
    assert len(rows) == 1
    assert collector._match_cms_station(rows, "Milazzo - Piana")["temperature"] == 24.1
