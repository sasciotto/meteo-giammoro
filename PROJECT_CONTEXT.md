# PROJECT_CONTEXT.md — Meteo Giammoro

Checkpoint operativo aggiornato: **29 ottobre 2026, circa 08:32 CET** (`Europe/Rome`).

Repository: `sasciotto/meteo-giammoro`  
Branch operativo: `main`  
Dashboard pubblica: `https://sasciotto.github.io/meteo-giammoro/`  
Territorio di riferimento: **Giammoro, Pace del Mela (ME)**  
Coordinate: circa **38.2018 N, 15.31816 E**  
Schema principale: `data.json` **2.1**

Attribuzione da mantenere:

**“Modello di analisi meteo creato da Salvatore Sciotto”**

> Questo documento è la fonte operativa principale per riprendere il progetto. Prima di qualsiasi modifica rileggere comunque il `main` corrente e gli ultimi workflow: il bot aggiorna continuamente i JSON runtime e può far avanzare il branch dopo questo checkpoint.

---

## Obiettivo generale del progetto

Realizzare e mantenere, a **costo monetario zero**, una dashboard pubblica, automatica e prudente per Giammoro che integri:

- osservazioni e stazioni di supporto;
- Radar-DPC;
- fulminazioni EUMETSAT MTG-LI;
- modelli numerici deterministici ed ensemble;
- allerte ufficiali regionali/nazionali;
- nowcasting locale 0–3 h;
- previsione oraria e Oggi/Domani;
- scenario 3–48 h e tendenza successiva;
- verifica ex-post delle previsioni;
- monitoraggio separato degli eventi sismici INGV.

La dashboard deve restare comprensibile a un utente non tecnico ma offrire anche strumenti di verifica e analisi avanzata.

Modalità principali correnti:

**Meteo | Analisi dettagliata | Radar | Eventi**

La sezione **Eventi** è un monitoraggio ex-post di fenomeni geofisici già rilevati; non effettua previsioni di terremoti né stime autonome di rischio tsunami.

---

## Stato attuale

### Repository e baseline valida

- `main` osservato al checkpoint: **`36d755f1e10d339e075883fb32f088f253b242c3`**.
- Ultimo commit di **codice/test intenzionale** da considerare baseline: **`ec1d0cb2ef9e552c05ed469f322ed752ed505794`** — `Verifica auto-refresh degli eventi sismici`.
- Il commit immediatamente precedente di funzione è **`eac0478da1b256d6523f57ef77a2eb50945c4bc3`** — auto-refresh sismico.
- Dopo `ec1d0cb2…`, i commit fino al ciclo osservato modificano solo JSON runtime (`data.json`, `events.json`, `verification.json`, `seismic_events.json` e, quando necessario, `history.json`).

Quindi: **il codice corrente valido è quello contenuto in `ec1d0cb2…`; il HEAD di `main` contiene dati più recenti**.

### Ultima validazione completa osservata

Workflow principale:

- nome: `Aggiorna Meteo Giammoro`;
- run: **#1747**;
- run ID: **`40835231839`**;
- esito: **success**;
- eseguito il 29/10/2026 circa 08:24–08:25 CET;
- **161 test passati**;
- collector, nowcast, home, runtime quality, verifiche, build sito, Pages e persistenza Git tutti riusciti;
- Pages pubblicata con successo;
- persistenza riuscita al primo tentativo, generando il commit runtime `36d755f…`.

Warning non bloccanti osservati nel run:

- `fontTools` non installato durante parsing di font PDF; finora non causa errore funzionale;
- alcune GitHub Actions dichiarano Node.js 20 ma GitHub le forza su Node.js 24; monitorare futuri aggiornamenti delle action.

### Snapshot runtime al checkpoint — valori volatili

`data.json`:

- ultimo controllo: **29/10/2026 08:25 CET**;
- `collector_status: ok`;
- `collector_errors: []`;
- MeteoGiammoro: `maintenance`, `excluded_from_analysis: true`;
- nowcast corrente: **Basso (radar)**;
- scenario 3–48 h: **Pioggia probabile**, 2/4 modelli con ≥0,5 mm, mediana circa 0,5 mm;
- `analysis_quality`: 80/100, **Alta**;
- nessuna traiettoria radar applicabile nel ciclo osservato.

