# PROJECT_CONTEXT.md — Meteo Giammoro

Checkpoint operativo: 18 ottobre 2026, ~14:56 CEST (Europe/Rome)
Repository: sasciotto/meteo-giammoro
Dashboard pubblica: https://sasciotto.github.io/meteo-giammoro/
Riferimento territoriale: Giammoro, Pace del Mela (ME), circa 38.2018 N, 15.31816 E
Schema dati corrente: data.json schema 2.1

> Questo documento è la fonte di contesto operativa da usare per riprendere il progetto.  
> `README.md` nel repository è attualmente parzialmente obsoleto e non descrive tutte le funzioni oggi attive.

---

## Obiettivo generale

Realizzare e mantenere una dashboard meteorologica pubblica, gratuita e automatica per Giammoro, capace di combinare osservazioni, radar, fulminazioni, modelli numerici, allerte ufficiali e verifica ex-post per fornire:

- situazione corrente riferita a Giammoro;
- nowcasting 0–3 h con priorità alle osservazioni;
- previsione breve/oraria e oggi-domani;
- scenario multi-modello 3–48 h;
- quadro 2–7+ giorni con modelli/ensemble;
- allerta ufficiale contestualizzata per l’area;
- confidenza dell’analisi;
- verifica storica delle previsioni;
- notifiche solo in caso di cambiamenti meteorologicamente significativi.

La dashboard è presentata come:

**“Modello di analisi meteo creato da Salvatore Sciotto”**

Questa attribuzione va mantenuta.

---

## Stato attuale

Il progetto è operativo su GitHub Pages e aggiornato automaticamente.

### Stato repository

- Branch operativo: `main`.
- Ultimo commit di codice intenzionale da considerare baseline:
  - `49080c0bb1896aba2a3a5c4c7b72b351c8604a7e`
  - messaggio: `Rende la dashboard più resiliente e coerente`
- `main` avanza poi continuamente tramite commit automatici del bot che aggiornano `data.json`, `history.json`, `verification.json` ed `events.json`.
- HEAD osservato durante questo checkpoint:
  - `11b7a508d8e2aab78b6750fa8385d1385269ff59`
  - commit automatico dati del 18/10/2026.
- Ultimo ciclo operativo verificato:
  - workflow `Aggiorna Meteo Giammoro`
  - run #599
  - conclusione `success`.
- Backup storico da NON eliminare o rinominare senza richiesta esplicita:
  - branch `backup/pre-modifiche-2026-10-16-0954`
  - commit `2bb886bf38d6f01eef7c241caa75cedc3ed78b3e`

### Snapshot dati al checkpoint

Ultimo `data.json` osservato:

- aggiornamento: 18/10/2026 14:46 CEST;
- `collector_status`: `ok`;
- nessun errore collector;
- stazione primaria MeteoGiammoro: `maintenance`, esclusa dall’analisi;
- nowcast: Basso (radar);
- rischio 3–48 h: Basso–moderato;
- allerta: Gialla (oggi 18/10) per rischi idrogeologico e temporali, validata tramite bollettino nazionale DPC;
- pioggia radar 1 h / 24 h: 0 mm;
- EUMETSAT MTG-LI attivo;
- trend pressione modellistico attivo.

Questi valori meteo sono uno snapshot e cambiano a ogni ciclo: non trattarli come configurazione permanente.

---

## Requisiti e vincoli confermati

### Territorio e fonti

1. Il riferimento deve essere sempre Giammoro.
2. Le stazioni vicine sono solo supporto/validazione e devono mantenere la propria identità geografica.
3. Non rinominare una stazione vicina come “Giammoro” e non creare una falsa media locale.
4. La stazione MeteoGiammoro è attualmente guasta/in manutenzione:
   - stato corrente: `maintenance`;
   - esclusa dai calcoli;
   - percorso di rientro previsto: `maintenance` → `test` (visibile ma ancora esclusa) → `online` dopo validazione.
5. Se un dato non è disponibile, è preferibile mostrare `null`/“non disponibile” piuttosto che inventare o interpolare senza dichiararlo.

### Prodotto e UX

