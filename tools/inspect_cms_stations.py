"""One-off public HTML structure check for the CMS station feed."""
from bs4 import BeautifulSoup
import requests
import json

url = "https://www.centrometeosicilia.it/stations/database.php"
try:
    r = requests.get(url, timeout=25, headers={"User-Agent": "MeteoGiammoroCMSChecker/1.0"})
    print("CMS_HTTP", r.status_code, "bytes", len(r.content), flush=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for i, table in enumerate(soup.find_all("table")):
        headers = [c.get_text(" ", strip=True) for c in table.find_all("tr")[0].find_all(["th","td"])] if table.find("tr") else []
        print("CMS_TABLE", i, json.dumps(headers, ensure_ascii=False), flush=True)
        if "Stazione" not in " ".join(headers) and "Nome" not in " ".join(headers):
            continue
        rows = table.find_all("tr")
        print("CMS_ROW_COUNT", len(rows), flush=True)
        for row in rows[1:4]:
            td = row.find_all("td")
            if td:
                print("CMS_SAMPLE_TDS", [v.get_text(" ", strip=True)[:130] for v in td[:6]], flush=True)
                print("CMS_SAMPLE_FIRST_CELL_HTML", str(td[0])[:1100], flush=True)
        for word in ["Milazzo","Monforte","Messina","San Filippo","Barcellona","Pace del Mela","Venetico","Santa Lucia","Merì"]:
            matches=[td for tr in rows for td in tr.find_all("td")[:1] if word.casefold() in td.get_text(" ",strip=True).casefold()]
            print("CMS_MATCH",word, json.dumps([m.get_text(" ",strip=True)[:160] for m in matches[:5]],ensure_ascii=False),flush=True)
except Exception as exc:
    print("CMS_PROBE_ERROR", type(exc).__name__, str(exc)[:200], flush=True)

try:
    import collector
    stations, meta = collector.fetch_stations()
    print("CMS_PARSER_RESULTS", json.dumps({
        "feed_rows": meta.get("rows"),
        "stations": [
            {"display": st.get("display_name"), "actual": st.get("name"),
             "status": st.get("status"), "temperature": st.get("temperature"),
             "rain_day": st.get("rain_day"), "time": st.get("updated")}
            for st in stations
        ]
    }, ensure_ascii=False), flush=True)
except Exception as exc:
    print("CMS_PARSER_ERROR", type(exc).__name__, str(exc)[:220], flush=True)