`seismic_events.json`:

- schema 1.0;
- aggiornato circa **08:25 CET**;
- stato `ok`;
- 314 eventi nel dataset 7 giorni / 500 km, di cui 248 entro 150 km nello snapshot osservato.

Questi numeri non sono configurazione e cambiano a ogni ciclo.

---

## Requisiti e vincoli confermati

### Territorio e integrità dei dati

1. Il riferimento operativo è sempre **Giammoro**.
2. La posizione reale del dispositivo dell’utente non deve cambiare il territorio analizzato.
3. Non rinominare mai una stazione vicina come “Giammoro”.
4. Le stazioni circostanti sono supporto/controllo e devono conservare identità e rete reali.
5. Non costruire una falsa “media Giammoro” da stazioni circostanti.
6. Se un dato manca, usare `null`, `unknown`, `unavailable` o equivalente; non inventare.
7. I massimi radar areali non sono accumuli puntuali su Giammoro.
8. Le allerte ufficiali prevalgono su interpretazioni locali o modellistiche.
9. Le traiettorie radar fragili non devono essere presentate come certe.
10. Qualità tecnica, affidabilità geometrica e probabilità meteorologica sono concetti separati.

### Stazione primaria MeteoGiammoro

Stato valido:

- `maintenance`;
- `excluded_from_analysis: true`.

Percorso di rientro obbligatorio:

`maintenance` → `test` visibile ma ancora esclusa → `online` solo dopo validazione.

Non anticipare il rientro online.

### Costi e infrastruttura

- costo monetario: **zero**;
- hosting: GitHub Pages;
- elaborazione: GitHub Actions;
- fonti gratuite;
- nessun servizio a pagamento/trial senza richiesta esplicita;
- aggiornamento operativo circa ogni 15 minuti.

### Sicurezza e fonti

Secret EUMETSAT da mantenere solo in GitHub Secrets:

- `EUMETSAT_CONSUMER_KEY`;
- `EUMETSAT_CONSUMER_SECRET`.

Non esporli mai in client, JSON pubblico, log intenzionali o documentazione operativa.

### Geofisica

- nessuna previsione autonoma di terremoti;
- nessuna inferenza di rischio tsunami da magnitudo/profondità/distanza;
- informazioni tsunami: **solo fonti ufficiali CAT-INGV / Protezione Civile**.

---

## Decisioni progettuali correnti e motivazioni

### 1. Osservazioni prima dei modelli nel 0–3 h

Priorità nel brevissimo termine:

1. Radar-DPC;
2. EUMETSAT MTG-LI;
3. osservazioni/stazioni affidabili;
4. modelli numerici come supporto.

Motivo: un fenomeno osservato reale deve prevalere su un modello che non lo risolve; un singolo modello non deve produrre allarmismo con osservazioni asciutte.

### 2. Pioggia presente separata da impatto/severità

`local_precipitation` misura la semplice presenza/coerenza della pioggia locale.  
`nowcast.level` e le regole di rischio descrivono impatto/intensità.

Il radar locale usa intorni 1/3/5 km e memoria temporale; i valori areali servono per coerenza spaziale, non come pluviometro puntuale.

### 3. `tracked_cell` e `hazard_cell` restano separate

- `tracked_cell`: continuità temporale, direzione, velocità, ETA;
- `hazard_cell`: cella più rilevante localmente per Giammoro.

Non sacrificare la continuità del track per inseguire semplicemente il massimo radar più vicino.

### 4. Qualità, traiettoria e probabilità sono metriche diverse

- `analysis_quality`: disponibilità/freschezza delle fonti;
- `trajectory_reliability`: robustezza geometrica del track;
- `predictive_confidence`: probabilità previsionale, tuttora non calibrata.

Un track a due frame è limitato a massimo 64/100.  
Se `lightning.age_minutes` manca, il contributo qualità fulmini è 0.

### 5. Previsione oraria home: consenso multi-modello

La vecchia timeline oraria basata di fatto su un solo modello è stata sostituita da `home_hourly_consensus.py` usando la cache Open-Meteo già acquisita dal collector, senza nuove chiamate.

Modelli principali:

- ICON-2I;
- DWD ICON;
- ECMWF IFS;
- NOAA GFS.

