# Meteo Giammoro — Dashboard 2.1

Dashboard statica + collector Python per il monitoraggio meteorologico del territorio di **Giammoro (Pace del Mela, ME)**.

## Regola fondamentale

Il riferimento è sempre **Giammoro** (circa 38.2018 N, 15.31816 E). Le stazioni vicine restano osservazioni delle rispettive località: non vengono rinominate come Giammoro e non vengono mediate automaticamente per produrre un falso "dato locale".

La stazione **MeteoGiammoro** è configurata come `maintenance` ed è esclusa da tutti i calcoli finché non termina riparazione, test e validazione. Il rientro previsto è: `maintenance` → `test` (visibile ma esclusa) → `online` (utilizzabile dopo validazione).

## Dove avviene il ragionamento

`index.html` non effettua inferenze meteorologiche. Visualizza soltanto `data.json`.

Pipeline:

1. `collector.py` acquisisce le fonti.
2. normalizza timestamp, unità e qualità dei dati;
3. valuta il territorio di Giammoro e non la media delle stazioni;
4. nel 0–3 h dà priorità ai prodotti osservativi Radar-DPC quando disponibili;
5. confronta i modelli deterministici per 3–48 h;
6. legge media/spread ensemble per 2–7 giorni;
7. controlla le allerte ufficiali;
8. confronta il risultato con il controllo precedente e registra solo variazioni significative;
9. scrive `data.json` e `history.json`;
10. la dashboard visualizza il risultato.

La parte deterministica è già nel repository. Un eventuale livello AI/esperto va eseguito **server-side**, dopo la raccolta, e deve scrivere un output strutturato con evidenze; non va messo nel JavaScript del browser e non deve contenere credenziali lato client.

## Fonti già collegate nel collector

### Stazioni locali

Il collector usa il database stazioni live del Centro Meteorologico Siciliano come indice/aggregatore e conserva sempre la **rete originaria** dichiarata (es. DRPC, SIAS, LineaMeteo). Sono configurati gruppi per:

- Pace del Mela / area Giammoro;
- Milazzo;
- San Filippo del Mela;
- Santa Lucia del Mela;
- Merì;
- Monforte San Giorgio;
- Barcellona Pozzo di Gotto;
- Messina;
- supporto aggiuntivo: Venetico, San Pier Marina, San Pier Niceto.

Uno stato viene classificato `online`, `dato vecchio`, `offline/obsoleto` in base al timestamp. Un valore mancante resta `null`: non viene inventato.

### Radar-DPC / Protezione Civile

Tramite le REST API Radar-DPC il collector prova a scaricare e campionare sulle coordinate di Giammoro:

- `SRI` — intensità di pioggia al suolo;
- `VMI` — riflettività massima;
- `SRT1` — cumulata dell'ultima ora;
- `CUM24` — cumulata 24 h;
- `TEMP` — temperatura interpolata dalla rete termometrica;
- `IR_108` — prodotto satellitare infrarosso.

Per SRI/VMI/SRT1 vengono calcolate statistiche in intorni di 5, 15 e 30 km. Il nowcasting usa queste osservazioni prima del segnale modellistico. **Non viene dedotta automaticamente una traiettoria** della cella: per quello serve una futura integrazione HRD/animazione o un livello di analisi dedicato.

Il prodotto satellitare raw viene acquisito ma non convertito arbitrariamente in percentuale di copertura nuvolosa.

### Modelli sul punto di Giammoro

Via Open-Meteo vengono interrogati:

- ItaliaMeteo / ARPAE ICON-2I;
- DWD ICON;
- ECMWF IFS;
- NOAA GFS.

Per 2–7 giorni vengono interrogati anche:

- ECMWF ENS (media/spread);
- ICON EPS (media/spread);
- GEFS (media/spread).

La stima principale sul punto preferisce ICON-2I quando disponibile. Se Radar-DPC fornisce `TEMP`, `SRT1` e `CUM24`, questi valori osservativi/interpolati ufficiali possono sostituire rispettivamente temperatura e precipitazioni modellistiche nella scheda territoriale, mantenendo la fonte indicata per ogni metrica.

### Allerte

Il collector individua l'ultimo avviso del **CFD/DRPC Sicilia**. Poiché il codice colore nel PDF regionale è spesso rappresentato come mappa, la validazione automatica del livello usa anche il **Bollettino nazionale di criticità/allerta DPC**, cercando esplicitamente la zona:

`Nord-Orientale, versante tirrenico e isole Eolie`

che corrisponde al settore di interesse per Giammoro. L'avviso regionale resta la fonte di dettaglio; la sintesi nazionale evita di inferire colori da immagini in modo fragile.

`config/overrides.json` esiste solo come correzione manuale temporanea e non va usato per lasciare un'allerta fissa.

## Cosa non è ancora automatico

- fulminazioni LTG puntuali/area (il prodotto è disponibile sulla piattaforma DPC ma non è incluso negli endpoint REST documentati usati qui);
- traiettoria HRD delle celle;
- analisi sinottica/mesoscalare qualitativa avanzata (convergenze, outflow, orografia) con un modello AI;
- notifiche push dal sito.

La dashboard dichiara esplicitamente queste assenze invece di inventare dati.

## File

- `index.html` — dashboard responsive;
- `data.json` — stato corrente letto dal browser;
- `history.json` — storico sintetico delle variazioni significative;
- `collector.py` — raccolta, normalizzazione e regole deterministiche;
- `config/stations.json` — coordinate e selezione stazioni;
- `config/overrides.json` — override manuali temporanei;
- `tests/test_collector.py` — test unitari;
- `.github/workflows/update-weather.yml` — aggiornamento automatico ogni 30 minuti;
- `requirements.txt` — dipendenze Python.

## Esecuzione locale

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python collector.py
```

Per validare la pipeline senza rete:

```bash
python collector.py --offline --stdout
```

## Pubblicazione con GitHub Pages

1. creare un repository, ad esempio `meteo-giammoro`;
2. caricare tutti i file, inclusa `.github/workflows/update-weather.yml`;
3. in **Settings → Actions → General**, consentire al workflow i permessi di scrittura se richiesto;
4. in **Settings → Pages**, scegliere `Deploy from a branch`, branch `main`, cartella `/ (root)`;
5. eseguire una volta manualmente il workflow **Aggiorna Meteo Giammoro**;
6. verificare `data.json` e poi la pagina pubblicata.

Il workflow gira ai minuti 07 e 37 di ogni ora e committa solo quando `data.json`/`history.json` cambiano.

## Sicurezza e limiti

La pagina ha finalità informative. Per allerte e comportamenti di protezione civile fanno fede esclusivamente le autorità competenti. Le fonti real-time possono avere ritardi, manutenzioni o anomalie; il collector conserva stato/età del dato e deve preferire l'assenza del dato a una stima non dichiarata.
