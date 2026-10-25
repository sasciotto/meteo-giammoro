(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const DATA_URL = 'seismic_events.json';
  let loaded = false;
  let loading = false;

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function num(value) {
    const x = Number(value);
    return Number.isFinite(x) ? x : null;
  }

  function magnitude(event) {
    const value = num(event?.magnitude);
    if (value == null) return 'M —';
    const type = String(event?.magnitude_type || 'M').toUpperCase();
    return `${type} ${value.toLocaleString('it-IT', {minimumFractionDigits:1, maximumFractionDigits:1})}`;
  }

  function localTime(value) {
    try {
      return new Intl.DateTimeFormat('it-IT', {
        timeZone:'Europe/Rome', day:'2-digit', month:'2-digit', year:'numeric',
        hour:'2-digit', minute:'2-digit'
      }).format(new Date(value));
    } catch (_) {
      return String(value || '—');
    }
  }

  function ensureStyles() {
    if (byId('seismicEventsStyles')) return;
    const style = document.createElement('style');
    style.id = 'seismicEventsStyles';
    style.textContent = `
      .events-only{display:none}body.mode-events .events-only{display:block}
      .events-view{margin-top:0}.events-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:12px}
      .events-head h2{margin:0;font-size:25px}.events-head p{margin:5px 0 0;color:var(--muted);max-width:780px}
      .events-status{font-size:11px;color:var(--muted);text-align:right}.events-status strong{display:block;color:var(--text);font-size:12px}
      .events-summary-grid{display:grid;grid-template-columns:1.25fr .75fr .75fr;gap:10px;margin-top:12px}
      .events-summary-card{border:1px solid var(--line);border-radius:14px;padding:14px;background:var(--surface)}
      .events-summary-card.primary{background:linear-gradient(135deg,#f4f7f9,#fff)}
      .events-magnitude{font-size:31px;font-weight:820;letter-spacing:-.03em;margin-top:4px}.events-place{font-size:14px;font-weight:760;margin-top:3px}.events-meta{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.45}
      .events-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:12px;margin-top:12px}.events-panel{padding:16px 17px}
      .events-panel h3{margin:0;font-size:18px}.events-panel-sub{font-size:11px;color:var(--muted);margin-top:3px}
      .seismic-map{position:relative;min-height:410px;margin-top:12px;border:1px solid var(--line);border-radius:14px;background:radial-gradient(circle at center,#fff 0,#f6f9fa 58%,#eef3f5 100%);overflow:hidden}
      .seismic-map svg{display:block;width:100%;height:410px}.seismic-map text{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;fill:#64727d}.seismic-map .ring{fill:none;stroke:#cbd7dd;stroke-width:1;stroke-dasharray:4 5}.seismic-map .axis{stroke:#dce5e9;stroke-width:1}.seismic-map .home{fill:#0f6786;stroke:#fff;stroke-width:3}.seismic-map .quake{fill:#ad2a2a;fill-opacity:.78;stroke:#fff;stroke-width:1.4;cursor:pointer}.seismic-map .quake:hover{fill-opacity:1}.seismic-map .label{font-size:10px}.seismic-map .home-label{font-size:11px;font-weight:800;fill:#0f6786}
      .events-list{margin-top:10px}.event-row{display:grid;grid-template-columns:76px 1fr auto;gap:10px;align-items:center;padding:10px 0;border-top:1px solid var(--line)}.event-row:first-child{border-top:0}.event-mag{font-size:18px;font-weight:820}.event-place{font-weight:720;font-size:13px}.event-detail{font-size:10px;color:var(--muted);margin-top:2px;line-height:1.4}.event-link{font-size:11px;font-weight:760;white-space:nowrap}
      .events-note{margin-top:12px;padding:12px 13px;border:1px solid var(--line);border-radius:12px;background:var(--surface2);font-size:12px;line-height:1.5}.events-note strong{display:block;margin-bottom:3px}
      .events-error{padding:18px;border:1px solid #ead8aa;border-radius:13px;background:#fff8e9;color:#654c13;margin-top:12px}.events-loading{padding:22px;text-align:center;color:var(--muted)}
      @media(max-width:850px){.events-summary-grid{grid-template-columns:1fr 1fr}.events-summary-card.primary{grid-column:1/-1}.events-grid{grid-template-columns:1fr}.events-status{text-align:left}}
      @media(max-width:560px){.events-head{display:block}.events-status{margin-top:8px}.events-summary-grid{grid-template-columns:1fr}.events-summary-card.primary{grid-column:auto}.event-row{grid-template-columns:66px 1fr}.event-link{grid-column:2}.seismic-map,.seismic-map svg{min-height:340px;height:340px}}
    `;
    document.head.appendChild(style);
  }

  function ensureView() {
    ensureStyles();
    const switcher = document.querySelector('.mode-switch');
    const footer = document.querySelector('footer.foot');
    if (!switcher || !footer?.parentElement) return null;

    let button = byId('eventsBtn');
    if (!button) {
      button = document.createElement('button');
      button.id = 'eventsBtn';
      button.type = 'button';
      button.className = 'mode-btn';
      button.textContent = 'Eventi';
      switcher.appendChild(button);
    }

    let view = byId('eventsView');
    if (!view) {
      view = document.createElement('section');
      view.id = 'eventsView';
      view.className = 'events-only events-view';
      view.innerHTML = `<div class="card"><div class="events-head"><div><div class="k">MONITORAGGIO TERRITORIALE</div><h2>Terremoti e fenomeni geofisici</h2><p>Eventi sismici recenti attorno a Giammoro da fonte INGV. Questa pagina è osservativa: non prevede terremoti e non calcola autonomamente allerte tsunami.</p></div><div class="events-status" id="eventsStatus"><strong>Non caricato</strong>Dati caricati solo aprendo questa sezione</div></div><div id="eventsContent"><div class="events-loading">Apri la sezione per caricare gli eventi INGV.</div></div></div>`;
      footer.parentElement.insertBefore(view, footer);
    }
    return {button, view};
  }

  function eventSummaryCard(label, event, primary=false) {
    if (!event) return `<div class="events-summary-card${primary?' primary':''}"><div class="k">${esc(label)}</div><div class="events-place">Nessun evento nel periodo</div><div class="events-meta">Nessun terremoto corrispondente ai filtri correnti.</div></div>`;
    return `<div class="events-summary-card${primary?' primary':''}"><div class="k">${esc(label)}</div><div class="events-magnitude">${esc(magnitude(event))}</div><div class="events-place">${esc(event.location)}</div><div class="events-meta">${esc(localTime(event.time_local || event.time_utc))}<br>${esc(event.distance_km)} km ${esc(event.direction || '')} da Giammoro · profondità ${event.depth_km == null ? '—' : esc(event.depth_km)+' km'}</div></div>`;
  }

  function mapSvg(events) {
    const width = 760, height = 410, cx = width/2, cy = height/2, radius = 170, maxKm = 500;
    const rings = [100,250,500].map(km => {
      const r = radius * km / maxKm;
      return `<circle class="ring" cx="${cx}" cy="${cy}" r="${r}"></circle><text class="label" x="${cx+r+4}" y="${cy-4}">${km} km</text>`;
    }).join('');
    const points = (events || []).slice(0,80).map(event => {
      const distance = Math.min(maxKm, num(event.distance_km) ?? maxKm);
      const bearing = (num(event.bearing_deg) ?? 0) * Math.PI / 180;
      const r = radius * distance / maxKm;
      const x = cx + Math.sin(bearing) * r;
      const y = cy - Math.cos(bearing) * r;
      const mag = Math.max(1, num(event.magnitude) ?? 1);
      const size = Math.max(3.5, Math.min(12, 2.4 + mag * 1.45));
      const title = `${magnitude(event)} · ${event.location} · ${event.distance_km} km da Giammoro`;
      return `<a href="${esc(event.source_url)}" target="_blank" rel="noopener noreferrer"><circle class="quake" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${size.toFixed(1)}"><title>${esc(title)}</title></circle></a>`;
    }).join('');
    return `<div class="seismic-map" aria-label="Mappa radiale degli eventi sismici rispetto a Giammoro"><svg viewBox="0 0 ${width} ${height}" role="img"><line class="axis" x1="${cx}" y1="35" x2="${cx}" y2="375"></line><line class="axis" x1="${cx-170}" y1="${cy}" x2="${cx+170}" y2="${cy}"></line>${rings}<circle class="home" cx="${cx}" cy="${cy}" r="7"></circle><text class="home-label" x="${cx+11}" y="${cy-10}">Giammoro</text><text class="label" x="${cx-4}" y="28">N</text><text class="label" x="${cx+178}" y="${cy+4}">E</text><text class="label" x="${cx-4}" y="397">S</text><text class="label" x="${cx-186}" y="${cy+4}">O</text>${points}</svg></div>`;
  }

  function eventRows(events, limit=12) {
    const rows = (events || []).slice(0,limit);
    if (!rows.length) return '<div class="events-note">Nessun evento nel periodo e raggio selezionati.</div>';
    return `<div class="events-list">${rows.map(event => `<div class="event-row"><div class="event-mag">${esc(magnitude(event))}</div><div><div class="event-place">${esc(event.location)}</div><div class="event-detail">${esc(localTime(event.time_local || event.time_utc))} · ${esc(event.distance_km)} km ${esc(event.direction || '')} da Giammoro · prof. ${event.depth_km == null ? '—' : esc(event.depth_km)+' km'}</div></div><a class="source-link event-link" href="${esc(event.source_url)}" target="_blank" rel="noopener noreferrer">Scheda INGV ↗</a></div>`).join('')}</div>`;
  }

  function render(data) {
    const content = byId('eventsContent');
    const status = byId('eventsStatus');
    if (!content || !status) return;
    const meta = data?.meta || {};
    const summary = data?.summary || {};
    const regional = Array.isArray(data?.regional) ? data.regional : [];
    const local = Array.isArray(data?.local) ? data.local : [];

    status.innerHTML = `<strong>${meta.status === 'ok' ? 'INGV aggiornato' : meta.status === 'stale' ? 'Ultimo dato disponibile' : 'Dato non disponibile'}</strong>${esc(meta.generated_at ? localTime(meta.generated_at) : '—')} · ${esc(meta.events_count ?? regional.length)} eventi`;

    content.innerHTML = `<div class="events-summary-grid">${eventSummaryCard(`Ultimo evento entro ${summary.local_radius_km || 150} km`, summary.latest_local, true)}${eventSummaryCard('Più forte vicino', summary.strongest_local)}${eventSummaryCard('Più forte entro 500 km', summary.strongest_regional)}</div><div class="events-grid"><div class="card events-panel"><h3>Mappa rispetto a Giammoro</h3><div class="events-panel-sub">Mappa radiale: posizione relativa e distanza. Non rappresenta confini amministrativi o pericolosità.</div>${mapSvg(regional)}</div><div class="card events-panel"><h3>Eventi entro 150 km</h3><div class="events-panel-sub">Ultimi ${esc(meta.period_days || 7)} giorni · fonte INGV</div>${eventRows(local,10)}</div></div><div class="card events-panel section"><h3>Sicilia, Calabria e area circostante</h3><div class="events-panel-sub">Eventi entro ${esc(summary.regional_radius_km || 500)} km da Giammoro · ordinati dal più recente</div>${eventRows(regional,16)}</div><div class="events-note"><strong>${esc(data?.tsunami?.title || 'Maremoti: solo informazioni ufficiali')}</strong>${esc(data?.tsunami?.text || '')} <a class="source-link" href="${esc(data?.tsunami?.cat_url || 'https://cat.ingv.it/')}" target="_blank" rel="noopener noreferrer">CAT-INGV ↗</a></div><div class="events-note"><strong>${esc(data?.safety?.title || 'In caso di terremoto')}</strong>${esc(data?.safety?.text || '')} <a class="source-link" href="${esc(data?.safety?.url || '#')}" target="_blank" rel="noopener noreferrer">Protezione Civile ↗</a></div>${meta.error ? `<div class="events-error">Aggiornamento INGV non riuscito: viene mostrato l'ultimo dataset disponibile. ${esc(meta.error)}</div>` : ''}`;
  }

  async function loadEvents() {
    if (loaded || loading) return;
    loading = true;
    const content = byId('eventsContent');
    if (content) content.innerHTML = '<div class="events-loading">Caricamento eventi sismici INGV…</div>';
    try {
      const response = await fetch(`${DATA_URL}?_=${Date.now()}`, {cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
      loaded = true;
    } catch (error) {
      if (content) content.innerHTML = `<div class="events-error">Dati sismici temporaneamente non disponibili. La dashboard meteo continua a funzionare normalmente.</div>`;
      const status = byId('eventsStatus');
      if (status) status.innerHTML = '<strong>Non disponibile</strong>Errore nel caricamento del dataset sismico';
    } finally {
      loading = false;
    }
  }

  function activateEvents() {
    document.body.className = 'mode-events';
    byId('homeBtn')?.classList.remove('active');
    byId('expertBtn')?.classList.remove('active');
    byId('radarBtn')?.classList.remove('active');
    byId('eventsBtn')?.classList.add('active');
    loadEvents();
  }

  const created = ensureView();
  if (!created) return;
  created.button.addEventListener('click', activateEvents);
  byId('homeBtn')?.addEventListener('click', () => created.button.classList.remove('active'));
  byId('expertBtn')?.addEventListener('click', () => created.button.classList.remove('active'));
  byId('radarBtn')?.addEventListener('click', () => created.button.classList.remove('active'));
})();