Per ogni ora vengono calcolate mediane di temperatura, precipitazione, copertura nuvolosa, vento e raffiche; sono conservati anche spread nuvolosità e range precipitazione.

Regole prudenti del cielo:

- spread nuvolosità ≥35 punti → `Cielo variabile` / `Nuvoloso variabile`, mai sereno;
- `Sereno` solo con almeno 3 modelli disponibili, almeno 75% dei modelli con cloud ≤20% e spread ≤20 punti;
- maggioranza temporali → `Possibili temporali`;
- maggioranza pioggia o mediana precipitazione ≥0,2 mm → `Possibili piogge`.

Nel `data.json` corrente `home_summary.source` è il **Consenso multi-modello (ICON-2I · DWD ICON · ECMWF IFS · NOAA GFS)**.

### 6. Stato del cielo corrente in home: consenso, non osservazione diretta

`home_polish_ui.js` calcola un consenso sulla nuvolosità corrente dei modelli:

- mediana tra modelli;
- spread ≥35 → `Cielo variabile`;
- soglie conservative per molto/parzialmente/poco nuvoloso;
- pioggia/temporali osservati hanno priorità e non vengono sovrascritti.

Questo migliora il vecchio comportamento basato su un singolo ICON, ma **non è una osservazione visiva del cielo**: senza sensore/camera locale può ancora divergere dalle condizioni realmente percepite.

### 7. Eventi sismici completamente separati dagli eventi meteo

- `events.json`: verifica/ex-post meteorologica;
- `seismic_events.json`: dataset INGV.

Non riutilizzare o fondere i due file.

### 8. Persistenza sismica esplicita

Il workflow ora persiste insieme:

`data.json history.json verification.json events.json seismic_events.json`

La logica precedente, in cui `site_prepare.py` eseguiva un `git add` nascosto di `seismic_events.json`, è stata rimossa. La responsabilità Git appartiene solo al workflow.

### 9. Mappa Eventi aggiornata dai dati pubblicati

La mappa geografica usa direttamente gli eventi di `seismic_events.json`.

- marker sulle coordinate epicentrali INGV;
- dimensione = magnitudo;
- colore = recenza, non pericolosità;
- filtri client-side per periodo, distanza e magnitudo;
- Giammoro è il riferimento centrale.

L’auto-refresh controlla `seismic_events.json` ogni 60 secondi **solo mentre la modalità Eventi è attiva**. Se cambia la firma degli eventi (ID, tempo, magnitudo, coordinate o profondità), la pagina viene ricaricata e la mappa viene ricostruita.

Importante: la dashboard non interroga INGV ogni minuto. Il file sismico viene aggiornato dal workflow meteo, normalmente circa ogni 15 minuti; il controllo ogni 60 s serve a recepire rapidamente una nuova pubblicazione Pages.

### 10. Radar mobile protetto

Su mobile/coarse pointer gli embed pesanti sono disattivati per evitare crash/memoria eccessiva. Le sorgenti vengono aperte nella scheda corrente. Desktop mantiene gli iframe lazy.

Il vecchio link diretto/GIF satellite MTG non viene più usato: Satellite MTG apre la pagina Meteociel dedicata con fallback EUMETView ufficiale.

### 11. `site_prepare.py` è parte della build, non un dettaglio

`index.html` sorgente non coincide con l’HTML pubblicato. `site_prepare.py`:

- trasforma l’home;
- inietta gli script UI;
- aggiorna/copia `seismic_events.json`;
- acquisisce screenshot Radar-DPC best-effort;
- non deve rendere il deploy dipendente dallo screenshot o dalla rete sismica.

---

## Architettura e pipeline attiva

```text
collector.py
  ↓
nowcast_v4.py
  ↓
analysis_quality_update.py
    └─ analysis_quality.apply()
    └─ home_hourly_consensus.apply_from_cache()
  ↓
home_forecast_v2.py
  ↓
runtime_quality.py
  ↓
verification_engine_v2.py
  ↓
verification_history.py
  ↓
precipitation_verification.py
  ↓
analysis_quality_update.py
    └─ ricalcola qualità/confidenza
    └─ applica il consenso orario alla home corrente
  ↓
site_prepare.py
    └─ aggiorna/copia seismic_events.json
    └─ build HTML + screenshot radar best-effort
  ↓
GitHub Pages
  ↓
persistenza data.json / history.json / verification.json / events.json / seismic_events.json su main
```