6. Modalità semplice: “Meteo”.
7. Modalità tecnica: “Analisi dettagliata”.
8. La home deve restare semplice e leggibile.
9. Nessuna duplicazione della previsione “Oggi e domani”.
10. Struttura preferita della home:
    - Adesso a Giammoro;
    - Prossime ore;
    - Pioggia e temporali;
    - Previsione per Giammoro:
      - fasce orarie;
      - Oggi;
      - Domani;
      - consenso multi-modello 3–48 h;
    - Allerta ufficiale.
11. Non mostrare condizioni del cielo dedotte se i dati necessari non esistono.
12. Se la previsione modellistica fallisce temporaneamente, usare l’ultima previsione valida solo se chiaramente marcata come “Dato precedente”.
13. Le allerte ufficiali devono prevalere su qualsiasi interpretazione locale e devono essere presentate con prudenza se la validazione automatica non è sicura.

### Costi e infrastruttura

14. Il progetto deve restare a costo monetario zero.
15. Preferire GitHub Actions/GitHub Pages e fonti gratuite.
16. È accettabile una cadenza non perfettamente regolare se questo migliora affidabilità e mantiene costo zero.
17. Non introdurre servizi a pagamento o trial che rischiano di diventare a pagamento senza consenso esplicito.

### Notifiche

18. Notificare solo variazioni meteorologicamente significative.
19. Non generare notifiche ripetitive quando nulla cambia.
20. È stata creata anche una automazione ChatGPT esterna al repository, `Giammoro Meteo Watch`, configurata come condition-watch orario. Non è parte della pipeline GitHub e non va confusa con l’heartbeat del progetto.

---

## Approccio meteorologico adottato

### 0–3 ore

Priorità a:

1. Radar-DPC;
2. fulminazioni EUMETSAT MTG Lightning Imager;
3. osservazioni/stazioni affidabili;
4. modelli sul punto come supporto.

Il nowcasting non deve diventare modellocentrico quando sono disponibili osservazioni recenti.

### 3–48 ore

Confronto deterministico tra:

- ItaliaMeteo / ARPAE ICON-2I;
- DWD ICON;
- ECMWF IFS;
- NOAA GFS.

La home utilizza ICON-2I come base oraria principale, ma mostra separatamente un consenso multi-modello 3–48 h con:

- numero modelli che prevedono almeno 0,5 mm;
- minimo/massimo precipitazione;
- mediana;
- livello di accordo/dispersione.

### 2–7+ giorni

Sono previsti/collegati ensemble:

- ECMWF ENS;
- ICON EPS;
- GEFS.

Usarli per spread/incertezza, non come singola previsione deterministica.

### Effetti locali da considerare

Giammoro è un’area costiera della Valle del Mela. L’analisi deve poter tenere conto, quando utile, di:

- costa;
- orografia di Santa Lucia/Monforte;
- differenze rispetto a Milazzo;
- Stretto di Messina;
- convergenze locali;
- vento/outflow;
- CAPE e instabilità.

---

## Fonti dati attive

### Stazioni

Il collector usa il database live del Centro Meteorologico Siciliano come aggregatore e conserva la rete originaria.

Aree/stazioni configurate come supporto:

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

Reti possibili: DRPC/Protezione Civile, SIAS, LineaMeteo, Wunderground e altre, con qualità classificata.

### Radar e satellite DPC

Prodotti usati:

- SRI — intensità di pioggia;
- VMI — riflettività massima;
- SRT1 — cumulata ultima ora;
- CUM24 — cumulata 24 h;
- TEMP — temperatura interpolata rete termometrica;
- IR_108 — satellite infrarosso.

Statistiche locali calcolate in intorni 5/15/30 km quando applicabile.

### Fulminazioni

Fonte attiva:

**EUMETSAT MTG Lightning Imager L2 Lightning Flashes**

Credenziali GitHub Secrets:

- `EUMETSAT_CONSUMER_KEY`
- `EUMETSAT_CONSUMER_SECRET`

Le credenziali non devono mai finire nel browser o nei file pubblici.

### Allerte

Fonti:

- CFD/DRPC Sicilia — avviso regionale/PDF;
- Dipartimento Protezione Civile nazionale — bollettino di criticità/allerta per cross-validation.

Zona DPC usata:

**Nord-Orientale, versante tirrenico e isole Eolie**

L’avviso regionale resta fonte di dettaglio; il bollettino nazionale viene usato per validare automaticamente il livello quando possibile.

