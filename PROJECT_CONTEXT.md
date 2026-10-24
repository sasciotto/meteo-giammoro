# PROJECT_CONTEXT.md — Meteo Giammoro

Checkpoint operativo aggiornato: **24 ottobre 2026**, dopo il ciclo meteo delle **14:05 CEST** (`Europe/Rome`).

Repository: `sasciotto/meteo-giammoro`  
Dashboard pubblica: GitHub Pages del repository `meteo-giammoro`  
Territorio di riferimento: **Giammoro, Pace del Mela (ME)**  
Coordinate di riferimento: circa **38.2018 N, 15.31816 E**  
Schema principale: `data.json` **2.1**

> Questo file è il checkpoint operativo principale per riprendere il progetto in una nuova chat. Prima di qualsiasi modifica rileggere comunque il `main` corrente, perché il bot meteo aggiorna continuamente i JSON di runtime.

---

## Obiettivo generale del progetto

Realizzare e mantenere, a **costo monetario zero**, una dashboard meteorologica pubblica e automatica per Giammoro che combini dati osservativi, radar, fulminazioni, modelli numerici, allerte ufficiali e verifica ex-post.

Il prodotto deve offrire due livelli di lettura:

- **Meteo**: home semplice, chiara e prudente;
- **Analisi dettagliata**: evidenze tecniche, tracking radar, modelli, qualità dati e verifica storica.

Obiettivi operativi principali:

- situazione corrente riferita a Giammoro;
- nowcasting locale **0–3 h** con priorità alle osservazioni;
- previsione oraria e sintesi Oggi/Domani;
- scenario deterministico multi-modello **3–48 h**;
- supporto ensemble **2–7+ giorni**;
- allerta ufficiale correttamente riferita alla zona;
- tracking radar multi-cella e multi-frame;
- rilevamento separato della semplice presenza di pioggia locale;
- verifica ex-post a 30/60/120 minuti;
- raccolta di metriche sufficienti per migliorare progressivamente precisione e richiamo senza aumentare falsi allarmi.

Attribuzione da mantenere:

**“Modello di analisi meteo creato da Salvatore Sciotto”**

---

## Stato attuale

### Repository e versioni operative

- Branch operativo: `main`.
- **Ultimo commit di codice funzionale intenzionale da considerare baseline**:
  - `9ed00f56dc97882546862409ff42f6abe89e833c`
  - messaggio: `Allinea home e verifica pioggia al backend`.
- Dopo quel commit il bot ha continuato ad avanzare `main` con soli file dati.
- HEAD osservato al momento di questo checkpoint:
  - `149161b065ddbd39aa594549b88a8cb5cd8499fd`.
- Il confronto `9ed00f5… → 149161b…` modifica soltanto:
  - `data.json`;
  - `events.json`;
  - `history.json`;
  - `verification.json`.
- Quindi il **codice valido corrente è ancora quello di `9ed00f5…`**, mentre `main` contiene dati più recenti.

### Validazione CI/CD

Il commit di codice `9ed00f5…` è stato validato dal workflow `Aggiorna Meteo Giammoro`, run **#1217**, concluso con successo:

- **128 test passati**;
- collector completato;
- nowcast v4 completato;
- home forecast completata;
- runtime quality completata;
- verifica eventi v2 completata;
- storico verifica completato;
- verifica presenza pioggia completata;
- preparazione sito completata;
- screenshot Radar-DPC acquisito;
- GitHub Pages pubblicata;
- persistenza dati su `main` riuscita.

L’ultimo ciclo operativo osservato prima del checkpoint è il run **#1233**, anch’esso concluso con `success`.

### Backup

Backup più recente creato prima delle prossime novità:

- branch: `backup/pre-novita-2026-10-24-1403`
- commit: `96d884de80a1a1c2f122c77f73186b0286d8a3c5`

Il branch fotografa integralmente progetto e dati prima delle modifiche future. Non spostarlo, riscriverlo o eliminarlo.

Backup storici da conservare:

- `backup/pre-modifiche-2026-10-19-0904`
- `backup/pre-modifiche-2026-10-16-0954`

### Snapshot meteo al checkpoint — dato volatile