### Nota sull’integrazione del consenso orario

`analysis_quality_update.py` viene eseguito due volte. Il primo passaggio avviene prima della ricostruzione `home_forecast_v2`; il secondo, dopo le verifiche, applica il consenso alla home appena generata. Funziona ed è validato, ma l’integrazione è indiretta: in futuro può essere più pulito applicare esplicitamente il consenso subito dopo `home_forecast_v2`.

### Workflow principale

`.github/workflows/update-weather.yml`

- `workflow_dispatch`;
- cron `7,22,37,52 * * * *`;
- guardia freschezza: i run non-push possono saltare il ciclo se `data.json` ha meno di 10 minuti;
- Python 3.12;
- suite pytest completa prima della raccolta;
- `/tmp/data-previous.json` per confronto col ciclo precedente;
- `/tmp/open-meteo-model-cache.json` per riuso delle risposte deterministiche;
- Pages pubblicata prima della persistenza Git;
- push dati con fetch/rebase/retry fino a 3 tentativi;
- `concurrency.cancel-in-progress: false`: i trigger vengono accodati.

### Heartbeat

`.github/workflows/weather-heartbeat.yml`

- richiama `update-weather.yml`;
- attende 15 minuti;
- rilancia se stesso;
- usa retry sul dispatch;
- il cron del workflow principale resta backup opportunistico.

È funzionale ma occupa un runner durante `sleep 900`: debito infrastrutturale, non priorità meteorologica.

---

## Componenti e file rilevanti

| File | Ruolo corrente |
|---|---|
| `PROJECT_CONTEXT.md` | fonte operativa principale |
| `README.md` | panoramica sintetica; rimanda a questo checkpoint |
| `collector.py` | acquisizione, modelli, radar, allerte, stazioni, `data.json` |
| `station_fallback.py` | fallback conservativo del feed stazioni |
| `nowcast_v2.py` | base tracking multi-cella/multi-frame |
| `nowcast_v4.py` | entry point nowcasting corrente |
| `approaching_cells.py` | celle secondarie e diagnostica avvicinamento |
| `lightning_eumetsat.py` | fulminazioni MTG-LI |
| `quality_guard.py` | guardie conservative/sanitizzazione |
| `analysis_quality.py` | qualità dati, traiettoria, stato calibrazione |
| `analysis_quality_update.py` | applicazione qualità + consenso orario |
| `home_forecast.py` | funzioni base della previsione home |
| `home_forecast_v2.py` | entry point previsione home corrente |
| `home_hourly_consensus.py` | consenso orario multi-modello |
| `model_outlook.py` | scenario multi-modello più ampio |
| `runtime_quality.py` | lifecycle, allerte, pioggia locale, normalizzazioni |
| `verification_engine_v2.py` | verifica eventi meteo `local-event-v2` |
| `verification_history.py` | metriche cumulative e archivio storico |
| `precipitation_verification.py` | verifica presenza pioggia `local-precipitation-v1` |
| `seismic_collector.py` | acquisizione eventi INGV FDSN |
| `seismic_events_ui.js` | sezione Eventi, mappa Leaflet, filtri, lista |
| `auto_refresh_ui.js` | polling `data.json` + polling sismico in modalità Eventi |
| `home_polish_ui.js` | home, consenso cielo corrente, timeline sintetica |
| `forecast_dashboard.js` | previsione principale e render dati meteo |
| `radar_ui.js` | radar ufficiale / UI principale radar |
| `radar_sources_ui.js` | sorgenti radar/satellite esterne e protezione mobile |
| `site_prepare.py` | trasformazione HTML, dataset sismico, screenshot radar |
| `index.html` | sorgente HTML, non output finale Pages |
| `data.json` | stato meteo corrente, schema 2.1 |
| `history.json` | storico cambiamenti meteo |
| `verification.json` | verifica meteo rolling, schema 1.1 |
| `events.json` | stato/pending/archivio eventi meteo |
| `seismic_events.json` | eventi sismici INGV, schema 1.0 |
| `config/stations.json` | territorio/stazioni |
| `config/overrides.json` | override configurativi |
| `tests/` | regressioni automatiche |
| `.github/workflows/update-weather.yml` | pipeline principale |
| `.github/workflows/weather-heartbeat.yml` | heartbeat auto-rilanciante |

