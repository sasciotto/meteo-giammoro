# Meteo Giammoro — note operative

Aggiornato: 16 novembre 2026

## Integrità delle stazioni

La stazione primaria `MeteoGiammoro` è stata segnalata riattivata il 16 novembre 2026. Sito comunicato: https://meteogiammoro.altervista.org/. Il feed non è ancora stato validato automaticamente: lo stato è `test` / «Riattivata · in verifica», con valori strumentali `null` ed esclusione dai calcoli. La segnalazione di riattivazione non costituisce conferma di freschezza osservativa.

Per passare a `online` servono un endpoint effettivamente leggibile, timestamp osservativo, verifica di plausibilità dei valori e controllo su più cicli. Finché manca questa verifica, la dashboard continua a distinguere la stima modellistica territoriale dalle osservazioni delle stazioni limitrofe e non presenta nessuna misura locale inventata.

`config/stations.json` distingue:

- `candidates`: stazione prevista o alias nominali ammessi;
- `substitutes`: stazioni alternative territoriali;
- `allow_substitute`: autorizzazione esplicita all'uso delle alternative.

Regola operativa: i gruppi con `allow_substitute: false` non devono contenere sostituti. Se la stazione prevista non è disponibile, il dato deve risultare non disponibile e non può essere rimpiazzato silenziosamente con un'altra località.

Per `Pace del Mela / area Giammoro` sono ammessi fallback territoriali espliciti; il nome reale della stazione viene comunque mantenuto nell'output.

## Classificazione delle reti

Il feed CMS può non valorizzare la rete. Quando il nome della stazione contiene un suffisso esplicito e non ambiguo, il backend può classificare la rete senza cambiare il nome della stazione:

- `(DRPC)` → rete ufficiale, DRPC Sicilia / Protezione Civile;
- `(SIAS)` → rete ufficiale, SIAS Regione Siciliana;
- `(LineaMeteo)` → rete locale affidabile.

L'inferenza viene marcata con `network_inferred: true` e con una nota dedicata. Una rete già dichiarata dal feed non viene mai sovrascritta.

## Fulminazioni e mappa Blitzortung (18 novembre 2026)

Il download automatico EUMETSAT MTG-LI è stato rimosso dalla pipeline
(nowcast_v4.py e segreti EUMETSAT_CONSUMER_* non più utilizzati). I dati
di fulminazione analitici, quando effettivamente accessibili, provengono
dal prodotto ufficiale Radar-DPC LTG/LAMPINET; il layer WMS di fallback è
solo un'indicazione grafica e non viene convertito in conteggi di flash.

Blitzortung.org viene mostrato in una mappa iframe come servizio
esterno, con attribuzione e link alla mappa originale. La mappa **non**
è acquisita da un'API e **non** è utilizzata per le allerte ufficiali,
il nowcasting automatico, la calibrazione, gli eventi o i punteggi di
rischio. I termini di Blitzortung limitano l'accesso ai dati grezzi e
l'impiego per sistemi di allerta: https://www.blitzortung.org/it/contact.php
Embed documentato: https://map.blitzortung.org/mapexample.html

Le credenziali LSASAF_* e l'integrazione di radiazione solare LSA SAF
restano distinte e non vengono eliminate da questa modifica.

## Scheduling GitHub Actions

Il workflow principale `update-weather.yml` mantiene lo schedule di backup ogni 15 minuti ai minuti `:07`, `:22`, `:37`, `:52` e la guardia di freschezza evita cicli duplicati troppo ravvicinati.

`weather-heartbeat.yml` è un heartbeat auto-rilanciante con attesa di 15 minuti e schedule orario di recupero; controlla che non esistano heartbeat successori già attivi. Il cron di `update-weather.yml` resta una ridondanza opportunistica. La continuità va verificata dagli ultimi run Actions, senza assumere una garanzia di scheduling.

## Persistenza e branch main

La pipeline pubblica GitHub Pages prima della persistenza dei JSON su `main`. Il push dati usa fetch/rebase/retry per ridurre i conflitti con aggiornamenti concorrenti.

La branch `main` riceve quindi commit automatici del bot. Qualunque futura branch protection deve consentire esplicitamente questo flusso oppure spostare i dati runtime su una branch/storage separato prima di vietare i push diretti.

## Validazione

Le modifiche alla policy stazioni devono essere accompagnate dai test in `tests/test_station_policy.py` e dalla suite completa `pytest` prima del merge.

## Sicurezza rollback

Backup precedente al consolidamento del 30 ottobre 2026:

`backup/2026-10-30-pre-improvements`

commit di riferimento:

`595271abd64eca73262531ab7db2327b728fc206`

Non riscrivere o riutilizzare questa branch per sviluppo ordinario.
