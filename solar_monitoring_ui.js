(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = value => { const x = Number(value); return Number.isFinite(x) ? x : null; };

  function ensureStyles() {
    if (byId('solarMonitoringStyles')) return;
    const style = document.createElement('style');
    style.id = 'solarMonitoringStyles';
    style.textContent = `
      .solar-only{display:none}body.mode-solar .solar-only{display:block}
      .solar-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:12px}
      .solar-head h2{margin:0;font-size:25px}.solar-head p{margin:5px 0 0;color:var(--muted);max-width:790px;line-height:1.5}
      .solar-status{text-align:right;min-width:150px}.solar-status .small{margin-top:4px}
      .solar-hero{display:grid;grid-template-columns:1.25fr .75fr;gap:12px;margin-top:12px}
      .solar-main{padding:20px;background:linear-gradient(135deg,#fff8df 0%,#fff 68%)}
      .solar-main-value{font-size:clamp(44px,8vw,70px);font-weight:830;line-height:.95;letter-spacing:-.045em;margin-top:8px}
      .solar-main-unit{font-size:18px;font-weight:720;color:#5b6670;margin-left:5px}.solar-main-note{margin-top:10px;color:#52616b;font-size:13px;line-height:1.5}
      .solar-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-top:12px}.solar-metric{background:var(--surface2);border:1px solid var(--line);border-radius:12px;padding:12px}.solar-metric b{display:block;font-size:20px;margin-top:3px}.solar-metric span{display:block;font-size:10px;color:var(--muted);margin-top:2px;line-height:1.35}
      .solar-detail-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:12px}.solar-note{margin-top:12px;padding:12px 13px;border:1px solid var(--line);border-radius:12px;background:var(--surface2);font-size:12px;line-height:1.5}.solar-note strong{display:block;margin-bottom:3px}.solar-note.warn{border-left:4px solid var(--warn);background:#fff9eb}.solar-note.info{border-left:4px solid var(--accent);background:#f3f8fa}
      .solar-source{margin-top:10px;font-size:11px;color:var(--muted);line-height:1.5}.solar-source a,.ground-source{color:var(--accent);font-weight:700;text-decoration:none}.solar-source a:hover,.ground-source:hover{text-decoration:underline}
      .ground-title{margin-top:16px}.ground-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:9px}.ground-card{border:1px solid var(--line);border-radius:13px;padding:13px;background:var(--surface2)}.ground-card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.ground-card h3{margin:2px 0 0;font-size:16px}.ground-values{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.ground-value{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px}.ground-value b{display:block;font-size:23px}.ground-meta{margin-top:8px;font-size:11px;color:var(--muted);line-height:1.45}.ground-note{margin-top:8px;font-size:11px;line-height:1.45}
      @media(max-width:900px){.solar-hero{grid-template-columns:1fr}.solar-status{text-align:left}.solar-detail-grid{grid-template-columns:repeat(2,1fr)}}
      @media(max-width:650px){.solar-head{display:block}.solar-status{margin-top:8px}.solar-metrics,.solar-detail-grid,.ground-grid{grid-template-columns:1fr 1fr}}
      @media(max-width:520px){.ground-grid{grid-template-columns:1fr}}
      @media(max-width:430px){.solar-metrics,.solar-detail-grid{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }

  function ensureView() {
    ensureStyles();
    const switcher = document.querySelector('.mode-switch');
    const footer = document.querySelector('footer.foot');
    if (!switcher || !footer?.parentElement) return null;
    let button = byId('solarBtn');
    if (!button) {
      button = document.createElement('button'); button.id = 'solarBtn'; button.type = 'button'; button.className = 'mode-btn'; button.textContent = 'Solare'; switcher.appendChild(button);
    }
    let view = byId('solarView');
    if (!view) {
      view = document.createElement('section'); view.id = 'solarView'; view.className = 'solar-only';
      view.innerHTML = `<div class="card"><div class="solar-head"><div><div class="k">MONITORAGGIO SOLARE</div><h2>Radiazione solare su Giammoro</h2><p>Confronto tra stime satellitari sul punto di Giammoro e sensori reali al suolo nelle stazioni vicine. Le stazioni esterne restano sempre identificate con il loro vero nome e non vengono assimilate a Giammoro.</p></div><div class="solar-status"><span class="badge unknown" id="solarStatus">—</span><div class="small muted" id="solarObserved">—</div></div></div><div id="solarContent"><div class="solar-note">Dati solari non ancora caricati.</div></div></div>`;
      footer.parentElement.insertBefore(view, footer);
    }
    return {button, view};
  }

  const formatNumber = (value, digits = 0) => { const x = num(value); return x == null ? '—' : x.toLocaleString('it-IT', {minimumFractionDigits:digits, maximumFractionDigits:digits}); };
  function formatTime(value) {
    if (!value) return '—';
    try { return new Intl.DateTimeFormat('it-IT', {timeZone:'Europe/Rome', day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'}).format(new Date(value)); } catch (_) { return String(value); }
  }
  function statusInfo(status) {
    if (status === 'ok') return ['Disponibile', 'online'];
    if (status === 'stale') return ['Dato precedente', 'warning'];
    if (status === 'credentials_missing') return ['Satellite in attesa', 'warning'];
    return ['Non disponibile', 'unknown'];
  }
  function activateSolar() {
    document.body.className = 'mode-solar'; document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active')); byId('solarBtn')?.classList.add('active');
  }
  function safeLink(url, label) {
    try { const parsed = new URL(url, window.location.href); if (!['http:', 'https:'].includes(parsed.protocol)) return ''; return `<a class="ground-source" href="${esc(parsed.href)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`; } catch (_) { return ''; }
  }

  function groundCard(item) {
    const online = item?.status === 'ok';
    const badge = online ? '<span class="badge online">Disponibile</span>' : '<span class="badge unknown">Non disponibile</span>';
    const solar = num(item?.solar_wm2); const uv = num(item?.uv_index);
    const when = item?.observed_at ? `Osservazione ${formatTime(item.observed_at)}` : item?.retrieved_at ? `Acquisizione ${formatTime(item.retrieved_at)}` : 'Timestamp non disponibile';
    const distance = num(item?.distance_km);
    return `<div class="ground-card"><div class="ground-card-head"><div><div class="k">OSSERVAZIONE AL SUOLO</div><h3>${esc(item?.name || 'Stazione')}</h3></div>${badge}</div><div class="ground-values"><div class="ground-value"><div class="k">RADIAZIONE</div><b>${solar == null ? '—' : `${formatNumber(solar,0)} W/m²`}</b></div><div class="ground-value"><div class="k">UV</div><b>${uv == null ? '—' : formatNumber(uv,1)}</b></div></div><div class="ground-meta">${esc(when)}${distance == null ? '' : ` · ${formatNumber(distance,1)} km da Giammoro`} · ${safeLink(item?.source_url, item?.source || 'Fonte')}</div><div class="ground-note">${esc(item?.note || '')}</div></div>`;
  }

  function render(data) {
    const created = ensureView(); if (!created) return;
    const solar = data?.solar_monitoring || {}; const observation = solar?.observation || null; const daily = solar?.daily || null; const ground = Array.isArray(solar?.ground_observations) ? solar.ground_observations : [];
    const [label, klass] = statusInfo(solar?.status); const status = byId('solarStatus'); if (status) { status.className = `badge ${klass}`; status.textContent = label; }
    const observed = byId('solarObserved'); if (observed) { const age = num(observation?.age_minutes); observed.textContent = observation?.observed_at ? `${formatTime(observation.observed_at)}${age == null ? '' : ` · ${age} min fa`}` : 'Satellite non disponibile'; }
    const content = byId('solarContent'); if (!content) return;

    const groundHtml = `<div class="ground-title"><div class="k">RETE DI CONTROLLO AL SUOLO</div></div><div class="ground-grid">${ground.length ? ground.map(groundCard).join('') : '<div class="solar-note">Nessuna stazione al suolo configurata.</div>'}</div>`;
    if (!observation) {
      content.innerHTML = `<div class="solar-note warn"><strong>${esc(solar?.message || 'Dato satellitare non disponibile')}</strong>Le osservazioni al suolo restano indipendenti da LSA SAF: quando un sensore vicino è leggibile viene mostrato anche senza credenziali satellitari.</div>${groundHtml}`;
      return;
    }

    const total = num(observation.total_shortwave_wm2); const direct = num(observation.direct_horizontal_wm2); const diffuse = num(observation.diffuse_wm2); const directFraction = num(observation.direct_fraction); const diffuseFraction = num(observation.diffuse_fraction); const energy = num(daily?.energy_kwh_m2); const coverage = num(daily?.coverage_minutes); const samples = num(daily?.samples);
    content.innerHTML = `<div class="solar-hero"><div class="solar-main card"><div class="k">RADIAZIONE SOLARE TOTALE AL SUOLO · SATELLITE</div><div class="solar-main-value">${formatNumber(total,0)}<span class="solar-main-unit">W/m²</span></div><div class="solar-main-note">Valore LSA SAF sul punto di griglia più vicino a Giammoro.</div><div class="solar-metrics"><div class="solar-metric"><div class="k">Componente diretta</div><b>${formatNumber(direct,0)} W/m²</b><span>Derivata da DSSF totale e frazione diffusa.</span></div><div class="solar-metric"><div class="k">Quota diretta</div><b>${directFraction == null ? '—' : formatNumber(directFraction*100,0)+'%'}</b><span>Quota non diffusa; non è una percentuale meteorologica di sole.</span></div><div class="solar-metric"><div class="k">Componente diffusa</div><b>${formatNumber(diffuse,0)} W/m²</b><span>${diffuseFraction == null ? 'Frazione diffusa non disponibile' : formatNumber(diffuseFraction*100,0)+'% del totale'}</span></div></div></div><div class="card"><div class="k">ENERGIA SOLARE ACCUMULATA OGGI</div><div class="v">${energy == null ? '—' : formatNumber(energy,2)+' kWh/m²'}</div><div class="small muted">Integrazione progressiva delle osservazioni satellitari effettivamente raccolte.</div><div class="solar-note"><strong>Copertura disponibile</strong>${coverage == null ? '—' : formatNumber(coverage,0)+' min'}${samples == null ? '' : ` · ${formatNumber(samples,0)} campioni`}.</div></div></div><div class="solar-detail-grid"><div class="solar-metric"><div class="k">Aerosol AOD 550 nm</div><b>${formatNumber(observation.aod_550nm,3)}</b><span>Parametro tecnico del prodotto.</span></div><div class="solar-metric"><div class="k">Indice di opacità</div><b>${formatNumber(observation.opacity_index,3)}</b><span>Indicatore tecnico LSA SAF.</span></div><div class="solar-metric"><div class="k">Quality flag</div><b>${formatNumber(observation.quality_flag,0)}</b><span>Flag grezzo del prodotto.</span></div><div class="solar-metric"><div class="k">Punto di griglia</div><b>${formatNumber(observation?.grid_point?.latitude,2)}°, ${formatNumber(observation?.grid_point?.longitude,2)}°</b><span>Pixel NetCDF utilizzato.</span></div></div>${groundHtml}<div class="solar-source">Fonte satellitare: ${safeLink(observation.source_url || solar.source_url, observation.source || solar.source || 'EUMETSAT LSA SAF MDSSFTD')}<br>${esc(solar?.message || '')}</div>`;
  }

  const created = ensureView();
  if (created) { created.button.addEventListener('click', activateSolar); ['homeBtn','expertBtn','radarBtn','eventsBtn'].forEach(id => byId(id)?.addEventListener('click', () => created.button.classList.remove('active'))); }
  window.renderSolarMonitoring = render;
})();