---

## Fonti dati attive

### Meteo

Radar-DPC, prodotti principali:

- `SRI`;
- `VMI`;
- `SRT1`;
- `CUM24`;
- `TEMP`;
- IR/satellite quando disponibile.

Modelli deterministici:

- ItaliaMeteo / ARPAE ICON-2I;
- DWD ICON;
- ECMWF IFS;
- NOAA GFS.

Ensemble:

- ECMWF ENS;
- ICON EPS;
- GEFS.

Fulminazioni:

- EUMETSAT MTG Lightning Imager L2 Lightning Flashes.

Stazioni:

- feed Centro Meteorologico Siciliano e reti originarie indicate dal feed;
- fallback all’ultimo dato noto in caso di guasto, marcato precedente ed escluso dall’analisi.

Allerte:

- DRPC/CFD Sicilia per dettaglio regionale;
- DPC nazionale per cross-validation.

Zona operativa di riferimento dell’allerta:

**Nord-Orientale, versante tirrenico e isole Eolie**.

### Eventi sismici

Fonte:

`https://webservices.ingv.it/fdsnws/event/1/query`

Parametri correnti:

- ultimi 7 giorni;
- centro Giammoro;
- raggio massimo 500 km;
- magnitudo minima 1.0;
- limite 500 eventi;
- classificazione locale ≤150 km / regionale ≤500 km.

Portale ufficiale: `https://terremoti.ingv.it/`  
CAT-INGV tsunami: `https://cat.ingv.it/`

---

## Versioni correnti da considerare valide

- `data.json.schema_version`: **2.1**
- `verification.json.schema_version`: **1.1**
- `seismic_events.json.meta.schema_version`: **1.0**
- metrica eventi meteo: **`local-event-v2`**
- metrica presenza pioggia: **`local-precipitation-v1`**
- baseline legacy: **`legacy-event-v1`**, solo confronto storico
- Python workflow: **3.12**
- Leaflet Eventi: **1.9.4**
- codice baseline corrente: **`ec1d0cb2ef9e552c05ed469f322ed752ed505794`**
- HEAD runtime osservato: **`36d755f1e10d339e075883fb32f088f253b242c3`**
- ultima suite validata: **161 test**
- ultimo workflow completo validato: **#1747 / run `40835231839`**

---

## Verifica e calibrazione — stato corrente

### `local-event-v2`

Il file `verification.json` mantiene una rolling window di 300 risultati. Nello snapshot osservato i 300 casi correnti sono tutti non-eventi, quindi mostra 100% di accuracy e `event_samples: 0`.

La storia cumulativa, invece, al run #1747 riporta:

- **1883 campioni cumulativi**;
- **42 campioni evento**;
- **68 risultati evento archiviati**.

Quindi **non usare l’accuracy rolling del 100% come prova di capacità sugli eventi**.

### `local-precipitation-v1`

Al run #1747:

- 1804 campioni;
- 43 con pioggia osservata;
- POD riportato dal motore: circa **95,3%**.

Continuare a valutare anche falsi allarmi/precisione per orizzonte, non solo POD.

### Problema attuale della `predictive_confidence`

`analysis_quality.predictive_confidence()` legge `data.verification.summary.event_metrics.event_samples`, cioè il dato rolling/corrente. Nel ciclo osservato questo vale 0, mentre la storia cumulativa contiene già 42 campioni evento.

Di conseguenza `data.json` continua a mostrare:

- `predictive_confidence.status: uncalibrated`;
- `event_samples: 0`;
- progresso 0/20.

La confidenza probabilistica **non deve comunque diventare automaticamente una percentuale**; prima va corretta la sorgente dei campioni e poi studiata una vera calibrazione. Questo è il debito tecnico più importante emerso al checkpoint.

---

## Sezione Eventi — architettura corrente

### Dataset

`seismic_collector.py` produce `seismic_events.json` senza interferire con la pipeline meteo in caso di errore. Se la rete INGV fallisce e esiste un dataset precedente, deve restare disponibile come stale/ultimo dato noto.

