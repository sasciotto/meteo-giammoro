# Meteo Giammoro — note operative

Aggiornato: 30 ottobre 2026

## Integrità delle stazioni

La stazione primaria `MeteoGiammoro` resta esclusa dall'analisi finché è in manutenzione/test.

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

## Scheduling GitHub Actions

Il workflow principale `update-weather.yml` mantiene lo schedule di backup ogni 15 minuti ai minuti `:07`, `:22`, `:37`, `:52` e la guardia di freschezza evita cicli duplicati troppo ravvicinati.

`weather-heartbeat.yml` è un trigger manuale one-shot: avvia il workflow principale e termina. Non mantiene più un runner GitHub occupato per 15 minuti in attesa di rilanciarsi.

## Persistenza e branch main

La pipeline pubblica GitHub Pages prima della persistenza dei JSON su `main`. Il push dati usa fetch/rebase/retry per ridurre i conflitti con aggiornamenti concorrenti.

La branch `main` riceve quindi commit automatici del bot. Qualunque futura branch protection deve consentire esplicitamente questo flusso oppure spostare i dati runtime su una branch/storage separato prima di vietare i push diretti.

## Sicurezza rollback

Backup precedente al consolidamento del 30 ottobre 2026:

`backup/2026-10-30-pre-improvements`

commit di riferimento:

`595271abd64eca73262531ab7db2327b728fc206`

Non riscrivere o riutilizzare questa branch per sviluppo ordinario.