Al ciclo delle **14:05 CEST del 24/10/2026**:

- collector: `ok`, nessun errore;
- stazione primaria MeteoGiammoro: `maintenance`, esclusa dall’analisi;
- nowcast: `Moderato (radar vicino)`;
- SRI: eco significativo nell’area vasta, con massimo entro 30 km circa 9,9 mm/h;
- track principale: nucleo a circa 37,6 km NW, moto ESE ~25,9 km/h, minima distanza proiettata ~13,5 km;
- `latest_change`: `Nucleo radar in avvicinamento verso Giammoro`, evento attivo con scadenza automatica;
- fulmini MTG-LI: nessun flash entro 30 km nel granulo recente;
- tendenza 3–48 h: pioggia probabile, 4/4 modelli bagnati, impatto modellistico moderato;
- allerta: **Gialla (oggi 24/10)** per rischio idrogeologico e temporali, validata con bollettino nazionale DPC.

Questi valori non sono configurazione: cambiano a ogni ciclo.

---

## Requisiti e vincoli confermati

### Integrità meteorologica e territoriale

1. Il riferimento deve essere sempre **Giammoro**.
2. Non rinominare mai una stazione vicina come “Giammoro”.
3. Le stazioni vicine servono come supporto/contesto e devono conservare nome e località reali.
4. Non creare una falsa “media Giammoro” usando stazioni circostanti.
5. Se un dato non esiste o non è affidabile, usare `null`, `unknown`, `unavailable` o testo equivalente; **non inventare**.
6. I massimi radar areali non devono essere descritti come accumuli puntuali su Giammoro.
7. Le allerte ufficiali hanno priorità su interpretazioni locali o modellistiche.
8. Una traiettoria radar non deve essere presentata come certa se l’associazione della cella è fragile.

### Stazione MeteoGiammoro

Stato corrente:

- `maintenance`;
- `excluded_from_analysis: true`.

Percorso obbligatorio di rientro:

`maintenance` → `test` visibile ma ancora esclusa → `online` solo dopo validazione.

Non anticipare il ritorno online.

### UX

Home semplice: **Meteo**.  
Sezione tecnica: **Analisi dettagliata**.

Ordine attuale confermato della home:

1. **Previsione per Giammoro**
2. **PROSSIME ORE**
3. **PIOGGIA E TEMPORALI**
4. **Allerta ufficiale**

La vecchia card combinata **OGGI E DOMANI** è rimossa dal markup pubblico perché sostituita dalla previsione completa.

Le due card sintetiche restano visibili e devono usare gli stessi segnali del backend, non logiche meteorologiche indipendenti.

### Costi e infrastruttura

- costo monetario: **zero**;
- hosting: GitHub Pages;
- elaborazione: GitHub Actions;
- fonti gratuite;
- nessun servizio a pagamento/trial senza richiesta esplicita;
- aggiornamento circa ogni 15 minuti, accettando piccole irregolarità dello scheduler.

---

## Decisioni progettuali principali e motivazioni

### 1. Osservazioni prima dei modelli nel 0–3 h

Nel brevissimo termine la priorità è:

1. Radar-DPC;
2. EUMETSAT MTG Lightning Imager;
3. osservazioni/stazioni affidabili;
4. modelli numerici come supporto.

Motivo: un rovescio locale reale deve prevalere su un modello che non lo risolve, mentre un singolo modello non deve generare allarmismo con radar asciutto.

### 2. Presenza di pioggia separata dall’impatto

La semplice domanda “sta piovendo / può piovere?” è separata da “quanto è significativo il fenomeno?”.

`local_precipitation` misura la **presenza**; `nowcast.level` e le regole di rischio descrivono l’**impatto/intensità**.

Questo evita che un piovasco debole venga trattato come “nessun fenomeno” solo perché non raggiunge soglie d’impatto.

### 3. Radar locale multi-raggio 1/3/5 km

Per ridurre i falsi negativi dovuti al singolo pixel:

- SRI e SRT1 vengono riletti su 1/3/5 km;
- sono conservati `point`, `max`, `mean`, `p90`;
- esiste una memoria locale di circa 180 minuti;
- lo stato è `active`, `recent` o `dry`.

