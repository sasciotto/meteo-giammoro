(() => {
  'use strict';

  const byId = id => document.getElementById(id);
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
  const verificationMetric = (label, value, {unit = '', digits = 0, note = ''} = {}) => {
    const rendered = num(value) == null ? '—' : fmt(value, digits);
    return `<div class="metric"><div class="k">${esc(label)}</div><div class="mv">${rendered}${rendered === '—' ? '' : esc(unit)}</div>${note ? `<div class="ms">${esc(note)}</div>` : ''}</div>`;
  };

  function ensureStyles() {
    if (byId('forecastDashboardStyles')) return;
    const style = document.createElement('style');
    style.id = 'forecastDashboardStyles';
    style.textContent = `
      .forecast-detail{margin-top:14px}
      .forecast-detail .section-title{margin-bottom:13px}
      .forecast-source{font-size:12px;color:var(--muted)}
      .forecast-stale{margin:0 0 12px;padding:10px 12px;border:1px solid #ead8aa;border-radius:11px;background:#fff8e9;color:#654c13;font-size:12px}
      .forecast-unavailable{margin-top:12px;padding:12px 14px;border-radius:12px;background:#f4f6f7;border:1px solid var(--line);color:#56636c}
      .home-nowcast{margin:0 0 14px;padding:15px 16px;border:1px solid var(--line);border-radius:14px;background:var(--surface2)}
      .home-nowcast.calm{background:#eef8f2;border-color:#cee5d7;color:#285c3d}
      .home-nowcast.watch{background:#fff8e9;border-color:#ead8aa;color:#654c13}
      .home-nowcast.incoming{background:#fff4e8;border-color:#e9cfaa;color:#6b4814}
      .home-nowcast.active{background:#fff0f0;border-color:#e8c4c4;color:#702929}
      .home-nowcast-k{font-size:10px;font-weight:800;letter-spacing:.08em;opacity:.72;text-transform:uppercase}
      .home-nowcast-title{font-size:20px;font-weight:800;line-height:1.2;margin-top:3px}
      .home-nowcast-text{font-size:13px;line-height:1.5;margin-top:5px}
      .home-nowcast-detail{font-size:11px;font-weight:700;margin-top:8px;opacity:.82}
      .home-nowcast-signals{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-top:11px}
      .home-nowcast-signal{min-width:0;padding:9px 10px;border:1px solid rgba(100,114,125,.2);border-radius:10px;background:rgba(255,255,255,.58)}
      .home-nowcast-signal span{display:block;font-size:9px;font-weight:800;letter-spacing:.07em;text-transform:uppercase;opacity:.66}
      .home-nowcast-signal b{display:block;margin-top:2px;font-size:11px;line-height:1.35;overflow-wrap:anywhere}
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
      @media(max-width:650px){.day-grid{grid-template-columns:1fr}.hourly-strip{grid-auto-columns:minmax(122px,42vw)}.home-nowcast-title{font-size:18px}.home-nowcast-signals{grid-template-columns:repeat(2,minmax(0,1fr))}}
    `;
    document.head.appendChild(style);
  }

  function simpleNowcastHtml(home) {
    const row = home?.nowcast_simple || {};
    if (!row.title || !row.text) return '';
    const allowed = new Set(['calm', 'watch', 'incoming', 'active']);
    const status = allowed.has(String(row.status || '')) ? row.status : 'watch';
    const indicators = row.indicators || {};
    const signalRows = [
      ['Radar', indicators.radar],
      ['Traiettoria', indicators.trajectory],
      ['Fulmini', indicators.lightning],
      ['Distanza', indicators.distance]
    ].filter(([, value]) => value);
    const signalsHtml = signalRows.length
      ? `<div class="home-nowcast-signals">${signalRows.map(([label, value]) => `<div class="home-nowcast-signal"><span>${esc(label)}</span><b>${esc(value)}</b></div>`).join('')}</div>`
      : (row.detail ? `<div class="home-nowcast-detail">${esc(row.detail)}</div>` : '');
    return `<div class="home-nowcast ${status}" id="homeNowcastSimple" aria-label="Nowcasting semplificato prossime 3 ore">
      <div class="home-nowcast-k">Prossime 3 ore</div>
      <div class="home-nowcast-title">${esc(row.title)}</div>
      <div class="home-nowcast-text">${esc(row.text)}</div>
      ${signalsHtml}
    </div>`;
  }

  function renderVerification(data) {
    const metricsEl = byId('verificationMetrics');
    if (!metricsEl) return;

    const verification = data?.verification || {};
    const summary = verification.summary || {};
    const events = summary.event_metrics || {};
    const total = num(summary.evaluable_results) || 0;
    const binarySamples = num(events.samples) ?? total;
    const eventSamples = num(events.event_samples) || 0;
    const noEventSamples = num(events.no_event_samples) || 0;

    const badgeEl = byId('verificationBadge');
    if (badgeEl) {
      const matureEvents = eventSamples >= 20;
      badgeEl.className = `badge ${matureEvents ? 'online' : total > 0 ? 'warning' : 'unknown'}`;
      badgeEl.textContent = total === 0
        ? 'In raccolta'
        : eventSamples === 0
          ? `${fmt(binarySamples)} campioni · 0 eventi`
          : `${fmt(eventSamples)} eventi / ${fmt(binarySamples)} campioni`;
    }

    const introEl = byId('verificationIntro');
    if (introEl) {
      if (total === 0) {
        introEl.textContent = 'La raccolta è attiva. Le metriche evento saranno calcolate quando maturano i primi campioni verificabili.';
      } else if (eventSamples === 0) {
        introEl.textContent = `${fmt(binarySamples)} campioni binari verificati, ma nessun evento osservato finora. POD e balanced accuracy non sono ancora valutabili; l’accuracy globale descrive soprattutto i non-eventi.`;
      } else if (eventSamples < 20) {
        introEl.textContent = `${fmt(eventSamples)} campioni evento su ${fmt(binarySamples)} verifiche binarie: POD, FAR, CSI e balanced accuracy sono già calcolati ma il campione evento è ancora ridotto.`;
      } else {
        introEl.textContent = `${fmt(eventSamples)} campioni evento su ${fmt(binarySamples)} verifiche binarie. Le metriche evento sono il riferimento principale; l’accuracy globale resta secondaria.`;
      }
    }

    metricsEl.innerHTML = [
      verificationMetric('Campioni evento', eventSamples, {note: `${fmt(noEventSamples)} non-eventi`}),
      verificationMetric('TP', events.true_positive, {note: 'evento previsto e osservato'}),
      verificationMetric('FP', events.false_positive, {note: 'falso allarme'}),
      verificationMetric('FN', events.false_negative, {note: 'evento mancato'}),
      verificationMetric('POD', events.event_detection_percent, {unit: ' %', digits: 1, note: 'event detection / recall'}),
      verificationMetric('FAR', events.false_alarm_ratio_percent, {unit: ' %', digits: 1, note: 'false alarm ratio'}),
      verificationMetric('CSI', events.csi_percent, {unit: ' %', digits: 1, note: 'critical success index'}),
      verificationMetric('Balanced accuracy', events.balanced_accuracy_percent, {unit: ' %', digits: 1}),
      verificationMetric('Precision', events.precision_percent, {unit: ' %', digits: 1}),
      verificationMetric('Campioni ETA', summary.eta_samples, {note: 'previsioni con ETA valutabile'}),
      verificationMetric('Errore ETA', summary.eta_mae_minutes, {unit: ' min', digits: 1, note: 'MAE'}),
      verificationMetric('Campioni traiettoria', summary.trajectory_samples, {note: 'track valutabili'}),
      verificationMetric('Errore traiettoria', summary.trajectory_mae_km, {unit: ' km', digits: 1, note: 'MAE'}),
      verificationMetric('Accuracy globale', summary.accuracy_percent, {unit: ' %', digits: 1, note: 'metrica secondaria; può essere dominata dai non-eventi'})
    ].join('');

    const confidenceEl = byId('verificationConfidence');
    if (confidenceEl) confidenceEl.textContent = summary.note || 'Metriche sperimentali ex-post; interpretare la qualità degli eventi soprattutto tramite POD, FAR, CSI e balanced accuracy.';
  }

  function ensureSection() {
    ensureStyles();
    let section = byId('forecastDetail');
    if (!section) {
      section = document.createElement('section');
      section.id = 'forecastDetail';
      section.className = 'section card forecast-detail';
      const summaryCards = byId('homeSummaryCards');
      if (summaryCards?.parentElement) {
        summaryCards.parentElement.insertBefore(section, summaryCards);
      } else {
        const alertCard = byId('homeAlertCard');
        const homeSection = alertCard?.parentElement;
        if (homeSection && alertCard) homeSection.insertBefore(section, alertCard);
      }
    }
    return section;
  }

  function render(data) {
    renderVerification(data);
    const section = ensureSection();
    if (!section) return;

    const home = data?.home_summary || {};
    const hourly = Array.isArray(home.hourly) ? home.hourly.slice(0, 8) : [];
    const days = Array.isArray(home.days) ? home.days.slice(0, 2) : [];
    const nowcastHtml = simpleNowcastHtml(home);

    if (!home.forecast_available || (!hourly.length && !days.length)) {
      section.innerHTML = `
        <div class="section-title"><div><h2>Previsione per Giammoro</h2><div class="forecast-source">Aggiornata a ogni ciclo</div></div></div>
        ${nowcastHtml}
        <div class="forecast-unavailable"><strong>Previsione temporaneamente non disponibile</strong><br>I dati osservativi, radar e fulminazioni restano comunque aggiornati.</div>`;
      return;
    }

    const staleHtml = home.stale
      ? `<div class="forecast-stale"><strong>Dato precedente.</strong> Ultima previsione valida di circa ${fmt(home.stale_age_minutes)} minuti fa; ${esc(home.stale_reason || 'fonte temporaneamente non disponibile')}.</div>`
      : '';

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

    section.innerHTML = `
      <div class="section-title"><div><h2>Previsione per Giammoro</h2><div class="forecast-source">Scenario orario ${esc(home.source || 'modello di riferimento')} · aggiornato automaticamente</div></div></div>
      ${nowcastHtml}
      ${staleHtml}
      <div class="hourly-strip" aria-label="Previsione oraria">${hourHtml}</div>
      <div class="day-grid">${dayHtml}</div>`;
  }

  window.renderForecastDashboard = render;
})();
