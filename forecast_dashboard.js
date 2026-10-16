(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = value => {
    const x = Number(value);
    return Number.isFinite(x) ? x : null;
  };
  const fmt = (value, digits = 0) => {
    const x = num(value);
    return x == null ? '—' : x.toLocaleString('it-IT', {minimumFractionDigits: digits, maximumFractionDigits: digits});
  };

  function ensureStyles() {
    if (byId('forecastDashboardStyles')) return;
    const style = document.createElement('style');
    style.id = 'forecastDashboardStyles';
    style.textContent = `
      .forecast-detail{margin-top:14px}
      .forecast-detail .section-title{margin-bottom:13px}
      .forecast-source{font-size:12px;color:var(--muted)}
      .hourly-strip{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(128px,1fr);gap:9px;overflow-x:auto;padding-bottom:5px;scroll-snap-type:x proximity}
      .hour-cell{scroll-snap-align:start;background:var(--surface2);border:1px solid var(--line);border-radius:13px;padding:12px;min-height:142px}
      .hour-time{font-size:12px;font-weight:760;color:var(--muted)}
      .hour-icon{font-size:27px;line-height:1.2;margin:5px 0 2px}
      .hour-temp{font-size:23px;font-weight:780}
      .hour-cond{font-size:12px;color:#40505b;min-height:36px}
      .hour-meta{font-size:11px;color:var(--muted);margin-top:7px}
      .day-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:13px}
      .day-card{border:1px solid var(--line);border-radius:14px;padding:14px;background:var(--surface)}
      .day-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
      .day-title{font-weight:780;font-size:17px}
      .day-icon{font-size:28px}
      .day-range{font-size:21px;font-weight:770;margin-top:5px}
      .day-meta{font-size:12px;color:var(--muted);margin-top:5px}
      .day-basis{font-size:10px;color:var(--muted);margin-top:7px}
      .model-outlook{margin-top:12px;padding:12px 14px;border-radius:12px;background:#f4f8fa;border:1px solid var(--line)}
      .model-outlook strong{display:block;margin-bottom:3px}
      .model-outlook.warning{background:#fff8e9;border-color:#ead8aa;color:#654c13}
      .model-outlook.online{background:#eef8f2;border-color:#cee5d7;color:#285c3d}
      .model-outlook.unknown{background:#f4f6f7;color:#56636c}
      .model-values{font-size:11px;margin-top:6px;opacity:.85}
      .forecast-summary-two{grid-template-columns:repeat(2,1fr)}
      @media(max-width:650px){.day-grid{grid-template-columns:1fr}.hourly-strip{grid-auto-columns:minmax(122px,42vw)}.forecast-summary-two{grid-template-columns:1fr 1fr}}
      @media(max-width:430px){.forecast-summary-two{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }

  function uncertainty(row) {
    const agreement = String(row?.agreement || '').toLowerCase();
    if (agreement.includes('alto') || agreement.includes('buon')) return ['Accordo modellistico buono', 'online'];
    if (agreement.includes('medio')) return ['Scenario da monitorare', 'warning'];
    if (agreement.includes('bass')) return ['Incertezza modellistica elevata', 'warning'];
    return ['Incertezza in valutazione', 'unknown'];
  }

  function consensusHtml(home, data) {
    const mm = home?.multi_model || {};
    if (mm.available) {
      const [label, klass] = uncertainty(mm);
      const models = Array.isArray(mm.models) ? mm.models : [];
      const values = models.map(m => `${esc(m.label)} ${fmt(m.precip_mm,1)} mm`).join(' · ');
      return {
        label: mm.label || label,
        klass,
        text: `${mm.wet_models}/${mm.models_count} modelli indicano pioggia ≥0,5 mm nelle 3–48 h. Intervallo ${fmt(mm.precip_min_mm,1)}–${fmt(mm.precip_max_mm,1)} mm; mediana ${fmt(mm.precip_median_mm,1)} mm.`,
        values
      };
    }
    const modelRow = (data.models || []).find(x => String(x.horizon || '').includes('3–48')) || {};
    const [label, klass] = uncertainty(modelRow);
    return {
      label,
      klass,
      text: modelRow.note || modelRow.signal || 'Confronto multi-modello in aggiornamento.',
      values: modelRow.signal || ''
    };
  }

  function hideLegacyCombinedForecast() {
    const title = byId('homeForecastTitle');
    const legacyCard = title?.closest('.forecast-card');
    if (!legacyCard) return;
    const grid = legacyCard.parentElement;
    legacyCard.style.display = 'none';
    if (grid) grid.classList.add('forecast-summary-two');
  }

  function render(data) {
    const home = data?.home_summary || {};
    const hourly = Array.isArray(home.hourly) ? home.hourly.slice(0, 8) : [];
    const days = Array.isArray(home.days) ? home.days.slice(0, 2) : [];
    if (!home.forecast_available || (!hourly.length && !days.length)) return;

    ensureStyles();
    let section = byId('forecastDetail');
    if (!section) {
      section = document.createElement('section');
      section.id = 'forecastDetail';
      section.className = 'section card forecast-detail';
      const alertCard = byId('homeAlertCard');
      const homeSection = alertCard?.parentElement;
      if (homeSection && alertCard) homeSection.insertBefore(section, alertCard);
    }
    if (!section) return;

    hideLegacyCombinedForecast();

    const hourHtml = hourly.map(h => {
      const rain = num(h.precipitation) || 0;
      const gust = num(h.gust_kmh);
      return `<div class="hour-cell">
        <div class="hour-time">${esc(h.label_time || '—')}</div>
        <div class="hour-icon" aria-hidden="true">${esc(h.icon || '•')}</div>
        <div class="hour-temp">${fmt(h.temperature,1)} °C</div>
        <div class="hour-cond">${esc(h.label || '')}</div>
        <div class="hour-meta">Pioggia ${fmt(rain,1)} mm<br>Vento ${fmt(h.wind_kmh)} km/h${gust == null ? '' : ` · raff. ${fmt(gust)}`}</div>
      </div>`;
    }).join('');

    const dayHtml = days.map(day => `<div class="day-card">
      <div class="day-head"><div><div class="k">${esc(day.label || '')}</div><div class="day-title">${esc(day.condition || 'Previsione')}</div></div><div class="day-icon" aria-hidden="true">${esc(day.icon || '•')}</div></div>
      <div class="day-range">${fmt(day.temp_min,1)}° / ${fmt(day.temp_max,1)}°</div>
      <div class="day-meta">Pioggia ${fmt(day.precipitation_sum,1)} mm · raffiche max ${fmt(day.gust_max_kmh)} km/h${day.thunder_signal ? ' · possibile segnale temporalesco' : ''}</div>
      <div class="day-basis">Scenario orario: ${esc(day.basis || home.source || 'modello di riferimento')}</div>
    </div>`).join('');

    const consensus = consensusHtml(home, data);

    section.innerHTML = `
      <div class="section-title"><div><h2>Previsione per Giammoro</h2><div class="forecast-source">Aggiornata a ogni ciclo · base oraria ${esc(home.source || 'modello locale')} · consenso multi-modello 3–48 h</div></div></div>
      <div class="hourly-strip" aria-label="Previsione oraria">${hourHtml}</div>
      <div class="day-grid">${dayHtml}</div>
      <div class="model-outlook ${consensus.klass}"><strong>${esc(consensus.label)}</strong>${esc(consensus.text)}${consensus.values ? `<div class="model-values">${consensus.values}</div>` : ''}</div>`;
  }

  function refreshForecast() {
    fetch(`data.json?forecast=${Date.now()}`, {cache:'no-store'})
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(render)
      .catch(() => {});
  }

  window.addEventListener('load', () => {
    setTimeout(refreshForecast, 900);
    setInterval(refreshForecast, 300000);
  });
})();