I valori areali servono per riconoscere coerenza spaziale e persistenza, **non come pluviometro puntuale**.

### 4. `tracked_cell` separata da `hazard_cell`

Il track temporalmente coerente può essere diverso dalla cella più rilevante per Giammoro.

- `tracked_cell`: usata per continuità, velocità, direzione, ETA;
- `hazard_cell`: cella più rilevante localmente.

Motivo: non perdere la continuità temporale del track e, contemporaneamente, non ignorare una cella secondaria più vicina/pericolosa.

### 5. Qualità dati, affidabilità traiettoria e probabilità sono concetti distinti

Tre campi separati:

- `analysis_quality`: freschezza/disponibilità delle fonti;
- `trajectory_reliability`: robustezza geometrica del track;
- `predictive_confidence`: probabilità previsionale, che resta **non calibrata**.

Non trasformare `analysis_quality` in una percentuale di “probabilità di previsione corretta”.

Una traiettoria basata su soli **2 frame** è limitata a massimo **64/100, “Media”**.

Se `lightning.age_minutes` manca, il contributo qualità fulmini è **0**, non massimo.

### 6. Allerte ufficiali con validazione e normalizzazione temporale

La fonte regionale DRPC/CFD resta primaria per il dettaglio; il bollettino DPC nazionale viene usato per validare livello e zona.

Zona operativa:

**Nord-Orientale, versante tirrenico e isole Eolie**.

`runtime_quality.py` corregge anche etichette relative come “domani” dopo il cambio di giorno.

### 7. Verifica eventi significativa separata dalla verifica semplice della pioggia

Le due metriche non vanno mescolate:

- `local-event-v2`: eventi locali significativi;
- `local-precipitation-v1`: semplice presenza di pioggia.

La baseline storica `legacy-event-v1` resta visibile ma non viene sommata alla v2 perché usa una semantica differente.

### 8. Home coerente con il backend

Le card **PROSSIME ORE** e **PIOGGIA E TEMPORALI** sono state riallineate al backend.

- PROSSIME ORE riprende `home_summary.nowcast_simple`;
- PIOGGIA E TEMPORALI considera, in ordine, pioggia locale attiva, fulmini, pioggia recente, cella radar vicina e segnale modellistico 0–3 h.

Motivo: eliminare contraddizioni fra la previsione principale e le vecchie regole JavaScript.

### 9. Lifecycle di `latest_change`

- gli eventi radar di avvicinamento hanno `valid_until` e vengono chiusi se non riconfermati;
- i cambi generici 0–3 h vengono risolti quando il target annunciato non coincide più con il nowcast corrente.

Motivo: evitare che la home mostri per ore un aumento/riduzione ormai superato.

---

## Architettura e pipeline corrente

Pipeline effettiva del workflow principale:

```text
collector.py
  ↓
nowcast_v4.py
  ↓
analysis_quality_update.py
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
  ↓
site_prepare.py
  ↓
GitHub Pages
  ↓
persistenza data.json / history.json / verification.json / events.json su main
```

### Workflow

`.github/workflows/update-weather.yml`

- `workflow_dispatch`;
- cron ai minuti `7,22,37,52`;
- guardia freschezza: salta cicli non-push se i dati hanno meno di 10 minuti;
- Python 3.12;
- esegue l’intera suite pytest prima di acquisire nuovi dati;
- conserva `/tmp/data-previous.json`;
- riusa la cache Open-Meteo fra collector e home forecast;
- deploya Pages prima della persistenza Git dei JSON;
- persistenza con fetch/rebase/retry fino a 3 tentativi;
- concorrenza accodata, `cancel-in-progress: false`.

Esiste anche `.github/workflows/weather-heartbeat.yml`, auto-rilanciante, che chiede un aggiornamento e poi attende 15 minuti. Funziona, ma tenere un runner in `sleep 900` resta debito infrastrutturale da valutare in futuro.

---

## Componenti principali

### `collector.py`

Responsabilità:

- stazioni;
- Radar-DPC;
- modelli deterministici;
- ensemble;
- satellite/prodotti DPC;
- allerte regionali e nazionali;
- dati territoriali;
- `data.json` schema 2.1.

