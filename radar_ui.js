(() => {
  'use strict';

  const previousRender = window.renderForecastDashboard;
  const byId = id => document.getElementById(id);
  const REF = {lat: 38.2018, lon: 15.31816};
  const RADIUS_KM = 65;
  const WMS = 'https://radar-geowebcache.protezionecivile.it/service/wms';
  const PRODUCT_META = {
    SRI: {layer: 'radar:sri', label: 'Precipitazione SRI', unit: 'mm/h', description: 'Intensità istantanea di precipitazione'},
    VMI: {layer: 'radar:vmi', label: 'Riflettività VMI', unit: 'dBZ', description: 'Riflettività radar massima'},
  };
  let currentData = null;
  let selectedProduct = 'SRI';

  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = value => {
    if (value === null || value === undefined || value === '') return null;
    const x = Number(value);
    return Number.isFinite(x) ? x : null;
  };
  const fmt = (value, digits = 0) => {
    const x = num(value);
    return x == null ? '—' : x.toLocaleString('it-IT', {minimumFractionDigits: digits, maximumFractionDigits: digits});
  };

  function bounds() {
    const latDelta = RADIUS_KM / 111.32;
    const lonDelta = RADIUS_KM / (111.32 * Math.cos(REF.lat * Math.PI / 180));
    return {
      left: REF.lon - lonDelta,
      bottom: REF.lat - latDelta,
      right: REF.lon + lonDelta,
      top: REF.lat + latDelta,
    };
  }

  function toWmsTime(value) {
    if (!value) return null;
    const d = new Date(value);
    if (!Number.isFinite(d.getTime())) return null;
    return d.toISOString();
  }

  function wmsUrl(layer, timestamp = null) {
    const b = bounds();
    const params = new URLSearchParams({
      service: 'WMS',
      request: 'GetMap',
      layers: layer,
      styles: '',
      format: 'image/png',
      transparent: 'true',
      version: '1.1.1',
      tiled: 'true',
      width: '768',
      height: '640',
      srs: 'EPSG:4326',
      bbox: `${b.left},${b.bottom},${b.right},${b.top}`,
    });
    const time = toWmsTime(timestamp);
    if (time) params.set('time', time);
    return `${WMS}?${params.toString()}`;
  }

  function position(lat, lon) {
    const b = bounds();
    const la = num(lat);
    const lo = num(lon);
    if (la == null || lo == null || lo < b.left || lo > b.right || la < b.bottom || la > b.top) return null;
    return {
      x: 100 * (lo - b.left) / (b.right - b.left),
      y: 100 * (b.top - la) / (b.top - b.bottom),
    };
  }

  function ensureStyles() {
    if (byId('radarViewerStyles')) return;
    const style = document.createElement('style');
    style.id = 'radarViewerStyles';
    style.textContent = `
      .radar-viewer{margin-top:14px;overflow:hidden}
      .radar-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}
      .radar-source{font-size:12px;color:var(--muted);margin-top:3px}
      .radar-tabs{display:inline-flex;gap:4px;padding:4px;border:1px solid var(--line);border-radius:999px;background:var(--surface2)}
      .radar-tab{border:0;border-radius:999px;padding:7px 11px;background:transparent;color:var(--muted);font:inherit;font-size:12px;font-weight:760;cursor:pointer}
      .radar-tab.active{background:var(--accent);color:#fff}.radar-tab:disabled{opacity:.45;cursor:not-allowed}
      .radar-layout{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(230px,.65fr);gap:12px;align-items:start}
      .radar-map{position:relative;overflow:hidden;min-height:360px;aspect-ratio:6/5;border:1px solid var(--line);border-radius:14px;background:#e7edf0}
      .radar-map img{position:absolute;inset:0;width:100%;height:100%;object-fit:fill;display:block}
      .radar-map .radar-boundaries{z-index:2;pointer-events:none}
      .radar-map .radar-product-image{z-index:1}
      .radar-overlay{position:absolute;inset:0;z-index:3;width:100%;height:100%;pointer-events:none}
      .radar-loading{position:absolute;left:10px;bottom:10px;z-index:4;padding:5px 8px;border-radius:999px;background:rgba(255,255,255,.88);border:1px solid var(--line);font-size:11px;color:#40505b}
      .radar-side{display:grid;gap:9px}
      .radar-info{border:1px solid var(--line);border-radius:12px;background:var(--surface2);padding:11px}
      .radar-info strong{display:block;font-size:15px}.radar-info p{margin:4px 0 0;font-size:12px;color:var(--muted);line-height:1.45}
      .radar-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}
      .radar-stat{padding:8px;border-radius:9px;background:var(--surface);border:1px solid var(--line)}
      .radar-stat b{display:block;font-size:14px}.radar-stat span{font-size:10px;color:var(--muted)}
      .radar-legend-note{font-size:11px;color:var(--muted);line-height:1.45}
      @media(max-width:820px){.radar-layout{grid-template-columns:1fr}.radar-map{min-height:320px}.radar-head{display:block}.radar-tabs{margin-top:9px}}
      @media(max-width:520px){.radar-map{min-height:260px}.radar-stats{grid-template-columns:1fr 1fr 1fr}}
    `;
    document.head.appendChild(style);
  }

  function ensureSection() {
    ensureStyles();
    let section = byId('radarViewerSection');
    if (section) return section;

    const trackingStatus = byId('trackingStatus');
    const trackingCard = trackingStatus?.closest('.card');
    const trackingSection = trackingCard?.parentElement;
    const expertRoot = trackingSection?.parentElement;
    if (!expertRoot || !trackingSection) return null;

    section = document.createElement('section');
    section.id = 'radarViewerSection';
    section.className = 'section card radar-viewer';
    const approachSection = byId('approachingCellsSection');
    expertRoot.insertBefore(section, approachSection || trackingSection);
    return section;
  }

  function product(data, key) {
    return (((data || {}).dpc_observations || {}).products || {})[key] || {};
  }

  function productAvailable(data, key) {
    return product(data, key).ok === true;
  }

  function productStats(info, unit) {
    const stats = Array.isArray(info.stats) ? info.stats : [];
    const requested = [5, 15, 30];
    return requested.map(radius => {
      const row = stats.find(s => Number(s.radius_km) === radius) || {};
      const value = num(row.max);
      return `<div class="radar-stat"><span>MAX ${radius} KM</span><b>${value == null ? '—' : `${fmt(value,1)} ${esc(unit)}`}</b></div>`;
    }).join('');
  }

  function overlaySvg(data, key) {
    const ref = position(REF.lat, REF.lon);
    const tracking = (data || {}).nowcast_tracking || {};
    const cell = tracking.tracked_cell || tracking.cell || {};
    const motion = tracking.motion || {};
    const cellPos = String(tracking.product || '').toUpperCase() === key ? position(cell.lat, cell.lon) : null;
    const direction = num(motion.direction_deg);

    let track = '';
    if (cellPos) {
      let arrow = '';
      if (motion.status === 'tracked' && direction != null) {
        const rad = direction * Math.PI / 180;
        const length = 15;
        const x2 = Math.max(1, Math.min(99, cellPos.x + Math.sin(rad) * length));
        const y2 = Math.max(1, Math.min(99, cellPos.y - Math.cos(rad) * length));
        arrow = `<line x1="${cellPos.x}" y1="${cellPos.y}" x2="${x2}" y2="${y2}" stroke="#7a1f1f" stroke-width="1.2" vector-effect="non-scaling-stroke" marker-end="url(#radarArrowHead)"/>`;
      }
      track = `${arrow}<circle cx="${cellPos.x}" cy="${cellPos.y}" r="2.1" fill="#fff" stroke="#7a1f1f" stroke-width="1.1" vector-effect="non-scaling-stroke"/><text x="${Math.min(94, cellPos.x + 2.8)}" y="${Math.max(5, cellPos.y - 2.2)}" font-size="3.2" font-weight="700" fill="#611818" stroke="#fff" stroke-width=".7" paint-order="stroke">Track ${esc(tracking.track_id || '')}</text>`;
    }

    return `<svg class="radar-overlay" id="radarOverlay" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <defs><marker id="radarArrowHead" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#7a1f1f"/></marker></defs>
      ${ref ? `<circle cx="${ref.x}" cy="${ref.y}" r="2.1" fill="#fff" stroke="#0f6786" stroke-width="1.2" vector-effect="non-scaling-stroke"/><circle cx="${ref.x}" cy="${ref.y}" r=".65" fill="#0f6786"/><text x="${ref.x + 2.8}" y="${ref.y - 2.2}" font-size="3.4" font-weight="800" fill="#0d4d66" stroke="#fff" stroke-width=".8" paint-order="stroke">Giammoro</text>` : ''}
      ${track}
    </svg>`;
  }

  function renderSelected() {
    if (!currentData) return;
    const section = ensureSection();
    if (!section) return;

    if (!productAvailable(currentData, selectedProduct)) {
      selectedProduct = productAvailable(currentData, 'SRI') ? 'SRI' : productAvailable(currentData, 'VMI') ? 'VMI' : selectedProduct;
    }

    const meta = PRODUCT_META[selectedProduct];
    const info = product(currentData, selectedProduct);
    const available = info.ok === true;
    const timeText = info.timestamp || 'timestamp non disponibile';
    const dataLayerUrl = available ? wmsUrl(meta.layer, info.timestamp) : '';
    const boundaryUrl = wmsUrl('radar:regioni');
    const tracking = currentData.nowcast_tracking || {};
    const trackingNote = available && String(tracking.product || '').toUpperCase() === selectedProduct
      ? `Overlay: cella tracciata ${tracking.track_id || ''}${(tracking.motion || {}).status === 'tracked' ? ` · moto ${(tracking.motion || {}).direction || '—'} ${(tracking.motion || {}).speed_kmh ?? '—'} km/h` : ''}.`
      : 'Il tracking viene sovrapposto solo al prodotto radar usato dal tracker corrente.';

    section.innerHTML = `
      <div class="radar-head">
        <div><h2 style="margin:0">Radar</h2><div class="radar-source">Radar-DPC · area ~${RADIUS_KM} km attorno a Giammoro · <a class="source-link" href="https://radar.protezionecivile.it/" target="_blank" rel="noopener">fonte ufficiale</a></div></div>
        <div class="radar-tabs" role="group" aria-label="Prodotto radar">
          ${Object.keys(PRODUCT_META).map(key => `<button type="button" class="radar-tab ${key === selectedProduct ? 'active' : ''}" data-radar-product="${key}" ${productAvailable(currentData,key) ? '' : 'disabled'}>${key}</button>`).join('')}
        </div>
      </div>
      <div class="radar-layout">
        <div class="radar-map" id="radarMap">
          ${available ? `<img class="radar-product-image" id="radarProductImage" src="${esc(dataLayerUrl)}" alt="${esc(meta.label)} nell'area di Giammoro" loading="lazy">` : ''}
          <img class="radar-boundaries" src="${esc(boundaryUrl)}" alt="" loading="lazy">
          ${overlaySvg(currentData, selectedProduct)}
          <div class="radar-loading" id="radarImageStatus">${available ? 'Caricamento radar…' : 'Prodotto non disponibile nel ciclo corrente'}</div>
        </div>
        <div class="radar-side">
          <div class="radar-info"><strong>${esc(meta.label)}</strong><p>${esc(meta.description)} · ${esc(timeText)}${info.age_minutes == null ? '' : ` · ${fmt(info.age_minutes)} min fa`}.</p>${available ? `<div class="radar-stats">${productStats(info, meta.unit)}</div>` : ''}</div>
          <div class="radar-info"><strong>Overlay locale</strong><p>${esc(trackingNote)}</p></div>
          <div class="radar-legend-note">La mappa visualizza il layer WMS ufficiale corrispondente allo stesso timestamp analizzato dal backend. Il marker di Giammoro e la traiettoria sono overlay del progetto e non elementi del prodotto DPC.</div>
        </div>
      </div>`;

    section.querySelectorAll('[data-radar-product]').forEach(button => {
      button.addEventListener('click', () => {
        selectedProduct = button.dataset.radarProduct;
        renderSelected();
      });
    });
    const image = byId('radarProductImage');
    const status = byId('radarImageStatus');
    if (image && status) {
      image.addEventListener('load', () => { status.textContent = 'Radar caricato'; });
      image.addEventListener('error', () => { status.textContent = 'Immagine radar temporaneamente non disponibile'; });
    }
  }

  function render(data) {
    currentData = data || {};
    renderSelected();
  }

  window.renderForecastDashboard = data => {
    if (typeof previousRender === 'function') previousRender(data);
    render(data);
  };
})();