---

## Architettura corrente

Pipeline attiva del workflow principale:

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

### collector.py

Responsabilità principali:

- acquisizione stazioni;
- modelli deterministici;
- ensemble;
- radar DPC;
- satellite;
- allerte;
- prima valutazione territoriale;
- `data.json` e storico di base.

`data.json` usa schema 2.1.

### Nowcasting

La catena è stratificata:

- `nowcast_engine.py` — base/legacy;
- `nowcast_v2.py` — tracking multi-cella/multi-frame;
- `nowcast_v4.py` — wrapper attivo e corrente.

`nowcast_v4.py` aggiunge:

- separazione tra `tracked_cell` e `hazard_cell`;
- scoring di rilevanza locale;
- controllo qualità del tracking;
- penalizzazione della confidenza se il track è incoerente;
- EUMETSAT MTG-LI;
- quality guard;
- trend pressione;
- sanitizzazione dew point;
- testi runtime aggiornati.

### Tracking radar

Principi correnti:

- una cella può essere mantenuta temporalmente come `tracked_cell`;
- la cella più pericolosa/localmente rilevante può essere diversa e viene esposta come `hazard_cell`;
- ETA e traiettoria appartengono al track temporale, non automaticamente all’hazard locale;
- associazioni con velocità implicita/errore/residuo sospetti vengono declassate;
- se l’associazione è sospetta, ETA e closest approach vengono rimossi;
- `track_quality` può essere `good`, `degraded`, `suspect`, `unavailable`.

### Confidenza nowcasting

La confidenza usa:

- freschezza radar;
- rilevamento cella;
- tracking;
- cross-check radar;
- stazioni;
- modelli;
- fulminazioni;
- penalità qualità tracking.

Non interpretare il punteggio come probabilità meteorologica calibrata.

### quality_guard.py

Funzioni principali:

- evita di presentare come certa un’allerta regionale euristica non validata;
- conserva eventuale livello come `regional_candidate`;
- ripulisce validità PDF contaminate;
- sopprime falsi cambi `Da verificare → <colore>`;
- pulisce testi legacy sui fulmini;
- mantiene storico pressione fino a circa 6 h;
- calcola Δ1 h e Δ3 h;
- dichiara esplicitamente che il trend di pressione è modellistico sul punto, non barometro locale.

### Home/previsione

`home_forecast.py` è il motore base.

Entry point attivo: `home_forecast_v2.py`.

Comportamenti v2:

- non deduce “sereno/poco nuvoloso” se la copertura nuvolosa manca;
- produce `home_summary.current`;
- produce previsione oraria;
- produce Oggi/Domani;
- aggiunge consenso multi-modello;
- se il modello home fallisce:
  - `collector_status` diventa `degraded`;
  - tenta fallback all’ultima `home_summary` valida;
  - massimo fallback: 360 minuti / 6 h;
  - marca `stale: true`;
  - mostra età e motivo del dato precedente.

Il workflow riusa la cache Open-Meteo generata dal collector per evitare una seconda chiamata quando possibile.

### runtime_quality.py

Normalizza testi runtime relativi alle date.

Caso principale:

- un bollettino emesso il 17 che dice “domani” per il 18 non deve continuare a mostrare “domani” dopo la mezzanotte del 18;
- viene trasformato, per esempio, in `Gialla (oggi 18/10)`.

### Frontend

File sorgente:

- `index.html`
- `forecast_dashboard.js`

Importante: `index.html` nel repository non coincide esattamente con l’HTML pubblicato.

Durante il deploy, `site_prepare.py`:

- rimuove dal markup pubblico la vecchia card combinata OGGI E DOMANI;
- converte la griglia a due card;
- fa usare alla home `data.home_summary.current` quando disponibile;
- inserisce `forecast_dashboard.js` prima dello script principale;
- collega `window.renderForecastDashboard(d)` al medesimo oggetto `data` già caricato.

Quindi sulla pagina pubblica:

- `data.json` viene fetchato una sola volta per ciclo frontend;
- `forecast_dashboard.js` non effettua un secondo fetch;
- espone `window.renderForecastDashboard`;
- mostra fallback “Previsione temporaneamente non disponibile” se necessario;
- mostra badge/testo “Dato precedente” se viene servito il fallback stale.