Modelli deterministici principali:

- ItaliaMeteo / ARPAE ICON-2I;
- DWD ICON;
- ECMWF IFS;
- NOAA GFS.

Ensemble:

- ECMWF ENS;
- ICON EPS;
- GEFS.

### `nowcast_v4.py`

Entry point attivo del nowcasting.

Aggiunge sopra la base v2:

- tracking multi-cella/multi-frame;
- `tracked_cell` e `hazard_cell` separate;
- scoring di rilevanza locale;
- quality guard del track;
- soppressione di ETA/proiezioni fragili;
- EUMETSAT MTG-LI;
- sanitizzazione di dati incoerenti;
- integrazione delle variazioni significative.

Non creare `nowcast_v5.py`/`v6.py` per nuove modifiche ordinarie: consolidare l’architettura esistente.

### `analysis_quality.py` / `analysis_quality_update.py`

Calcola:

- qualità dati;
- affidabilità traiettoria;
- stato della calibrazione previsionale.

`analysis_confidence` esiste solo come alias legacy deprecato della qualità dati.

Soglia minima attuale per iniziare a studiare una calibrazione probabilistica: **20 campioni evento**.

### `home_forecast_v2.py`

Entry point attivo della previsione home.

- modello base orario: ICON-2I quando disponibile;
- previsione oraria;
- Oggi/Domani;
- fallback dell’ultima previsione valida fino a 6 ore, marcato `stale`;
- consenso multi-modello conservato per l’analisi tecnica.

### `runtime_quality.py`

Responsabilità correnti:

- normalizzazione del giorno dell’allerta;
- chiusura `latest_change` obsoleti;
- raffinamento indicatori radar della home;
- radar locale 1/3/5 km;
- memoria della pioggia locale;
- separazione presenza pioggia / impatto;
- segnale modelli 0–3 h;
- `current_wet_models` ricavato dalla precipitazione corrente dei modelli.

Soglie correnti del segnale modellistico di presenza:

- `wet`: accumulo 0–3 h ≥ 0,2 mm;
- `notable`: accumulo 0–3 h ≥ 0,5 mm;
- modello corrente bagnato: precipitazione corrente ≥ 0,1 mm.

Non abbassare queste soglie senza prima valutare eventi reali e falsi allarmi.

### `verification_engine_v2.py`

Metrica eventi locali significativi, `local-event-v2`.

Evento osservato se almeno uno dei driver principali è presente, con dati freschi:

- cella radar significativa entro 15 km;
- `rain_1h >= 2 mm` quando disponibile;
- fulmini entro 20 km.

Esiste anche `nearby_signal` più debole per diagnostica/watch.

Orizzonti: 30, 60, 120 minuti.

Metriche principali:

- TP / TN / FP / FN;
- POD / event detection;
- precision;
- FAR;
- specificity;
- balanced accuracy;
- CSI;
- ETA e errore traiettoria quando valutabili.

L’accuracy globale è **secondaria** perché può essere dominata dai non-eventi.

### `verification_history.py`

Conserva metriche cumulative v2 indipendenti dalla rolling window di 300 risultati.

Baseline legacy separata:

- `legacy-event-v1`;
- commit sorgente `626b2f168212dc46d27f3fb03191a0b4174fb9d4`;
- 300 campioni;
- TP 14, TN 234, FP 9, FN 43;
- POD 24,6%; precision 60,9%; FAR 39,1%; CSI 21,2%.

Non sommare baseline v1 e v2.

### `precipitation_verification.py`

Metrica `local-precipitation-v1`, semantica `rain_presence_not_severity`.

Previsione positiva:

- 30 min: pioggia già attiva oppure almeno 2 modelli con precipitazione corrente;
- 60 min: pioggia già attiva oppure segnale 0–3 h forte/supportato o almeno 2 modelli `notable`;
- 120 min: pioggia già attiva oppure segnale 0–3 h `weak`/`supported`.

L’osservazione usa la storia radar multi-raggio persistita.

### `site_prepare.py`

Genera l’HTML realmente pubblicato.