Ogni evento conserva almeno:

- ID INGV;
- orari UTC/locali;
- coordinate;
- profondità;
- magnitudo/tipo;
- località;
- autore/tipo evento;
- distanza, bearing e direzione rispetto a Giammoro;
- URL ufficiale INGV.

### Mappa geografica

`seismic_events_ui.js` usa:

- Leaflet 1.9.4 caricato lazy;
- tile OpenStreetMap con attribuzione;
- marker Giammoro;
- marker eventi sulle coordinate reali;
- raggio marker proporzionale alla magnitudo;
- colore basato sulla recenza;
- popup con dati e scheda INGV;
- `scrollWheelZoom: false`;
- `preferCanvas: true`;
- fallback radiale se Leaflet non è disponibile.

Filtri correnti:

- periodo: 24 h / 7 giorni;
- raggio: 50 / 150 / 500 km;
- magnitudo: M≥1 / M≥2 / M≥3.

### Auto-refresh Eventi

`auto_refresh_ui.js`:

- polling principale `data.json` ogni 60 s;
- polling `seismic_events.json` ogni 60 s solo in `mode-events`;
- `cache: no-store`;
- reload solo quando cambia il dataset;
- conserva modalità corrente, sorgente Radar selezionata e posizione scroll.

Limite noto: **i filtri Eventi non sono salvati nel view state**, quindi dopo un reload automatico tornano ai default (`7d`, `150 km`, `M≥1`).

---

## Radar — stato corrente

Sorgenti aggiuntive in `radar_sources_ui.js`:

1. Weather Sicily;
2. Meteo & Radar Giammoro;
3. Windy radar;
4. Satellite MTG / Meteosat-12.

Su desktop gli iframe vengono caricati lazy solo quando selezionati.  
Modalità mobile protetta:

- schermi ≤900 px, oppure pointer coarse fino a 1180 px;
- niente iframe pesanti nella vista mobile;
- apertura della sorgente nella scheda corrente per ridurre memoria e crash.

Satellite MTG:

- pagina dedicata Meteociel;
- fallback EUMETView ufficiale;
- nessuna vecchia GIF diretta incorporata.

Caveat minore: un resize da desktop già caricato verso mobile può lasciare in DOM un iframe creato precedentemente; la protezione principale riguarda il caricamento iniziale mobile.

---

## Approcci scartati o da non riproporre

- Non creare `nowcast_v5.py`, `v6.py`, ecc. per modifiche ordinarie: consolidare i moduli attuali.
- Non usare un solo modello per la timeline oraria quando la cache dei quattro modelli è disponibile.
- Non usare un singolo ICON per descrivere il cielo corrente in home.
- Non rinominare stazioni circostanti come Giammoro.
- Non mediare arbitrariamente stazioni vicine per inventare un’osservazione locale.
- Non presentare massimi radar areali come accumuli puntuali.
- Non usare `analysis_quality` o `trajectory_reliability` come probabilità meteorologica.
- Non fondere `legacy-event-v1` con `local-event-v2`.
- Non fondere `events.json` meteo con `seismic_events.json`.
- Non usare report umani come ground truth automatica; eventuali segnalazioni manuali devono avere provenienza distinta `manual_report`.
- Non rendere il deploy dipendente dallo screenshot Radar-DPC.
- Non usare il vecchio GIF/link diretto satellite MTG come embed.
- Non reintrodurre `git add` impliciti dentro `site_prepare.py`.
- Non prevedere terremoti e non derivare autonomamente rischio tsunami.
- Non usare LTG/LAMPINET come fonte attiva finché la REST Radar-DPC v2 utilizzata non espone il prodotto necessario.

---

## Problemi noti e punti ancora incerti

### 1. Calibrazione: sorgente campioni incoerente

La rolling window può avere 0 eventi mentre lo storico cumulativo ne ha 42. `predictive_confidence` usa oggi il valore rolling, quindi la progressione 0/20 è fuorviante rispetto al campione storico disponibile.

### 2. Una soglia numerica non equivale a calibrazione probabilistica

Anche dopo aver corretto il conteggio campioni, non trasformare automaticamente la previsione in una percentuale. Serve uno studio per orizzonte su POD, precisione, FAR, CSI, affidabilità e numerosità.

