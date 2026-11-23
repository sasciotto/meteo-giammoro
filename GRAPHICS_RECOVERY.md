# METEO Giammoro — ripristino grafico di emergenza

## Stato grafico attuale — ritorno al tema chiaro (23 novembre 2026)
Ripristinati i file dell'interfaccia dal backup `backup/main-20261123-before-mobile-blue-redesign` (versione **bianca/azzurro molto chiaro precedente al tema blu**). È rimasta l'intestazione solo «Meteo Giammoro», secondo la preferenza espressa. I successivi renderer blu e i relativi test sono stati rimossi dal codice attivo, senza modificare `data.json` o i motori.

Il backup immediatamente precedente al ripristino è `backup/main-20261123-before-return-to-white` e permette il ritorno alla versione prima della richiesta. Gli altri rami di backup storici rimangono disponibili.

Questo file è il riferimento **persistente nel repository** per ritrovare le versioni grafiche precedenti, senza fare affidamento sulla memoria della chat.

## Copie di sicurezza (non eliminare)
- **Grafica iniziale**, precedente al restyling del 23 novembre 2026: ramo `backup/graphics-original-emergency-20261123`, commit base `ddfcfe46d947049f371e2728486e26404b1e5fc6`. Dedicato al ripristino rapido del layout originario.
- **Grafica blu precedente al bilanciamento e alla correzione della leggibilità**: ramo `backup/main-20261123-before-readable-home`. Conserva il sito intero prima della presente modifica.
- **Backup prima della grafica blu**: `backup/main-20261123-before-mobile-blue-redesign`.
- **Backup prima del primo restyling**: `backup/main-20261123-before-home-redesign`.

## Nuovo layout ispirato al rendering (23 novembre 2026)
- **Backup dello stato precedente al layout ispirato al rendering:** `backup/main-20261123-before-render-match` (baseline `75f34e8ca7c5c19b78bc24b3428b724bbb370e55`).
- Il nuovo layout si trova in `render_match_ui.js` e viene iniettato da `site_prepare.py`. Per annullare **solo** questo restyling, ripristinare questi file dal backup in un ramo/PR, senza toccare `data.json` o i motori meteorologici.
- Il backup originario `backup/graphics-original-emergency-20261123` resta disponibile per un recupero più ampio della grafica.

## Ripristino sicuro della sola grafica iniziale
Non fare reset forzati di `main` o ripristini integrali: annullerebbero anche i successivi dati meteorologici pubblicati automaticamente.

Da una copia locale con Git configurato:

```bash
git fetch origin
git switch main
git pull --ff-only
git switch -c restore/graphics-emergency
git restore --source origin/backup/graphics-original-emergency-20261123 -- index.html home_polish_ui.js forecast_dashboard.js
git add index.html home_polish_ui.js forecast_dashboard.js
git commit -m "Ripristina grafica iniziale da backup di emergenza"
git push -u origin restore/graphics-emergency
```

Aprire una pull request verso `main`, aggiornare eventuali test grafici che descrivono il layout più recente, verificare il rendering desktop/mobile e solo allora effettuare il merge.

## Componenti che NON vanno sostituiti durante il ripristino
- `data.json`, storico, radar, fulminazioni, stazioni, modelli, allerte e snapshot
- `collector.py`, `nowcast_v4.py` e gli altri motori
- workflow di aggiornamento o credenziali

## Check rapido post-ripristino
1. Home e Analisi navigabili su telefono e desktop.
2. Valori attuali e data di aggiornamento visibili e non falsificati.
3. Avvisi vento e allerte ufficiali funzionanti.
4. Previsioni, stazioni e provenienza dei dati ancora consultabili.
5. Build GitHub Pages completata e dati realmente freschi.

Il backup conserva codice e aspetto originali, **non garantisce** la presenza dei dati meteo più recenti: questi rimangono sul ramo `main`.