- rimuove la vecchia card OGGI E DOMANI;
- conserva PROSSIME ORE / PIOGGIA E TEMPORALI;
- assegna `id="homeSummaryCards"`;
- inietta gli script UI;
- cattura in modo best-effort uno screenshot Radar-DPC ufficiale;
- se lo screenshot fallisce, il deploy continua con link alla piattaforma ufficiale.

Importante: `index.html` sorgente non coincide esattamente con l’HTML finale di Pages.

### `forecast_dashboard.js`

Frontend della previsione principale e delle due card sintetiche.

- inserisce **Previsione per Giammoro** prima di `homeSummaryCards`;
- usa lo stesso oggetto `data.json` già caricato, senza secondo fetch;
- PROSSIME ORE usa `home_summary.nowcast_simple`;
- PIOGGIA E TEMPORALI usa `local_precipitation`, MTG-LI, hazard radar e segnale modellistico;
- mostra indicatori Radar, Pioggia locale, Modelli 0–3 h, Traiettoria, Fulmini, Distanza;
- visualizza la verifica eventi privilegiando le metriche evento rispetto all’accuracy globale.

---

## Fonti dati attive

### Radar-DPC

Prodotti principali:

- `SRI` — intensità precipitazione;
- `VMI` — riflettività;
- `SRT1` — cumulata ultima ora;
- `CUM24` — cumulata 24 h;
- `TEMP` — temperatura interpolata rete termometrica;
- `IR10.8` / equivalente IR usato dal collector quando disponibile.

Nowcasting strutturato tipicamente su intorni 5/15/30 km; rilevamento pioggia locale aggiuntivo su 1/3/5 km.

### Fulminazioni

Fonte attiva:

**EUMETSAT MTG Lightning Imager L2 Lightning Flashes**.

Secret GitHub richiesti:

- `EUMETSAT_CONSUMER_KEY`
- `EUMETSAT_CONSUMER_SECRET`

Non esporli mai in client, JSON pubblico o log intenzionali.

DPC LTG/LAMPINET resta legacy/non usato: il productType necessario non è disponibile nella REST Radar-DPC v2 utilizzata dal progetto.

### Stazioni

Feed/aggregatore: Centro Meteorologico Siciliano.

Principio vincolante: il nome reale della stazione resta sempre visibile.

Stazioni supportate/configurate comprendono Pace del Mela / area Giammoro, San Filippo del Mela, Santa Lucia del Mela, Monforte San Giorgio, Barcellona, Messina e altre località circostanti.

Fallback in caso di feed indisponibile:

- conserva l’ultimo dato noto;
- lo marca come dato precedente / stato non corrente;
- lo esclude dall’analisi;
- `collector_status` diventa `degraded`.

### Allerte

- DRPC/CFD Sicilia: fonte regionale di dettaglio;
- DPC nazionale: cross-validation automatica.

---

## File e risorse rilevanti

| File | Ruolo |
|---|---|
| `collector.py` | acquisizione e prima analisi dati |
| `nowcast_v2.py` | tracking multi-cella/multi-frame di base |
| `nowcast_v4.py` | entry point nowcast corrente |
| `approaching_cells.py` | diagnostica celle secondarie/avvicinamento |
| `lightning_eumetsat.py` | MTG-LI |
| `quality_guard.py` | normalizzazione/guardie conservative |
| `analysis_quality.py` | qualità, traiettoria, calibrazione |
| `analysis_quality_update.py` | applicazione qualità al JSON |
| `home_forecast.py` | base previsione home |
| `home_forecast_v2.py` | entry point home corrente |
| `model_outlook.py` | outlook multi-modello |
| `runtime_quality.py` | pioggia locale, lifecycle, normalizzazioni |
| `verification_engine.py` | motore verifica base |
| `verification_engine_v2.py` | verifica eventi locale corrente |
| `verification_history.py` | metriche cumulative e baseline |
| `precipitation_verification.py` | verifica presenza pioggia |
| `index.html` | sorgente HTML |
| `forecast_dashboard.js` | UI previsione e sintesi home |
| `approaching_cells_ui.js` | UI celle |
| `analysis_quality_ui.js` | UI qualità |
| `verification_history_ui.js` | UI storico verifica |
| `radar_ui.js` | UI radar ufficiale |
| `site_prepare.py` | build dell’HTML pubblico |
| `data.json` | stato corrente e output principale |
| `history.json` | storico variazioni |
| `verification.json` | metriche ex-post |
| `events.json` | snapshot/eventi/pending e stato cumulativo |
| `config/stations.json` | territorio e stazioni |
| `config/overrides.json` | override configurativi |
| `requirements.txt` | dipendenze Python |
| `tests/` | suite regressione |
| `.github/workflows/update-weather.yml` | pipeline principale |
| `.github/workflows/weather-heartbeat.yml` | heartbeat auto-rilanciante |

