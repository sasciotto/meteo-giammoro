(() => {
  'use strict';

  // Layout only: never create meteorological observations or radar imagery.
  const byId = id => document.getElementById(id);
  const RADAR_URL = 'https://radar.protezionecivile.it/#/pages/dashboard?zoom=6';
  let stationsExpanded = false;

  const styles = [
    'body.mode-home{background:linear-gradient(180deg,#d9ebf5 0%,#e5f2f9 46%,#d9eaf3 100%);--surface:#e7f4fb;--surface2:#dceefa;--text:#132e48;--muted:#45687f;--line:#b8d5e6;--accent:#116b92}',
    'body.mode-home .wrap{max-width:1220px;width:100%;min-width:0;padding:16px}',
    'body.mode-home .hero{background:linear-gradient(115deg,#0c416d,#16729d);border-radius:20px;padding:19px 25px;box-shadow:0 10px 24px rgba(17,65,100,.13);gap:16px}',
    'body.mode-home .hero h1{font-size:clamp(27px,3.6vw,41px);font-weight:830;line-height:1.12;color:#fff;letter-spacing:-.03em}',
    'body.mode-home .hero-meta{font-size:12px;line-height:1.45;background:rgba(9,48,79,.45);border:1px solid rgba(225,244,255,.25);color:#f2f9ff;padding:10px 14px}',
    'body.mode-home .hero-meta .muted{color:#e0eef7}',
    'body.mode-home .home-auto-refresh{color:#c9f4e1;font-size:10px}',
    'body.mode-home .navbar{margin:11px 0 14px}',
    'body.mode-home .mode-switch{background:#c4e0ef;border:1px solid #9fc8dd}',
    'body.mode-home .mode-btn{min-height:42px}',
    'body.mode-home .weather-main{background:transparent;border:0;box-shadow:none;overflow:visible}',
    'body.mode-home .weather-main:before{display:none}',
    'body.mode-home .weather-main-inner{display:grid;grid-template-columns:minmax(0,.94fr) minmax(0,1.06fr);gap:14px;padding:0;align-items:stretch}',
    'body.mode-home .weather-top{display:grid;grid-template-columns:92px minmax(0,1fr);gap:16px;align-content:center;align-items:center;min-width:0;min-height:224px;padding:25px;border-radius:21px;background:linear-gradient(125deg,#08436f,#0876aa);border:1px solid #166c9b;box-shadow:0 10px 22px rgba(13,72,110,.13)}',
    'body.mode-home .weather-icon{width:92px;height:92px;min-width:92px;font-size:60px;border-radius:23px;border:1px solid rgba(238,249,255,.28);background:rgba(226,246,255,.17);filter:none}',
    'body.mode-home .weather-top .weather-place{color:#cceaf8;font-size:11px;margin-bottom:8px}',
    'body.mode-home .weather-top .weather-temp{color:#fff;font-size:clamp(57px,5.5vw,79px);font-weight:830;line-height:.99}',
    'body.mode-home .weather-top .weather-description{color:#fff;font-size:clamp(19px,2vw,26px);line-height:1.2;margin-top:12px}',
    'body.mode-home .weather-top .weather-subline{color:#e1f4fb;font-size:12px}',
    'body.mode-home .weather-top .weather-badge{grid-column:2;justify-self:start;text-align:left}',
    'body.mode-home .weather-main .quick-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin:0;gap:10px;padding:9px;border:1px solid #c6dfec;border-radius:21px;background:#eaf5fb}',
    'body.mode-home .weather-main .quick{display:flex;flex-direction:column;min-width:0;min-height:0;align-items:center;text-align:center;justify-content:center;gap:6px;padding:13px 7px;border:1px solid #c7e1ee;border-radius:17px;background:linear-gradient(155deg,#d9edf9,#cae5f4);box-shadow:none}',
    'body.mode-home .weather-main .quick .k{display:flex;flex-direction:column;align-items:center;gap:5px;font-size:12px;color:#21485e;line-height:1.2;text-transform:none;letter-spacing:0}',
    'body.mode-home .weather-main .quick .k>span:last-child{font-size:12px;font-weight:740;line-height:1.3}',
    'body.mode-home .weather-main .quick .quick-icon{width:35px;height:35px;flex:0 0 35px;background:transparent;color:#117aaf}',
    'body.mode-home .quick-icon svg{width:27px;height:27px}',
    'body.mode-home .weather-main .quick b{margin:4px 0 0;font-size:clamp(17px,1.6vw,23px);font-weight:800;color:#14324b;letter-spacing:-.03em;overflow-wrap:anywhere}',
    'body.mode-home .weather-main .quick span{color:#415e71;font-size:11px}',
    'body.mode-home .quick .wind-line{justify-content:center;gap:5px}',
    'body.mode-home .quick .wind-compass{width:20px;height:20px;flex:0 0 20px}',
    'body.mode-home .quick .wind-text{font-size:10px}',
    'body.mode-home #forecastDetail{background:transparent;border:0;box-shadow:none;padding:0;margin-top:17px}',
    'body.mode-home #forecastDetail>.section-title{display:none}',
    'body.mode-home .home-nowcast-stage{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,.92fr);gap:16px;padding:19px;border-radius:20px;background:linear-gradient(113deg,#09627b,#0b456e);box-shadow:0 9px 21px rgba(15,74,108,.13);color:#fff}',
    'body.mode-home #forecastDetail .home-nowcast{margin:0;min-width:0;background:transparent;border:0;padding:0;color:#fff}',
    'body.mode-home #forecastDetail .home-nowcast.calm,body.mode-home #forecastDetail .home-nowcast.watch,body.mode-home #forecastDetail .home-nowcast.incoming,body.mode-home #forecastDetail .home-nowcast.active{background:transparent;border:0;color:#fff}',
    'body.mode-home #forecastDetail .home-nowcast-k{font-size:12px;color:#d9f2fb;letter-spacing:.05em;opacity:1}',
    'body.mode-home #forecastDetail .home-nowcast-title{font-size:clamp(19px,2vw,25px);line-height:1.23;color:#fff;margin-top:8px}',
    'body.mode-home #forecastDetail .home-nowcast-text{font-size:13px;font-weight:500;color:#e3f2fa;line-height:1.55}',
    'body.mode-home #forecastDetail .home-nowcast-signals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:17px}',
    'body.mode-home #forecastDetail .home-nowcast-signal{background:#d8ecf5;border:1px solid #b8d9e8;padding:10px 11px;border-radius:10px;color:#1c465d}',
    'body.mode-home #forecastDetail .home-nowcast-signal span{color:#58778a;font-size:10px;letter-spacing:.025em;opacity:1}',
    'body.mode-home #forecastDetail .home-nowcast-signal b{font-size:12px;line-height:1.45;color:#17465e}',
    'body.mode-home .render-radar-panel{display:flex;flex-direction:column;gap:8px;min-width:0}',
    'body.mode-home .render-radar-media{position:relative;display:flex;flex:1;align-items:stretch;justify-content:center;min-height:235px;border:1px solid rgba(194,231,246,.4);border-radius:15px;background:linear-gradient(140deg,#082e4f,#0b476a);overflow:hidden}',
    'body.mode-home .render-radar-media img{display:block;width:100%;height:245px;max-height:350px;object-fit:contain;object-position:center}',
    'body.mode-home .render-radar-fallback{display:flex;align-items:center;justify-content:center;flex:1;padding:24px;text-align:center;color:#e6f3fa;font-size:13px;line-height:1.6}',
    'body.mode-home .render-radar-title{font-size:16px;font-weight:790;color:#fff}',
    'body.mode-home .render-radar-meta{font-size:11px;color:#d0e7f5;line-height:1.4}',
    'body.mode-home .render-radar-link{color:#fff;text-decoration:underline;text-underline-offset:3px;font-weight:700}',
    'body.mode-home .render-hourly-panel{margin-top:17px;padding:20px;border:1px solid #c4dfed;border-radius:19px;background:#e3f2fa;box-shadow:0 6px 15px rgba(21,79,112,.06)}',
    'body.mode-home .render-hourly-panel .forecast-block-heading{margin:0 0 13px;align-items:center}',
    'body.mode-home .render-hourly-panel .forecast-block-heading h3{font-size:23px;color:#183e5b}',
    'body.mode-home .render-hourly-panel .forecast-block-eyebrow{font-size:11px}',
    'body.mode-home .render-hourly-panel .hourly-strip{display:grid;grid-auto-columns:minmax(130px,1fr);gap:9px;scrollbar-width:thin}',
    'body.mode-home .render-hourly-panel .hour-cell{background:#f0f8fd;border-color:#c4dfed;border-radius:14px;min-height:173px;text-align:center}',
    'body.mode-home .render-hourly-panel .hour-icon{font-size:29px}',
    'body.mode-home .render-hourly-panel .hour-meta{font-size:10px}',
    'body.mode-home .render-lower-grid.stations-only{grid-template-columns:1fr}',
    'body.mode-home .render-lower-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr);gap:14px;margin-top:17px;align-items:stretch}',
    'body.mode-home .render-day-panel{min-width:0;padding:17px;border:1px solid #c6dfec;border-radius:18px;background:#e2f1fa}',
    'body.mode-home .render-day-panel .forecast-day-heading{margin:0 0 10px}',
    'body.mode-home .render-day-panel .forecast-block-heading h3{font-size:21px}',
    'body.mode-home .render-day-panel .day-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:0}',
    'body.mode-home .render-day-panel .day-card{border:1px solid #c6e0eb;border-radius:13px;background:#f0f8fc;padding:13px;min-width:0}',
    'body.mode-home .render-day-panel .day-title{font-size:14px}',
    'body.mode-home .render-day-panel .day-icon{font-size:25px}',
    'body.mode-home .render-day-panel .day-range{font-size:18px}',
    'body.mode-home .render-day-panel .day-meta{font-size:11px;line-height:1.5}',
    'body.mode-home .render-day-panel .day-basis{font-size:10px}',
    'body.mode-home .render-lower-grid .home-stations{margin:0;min-width:0;padding:16px 17px;background:#e5f3fb;border:1px solid #c5dfea;border-radius:18px;box-shadow:none}',
    'body.mode-home .render-lower-grid .home-stations .section-title h2{font-size:21px}',
    'body.mode-home .render-lower-grid .home-stations-grid{display:grid;grid-template-columns:1fr;gap:0;margin-top:12px}',
    'body.mode-home .render-lower-grid .home-station-item{display:grid;grid-template-columns:minmax(0,1fr) auto auto;align-items:center;gap:2px 10px;min-width:0;background:transparent;border:0;border-radius:0;border-bottom:1px solid #c2dce9;padding:10px 2px}',
    'body.mode-home .render-lower-grid .home-station-item b{font-size:13px;grid-column:1;color:#193b54}',
    'body.mode-home .render-lower-grid .home-station-item small{font-size:10px;color:#5b778b;margin:0;grid-column:1;line-height:1.35}',
    'body.mode-home .render-lower-grid .home-station-item .home-station-observation{grid-column:2;grid-row:1;font-size:17px;margin:0;text-align:right;white-space:nowrap}',
    'body.mode-home .render-lower-grid .home-station-item small:last-child{grid-column:2 / 4;grid-row:2;text-align:right}',
    'body.mode-home .render-lower-grid .home-station-wind{grid-column:3;grid-row:1;font-size:11px;color:#466c80;white-space:nowrap}',
    'body.mode-home .render-lower-grid .home-station-item.is-collapsed{display:none}',
    'body.mode-home .render-stations-toggle{margin-top:12px;min-height:38px;background:#d0e9f5;border:1px solid #abd3e5;color:#195a7c;border-radius:10px;padding:8px 12px;font-size:12px;font-weight:760;cursor:pointer}',
    'body.mode-home .home-alert{margin-top:14px}',
    'body.mode-home .render-sources{margin-top:19px;padding:0;border:1px solid #c2dce9;border-radius:16px;background:#dbeef8;overflow:hidden}',
    'body.mode-home .render-sources summary{cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:57px;padding:15px 18px;color:#19425d;font-size:17px;font-weight:780;list-style:none}',
    'body.mode-home .render-sources summary::-webkit-details-marker{display:none}',
    'body.mode-home .render-sources summary:after{content:"+";font-size:20px}',
    'body.mode-home .render-sources[open] summary:after{content:"−"}',
    'body.mode-home .render-sources .home-observation-strip{margin:0 14px 14px;padding:13px;background:#f0f7fb;border-color:#c5ddeb}',
    'body.mode-home .render-sources-note{font-size:12px;font-weight:450;color:#577488}',
    '@media(max-width:1000px){body.mode-home .weather-main-inner{grid-template-columns:1fr}body.mode-home .weather-main .quick-grid{grid-template-columns:repeat(4,minmax(0,1fr))}body.mode-home .render-lower-grid{grid-template-columns:1fr 1fr}body.mode-home .render-day-panel .day-grid{grid-template-columns:1fr}}',
    '@media(max-width:740px){body.mode-home .wrap{padding:11px}body.mode-home .hero{padding:15px 16px}body.mode-home .hero h1{font-size:clamp(25px,6vw,32px)}body.mode-home .weather-main .quick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}body.mode-home .weather-top{min-height:0;grid-template-columns:65px minmax(0,1fr);padding:18px;gap:12px}body.mode-home .weather-icon{width:65px;height:65px;min-width:65px;font-size:40px}body.mode-home .weather-top .weather-temp{font-size:clamp(46px,10vw,64px)}body.mode-home .weather-top .weather-description{font-size:20px}body.mode-home .home-nowcast-stage{grid-template-columns:1fr;padding:15px;gap:15px}body.mode-home .render-radar-media{min-height:180px;max-height:260px}body.mode-home .render-hourly-panel{padding:15px}body.mode-home .render-hourly-panel .hourly-strip{grid-auto-columns:minmax(130px,54vw)}body.mode-home .render-lower-grid{grid-template-columns:1fr}body.mode-home .render-day-panel .day-grid{grid-template-columns:1fr 1fr}}',
    '@media(max-width:430px){body.mode-home .hero-meta{font-size:11px}body.mode-home .weather-top{grid-template-columns:55px minmax(0,1fr);padding:14px;gap:9px}body.mode-home .weather-icon{width:55px;height:55px;min-width:55px;font-size:35px}body.mode-home .weather-top .weather-temp{font-size:clamp(39px,10.5vw,48px)}body.mode-home .weather-top .weather-description{font-size:17px}body.mode-home .weather-main .quick-grid{padding:7px;gap:7px}body.mode-home .weather-main .quick{padding:10px 7px;min-height:100px}body.mode-home .weather-main .quick b{font-size:18px}body.mode-home .weather-main .quick .k>span:last-child{font-size:11px}body.mode-home .render-hourly-panel .hourly-strip{grid-auto-columns:minmax(118px,66vw)}body.mode-home .render-day-panel{padding:13px}body.mode-home .render-day-panel .day-grid{grid-template-columns:1fr}body.mode-home #forecastDetail .home-nowcast-signals{grid-template-columns:1fr 1fr}body.mode-home .render-sources summary{font-size:15px}}',
    '@media(max-width:520px){body.mode-home .render-lower-grid .home-station-item{grid-template-columns:minmax(0,1fr) auto}body.mode-home .render-lower-grid .home-station-wind{grid-column:2;grid-row:2;text-align:right}body.mode-home .render-lower-grid .home-station-item small:last-child{grid-column:1 / -1;grid-row:3;text-align:left}}',
    '@media(max-width:335px){body.mode-home .weather-main .quick-grid{grid-template-columns:1fr 1fr}body.mode-home .weather-top .weather-temp{font-size:37px}body.mode-home #forecastDetail .home-nowcast-signals{grid-template-columns:1fr}body.mode-home .render-radar-media{min-height:155px}}'
  ].join('\n');

  function ensureStyles() {
    if (byId('renderMatchStyles')) return;
    const style = document.createElement('style');
    style.id = 'renderMatchStyles';
    style.textContent = styles;
    document.head.appendChild(style);
  }

  function make(className, tag = 'div') {
    const element = document.createElement(tag);
    element.className = className;
    return element;
  }

  function radarPreview(data) {
    const panel = make('render-radar-panel', 'aside');
    panel.setAttribute('aria-label', 'Anteprima radar ufficiale');
    const title = make('render-radar-title');
    title.textContent = 'Radar-DPC ufficiale';
    const sri = data?.dpc_observations?.products?.SRI || {};
    const observed = Date.parse(sri.timestamp || '');
    const check = Date.parse(data?.meta?.last_check_iso || '');
    const now = Date.now();
    const fresh = sri.ok === true && Number.isFinite(observed) && Number.isFinite(check)
      && observed <= now + 5 * 60000 && check <= now + 5 * 60000
      && now - observed >= 0 && now - observed < 30 * 60000
      && now - check >= 0 && now - check < 35 * 60000;
    const meta = make('render-radar-meta');
    meta.textContent = fresh
      ? 'SRI: ' + new Intl.DateTimeFormat('it-IT', {hour:'2-digit', minute:'2-digit', timeZone:'Europe/Rome', timeZoneName:'short'}).format(new Date(observed)) + ' · prodotto radar; orario distinto dallo screenshot'
      : 'SRI: dato attuale non verificabile';
    const media = make('render-radar-media');
    const link = make('render-radar-link', 'a');
    link.href = RADAR_URL;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'Apri radar interattivo ufficiale';
    function fallback() {
      media.replaceChildren();
      const notice = make('render-radar-fallback');
      notice.textContent = 'Anteprima radar non disponibile o non recente. Consulta la piattaforma ufficiale.';
      media.appendChild(notice);
    }
    if (fresh) {
      const img = document.createElement('img');
      img.src = 'radar-dpc.png?v=' + encodeURIComponent(data.meta.last_check_iso);
      img.alt = 'Schermata acquisita della piattaforma radar ufficiale DPC; non è una mappa locale ricostruita';
      img.loading = 'lazy';
      img.addEventListener('error', fallback, {once:true});
      media.appendChild(img);
    } else {
      fallback();
    }
    panel.append(title, media, meta, link);
    return panel;
  }

  function updateStations() {
    const stationSection = byId('homeStationsOverview');
    const list = stationSection?.querySelector('.home-stations-grid');
    if (!list) return;
    const rows = Array.from(list.querySelectorAll('.home-station-item'));
    rows.forEach((row, index) => row.classList.toggle('is-collapsed', !stationsExpanded && index >= 4));
    let button = stationSection.querySelector('.render-stations-toggle');
    if (rows.length <= 4) {
      if (button) button.remove();
      return;
    }
    if (!button) {
      button = make('render-stations-toggle', 'button');
      button.type = 'button';
      button.addEventListener('click', () => {
        stationsExpanded = !stationsExpanded;
        updateStations();
      });
      stationSection.appendChild(button);
    }
    button.textContent = stationsExpanded ? 'Mostra meno stazioni' : 'Mostra tutte le ' + rows.length + ' stazioni';
    button.setAttribute('aria-expanded', String(stationsExpanded));
  }

  function arrangeForecast(data) {
    const section = byId('forecastDetail');
    const nowcast = byId('homeNowcastSimple');
    const home = byId('weatherMain')?.closest('.home-only');
    if (!section || !home) return;

    if (nowcast && nowcast.parentElement === section) {
      const stage = make('home-nowcast-stage');
      section.insertBefore(stage, nowcast);
      stage.append(nowcast, radarPreview(data));
    }

    const heading = section.querySelector('.forecast-block-heading:not(.forecast-day-heading)');
    const hourly = section.querySelector('.hourly-strip');
    if (heading && hourly) {
      const panel = make('render-hourly-panel');
      section.insertBefore(panel, heading);
      panel.append(heading, hourly);
    }

    const dayHeading = section.querySelector('.forecast-day-heading');
    const dayGrid = section.querySelector('.day-grid');
    let lower = byId('renderLowerGrid');
    if (!lower) {
      lower = make('render-lower-grid');
      lower.id = 'renderLowerGrid';
    }
    section.after(lower);
    let dayPanel = lower.querySelector('.render-day-panel');
    if (!dayPanel) {
      dayPanel = make('render-day-panel');
      lower.appendChild(dayPanel);
    }
    const hasDays = Boolean(dayHeading && dayGrid);
    lower.classList.toggle('stations-only', !hasDays);
    dayPanel.hidden = !hasDays;
    if (hasDays) dayPanel.replaceChildren(dayHeading, dayGrid);
    else dayPanel.replaceChildren();

    const stations = byId('homeStationsOverview');
    if (stations) {
      lower.appendChild(stations);
      updateStations();
    }
    const alert = byId('homeAlertCard');
    if (alert && alert.parentElement === home) {
      const active = ['warning','orange','red'].includes(String(data?.alert?.level_class || '').toLowerCase());
      if (active) home.insertBefore(alert, section);
      else lower.after(alert);
    }
  }

  function foldSources() {
    const source = byId('homeObservationStrip');
    if (!source) return;
    let details = byId('renderSources');
    if (!details) {
      details = make('render-sources', 'details');
      details.id = 'renderSources';
      const summary = document.createElement('summary');
      const title = document.createElement('span');
      title.textContent = 'Fonti e metodologia';
      const note = make('render-sources-note', 'small');
      note.textContent = 'Osservazioni, radar, fulminazioni e modelli';
      summary.append(title, note);
      details.appendChild(summary);
      byId('homeObservationStrip')?.before(details);
    }
    details.appendChild(source);
  }

  function render(data) {
    ensureStyles();
    arrangeForecast(data || {});
    foldSources();
  }

  const previousRender = window.renderForecastDashboard;
  window.renderForecastDashboard = data => {
    if (typeof previousRender === 'function') previousRender(data);
    render(data);
  };
})();