### Verifica ex-post

File:

- `verification_engine.py` — base;
- `verification_engine_v2.py` — adattatore attivo.

Orizzonti:

- 30 min;
- 60 min;
- 120 min.

La v2 separa `hazard_cell` dal track radar e aggiunge metriche evento/non-evento:

- TP;
- TN;
- FP;
- FN;
- POD/event detection;
- precision;
- false alarm ratio;
- specificity;
- balanced accuracy;
- CSI.

Lo storico mantiene ancora `accuracy_percent` per compatibilità, ma non deve essere usato come metrica principale di qualità degli eventi.

Snapshot verifica al checkpoint:

- 300 risultati valutabili;
- 300 corretti;
- accuracy globale 100%;
- 0 campioni evento;
- 300 campioni non-evento;
- 0 campioni ETA;
- 0 campioni traiettoria.

Conclusione: il 100% attuale dimostra soprattutto corretta classificazione di “nessun evento”; non dimostra ancora capacità predittiva sugli eventi.

---

## Automazione, scheduling e deploy

### Workflow principale

`.github/workflows/update-weather.yml`

Trigger:

- `workflow_dispatch`;
- push di file di codice/config;
- cron backup:
  - `7,22,37,52 * * * *`.

Freshness guard:

- se `data.json` ha meno di 10 minuti, un trigger non-push può evitare un ciclo duplicato.

Ordine rilevante:

1. test;
2. snapshot ciclo precedente;
3. collector + cache modelli;
4. nowcast;
5. home forecast;
6. runtime quality;
7. verifica;
8. preparazione `_site`;
9. deploy Pages;
10. persistenza JSON su `main`.

Il deploy Pages avviene prima della persistenza dati su `main`, così un eventuale conflitto Git non rende la dashboard pubblica obsoleta.

La persistenza dati usa fetch/rebase/retry fino a 3 tentativi.

### Heartbeat

`.github/workflows/weather-heartbeat.yml`

Sistema self-relaying:

1. dispatch di `update-weather.yml`;
2. attesa 15 minuti;
3. dispatch del proprio workflow;
4. retry in caso di errori.

Il cron del workflow principale resta backup opportunistico.

Questa soluzione è stata scelta per rimanere a costo zero e ridurre la dipendenza dall’affidabilità del solo scheduler GitHub.

---

## File rilevanti

### Core

- `collector.py` — acquisizione e regole deterministiche principali.
- `nowcast_engine.py` — base nowcast legacy.
- `nowcast_v2.py` — tracking multi-cella/multi-frame e logica legacy lightning.
- `nowcast_v4.py` — entry point nowcast attivo.
- `lightning_eumetsat.py` — integrazione EUMETSAT MTG-LI.
- `quality_guard.py` — protezioni output, allerta, trend pressione.
- `home_forecast.py` — motore home base.
- `home_forecast_v2.py` — entry point home attivo.
- `runtime_quality.py` — normalizzazioni runtime/date.
- `verification_engine.py` — verifica base.
- `verification_engine_v2.py` — verifica attiva event-sensitive.
- `site_prepare.py` — trasforma `index.html` nel markup realmente pubblicato.

### Frontend

- `index.html` — sorgente dashboard, modalità Meteo/Analisi dettagliata.
- `forecast_dashboard.js` — modulo previsione dettagliata, senza fetch autonomo.

### Config

- `config/stations.json` — coordinate, timezone, stazioni/gruppi.
- `config/overrides.json` — override manuali temporanei; non lasciare livelli allerta fissi.

### Stato persistente

- `data.json` — stato corrente.
- `history.json` — cambiamenti significativi.
- `verification.json` — snapshot e risultati verifica.
- `events.json` — eventi archiviati.

### CI/CD

- `.github/workflows/update-weather.yml`
- `.github/workflows/weather-heartbeat.yml`

### Test

Suite corrente include almeno:

- `test_collector.py`
- `test_home_forecast.py`
- `test_home_forecast_v2.py`
- `test_lightning_eumetsat.py`
- `test_nowcast_engine.py`
- `test_nowcast_v2.py`
- `test_nowcast_v4.py`
- `test_quality_guard.py`
- `test_runtime_quality.py`
- `test_site_prepare.py`
- `test_verification_engine.py`
- `test_verification_engine_v2.py`