---

## Versioni correnti da considerare valide

- `data.json.schema_version`: **2.1**
- `verification.json.schema_version`: **1.1**
- metrica eventi: **`local-event-v2`**
- metrica pioggia: **`local-precipitation-v1`**
- baseline legacy: **`legacy-event-v1`**, solo confronto storico
- Python workflow: **3.12**
- codice funzionale baseline: **`9ed00f56dc97882546862409ff42f6abe89e833c`**
- HEAD dati osservato al checkpoint: **`149161b065ddbd39aa594549b88a8cb5cd8499fd`**
- backup pre-novità: **`backup/pre-novita-2026-10-24-1403` → `96d884de80a1a1c2f122c77f73186b0286d8a3c5`**
- suite validata: **128 test** sul commit di codice corrente.

---

## Stato della verifica al checkpoint

Questi numeri sono snapshot e continueranno ad aumentare.

### `local-event-v2`

Rolling window 300 risultati:

- TP 1;
- TN 286;
- FP 5;
- FN 8;
- eventi osservati 9;
- POD 11,1%;
- precision 16,7%;
- FAR 83,3%;
- balanced accuracy 54,7%;
- CSI 7,1%.

Cumulativo v2:

- 554 campioni;
- 9 eventi;
- TP 1;
- FP 5;
- FN 8.

Interpretazione: il campione evento è ancora piccolo e le prestazioni su eventi reali non sono soddisfacenti. **Non usare l’accuracy globale ~98% come prova di buona previsione**, perché è dominata dai non-eventi.

### `local-precipitation-v1`

Al checkpoint:

- 475 campioni;
- 0 campioni con pioggia osservata;
- 14 falsi positivi complessivi;
- nessun POD valutabile.

La parte a 30 minuti è stata appena corretta per usare `current_wet_models`; i campioni precedenti non rappresentano pienamente questa nuova logica. Non fare backfill artificiale.

### Confidenza previsionale

`predictive_confidence` resta **Non calibrata**.

Soglia minima di studio: 20 eventi. Al checkpoint la v2 ne ha 9.

---

## Approcci scartati o da non riproporre

- Non creare `nowcast_v5.py`, `v6.py`, ecc. solo per aggiungere funzionalità: consolidare v4/v2 esistenti.
- Non usare stazioni vicine come se fossero la stazione di Giammoro.
- Non mediare arbitrariamente stazioni vicine per inventare un dato locale.
- Non mostrare massimi radar areali come accumuli puntuali.
- Non trattare `analysis_quality` o `trajectory_reliability` come probabilità meteorologica.
- Non fondere la baseline `legacy-event-v1` con `local-event-v2`.
- Non retrodatare il racconto manuale di un episodio di pioggia dentro la metrica automatica: se in futuro si volesse conservare un report umano, usare una provenienza separata `manual_report` non mischiata alle osservazioni automatiche.
- Non riportare LTG/LAMPINET come fonte attiva se la REST DPC utilizzata non lo espone.
- Non rendere il deploy dipendente dallo screenshot radar: deve restare best-effort.
- Non aumentare indiscriminatamente la sensibilità per ridurre i miss prima di avere più eventi reali verificati.

---

## Problemi noti e punti ancora incerti

### 1. Pochi eventi reali nella metrica v2

Solo 9 eventi cumulativi al checkpoint. Serve più campione prima di tuning aggressivo o calibrazione probabilistica.

### 2. Prestazioni evento ancora deboli