### 3. Filtri Eventi persi al refresh

Il refresh automatico preserva modalità e scroll ma non periodo/raggio/magnitudo selezionati.

### 4. Latenza Eventi dipendente dal workflow

Il polling browser è a 60 s, ma `seismic_events.json` viene aggiornato dal workflow circa ogni 15 min. Un nuovo evento INGV non può apparire prima della successiva raccolta/pubblicazione.

### 5. Stato del cielo corrente resta modellistico

Il consenso riduce gli errori di un singolo modello ma non sostituisce una vera osservazione locale del cielo. Evitare testi che lo presentino come misurazione diretta.

### 6. Etichetta della stazione di supporto in home

`home_polish_ui.js` costruisce il testo usando `station.display_name || station.name`. Se `display_name` è un’etichetta territoriale più generica del nome reale, può risultare meno trasparente. Preferenza futura consigliata: mostrare prima `station.name` e usare `display_name` solo come contesto.

### 7. Integrazione consenso orario indiretta

Il consenso viene applicato da `analysis_quality_update.py`; il secondo passaggio rende il risultato corretto, ma l’accoppiamento fra qualità e previsione è poco pulito.

### 8. MeteoGiammoro ancora in manutenzione

Non deve influire sui calcoli finché non completa test e validazione.

### 9. Heartbeat con runner inattivo per 15 minuti

Funziona, ma `sleep 900` consuma tempo runner. Valutare una soluzione più elegante solo se non compromette costo zero e affidabilità.

### 10. Warning CI non bloccanti

Monitorare:

- warning `fontTools` nel parsing PDF;
- migrazione implicita delle action da Node 20 a Node 24.

---

## Attività completate

- pipeline GitHub Actions + Pages operativa;
- heartbeat ~15 min + cron di backup;
- schema meteo 2.1;
- Radar-DPC e prodotti locali;
- tracking multi-cella/multi-frame;
- distinzione `tracked_cell` / `hazard_cell`;
- quality guard traiettorie;
- EUMETSAT MTG-LI;
- allerte regionali + validazione nazionale;
- separazione qualità dati / traiettoria / probabilità;
- previsione home v2 con fallback stale;
- consenso multi-modello orario a quattro modelli;
- consenso nuvolosità corrente in home;
- rilevamento pioggia locale 1/3/5 km con memoria;
- verifica eventi `local-event-v2` + storico cumulativo;
- verifica presenza pioggia `local-precipitation-v1`;
- baseline legacy separata;
- lifecycle degli avvisi `latest_change`;
- Radar mobile protetto;
- Satellite MTG esterno con EUMETView di fallback;
- sezione Eventi sismici INGV separata;
- mappa geografica Leaflet/OSM con filtri e fallback;
- tsunami official-only;
- persistenza esplicita di `seismic_events.json`;
- rimozione dello staging Git nascosto da `site_prepare.py`;
- auto-refresh sismico in modalità Eventi;
- 161 test validati nell’ultimo ciclo osservato.

---

## Attività ancora aperte

1. Correggere la sorgente dei campioni usata da `predictive_confidence`, senza inventare probabilità.
2. Studiare la calibrazione per orizzonte usando i 42+ campioni evento cumulativi e le metriche appropriate.
3. Preservare i filtri Eventi durante auto-refresh/reload.
4. Valutare di applicare `home_hourly_consensus` direttamente subito dopo `home_forecast_v2` e separarlo da `analysis_quality_update.py`.
5. Rendere più trasparente il nome della stazione di supporto in home (`name` prima di `display_name`).
6. Continuare ad analizzare falsi positivi e falsi negativi per 30/60/120 min, senza tuning indiscriminato.
7. Migliorare mapping rete e quality control delle stazioni prima di aumentarne il peso.
8. Riportare MeteoGiammoro in `test` e poi `online` solo dopo validazione reale.
9. Monitorare warning GitHub Actions/Node e dipendenze PDF.
10. Valutare l’ottimizzazione dell’heartbeat se diventa necessario ridurre uso runner.
11. Verificare, in caso di modifiche Radar future, il comportamento resize desktop→mobile già caricato.

---

## Prossimi passi consigliati