Eseguire sempre:

```bash
python -m pytest -q
```

prima di considerare valida una modifica.

---

## Decisioni importanti e motivazioni

### GitHub Pages + Actions

Scelta per:

- costo zero;
- repository pubblico;
- deploy riproducibile;
- nessun server da mantenere.

### EUMETSAT MTG-LI per i fulmini

Sono stati tentati approcci DPC LTG/LAMPINET REST/WMS, ma il prodotto non è disponibile in modo sufficientemente stabile/strutturato negli endpoint usati.

Decisione corrente:

- EUMETSAT MTG-LI è la fonte automatica per le fulminazioni;
- non riaprire l’approccio LTG/LAMPINET come prima scelta senza nuove evidenze/API.

### Nessun falso dato locale

Le stazioni circostanti non vengono mediate come se fossero Giammoro.

Motivo: evitare un numero apparentemente locale ma meteorologicamente/fisicamente non rappresentativo.

### tracked_cell ≠ hazard_cell

Decisione presa per evitare che una cella mantenuta per continuità temporale venga automaticamente presentata come la minaccia principale per Giammoro.

### Quality guard sulle allerte

Un colore estratto euristicamente dal PDF regionale non viene pubblicato come certo se il cross-check nazionale fallisce.

### Consenso multi-modello separato dalla base oraria

ICON-2I resta pratico per la previsione oraria, ma non deve essere confuso con “consenso” quando ECMWF/GFS/ICON divergono.

### Fallback stale della previsione

Un timeout Open-Meteo non deve cancellare immediatamente una previsione utile.

Decisione:

- mantenere ultima previsione valida fino a 6 h;
- etichettarla esplicitamente;
- passare collector a `degraded`.

### Un solo fetch nel browser

La previsione non deve fare un fetch separato da quello della dashboard principale.

Motivo:

- evitare richieste inutili;
- evitare per pochi istanti dati di cicli diversi nella stessa pagina.

---

## Approcci scartati / da non riproporre senza motivo

### Render / scheduler esterno

Valutato e poi scartato.

Motivi:

- richiesta esplicita di costo zero;
- Render non era collegato/configurato.

### cron-job.org

Non è mai stato configurato.

Non dichiararlo attivo.

### DPC LTG/LAMPINET come fonte lightning automatica principale

Tentativi REST/WMS non hanno prodotto una pipeline affidabile.

Fonte corrente: EUMETSAT MTG-LI.

### Fidarsi del solo cron GitHub

Il cron GitHub è risultato intermittente.

Soluzione corrente:

- heartbeat self-relaying;
- cron come backup.

### Accuracy globale come “precisione del modello”

Da non usare come indicatore principale: il dataset corrente è dominato dai non-eventi.

---

## Problemi noti e punti ancora incerti

### 1. README.md è obsoleto

Attualmente contiene informazioni non più vere, tra cui:

- fulminazioni non automatiche;
- traiettoria non automatica;
- workflow ogni 30 minuti;
- vecchio modello di deploy.

Da aggiornare.

Il nuovo `PROJECT_CONTEXT.md` deve avere priorità fino all’aggiornamento del README.

### 2. index.html sorgente contiene ancora elementi legacy

La card OGGI E DOMANI e parte delle vecchie funzioni frontend esistono nel file sorgente.

`site_prepare.py` le modifica/rimuove nell’artifact pubblicato.

La pagina pubblica è corretta, ma questa architettura crea debito tecnico: una futura pulizia dovrebbe rendere `index.html` già coerente senza patch di deploy.

### 3. Testi legacy LTG/LAMPINET in nowcast_v2.py

`nowcast_v2.py` conserva ancora descrizioni/nomi LTG/LAMPINET, incluso `significant_lightning_change()`, mentre v4 passa dati EUMETSAT.

La maggior parte dei testi pubblici viene corretta da v4/quality guard, ma un nuovo evento elettrico significativo può ancora generare testo legacy.

Correzione consigliata: rendere `significant_lightning_change()` source-agnostic o EUMETSAT-specific.

### 4. Verifica eventi non ancora significativa

Al checkpoint:

- 0 event samples;
- ETA samples = 0;
- trajectory samples = 0.