POD e CSI sono bassi e il FAR è alto. È il problema meteorologico principale da migliorare, ma va affrontato analizzando i singoli miss/false alarm, non abbassando semplicemente tutte le soglie.

### 3. Verifica pioggia ancora senza eventi osservati

`local-precipitation-v1` ha molti campioni asciutti ma nessun evento pioggia osservato nel suo periodo prospettico. Attendere episodi reali prima di giudicare recall/POD.

### 4. Semantica della finestra della verifica pioggia

Attualmente un orizzonte è considerato “pioggia osservata” se esiste un rilevamento fra l’istante di emissione e la finestra fino a `horizon + 15 min`.

Quindi la metrica misura in pratica **“ha piovuto entro quell’orizzonte”**, non “pioveva esattamente al minuto 30/60/120”.

Anche `observed_at_issue` rende positiva la previsione di più orizzonti se sta già piovendo. Questa scelta è plausibile ma va rivalutata prima di una calibrazione formale.

### 5. Classificazione qualità delle stazioni

Il feed corrente può contenere nomi come `(DRPC)` o `(LineaMeteo)` ma non sempre espone il campo rete in modo utilizzabile; alcune stazioni risultano quindi `source_quality: unknown` anche se online.

Prima di usarle maggiormente nell’analisi servono:

- mapping affidabile della rete;
- quality control automatico;
- controlli su pressione, temperatura, umidità, pioggia e salti anomali.

### 6. MeteoGiammoro ancora fuori servizio

Finché non passa attraverso test e validazione non deve influenzare l’analisi.

### 7. ETA e errore traiettoria ancora scarsamente popolati

Le metriche ETA/traiettoria possono restare `null` se non esistono track coerenti valutabili sullo stesso ID. Non inventare valori per riempire la metrica.

### 8. Overhead del radar locale

`runtime_quality.py` effettua richieste DPC aggiuntive SRI/SRT1 per ottenere statistiche 1/3/5 km. È ancora a costo zero, ma aggiunge traffico e dipendenza di rete; se in futuro si ottimizza, riusare i raster raw senza cambiare la semantica.

### 9. Heartbeat GitHub

`weather-heartbeat.yml` funziona ma occupa un runner con `sleep 900`. È un possibile punto di semplificazione futura, non una priorità meteorologica.

### 10. UI dedicata della metrica pioggia

La metrica `precipitation_presence` è presente nei JSON e nella pipeline, ma prima di aggiungere nuove visualizzazioni verificare se serve davvero una sezione dedicata nell’Analisi dettagliata. Evitare duplicazioni con la verifica eventi.

---

## Attività completate

- pipeline GitHub Actions + Pages stabile;
- aggiornamento ~15 min con heartbeat + cron backup;
- schema `data.json` 2.1;
- integrazione Radar-DPC;
- tracking multi-cella/multi-frame;
- separazione `tracked_cell` / `hazard_cell`;
- filtro qualità della traiettoria;
- integrazione EUMETSAT MTG-LI;
- allerta regionale + validazione nazionale;
- normalizzazione “oggi/domani” delle allerte;
- separazione qualità dati / traiettoria / probabilità;
- previsione home v2 con fallback stale;
- consenso multi-modello 3–48 h;
- verifica eventi v2 e metriche cumulative;
- baseline legacy separata;
- rilevamento pioggia locale 1/3/5 km con memoria;
- verifica prospettica presenza pioggia 30/60/120 min;
- `current_wet_models` per il 30 min;
- lifecycle dei `latest_change`;
- fix qualità fulmini con timestamp assente;
- cap di affidabilità per traiettorie a due frame;
- card PROSSIME ORE e PIOGGIA E TEMPORALI riallineate al backend;
- ordine home aggiornato con Previsione per Giammoro sopra le due card sintetiche;
- screenshot Radar-DPC best-effort con fallback;
- suite CI corrente: 128 test passati;
- backup completo pre-novità del 24/10 creato.

---

## Attività ancora aperte

