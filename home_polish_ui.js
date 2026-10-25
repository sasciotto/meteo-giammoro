(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const num = value => {
    const x = Number(value);
    return Number.isFinite(x) ? x : null;
  };
  const fmt = (value, digits = 0) => {
    const x = num(value);
    return x == null ? '—' : x.toLocaleString('it-IT', {minimumFractionDigits: digits, maximumFractionDigits: digits});
  };

  function ensureStyles() {
    if (byId('homePolishStyles')) return;
    const style = document.createElement('style');
    style.id = 'homePolishStyles';
    style.textContent = `
      .hero{padding:4px 2px 10px;align-items:center}
      .hero h1{font-size:clamp(27px,4vw,38px);margin-bottom:4px}
      .hero .sub{font-size:13px}
      .hero-meta{display:flex;flex-direction:column;align-items:flex-end;gap:2px;padding:8px 11px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.72);line-height:1.25}
      .home-auto-refresh{display:inline-flex;align-items:center;gap:6px;margin-top:3px;font-size:10px;font-weight:760;color:var(--ok);letter-spacing:.02em}
      .home-auto-refresh:before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 0 3px rgba(38,116,71,.10)}
      .weather-main-inner{padding:22px 24px}
      .weather-top{gap:17px}
      .weather-icon{font-size:clamp(54px,8vw,78px);min-width:82px}
      .weather-temp{font-size:clamp(54px,8vw,76px)}
      .weather-description{font-size:clamp(22px,2.6vw,28px);max-width:760px}
      .weather-subline{font-size:14px}
      .quick-grid{margin-top:17px}
      .home-observation-strip{position:relative;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-top:11px;padding:10px 12px;border:1px solid rgba(216,225,230,.88);border-radius:12px;background:rgba(255,255,255,.55);font-size:11px;color:var(--muted);backdrop-filter:blur(8px)}
      .home-observation-main{font-weight:700;color:#40505b}
      .home-observation-sources{display:flex;gap:6px;flex-wrap:wrap}
      .home-observation-chip{padding:4px 7px;border:1px solid var(--line);border-radius:999px;background:rgba(255,255,255,.72);white-space:nowrap}
      #homeSummaryCards{display:none!important}
      #forecastDetail{padding:16px 17px}
      #forecastDetail .section-title{align-items:center;margin-bottom:11px}
      #forecastDetail .section-title h2{font-size:21px}
      #forecastDetail .forecast-source{font-size:11px}
      .home-forecast-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
      .home-radar-action{border:1px solid var(--accent);background:#eef7fb;color:var(--accent);border-radius:999px;padding:8px 12px;font:inherit;font-size:12px;font-weight:800;cursor:pointer}
      .home-radar-action:hover{background:#e3f2f8}
      .home-nowcast{padding:16px 17px;margin-bottom:10px}
      .home-nowcast-k{font-size:10px}
      .home-nowcast-title{font-size:22px}
      .home-nowcast-text{font-size:17px;font-weight:640;line-height:1.55;max-width:900px;margin-top:7px}
      .home-nowcast-signals{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
      .home-nowcast-signal{padding:8px 9px}
      .home-nowcast-timeline{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin:0 0 13px}
      .home-nowcast-step{padding:10px 11px;border:1px solid var(--line);border-radius:11px;background:var(--surface2)}
      .home-nowcast-step-time{font-size:10px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
      .home-nowcast-step-main{display:flex;align-items:center;gap:8px;margin-top:4px;font-size:13px;font-weight:770;color:#34434e;line-height:1.3}
      .home-nowcast-step-icon{display:inline-flex;align-items:center;justify-content:center;flex:0 0 30px;width:30px;height:30px;font-size:24px;line-height:1;filter:drop-shadow(0 2px 4px rgba(20,32,42,.08))}
      .home-nowcast-step-condition{min-width:0}
      .home-nowcast-step-meta{margin-top:5px;font-size:10px;color:var(--muted)}
      #forecastDetail .hourly-strip{display:none}
      #forecastDetail .day-grid{margin-top:8px}
      .home-alert.home-alert-compact{padding:10px 13px;gap:10px;border-left-width:4px;background:#f6fbf8}
      .home-alert.home-alert-compact .home-alert-symbol{font-size:21px}
      .home-alert.home-alert-compact .k{display:none}
      .home-alert.home-alert-compact .home-alert-title{font-size:14px}
      .home-alert.home-alert-compact .home-alert-text{display:none}
      .home-alert.home-alert-compact .home-alert-link{font-size:11px}
      @media(max-width:700px){
        .hero{align-items:flex-start}.hero-meta{align-items:flex-start;text-align:left;padding:7px 9px}.weather-main-inner{padding:18px}.home-nowcast-text{font-size:16px;line-height:1.5}.home-nowcast-signals{grid-template-columns:repeat(2,minmax(0,1fr))}.home-nowcast-timeline{grid-template-columns:repeat(2,minmax(0,1fr))}.home-observation-strip{display:block}.home-observation-sources{margin-top:7px}#forecastDetail .section-title{display:block}.home-forecast-actions{margin-top:9px}
      }
      @media(max-width:430px){
        .hero h1{font-size:29px}.hero-meta{margin-top:7px}.weather-icon{font-size:49px;min-width:58px}.weather-temp{font-size:55px}.weather-main-inner{padding:16px}.home-nowcast-title{font-size:19px}.home-nowcast-timeline{grid-template-columns:1fr 1fr}.home-nowcast-step-icon{flex-basis:27px;width:27px;height:27px;font-size:22px}
      }
    `;
    document.head.appendChild(style);
  }

  function bestSupportStation(data) {
    const stations = Array.isArray(data?.stations) ? data.stations : [];
    return stations.find(station => station && station.status === 'online' && !station.excluded_from_analysis) || null;
  }

  function shortSource(value) {
    const text = String(value || '').trim();
    if (!text) return null;
    if (text.includes('Radar-DPC TEMP')) return 'Temperatura: Radar-DPC TEMP';
    if (text.includes('Radar-DPC SRT1')) return 'Pioggia: Radar-DPC SRT1';
    if (text.length > 42) return text.slice(0, 39) + '…';
    return text;
  }

  function renderObservationStrip(data) {
    const inner = document.querySelector('#weatherMain .weather-main-inner');
    if (!inner) return;

    let strip = byId('homeObservationStrip');
    if (!strip) {
      strip = document.createElement('div');
      strip.id = 'homeObservationStrip';
      strip.className = 'home-observation-strip';
      inner.appendChild(strip);
    }

    const metrics = data?.territory?.metrics || {};
    const station = bestSupportStation(data);
    const support = station
      ? `Supporto osservativo: ${station.display_name || station.name}${station.updated ? ` · ${station.updated}` : ''}`
      : 'Supporto osservativo locale non disponibile';

    const sources = [
      shortSource(metrics.temperature?.quality),
      shortSource(metrics.rain_1h?.quality),
      'Stazioni circostanti usate come controllo'
    ].filter(Boolean);

    strip.replaceChildren();
    const main = document.createElement('div');
    main.className = 'home-observation-main';
    main.textContent = `Riferimento: coordinate di Giammoro · ${support}`;
    strip.appendChild(main);

    const sourceWrap = document.createElement('div');
    sourceWrap.className = 'home-observation-sources';
    sources.forEach(source => {
      const chip = document.createElement('span');
      chip.className = 'home-observation-chip';
      chip.textContent = source;
      sourceWrap.appendChild(chip);
    });
    strip.appendChild(sourceWrap);
  }

  function forecastStepLabel(row, index) {
    const time = String(row?.label_time || '').trim();
    if (time) return time;
    return index === 0 ? 'Prossima ora' : `+${index + 1} h`;
  }

  function fallbackWeatherIcon(label) {
    const text = String(label || '').toLowerCase();
    if (text.includes('temporal')) return '⛈';
    if (text.includes('piogg')) return '☂';
    if (text.includes('neve')) return '❄';
    if (text.includes('nebb')) return '≋';
    if (text.includes('molto nuvol')) return '☁';
    if (text.includes('parzial') || text.includes('poco nuvol')) return '⛅';
    if (text.includes('sereno')) return '☀';
    return '•';
  }

  function renderNowcastTimeline(data) {
    const card = byId('homeNowcastSimple');
    if (!card) return;

    const kicker = card.querySelector('.home-nowcast-k');
    if (kicker) kicker.textContent = 'Nowcast 0–3 h · osservazioni prioritarie';

    let timeline = byId('homeNowcastTimeline');
    if (!timeline) {
      timeline = document.createElement('div');
      timeline.id = 'homeNowcastTimeline';
      timeline.className = 'home-nowcast-timeline';
      card.insertAdjacentElement('afterend', timeline);
    }

    const rows = Array.isArray(data?.home_summary?.hourly) ? data.home_summary.hourly.slice(0, 4) : [];
    timeline.replaceChildren();
    rows.forEach((row, index) => {
      const rain = num(row?.precipitation);
      const step = document.createElement('div');
      step.className = 'home-nowcast-step';

      const time = document.createElement('div');
      time.className = 'home-nowcast-step-time';
      time.textContent = forecastStepLabel(row, index);

      const main = document.createElement('div');
      main.className = 'home-nowcast-step-main';

      const icon = document.createElement('span');
      icon.className = 'home-nowcast-step-icon';
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = String(row?.icon || fallbackWeatherIcon(row?.label));

      const condition = document.createElement('span');
      condition.className = 'home-nowcast-step-condition';
      condition.textContent = row?.label || 'Scenario orario';
      main.append(icon, condition);

      const meta = document.createElement('div');
      meta.className = 'home-nowcast-step-meta';
      meta.textContent = rain == null ? 'Pioggia: —' : `Pioggia modello: ${fmt(rain, 1)} mm`;

      step.append(time, main, meta);
      timeline.appendChild(step);
    });

    timeline.hidden = rows.length === 0;
  }

  function renderForecastHeader(data) {
    const section = byId('forecastDetail');
    const titleWrap = section?.querySelector('.section-title');
    if (!section || !titleWrap) return;

    const heading = titleWrap.querySelector('h2');
    if (heading) heading.textContent = 'Prossime ore · Oggi e domani';
    const source = titleWrap.querySelector('.forecast-source');
    if (source) {
      const basis = data?.home_summary?.source || 'modello di riferimento';
      source.textContent = `Nowcast osservativo 0–3 h · scenario orario ${basis}`;
    }

    let actions = titleWrap.querySelector('.home-forecast-actions');
    if (!actions) {
      actions = document.createElement('div');
      actions.className = 'home-forecast-actions';
      const radar = document.createElement('button');
      radar.type = 'button';
      radar.className = 'home-radar-action';
      radar.textContent = 'Radar live →';
      radar.addEventListener('click', () => byId('radarBtn')?.click());
      actions.appendChild(radar);
      titleWrap.appendChild(actions);
    }
  }

  function renderAlert(data) {
    const card = byId('homeAlertCard');
    if (!card) return;
    const level = String(data?.alert?.level_class || '').toLowerCase();
    const active = ['warning', 'orange', 'red'].includes(level);
    card.classList.toggle('home-alert-compact', !active);

    if (!active) {
      const symbol = card.querySelector('.home-alert-symbol');
      if (symbol) symbol.textContent = '✓';
      const title = byId('homeAlertTitle');
      if (title) title.textContent = 'Nessuna allerta meteo ufficiale attiva';
    }
  }

  function renderRefreshStatus() {
    const meta = document.querySelector('.hero-meta');
    if (!meta || byId('homeAutoRefresh')) return;
    const row = document.createElement('div');
    row.id = 'homeAutoRefresh';
    row.className = 'home-auto-refresh';
    row.textContent = 'Aggiornamento automatico · controllo 60 s';
    meta.appendChild(row);
  }

  function render(data) {
    ensureStyles();
    renderRefreshStatus();
    renderObservationStrip(data);
    renderForecastHeader(data);
    renderNowcastTimeline(data);
    renderAlert(data);
  }

  const original = window.renderForecastDashboard;
  window.renderForecastDashboard = data => {
    if (typeof original === 'function') original(data);
    render(data);
  };
})();