Non è ancora possibile valutare realmente POD/CSI/precision/ETA.

Serve raccogliere eventi reali.

### 5. UI tecnica non valorizza ancora bene le nuove metriche evento

`verification_engine_v2.py` produce metriche corrette, ma la sezione dettagliata della pagina conserva ancora molta enfasi su accuracy globale.

Da fare: mostrare esplicitamente POD, FAR, CSI, balanced accuracy e numero di event samples, relegando accuracy globale a dato secondario.

### 6. Fallback stale da rifinire

`home_forecast_v2.py` copia l’ultima previsione valida fino a 6 h.

Da verificare/migliorare:

- eliminare ore ormai passate dal blocco hourly;
- gestire correttamente cambio data/mezzanotte;
- ricalcolare etichette Oggi/Domani se il fallback attraversa il giorno successivo.

### 7. “Ultimo cambiamento significativo” può essere storico rispetto allo stato corrente

È possibile che `latest_change` descriva un aumento precedente mentre il nowcast corrente è già tornato basso.

Non è necessariamente un bug, ma può confondere.

Possibili miglioramenti:

- mostrare chiaramente l’età del cambiamento;
- registrare anche downgrade significativi;
- oppure separare “ultimo evento storico” da “cambiamento ancora attivo”.

### 8. Parser allerta regionale resta fragile

Il cross-check DPC nazionale rende l’output pubblico prudente, ma il parsing diretto del PDF regionale non è ancora robusto per tutte le impaginazioni.

Se si migliora il parser:

- analizzare la cella esatta della zona A;
- distinguere oggi/domani;
- usare fixture reali;
- per analizzare PDF via strumenti web usare screenshot delle pagine, non solo testo estratto.

### 9. MeteoGiammoro ancora fuori servizio

Rientro da gestire solo dopo test/validazione.

Non riattivarla automaticamente come fonte primaria.

---

## Attività completate

- Dashboard pubblica GitHub Pages.
- Collector multi-sorgente.
- Stazioni di supporto con provenienza preservata.
- Radar-DPC 5/15/30 km.
- Tracking multi-cella e multi-frame.
- Separazione `tracked_cell` / `hazard_cell`.
- Quality score del tracking.
- Penalizzazione confidenza su track dubbio.
- EUMETSAT MTG-LI integrato.
- Dew point protetto da mix incoerente di fonti.
- Trend pressione 1 h / 3 h con storico breve.
- Allerte DRPC + validazione DPC nazionale.
- Soppressione falso loop `Da verificare → Verde`.
- Normalizzazione oggi/domani rispetto alla data effettiva.
- Previsione oraria e Oggi/Domani.
- Consenso multi-modello 3–48 h.
- Fallback previsione precedente su timeout.
- Collector `degraded` se previsione home fallisce.
- Eliminazione duplicazione Oggi/Domani nella pagina pubblica.
- Unificazione fetch frontend.
- Verifica ex-post 30/60/120.
- Metriche evento/non-evento.
- Heartbeat self-relaying.
- Cron GitHub di backup.
- Persistenza con rebase/retry.
- Test automatici nel workflow.
- Backup branch storico.

---

## Attività ancora aperte

Priorità consigliata:

1. Aggiornare `README.md` all’architettura reale e rimandare a `PROJECT_CONTEXT.md`.
2. Correggere definitivamente i testi LTG/LAMPINET legacy in `nowcast_v2.py`.
3. Portare le metriche evento nella UI tecnica e de-enfatizzare accuracy globale.
4. Rifinire il fallback stale attraversando ore/data.
5. Ridurre debito frontend:
   - rimuovere realmente dal sorgente `index.html` la card legacy;
   - eliminare le vecchie inferenze JS ormai sostituite dal backend;
   - ridurre la necessità di patch in `site_prepare.py`.
6. Migliorare parser allerta regionale con fixture PDF reali.
7. Attendere/raccogliere eventi reali per validare:
   - POD;
   - CSI;
   - FAR;
   - precision;
   - ETA;
   - traiettoria.
8. Monitorare stabilità dell’heartbeat e dei timeout Open-Meteo.
9. Quando MeteoGiammoro torna disponibile, creare una fase di validazione `test` prima di `online`.

---

## Prossimi passi consigliati

