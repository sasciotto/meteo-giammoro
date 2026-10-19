(() => {
  'use strict';

  const previousRender = window.renderForecastDashboard;
  const byId = id => document.getElementById(id);
  const OFFICIAL_RADAR_URL = 'https://radar.protezionecivile.it/#/pages/dashboard?zoom=6';

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

  function ensureStyles() {
    if (byId('radarViewerStyles')) return;
    const style = document.createElement('style');
    style.id = 'radarViewerStyles';
    style.textContent = `
      .radar-viewer{margin-top:14px;overflow:hidden}
      .radar-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}
      .radar-source{font-size:12px;color:var(--muted);margin-top:3px;line-height:1.45}
      .radar-layout{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(250px,.65fr);gap:12px;align-items:start}
      .radar-shot-wrap{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:14px;background:var(--surface2);min-height:330px}
      .radar-shot{width:100%;height:auto;display:block;aspect-ratio:14/9;object-fit:cover;background:#e7edf0}
      .radar-shot-link{display:block;color:inherit;text-decoration:none}
      .radar-shot-caption{position:absolute;left:10px;bottom:10px;padding:6px 9px;border-radius:999px;background:rgba(255,255,255,.92);border:1px solid var(--line);font-size:11px;color:#40505b;box-shadow:0 2px 8px rgba(0,0,0,.08)}
      .radar-shot-fallback{min-height:330px;display:flex;align-items:center;justify-content:center;text-align:center;padding:24px;color:var(--muted);line-height:1.5}
      .radar-side{display:grid;gap:9px}
      .radar-info{border:1px solid var(--line);border-radius:12px;background:var(--surface2);padding:11px}
      .radar-info strong{display:block;font-size:15px}.radar-info p{margin:4px 0 0;font-size:12px;color:var(--muted);line-height:1.45}
      .radar-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}
      .radar-stat{padding:8px;border-radius:9px;background:var(--surface);border:1px solid var(--line)}
      .radar-stat b{display:block;font-size:14px}.radar-stat span{font-size:10px;color:var(--muted)}
      .radar-open{display:inline-flex;align-items:center;gap:5px;margin-top:9px;font-size:12px;font-weight:760}
      .radar-note{font-size:11px;color:var(--muted);line-height:1.45}
      @media(max-width:820px){.radar-layout{grid-template-columns:1fr}.radar-head{display:block}.radar-shot-wrap,.radar-shot-fallback{min-height:260px}}
      @media(max-width:520px){.radar-stats{grid-template-columns:1fr 1fr 1fr}.radar-shot-wrap,.radar-shot-fallback{min-height:210px}}
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

  function statsHtml(info, unit) {
    const stats = Array.isArray(info.stats) ? info.stats : [];
    return [5, 15, 30].map(radius => {
      const row = stats.find(item => Number(item.radius_km) === radius) || {};
      const value = num(row.max);
      return `<div class="radar-stat"><span>MAX ${radius} KM</span><b>${value == null ? '—' : `${fmt(value,1)} ${esc(unit)}`}</b></div>`;
    }).join('');
  }

  function localProductCard(label, info, unit, description) {
    const available = info?.ok === true;
    const timestamp = info?.timestamp || 'timestamp non disponibile';
    return `<div class="radar-info">
      <strong>${esc(label)}</strong>
      <p>${esc(description)} · ${esc(timestamp)}${info?.age_minutes == null ? '' : ` · ${fmt(info.age_minutes)} min fa`}.</p>
      ${available ? `<div class="radar-stats">${statsHtml(info, unit)}</div>` : '<p>Prodotto non disponibile nel ciclo corrente.</p>'}
    </div>`;
  }

  function trackingCard(data) {
    const tr = data?.nowcast_tracking || {};
    const cell = tr.tracked_cell || tr.cell || {};
    const motion = tr.motion || {};
    if (tr.status !== 'detected') {
      return '<div class="radar-info"><strong>Tracking locale</strong><p>Nessuna cella radar tracciata in questo ciclo.</p></div>';
    }
    const parts = [`cella a ${fmt(cell.distance_km,1)} km ${esc(cell.bearing || '')}`];
    if (motion.status === 'tracked') {
      parts.push(`moto ${esc(motion.direction || '—')} a ${fmt(motion.speed_kmh,1)} km/h`);
      parts.push(motion.approaching ? `avvicinamento ${fmt(motion.approach_rate_kmh,1)} km/h` : 'traiettoria non diretta verso Giammoro');
    }
    return `<div class="radar-info"><strong>Tracking locale</strong><p>${parts.join(' · ')}.</p></div>`;
  }

  function render(data) {
    const section = ensureSection();
    if (!section) return;

    const sri = product(data, 'SRI');
    const vmi = product(data, 'VMI');
    const version = encodeURIComponent(data?.meta?.last_check_iso || Date.now());

    section.innerHTML = `
      <div class="radar-head">
        <div>
          <h2 style="margin:0">Radar-DPC ufficiale</h2>
          <div class="radar-source">Screenshot della piattaforma radar della Protezione Civile acquisito dal workflow durante l'aggiornamento. Clic sull'immagine per aprire la mappa interattiva originale.</div>
        </div>
        <a class="source-link" href="${OFFICIAL_RADAR_URL}" target="_blank" rel="noopener">Apri radar interattivo</a>
      </div>
      <div class="radar-layout">
        <div class="radar-shot-wrap" id="radarShotWrap">
          <a class="radar-shot-link" href="${OFFICIAL_RADAR_URL}" target="_blank" rel="noopener">
            <img class="radar-shot" id="radarOfficialShot" src="radar-dpc.png?v=${version}" alt="Screenshot della piattaforma Radar-DPC ufficiale" loading="lazy">
          </a>
          <div class="radar-shot-caption">Radar-DPC · schermata reale della piattaforma ufficiale</div>
        </div>
        <div class="radar-side">
          ${localProductCard('SRI · precipitazione', sri, 'mm/h', 'Massimi radar attorno a Giammoro')}
          ${localProductCard('VMI · riflettività', vmi, 'dBZ', 'Massimi di riflettività attorno a Giammoro')}
          ${trackingCard(data)}
          <div class="radar-note">Lo screenshot non viene modificato né usato per calcolare il tracking. I numeri locali a destra derivano dai prodotti Radar-DPC elaborati separatamente dal backend del progetto.</div>
        </div>
      </div>`;

    const image = byId('radarOfficialShot');
    const wrap = byId('radarShotWrap');
    image?.addEventListener('error', () => {
      if (!wrap) return;
      wrap.innerHTML = `<div class="radar-shot-fallback"><div>Anteprima Radar-DPC non disponibile in questo aggiornamento.<br><a class="source-link radar-open" href="${OFFICIAL_RADAR_URL}" target="_blank" rel="noopener">Apri la piattaforma radar ufficiale</a></div></div>`;
    });
  }

  window.renderForecastDashboard = data => {
    if (typeof previousRender === 'function') previousRender(data);
    render(data || {});
  };
})();