### Priorità 1 — correggere la calibrazione

Far leggere a `predictive_confidence` una statistica cumulativa coerente con `local-event-v2` oppure esporre esplicitamente sia rolling sia cumulative. Aggiungere test che impediscano il ritorno a `0/20` quando lo storico contiene eventi.

### Priorità 2 — rendere stabile l’esperienza Eventi

Persistenza client dei filtri (`period`, `radius`, `minMag`) nello stesso stato usato dall’auto-refresh, con test di regressione.

### Priorità 3 — consolidare il consenso home

Spostare, se opportuno, l’applicazione del consenso orario in una fase esplicita subito dopo `home_forecast_v2`, senza cambiare semantica o introdurre nuove chiamate Open-Meteo.

### Priorità 4 — qualità previsionale

Analizzare gli eventi cumulativi per orizzonte e driver osservato; evitare di ottimizzare sulla sola accuracy globale.

### Priorità 5 — stazioni

Migliorare identificazione rete, quality control e trasparenza dei nomi; la stazione MeteoGiammoro resta esclusa fino a validazione.

---

## Backup e punti di ripristino

Backup completo più recente esplicitamente creato:

- branch: **`backup/stabilita-sistema-2026-10-27-1456`**
- commit: **`b19a129a7022dbb31dc09aade355a84cb2dbfdf0`**

Nota: questo backup **precede** le ultime modifiche di persistenza sismica e auto-refresh Eventi del 29/10. Non creare nuovi backup per ogni piccola modifica; crearne uno quando richiesto o prima di interventi ad alto rischio.

Esistono anche snapshot storici specifici per Eventi/Radar, ma non sono la baseline corrente.

---

## Istruzioni operative importanti per continuare il progetto

1. **Prima di ogni write rileggere `main` e lo SHA del file interessato.** Il bot può avanzare il branch in qualsiasi momento.
2. Distinguere commit di codice intenzionale dai commit automatici dei JSON.
3. Non dichiarare una funzione “online/in produzione” finché un workflow che contiene quel codice non ha superato test, build e deploy Pages.
4. Dopo modifiche importanti controllare almeno: test → collector → nowcast → home → verifiche → `site_prepare` → Pages → persistenza.
5. Non modificare manualmente i JSON runtime se non strettamente necessario.
6. Preferire modifiche ai moduli esistenti con test di regressione; evitare proliferazione v5/v6.
7. Se cambia il significato di una metrica, introdurre una nuova `metric_version` o migrazione esplicita; non mischiare serie incompatibili.
8. Ricordare che `site_prepare.py` trasforma l’HTML: testare il risultato pubblicato, non solo `index.html` sorgente.
9. La renderizzazione normale della dashboard usa un solo caricamento principale di `data.json`; l’auto-refresh fa polling leggero separato. Eventi usa inoltre `seismic_events.json`.
10. Radar screenshot e raccolta sismica devono restare best-effort: un guasto non deve fermare la dashboard meteo.
11. Non esporre i secret EUMETSAT.
12. Le fonti ufficiali e la prudenza semantica hanno priorità su una UI più spettacolare.
13. Non interpretare il luogo dell’utente come territorio meteo: il progetto resta sempre centrato su Giammoro.
14. Per GitHub usare il repository corrente come fonte autoritativa; `PROJECT_CONTEXT.md` descrive l’architettura, ma il codice su `main` prevale in caso di divergenza.

---

## Prompt per la nuova chat

Usa `PROJECT_CONTEXT.md` del repository `sasciotto/meteo-giammoro` come fonte principale e autosufficiente per continuare il progetto Meteo Giammoro. Prima di modificare qualsiasi file, rileggi il `main` corrente, gli SHA interessati e gli ultimi workflow, perché il bot aggiorna continuamente i JSON. Mantieni i vincoli del checkpoint: costo zero, riferimento sempre Giammoro, nessun dato inventato, stazioni vicine mai rinominate, MeteoGiammoro esclusa finché non validata, osservazioni prioritarie nel 0–3 h, allerte ufficiali prioritarie, metriche/versioni non mischiate, terremoti non prevedibili e tsunami official-only. Integra le novità nell’architettura esistente, aggiungi test di regressione e verifica il deploy reale prima di considerare conclusa una modifica.