(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const DATA_URL = 'seismic_events.json';
  const GIAMMORO = [38.2018, 15.31816];
  const LEAFLET_CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  const LEAFLET_JS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
  const filters = {period:'7d', radius:150, minMag:1};

  let loaded = false;
  let loading = false;
  let currentData = null;
  let leafletPromise = null;
  let map = null;
  let quakeLayer = null;

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

  function eventTimestamp(event) {
    const raw = event?.time_utc || event?.time_local;
    const ts = raw ? new Date(raw).getTime() : NaN;
    return Number.isFinite(ts) ? ts : 0;
  }

  function ageHours(event) {
    const ts = eventTimestamp(event);
    return ts ? Math.max(0, (Date.now() - ts) / 3_600_000) : Infinity;
  }

  function magClass(event) {
    const mag = num(event?.magnitude) ?? 0;
    if (mag >= 4) return 'strong';
    if (mag >= 3) return 'marked';
    if (mag >= 2) return 'moderate';
    return 'minor';
  }

  function markerColor(event) {
    const age = ageHours(event);
    if (age <= 24) return '#0f6786';
    if (age <= 72) return '#657e8d';
    return '#9caab2';
  }

  function ensureStyles() {
    if (byId('seismicEventsStyles')) return;
    const style = document.createElement('style');
    style.id = 'seismicEventsStyles';
    style.textContent = `
      .events-only{display:none}body.mode-events .events-only{display:block}
      .events-view{margin-top:0}.events-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:12px}
      .events-head h2{margin:0;font-size:25px}.events-head p{margin:5px 0 0;color:var(--muted);max-width:780px;line-height:1.5}
      .events-status{font-size:11px;color:var(--muted);text-align:right}.events-status strong{display:block;color:var(--text);font-size:12px}.events-status-time{display:inline-block;margin-top:2px;color:#34434e;font-size:12px;font-weight:760;font-variant-numeric:tabular-nums}
      .events-hero{display:grid;grid-template-columns:auto 1fr auto;gap:18px;align-items:center;margin-top:13px;padding:19px 20px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(135deg,#f1f7fa 0%,#fff 70%)}
      .events-hero-mag{min-width:104px;font-size:38px;font-weight:850;letter-spacing:-.045em;color:#21323e}.events-hero-place{font-size:19px;font-weight:790;line-height:1.25}.events-hero-meta{margin-top:6px;color:#52616b;font-size:12px;line-height:1.55}.events-hero-meta .events-datetime{font-size:13px}
      .events-hero-side{text-align:right;font-size:11px;color:var(--muted);line-height:1.55}.events-hero-side strong{display:block;color:#34434e;font-size:14px}
      .events-summary-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}.events-summary-card{border:1px solid var(--line);border-radius:14px;padding:13px 14px;background:var(--surface)}
      .events-magnitude{font-size:25px;font-weight:820;letter-spacing:-.03em;margin-top:4px}.events-place{font-size:13px;font-weight:760;margin-top:3px}.events-meta{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.45}.events-datetime{display:inline-block;color:#34434e;font-size:12px;font-weight:780;letter-spacing:.01em;font-variant-numeric:tabular-nums}
      .mag-badge{display:inline-flex;align-items:center;justify-content:center;border-radius:999px;padding:3px 8px;font-size:10px;font-weight:820;margin-left:6px;vertical-align:middle}.mag-badge.minor{background:#eef3f5;color:#53636d}.mag-badge.moderate{background:#e8f2f6;color:#24566d}.mag-badge.marked{background:#fff3dc;color:#795413}.mag-badge.strong{background:#f9e7e5;color:#853a32}
      .events-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:14px;padding:12px 13px;border:1px solid var(--line);border-radius:14px;background:var(--surface2)}
      .events-filter-groups{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.events-filter-group{display:flex;align-items:center;gap:5px;flex-wrap:wrap}.events-filter-label{font-size:10px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-right:2px}.events-filter{border:1px solid var(--line);background:#fff;color:#40505b;border-radius:999px;padding:6px 9px;font:inherit;font-size:11px;font-weight:760;cursor:pointer}.events-filter.active{background:var(--accent);border-color:var(--accent);color:#fff}.events-filter-count{font-size:11px;color:var(--muted)}.events-filter-count strong{color:var(--text);font-size:13px}
      .events-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:12px;margin-top:12px}.events-panel{padding:16px 17px}.events-panel h3{margin:0;font-size:18px}.events-panel-sub{font-size:11px;color:var(--muted);margin-top:3px;line-height:1.45}
      .events-map-wrap{position:relative;min-height:470px;margin-top:12px;border:1px solid var(--line);border-radius:14px;background:#edf2f4;overflow:hidden}.events-leaflet-map{height:470px;width:100%;z-index:1}.events-map-loading{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:20px;text-align:center;color:var(--muted);background:linear-gradient(135deg,#f5f8f9,#eaf0f3);z-index:2}.events-map-legend{position:absolute;left:12px;bottom:12px;z-index:500;padding:8px 10px;border:1px solid rgba(255,255,255,.82);border-radius:10px;background:rgba(255,255,255,.94);box-shadow:0 3px 14px rgba(20,32,42,.14);font-size:10px;color:#40505b;line-height:1.45;pointer-events:none}.events-map-legend strong{display:block;margin-bottom:2px}.legend-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:middle}.legend-dot.recent{background:#0f6786}.legend-dot.older{background:#9caab2}
      .seismic-map{position:relative;min-height:410px;border:0;background:radial-gradient(circle at center,#fff 0,#f6f9fa 58%,#eef3f5 100%);overflow:hidden}.seismic-map svg{display:block;width:100%;height:410px}.seismic-map text{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;fill:#64727d}.seismic-map .ring{fill:none;stroke:#cbd7dd;stroke-width:1;stroke-dasharray:4 5}.seismic-map .axis{stroke:#dce5e9;stroke-width:1}.seismic-map .home{fill:#0f6786;stroke:#fff;stroke-width:3}.seismic-map .quake{fill:#718795;fill-opacity:.78;stroke:#fff;stroke-width:1.4}.seismic-map .label{font-size:10px}.seismic-map .home-label{font-size:11px;font-weight:800;fill:#0f6786}
      .events-list{margin-top:10px}.event-row{display:grid;grid-template-columns:76px 1fr auto;gap:10px;align-items:center;padding:11px 0;border-top:1px solid var(--line)}.event-row:first-child{border-top:0}.event-mag{font-size:18px;font-weight:830}.event-place{font-weight:730;font-size:13px;line-height:1.35}.event-detail{font-size:10px;color:var(--muted);margin-top:4px;line-height:1.5}.event-detail .events-datetime{font-size:11px;margin-right:2px}.event-link{font-size:11px;font-weight:760;white-space:nowrap}
      .events-empty{margin-top:10px;padding:20px;border:1px dashed var(--line);border-radius:12px;text-align:center;color:var(--muted);font-size:12px}
      .events-note{margin-top:12px;padding:12px 13px;border:1px solid var(--line);border-radius:12px;background:var(--surface2);font-size:12px;line-height:1.5}.events-note strong{display:block;margin-bottom:3px}.events-note.official{border-left:4px solid #0f6786;background:#f3f8fa}
      .events-disclaimer{margin-top:12px;padding:11px 13px;border-top:1px solid var(--line);color:var(--muted);font-size:11px;line-height:1.5}
      .events-error{padding:18px;border:1px solid #ead8aa;border-radius:13px;background:#fff8e9;color:#654c13;margin-top:12px}.events-loading{padding:22px;text-align:center;color:var(--muted)}
      .leaflet-container{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}.leaflet-popup-content{font-size:12px;line-height:1.45}.leaflet-popup-content strong{font-size:13px}.leaflet-control-attribution{font-size:9px!important}
      @media(max-width:900px){.events-grid{grid-template-columns:1fr}.events-status{text-align:left}.events-map-wrap,.events-leaflet-map{height:430px;min-height:430px}}
      @media(max-width:650px){.events-head{display:block}.events-status{margin-top:8px}.events-hero{grid-template-columns:1fr;gap:7px}.events-hero-mag{font-size:34px}.events-hero-side{text-align:left;display:flex;gap:14px;flex-wrap:wrap}.events-summary-grid{grid-template-columns:1fr}.events-toolbar{display:block}.events-filter-groups{display:block}.events-filter-group{margin-top:8px}.events-filter-group:first-child{margin-top:0}.events-filter-count{margin-top:10px}.event-row{grid-template-columns:66px 1fr}.event-link{grid-column:2}.events-map-wrap,.events-leaflet-map{height:390px;min-height:390px}}
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
      view.innerHTML = `<div class="card"><div class="events-head"><div><div class="k">MONITORAGGIO TERRITORIALE</div><h2>Terremoti e fenomeni geofisici</h2><p>Eventi sismici recenti attorno a Giammoro da fonte INGV. La pagina mostra eventi già rilevati: non prevede terremoti e non calcola autonomamente allerte tsunami.</p></div><div class="events-status" id="eventsStatus"><strong>Non caricato</strong>Dati caricati solo aprendo questa sezione</div></div><div id="eventsContent"><div class="events-loading">Apri la sezione per caricare gli eventi INGV.</div></div></div>`;
      footer.parentElement.insertBefore(view, footer);
    }
    return {button, view};
  }

  function summaryCard(label, event) {
    if (!event) return `<div class="events-summary-card"><div class="k">${esc(label)}</div><div class="events-place">Nessun evento nel periodo</div></div>`;
    return `<div class="events-summary-card"><div class="k">${esc(label)}</div><div class="events-magnitude">${esc(magnitude(event))}<span class="mag-badge ${magClass(event)}">${num(event.magnitude) == null ? 'n/d' : 'magnitudo'}</span></div><div class="events-place">${esc(event.location)}</div><div class="events-meta"><span class="events-datetime">${esc(localTime(event.time_local || event.time_utc))}</span><br>${esc(event.distance_km)} km ${esc(event.direction || '')} da Giammoro · profondità ${event.depth_km == null ? '—' : esc(event.depth_km)+' km'}</div></div>`;
  }

  function heroCard(event) {
    if (!event) return `<div class="events-hero"><div class="events-hero-mag">M —</div><div><div class="k">ULTIMO EVENTO VICINO A GIAMMORO</div><div class="events-hero-place">Nessun evento entro 150 km nel periodo disponibile</div></div></div>`;
    return `<div class="events-hero"><div class="events-hero-mag">${esc(magnitude(event))}</div><div><div class="k">ULTIMO EVENTO ENTRO 150 KM DA GIAMMORO</div><div class="events-hero-place">${esc(event.location)}</div><div class="events-hero-meta"><span class="events-datetime">${esc(localTime(event.time_local || event.time_utc))}</span><br>${esc(event.distance_km)} km ${esc(event.direction || '')} · profondità ${event.depth_km == null ? '—' : esc(event.depth_km)+' km'}</div></div><div class="events-hero-side"><strong>${esc(event.latitude)}, ${esc(event.longitude)}</strong>Coordinate epicentrali INGV<br><a class="source-link" href="${esc(event.source_url)}" target="_blank" rel="noopener noreferrer">Scheda ufficiale ↗</a></div></div>`;
  }

  function filterToolbar() {
    const group = (label, kind, values) => `<div class="events-filter-group"><span class="events-filter-label">${label}</span>${values.map(([value,text]) => `<button type="button" class="events-filter${String(filters[kind])===String(value)?' active':''}" data-event-filter="${kind}" data-event-value="${value}">${text}</button>`).join('')}</div>`;
    return `<div class="events-toolbar"><div class="events-filter-groups">${group('Periodo','period',[['24h','24 h'],['7d','7 giorni']])}${group('Raggio','radius',[[50,'50 km'],[150,'150 km'],[500,'500 km']])}${group('Magnitudo','minMag',[[1,'M ≥1'],[2,'M ≥2'],[3,'M ≥3']])}</div><div class="events-filter-count" id="eventsFilterCount"></div></div>`;
  }

  function filteredEvents() {
    const events = Array.isArray(currentData?.regional) ? currentData.regional : [];
    const cutoffHours = filters.period === '24h' ? 24 : 24 * 7;
    return events.filter(event => {
      const distance = num(event?.distance_km);
      const mag = num(event?.magnitude);
      return distance != null && distance <= Number(filters.radius) && mag != null && mag >= Number(filters.minMag) && ageHours(event) <= cutoffHours;
    }).sort((a,b) => eventTimestamp(b) - eventTimestamp(a));
  }

  function radialFallback(events) {
    const width = 760, height = 410, cx = width/2, cy = height/2, radius = 170, maxKm = Math.max(50, Number(filters.radius));
    const rings = [0.33,0.66,1].map(part => {
      const km = Math.round(maxKm * part);
      const r = radius * part;
      return `<circle class="ring" cx="${cx}" cy="${cy}" r="${r}"></circle><text class="label" x="${cx+r+4}" y="${cy-4}">${km} km</text>`;
    }).join('');
    const points = events.slice(0,80).map(event => {
      const distance = Math.min(maxKm, num(event.distance_km) ?? maxKm);
      const bearing = (num(event.bearing_deg) ?? 0) * Math.PI / 180;
      const r = radius * distance / maxKm;
      const x = cx + Math.sin(bearing) * r;
      const y = cy - Math.cos(bearing) * r;
      const mag = Math.max(1, num(event.magnitude) ?? 1);
      const size = Math.max(3.5, Math.min(12, 2.4 + mag * 1.45));
      return `<circle class="quake" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${size.toFixed(1)}"><title>${esc(magnitude(event))} · ${esc(event.location)}</title></circle>`;
    }).join('');
    return `<div class="seismic-map"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Mappa radiale di fallback"><line class="axis" x1="${cx}" y1="35" x2="${cx}" y2="375"></line><line class="axis" x1="${cx-170}" y1="${cy}" x2="${cx+170}" y2="${cy}"></line>${rings}<circle class="home" cx="${cx}" cy="${cy}" r="7"></circle><text class="home-label" x="${cx+11}" y="${cy-10}">Giammoro</text>${points}</svg></div>`;
  }

  function eventRows(events, limit=18) {
    const rows = events.slice(0, limit);
    if (!rows.length) return '<div class="events-empty">Nessun evento corrisponde ai filtri selezionati.</div>';
    return `<div class="events-list">${rows.map(event => `<div class="event-row"><div class="event-mag">${esc(magnitude(event))}</div><div><div class="event-place">${esc(event.location)}</div><div class="event-detail"><span class="events-datetime">${esc(localTime(event.time_local || event.time_utc))}</span> · ${esc(event.distance_km)} km ${esc(event.direction || '')} da Giammoro · prof. ${event.depth_km == null ? '—' : esc(event.depth_km)+' km'}</div></div><a class="source-link event-link" href="${esc(event.source_url)}" target="_blank" rel="noopener noreferrer">INGV ↗</a></div>`).join('')}</div>`;
  }

  function ensureLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (leafletPromise) return leafletPromise;
    leafletPromise = new Promise((resolve, reject) => {
      if (!document.querySelector(`link[href="${LEAFLET_CSS}"]`)) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = LEAFLET_CSS;
        link.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
        link.crossOrigin = '';
        document.head.appendChild(link);
      }
      const script = document.createElement('script');
      script.src = LEAFLET_JS;
      script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
      script.crossOrigin = '';
      script.onload = () => window.L ? resolve(window.L) : reject(new Error('Leaflet non disponibile'));
      script.onerror = () => reject(new Error('Leaflet non caricato'));
      document.head.appendChild(script);
    });
    return leafletPromise;
  }

  function popupHtml(event) {
    return `<strong>${esc(magnitude(event))} · ${esc(event.location)}</strong><br><span>${esc(localTime(event.time_local || event.time_utc))}</span><br>${esc(event.distance_km)} km ${esc(event.direction || '')} da Giammoro · prof. ${event.depth_km == null ? '—' : esc(event.depth_km)+' km'}<br><a href="${esc(event.source_url)}" target="_blank" rel="noopener noreferrer">Scheda INGV ↗</a>`;
  }

  function updateLeaflet(events) {
    if (!map || !quakeLayer || !window.L) return;
    quakeLayer.clearLayers();
    events.forEach(event => {
      const lat = num(event.latitude), lon = num(event.longitude), mag = num(event.magnitude) ?? 1;
      if (lat == null || lon == null) return;
      window.L.circleMarker([lat,lon], {
        radius: Math.max(4, Math.min(13, 3 + mag * 1.7)),
        color:'#fff', weight:1.4, fillColor:markerColor(event), fillOpacity:.82
      }).bindPopup(popupHtml(event)).addTo(quakeLayer);
    });
    const zoom = Number(filters.radius) <= 50 ? 9 : Number(filters.radius) <= 150 ? 8 : 6;
    map.setView(GIAMMORO, zoom, {animate:false});
    requestAnimationFrame(() => map.invalidateSize(false));
  }

  async function renderMap(events) {
    const wrap = byId('eventsMapWrap');
    if (!wrap) return;
    try {
      await ensureLeaflet();
      const loading = byId('eventsMapLoading');
      if (loading) loading.remove();
      const mapNode = byId('eventsLeafletMap');
      if (!mapNode) return;
      if (!map) {
        map = window.L.map(mapNode, {scrollWheelZoom:false, preferCanvas:true}).setView(GIAMMORO, 8);
        window.L.tileLayer(TILE_URL, {
          maxZoom:18,
          attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
        }).addTo(map);
        window.L.circleMarker(GIAMMORO, {radius:7,color:'#fff',weight:2.5,fillColor:'#0f6786',fillOpacity:1})
          .bindTooltip('Giammoro', {permanent:true,direction:'right',offset:[8,0]})
          .addTo(map);
        quakeLayer = window.L.layerGroup().addTo(map);
      }
      updateLeaflet(events);
    } catch (_) {
      wrap.innerHTML = `<div class="events-map-loading" style="position:static;min-height:54px">Mappa geografica non disponibile: visualizzazione radiale di fallback.</div>${radialFallback(events)}`;
    }
  }

  function bindFilters() {
    document.querySelectorAll('[data-event-filter]').forEach(button => {
      button.addEventListener('click', () => {
        const kind = button.dataset.eventFilter;
        const raw = button.dataset.eventValue;
        filters[kind] = kind === 'period' ? raw : Number(raw);
        document.querySelectorAll(`[data-event-filter="${kind}"]`).forEach(item => item.classList.toggle('active', item === button));
        renderFilteredViews();
      });
    });
  }

  function renderFilteredViews() {
    const events = filteredEvents();
    const count = byId('eventsFilterCount');
    if (count) count.innerHTML = `<strong>${events.length}</strong> eventi mostrati`;
    const list = byId('eventsFilteredList');
    if (list) list.innerHTML = eventRows(events);
    renderMap(events);
  }

  function render(data) {
    currentData = data;
    const content = byId('eventsContent');
    const status = byId('eventsStatus');
    if (!content || !status) return;
    const meta = data?.meta || {};
    const summary = data?.summary || {};

    status.innerHTML = `<strong>${meta.status === 'ok' ? 'INGV aggiornato' : meta.status === 'stale' ? 'Ultimo dato disponibile' : 'Dato non disponibile'}</strong><span class="events-status-time">${esc(meta.generated_at ? localTime(meta.generated_at) : '—')}</span> · ${esc(meta.events_count ?? 0)} eventi`;

    content.innerHTML = `${heroCard(summary.latest_local)}<div class="events-summary-grid">${summaryCard('Più forte entro 150 km', summary.strongest_local)}${summaryCard('Più forte entro 500 km', summary.strongest_regional)}</div>${filterToolbar()}<div class="events-grid"><div class="card events-panel"><h3>Mappa geografica degli eventi</h3><div class="events-panel-sub">Giammoro è il riferimento. Dimensione dei cerchi = magnitudo; colore = recenza dell'evento. Base cartografica OpenStreetMap.</div><div class="events-map-wrap" id="eventsMapWrap"><div class="events-map-loading" id="eventsMapLoading">Caricamento mappa geografica…</div><div class="events-leaflet-map" id="eventsLeafletMap"></div><div class="events-map-legend"><strong>Legenda</strong><span class="legend-dot recent"></span>ultime 24 h &nbsp; <span class="legend-dot older"></span>più vecchi<br>dimensione = magnitudo</div></div></div><div class="card events-panel"><h3>Eventi filtrati</h3><div class="events-panel-sub">Ordinati dal più recente · fonte INGV</div><div id="eventsFilteredList"></div></div></div><div class="events-note official"><strong>${esc(data?.tsunami?.title || 'Maremoti: solo informazioni ufficiali')}</strong>${esc(data?.tsunami?.text || '')} <a class="source-link" href="${esc(data?.tsunami?.cat_url || 'https://cat.ingv.it/')}" target="_blank" rel="noopener noreferrer">CAT-INGV ↗</a></div><div class="events-note"><strong>${esc(data?.safety?.title || 'In caso di terremoto')}</strong>${esc(data?.safety?.text || '')} <a class="source-link" href="${esc(data?.safety?.url || '#')}" target="_blank" rel="noopener noreferrer">Protezione Civile ↗</a></div><div class="events-disclaimer">I terremoti non sono prevedibili con questa dashboard. I dati mostrano eventi già rilevati e localizzati da INGV; numero di eventi e magnitudo non vengono trasformati in un indice locale di pericolosità o previsione.</div>${meta.error ? `<div class="events-error">Aggiornamento INGV non riuscito: viene mostrato l'ultimo dataset disponibile. ${esc(meta.error)}</div>` : ''}`;
    bindFilters();
    renderFilteredViews();
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
    } catch (_) {
      if (content) content.innerHTML = '<div class="events-error">Dati sismici temporaneamente non disponibili. La dashboard meteo continua a funzionare normalmente.</div>';
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
    loadEvents().then(() => requestAnimationFrame(() => map?.invalidateSize(false)));
  }

  const created = ensureView();
  if (!created) return;
  created.button.addEventListener('click', activateEvents);
  byId('homeBtn')?.addEventListener('click', () => created.button.classList.remove('active'));
  byId('expertBtn')?.addEventListener('click', () => created.button.classList.remove('active'));
  byId('radarBtn')?.addEventListener('click', () => created.button.classList.remove('active'));
})();