Il prossimo intervento dovrebbe essere soprattutto di consolidamento, non di aggiunta fonti.

### A. Pulizia documentazione

- aggiornare `README.md`;
- aggiungere/linkare `PROJECT_CONTEXT.md`;
- descrivere chiaramente i wrapper attivi (v4, v2) e quali file sono base/legacy.

### B. Pulizia lightning legacy

In `nowcast_v2.py`:

- non usare più “LTG/LAMPINET” nei testi se il provider reale è EUMETSAT;
- fare passare provider/source esplicito a `significant_lightning_change`;
- aggiungere test che simulino aumento flash EUMETSAT.

### C. UI verifica

In Analisi dettagliata mostrare:

- event samples;
- TP / FP / FN;
- POD;
- FAR;
- CSI;
- balanced accuracy;
- ETA samples;
- trajectory samples.

Mostrare accuracy globale soltanto come metrica secondaria.

### D. Hardening fallback previsione

Quando `home_summary.stale == true`:

- filtra hourly rispetto all’ora corrente;
- correggi today/tomorrow rispetto alla data corrente;
- se non rimane un orizzonte utile, passa a “temporaneamente non disponibile”.

### E. Semplificazione frontend

Obiettivo di medio periodo:

- rendere `index.html` il più vicino possibile all’HTML finale;
- usare `site_prepare.py` soltanto per composizione minima, non per correggere markup/logic legacy.

---

## Istruzioni operative importanti

### Prima di modificare il repository

1. Fetchare sempre la HEAD attuale di `main`.
2. Ricordare che il bot può fare commit dati ogni ~15 minuti.
3. Non usare una SHA vecchia per scritture multi-file senza riallineamento.
4. Non fare force push.
5. Se si crea un commit multi-file, basarlo sulla HEAD più recente.
6. Non toccare il branch backup senza richiesta esplicita.

### Dopo ogni modifica

1. Eseguire/attendere `python -m pytest -q`.
2. Verificare il workflow GitHub Actions reale.
3. Verificare:
   - collector;
   - nowcast;
   - home forecast;
   - runtime quality;
   - verifica;
   - preparazione sito;
   - upload/deploy Pages;
   - persistenza dati.
4. Controllare il `data.json` prodotto, non solo l’esito dei test.
5. Per verificare la pagina appena pubblicata, preferire l’artifact Pages/workflow se il crawler web pubblico mostra una cache vecchia.

### Scritture GitHub

Il repository cambia continuamente per commit del bot.

Per modifiche multi-file:

- preferire commit atomici con tree/commit/ref quando disponibile;
- usare lease/controllo della HEAD;
- se `main` avanza, ricostruire il commit sulla nuova HEAD;
- non sovrascrivere commit dati recenti.

### PDF/allerta

Se si analizza un PDF ufficiale:

- non affidarsi solo a regex sul testo;
- verificare layout/tabella;
- con strumenti web usare screenshot delle pagine rilevanti;
- distinguere data del bollettino da termini relativi “oggi/domani”.

### Sicurezza

- nessuna credenziale nel frontend;
- EUMETSAT solo tramite GitHub Secrets;
- non pubblicare token/API secret;
- gli override manuali devono essere temporanei e tracciabili.

### Stile di lavoro desiderato

- modifiche concrete, non solo proposte;
- domande di chiarimento solo se indispensabili;
- aggiornamenti brevi durante lavori lunghi;
- verificare l’effetto reale dopo il deploy;
- mantenere la dashboard semplice in modalità Meteo e tecnica in Analisi dettagliata.

---

## Prompt per la nuova chat

Sto continuando il progetto Meteo Giammoro (`sasciotto/meteo-giammoro`). Usa il file `PROJECT_CONTEXT.md` come fonte principale e più aggiornata di contesto. Prima di modificare qualcosa, verifica la HEAD corrente di `main` perché il bot aggiorna automaticamente i dati ogni ~15 minuti. Mantieni Giammoro come unico riferimento territoriale, costo zero, modalità “Meteo” semplice e “Analisi dettagliata” tecnica, e non riattivare MeteoGiammoro finché non è validata. Parti dalle attività aperte e dai prossimi passi indicati nel documento, esegui le modifiche direttamente nel repository e verifica sempre test, workflow, `data.json` e deploy GitHub Pages.