1. Raccogliere eventi reali sufficienti per `local-event-v2`.
2. Analizzare singolarmente FN e FP per orizzonte 30/60/120.
3. Raccogliere primi veri eventi di `local-precipitation-v1` dopo l’introduzione di `current_wet_models`.
4. Valutare una semantica più rigorosa della verifica pioggia per ogni orizzonte.
5. Classificare meglio le reti delle stazioni e introdurre quality control.
6. Riportare MeteoGiammoro prima in `test`, poi eventualmente `online` solo dopo confronto e validazione.
7. Valutare se esporre in UI la verifica pioggia separata.
8. Ridurre gradualmente il debito tecnico fra `nowcast_engine.py`, `nowcast_v2.py`, `nowcast_v4.py` e fra `verification_engine.py` / `verification_engine_v2.py`, senza creare nuove versioni parallele.
9. Valutare in futuro una semplificazione del heartbeat GitHub.

---

## Prossimi passi consigliati

### Priorità 1 — non toccare subito le soglie

Lasciare accumulare casi reali e usare la verifica per capire **perché** nascono FN/FP.

Per ogni nuovo evento reale, confrontare:

- SRI/VMI 1/3/5/15/30 km;
- cella più vicina e hazard score;
- direzione/velocità/closest approach;
- fulmini;
- precipitazione corrente dei 4 modelli;
- accumulo 0–3 h;
- stazioni vicine, solo come contesto attribuito correttamente.

### Priorità 2 — quality control stazioni

Definire mapping rete e controlli fisici prima di aumentare il loro peso.

### Priorità 3 — calibrazione

Solo quando esiste un campione evento sufficiente, studiare una probabilità reale per orizzonte. Fino ad allora mantenere `predictive_confidence = Non calibrata`.

### Priorità 4 — consolidamento

Quando si aggiungono nuove funzioni, preferire modifiche ai moduli correnti con test di regressione invece di introdurre nuove generazioni `v5/v6`.

---

## Istruzioni operative importanti per continuare il progetto

1. **Prima di ogni modifica, rileggere il HEAD di `main`**: il bot può aver aggiunto commit dati dopo l’ultimo messaggio della chat.
2. Distinguere sempre:
   - commit di codice intenzionale;
   - commit automatici dati.
3. Non riscrivere o spostare i branch di backup.
4. Per modifiche importanti creare un nuovo backup prima di procedere, se richiesto o se il rischio è alto.
5. Eseguire/aggiornare test per ogni cambio di semantica meteorologica o UI.
6. Dopo una modifica di codice controllare il workflow reale fino a:
   - test;
   - collector;
   - nowcast;
   - verifica;
   - Pages;
   - persistenza dati.
7. Non dichiarare una funzione “in produzione” finché il relativo workflow non è riuscito.
8. Non inventare dati mancanti nei test o nella UI.
9. Conservare sempre la frase di attribuzione del modello.
10. Le modifiche al frontend devono considerare che `site_prepare.py` trasforma `index.html` prima della pubblicazione.
11. Il sito pubblico deve continuare a usare un solo caricamento di `data.json` per la dashboard principale.
12. Le fonti ufficiali e la prudenza semantica hanno priorità sull’aspetto “più spettacolare” della previsione.
13. Se una nuova funzione cambia il significato di una metrica, creare una nuova `metric_version` o una migrazione esplicita; non mischiare serie incompatibili.
14. Non usare report umani come ground truth automatico senza provenienza distinta.

---

## Prompt per la nuova chat

Usa `PROJECT_CONTEXT.md` del repository `sasciotto/meteo-giammoro` come fonte principale e autosufficiente di contesto per continuare il progetto Meteo Giammoro. Prima di fare modifiche, rileggi il `main` corrente e gli ultimi workflow perché il bot aggiorna continuamente i JSON. Mantieni tutti i vincoli del checkpoint: costo zero, Giammoro come riferimento, nessun dato inventato, stazioni vicine mai rinominate, MeteoGiammoro esclusa finché non validata, allerte ufficiali prioritarie, qualità/traiettoria/probabilità separate, baseline di verifica non mischiate e nessuna nuova v5/v6 senza necessità. Quando propongo una novità, integrala nell’architettura esistente, aggiungi test di regressione e verifica il deploy reale prima di considerarla conclusa.
