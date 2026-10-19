# Meteo Giammoro — Dashboard 2.1

Dashboard meteorologica pubblica e automatica per **Giammoro (Pace del Mela, ME)**, circa **38.2018 N, 15.31816 E**.

**Modello di analisi meteo creato da Salvatore Sciotto**

Dashboard pubblica: https://sasciotto.github.io/meteo-giammoro/

> Per riprendere lo sviluppo usare **[`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)** come fonte operativa principale e più aggiornata. Questo README descrive l'architettura corrente a livello sintetico.

## Principi del progetto

- Il riferimento territoriale è sempre **Giammoro**.
- Le stazioni vicine sono solo supporto e validazione: mantengono identità geografica e rete originaria; non vengono rinominate come Giammoro e non vengono mediate per creare un falso dato locale.
- Un dato assente resta `null` / non disponibile: non viene inventato.
- Nel nowcasting 0–3 h le osservazioni hanno priorità sui modelli.
- Le allerte ufficiali prevalgono sull'interpretazione locale.
- Il progetto deve restare a **costo monetario zero**: GitHub Actions, GitHub Pages e fonti gratuite.
- La modalità **Meteo** deve restare semplice; **Analisi dettagliata** espone le informazioni tecniche.

## Stato della stazione MeteoGiammoro

La stazione primaria **MeteoGiammoro** è attualmente configurata come `maintenance` ed esclusa dai calcoli.

Il rientro previsto è:

`maintenance` → `test` (visibile ma ancora esclusa) → `online` solo dopo validazione.

Non va riattivata automaticamente come fonte primaria.

## Pipeline attiva

```text
collector.py
  ↓
nowcast_v4.py
  ↓
home_forecast_v2.py
  ↓
runtime_quality.py
  ↓
verification_engine_v2.py
  ↓
site_prepare.py
  ↓
GitHub Pages artifact/deploy
  ↓
persistenza JSON su main
```

### Collector

`collector.py` acquisisce e normalizza:

- stazioni locali e di supporto;
- modelli deterministici;
- ensemble;
- radar e satellite DPC;
- allerte ufficiali;
- dati necessari alla prima valutazione territoriale.

Lo stato corrente è scritto in `data.json` con **schema 2.1**.

### Nowcasting 0–3 h

Entry point attivo: **`nowcast_v4.py`**.

La catena mantiene `nowcast_engine.py` e `nowcast_v2.py` come base/legacy. La v4 aggiunge e coordina:

- tracking multi-cella e multi-frame;
- separazione tra `tracked_cell` e `hazard_cell`;
- quality score del tracking (`good`, `degraded`, `suspect`, `unavailable`);
- rimozione di ETA/closest approach quando l'associazione temporale è sospetta;
- EUMETSAT MTG Lightning Imager;
- quality guard;
- trend di pressione modellistico;
- protezioni sui dati incoerenti, incluso il dew point.

Ordine di priorità indicativo nel nowcasting:

1. Radar-DPC;
2. fulminazioni EUMETSAT MTG-LI;
3. osservazioni/stazioni affidabili;
4. modelli sul punto come supporto.

### Previsione breve e 3–48 h

Entry point attivo: **`home_forecast_v2.py`**; `home_forecast.py` resta motore base.

La home usa ICON-2I come base oraria principale quando disponibile e mostra separatamente il consenso multi-modello 3–48 h tra:

- ItaliaMeteo / ARPAE ICON-2I;
- DWD ICON;
- ECMWF IFS;
- NOAA GFS.

Il consenso espone numero di modelli con precipitazione significativa, range, mediana e accordo/dispersione.

Se la previsione home fallisce temporaneamente, la v2 può riusare l'ultima previsione valida fino a **6 ore**, marcandola esplicitamente come **Dato precedente** e impostando il collector come `degraded`.

### Ensemble 2–7+ giorni

Sono collegati:

- ECMWF ENS;
- ICON EPS;
- GEFS.

Vanno letti come spread/incertezza, non come singola previsione deterministica.

## Fonti osservative

### Stazioni

Il collector usa il database live del Centro Meteorologico Siciliano come aggregatore e conserva la rete originaria. Le aree di supporto configurate includono:

- Pace del Mela / area Giammoro;
- Milazzo;
- San Filippo del Mela;
- Santa Lucia del Mela;
- Merì;
- Monforte San Giorgio;
- Barcellona Pozzo di Gotto;
- Messina;
- Venetico;
- San Pier Marina;
- San Pier Niceto.

### Radar e satellite DPC

Prodotti usati:

- `SRI` — intensità di pioggia;
- `VMI` — riflettività massima;
- `SRT1` — cumulata ultima ora;
- `CUM24` — cumulata 24 h;
- `TEMP` — temperatura interpolata rete termometrica;
- `IR_108` — satellite infrarosso.

Quando applicabile vengono calcolate statistiche locali in intorni di 5/15/30 km.

### Fulminazioni

Fonte automatica attiva:

**EUMETSAT MTG Lightning Imager L2 Lightning Flashes**.

Le credenziali sono fornite esclusivamente tramite GitHub Secrets:

- `EUMETSAT_CONSUMER_KEY`
- `EUMETSAT_CONSUMER_SECRET`

Non devono mai essere pubblicate nel frontend o nei file statici.

## Allerte ufficiali

Fonti:

- CFD/DRPC Sicilia — avviso regionale/PDF;
- Dipartimento Protezione Civile nazionale — bollettino di criticità/allerta per cross-validation.

Zona DPC di riferimento:

`Nord-Orientale, versante tirrenico e isole Eolie`

L'avviso regionale resta la fonte di dettaglio; il bollettino nazionale viene usato per validare automaticamente il livello quando possibile. Se la validazione non è sicura, il quality guard evita di presentare come certo un colore estratto euristicamente.

`config/overrides.json` va usato solo per override manuali temporanei e tracciabili, mai per lasciare un livello di allerta fisso.

## Frontend e deploy

File sorgente principali:

- `index.html`
- `forecast_dashboard.js`

La pagina pubblicata viene preparata da `site_prepare.py`, che attualmente corregge ancora alcuni elementi legacy del markup sorgente. In particolare:

- rimuove la vecchia card combinata OGGI E DOMANI;
- collega la home a `data.home_summary.current` quando disponibile;
- integra `forecast_dashboard.js` nel medesimo flusso dati;
- mantiene **un solo fetch di `data.json`** per ciclo frontend;
- gestisce il fallback “Previsione temporaneamente non disponibile” e il badge “Dato precedente”.

Una futura semplificazione deve rendere `index.html` già coerente con l'HTML finale e ridurre il ruolo correttivo di `site_prepare.py`.

## Verifica ex-post

Entry point attivo: **`verification_engine_v2.py`**; `verification_engine.py` resta base.

Orizzonti:

- 30 min;
- 60 min;
- 120 min.

La v2 separa hazard locale e track radar e calcola metriche evento/non-evento:

- TP / TN / FP / FN;
- POD / event detection;
- precision;
- false alarm ratio;
- specificity;
- balanced accuracy;
- CSI.

`accuracy_percent` resta disponibile per compatibilità ma non deve essere usata come metrica principale quando i campioni sono dominati dai non-eventi.

## Automazione e scheduling

Workflow principale: `.github/workflows/update-weather.yml`.

Trigger principali:

- `workflow_dispatch`;
- push sui file di codice/configurazione rilevanti;
- cron di backup: `7,22,37,52 * * * *`.

Una freshness guard può evitare cicli duplicati se `data.json` è molto recente.

Il deploy Pages avviene **prima** della persistenza JSON su `main`, così un eventuale conflitto Git non rende obsoleta la pagina pubblica. La persistenza usa fetch/rebase/retry fino a 3 tentativi.

Heartbeat: `.github/workflows/weather-heartbeat.yml`.

Il sistema è self-relaying:

1. dispatch di `update-weather.yml`;
2. attesa circa 15 minuti;
3. nuovo dispatch dell'heartbeat;
4. retry in caso di errori.

Il cron del workflow principale resta un backup opportunistico. `cron-job.org` e Render non sono parte dell'infrastruttura corrente.

## File principali

### Core

- `collector.py`
- `nowcast_engine.py` — base/legacy
- `nowcast_v2.py` — tracking base e logiche legacy
- `nowcast_v4.py` — entry point nowcast attivo
- `lightning_eumetsat.py`
- `quality_guard.py`
- `home_forecast.py` — motore base
- `home_forecast_v2.py` — entry point home attivo
- `runtime_quality.py`
- `verification_engine.py` — base
- `verification_engine_v2.py` — entry point verifica attivo
- `site_prepare.py`

### Stato persistente

- `data.json`
- `history.json`
- `verification.json`
- `events.json`

### Configurazione

- `config/stations.json`
- `config/overrides.json`

### CI/CD

- `.github/workflows/update-weather.yml`
- `.github/workflows/weather-heartbeat.yml`

## Esecuzione locale e test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

Per le modifiche al progetto, `python -m pytest -q` deve essere eseguito prima di considerare valida la modifica.

## Debito tecnico / priorità correnti

Le priorità operative sono mantenute in `PROJECT_CONTEXT.md`. In sintesi:

1. eliminare i testi LTG/LAMPINET legacy residui in `nowcast_v2.py`;
2. valorizzare POD/FAR/CSI/balanced accuracy/event samples nella UI tecnica;
3. rifinire il fallback stale quando attraversa ore o cambio data;
4. ridurre il debito frontend e la necessità di patch in `site_prepare.py`;
5. irrobustire il parser dell'allerta regionale con fixture PDF reali;
6. raccogliere eventi reali sufficienti per validare ETA, traiettoria e metriche evento;
7. validare MeteoGiammoro in modalità `test` prima di qualunque rientro `online`.

## Sicurezza e limiti

La dashboard ha finalità informative. Per allerte e comportamenti di protezione civile fanno fede esclusivamente le autorità competenti.

Le fonti real-time possono avere ritardi, manutenzioni o anomalie: il sistema conserva stato/età del dato e deve preferire l'assenza del dato a una stima non dichiarata.
