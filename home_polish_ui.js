(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const num = value => {
    // Missing values are unknown, never a measured/modelled zero.
    if (value === null || value === undefined || value === '' ||
        (typeof value === 'string' && !value.trim())) return null;
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

    // New visual layer is scoped to the public Meteo view. The expert / radar
    // views keep their existing layout, while data provenance stays in footer.
    style.textContent += `
      body.mode-home{background:radial-gradient(ellipse at 12% 0%,rgba(212,232,243,.66),transparent 43%),#edf3f6;color:#142b40}
      body.mode-home .wrap{max-width:1200px;padding-top:22px}
      body.mode-home .hero{padding:4px 1px 17px;gap:15px}
      body.mode-home .hero h1{font-size:clamp(28px,3.6vw,40px);font-weight:820;letter-spacing:-.04em;color:#142b40;line-height:1.14}
      body.mode-home .hero .sub{font-size:13px;color:#566d7c;margin-top:4px}
      body.mode-home .hero-meta{border:1px solid #d9e5ec;background:rgba(255,255,255,.8);border-radius:15px;box-shadow:0 3px 14px rgba(20,43,64,.04);padding:11px 14px}
      body.mode-home .navbar{margin-bottom:16px}
      body.mode-home .mode-switch{padding:4px;background:#dae7ee;border-radius:14px}
      body.mode-home .mode-btn{border-radius:10px;min-height:38px;font-weight:740}
      body.mode-home .card,body.mode-home .home-stations{border-color:#dae5eb;box-shadow:0 8px 26px rgba(30,55,75,.055)}
      body.mode-home .weather-main{border:1px solid #cfdee8;border-radius:23px;box-shadow:0 17px 44px rgba(34,67,87,.095)}
      body.mode-home .weather-main.calm:before{background:linear-gradient(112deg,#dfeff9 0%,#f5fbfe 67%,#fff 100%)}
      body.mode-home .weather-main.cloudy:before{background:linear-gradient(112deg,#dfe8f1 0%,#f6f9fc 69%,#fff 100%)}
      body.mode-home .weather-main.rain:before{background:linear-gradient(112deg,#d5e4f0 0%,#f2f8fc 69%,#fff 100%)}
      body.mode-home .weather-main.storm:before{background:linear-gradient(112deg,#e4e5f2 0%,#f5f4fb 69%,#fff 100%)}
      body.mode-home .weather-main-inner{padding:29px 30px}
      body.mode-home .weather-top{grid-template-columns:96px minmax(0,1fr) auto;gap:25px;align-items:center}
      body.mode-home .weather-top>div:nth-child(2){min-width:0}
      body.mode-home .weather-icon{display:flex;align-items:center;justify-content:center;min-width:96px;width:96px;height:96px;font-size:61px;line-height:1;background:rgba(255,255,255,.7);border:1px solid rgba(255,255,255,.92);border-radius:26px;filter:drop-shadow(0 5px 10px rgba(20,50,70,.06))}
      body.mode-home .weather-place{font-size:11px;font-weight:820;letter-spacing:.11em;color:#496e83;text-transform:uppercase;margin-bottom:11px}
      body.mode-home .weather-temp{font-size:clamp(62px,8vw,96px);font-weight:820;letter-spacing:-.067em;line-height:.98;font-variant-numeric:tabular-nums;color:#102f43}
      body.mode-home .weather-description{font-size:clamp(21px,2.5vw,29px);font-weight:730;line-height:1.22;margin-top:12px;color:#24495e}
      body.mode-home .weather-subline{font-size:13px;color:#506c7a}
      body.mode-home .weather-gust{margin-top:13px;border-radius:999px;padding:6px 11px;font-size:12px;letter-spacing:.01em;background:#fdf3df;border-color:#e6d3aa;color:#77521e}
      body.mode-home .weather-gust.strong,body.mode-home .weather-gust.severe{background:#fcebe8;border-color:#e6b8af;color:#9b3d2e}
      body.mode-home .weather-badge[hidden]{display:none}
      body.mode-home .quick-grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:26px}
      body.mode-home .quick{min-width:0;min-height:121px;background:rgba(255,255,255,.82);border:1px solid #dce7ec;border-radius:17px;padding:14px 16px;box-shadow:0 2px 8px rgba(31,64,82,.025)}
      body.mode-home .quick .k{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:780;letter-spacing:.02em;color:#5c7484}
      body.mode-home .quick .k .quick-icon{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:9px;background:#edf5f8;color:#166f89;flex:0 0 28px}
      body.mode-home .quick .k>span:last-child{display:inline;min-width:0;font-size:11px;line-height:1.3}
      body.mode-home .quick-icon svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
      body.mode-home .quick b{font-size:clamp(18px,2vw,24px);font-weight:800;letter-spacing:-.025em;margin-top:9px;color:#18384b}
      body.mode-home .quick span{font-size:11px;line-height:1.4}
      body.mode-home .quick .wind-line{margin-top:6px;gap:7px}
      body.mode-home .quick .wind-compass{flex:0 0 24px;width:24px;height:24px}
      body.mode-home #forecastDetail{margin-top:18px;padding:22px 22px 23px;border-radius:20px}
      body.mode-home #forecastDetail>.section-title{margin-bottom:16px}
      body.mode-home #forecastDetail>.section-title h2{font-size:clamp(20px,2.6vw,26px);font-weight:790;letter-spacing:-.035em;color:#142b40}
      body.mode-home #forecastDetail .home-nowcast{border-radius:16px;border-width:1px;padding:18px 19px;margin-bottom:17px}
      body.mode-home #forecastDetail .home-nowcast-title{font-size:clamp(19px,2vw,23px);font-weight:790}
      body.mode-home #forecastDetail .home-nowcast-text{font-size:14px;line-height:1.58}
      body.mode-home #forecastDetail .home-nowcast-signals{grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
      body.mode-home #forecastDetail .home-nowcast-signal{border-radius:10px;background:rgba(255,255,255,.73)}
      body.mode-home .forecast-block-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:14px;margin:23px 1px 12px}
      body.mode-home .forecast-block-eyebrow{font-size:10px;font-weight:800;letter-spacing:.1em;color:#658091}
      body.mode-home .forecast-block-heading h3{font-size:19px;line-height:1.25;margin:3px 0 0;color:#1b3b4e;font-weight:800;letter-spacing:-.025em}
      body.mode-home .forecast-block-hint{font-size:11px;color:#718795;text-align:right}
      body.mode-home #forecastDetail .hourly-strip{display:grid;grid-auto-columns:minmax(146px,1fr);gap:10px;scrollbar-width:thin;overscroll-behavior-inline:contain;padding:2px 2px 10px}
      body.mode-home #forecastDetail .hourly-strip:focus-visible{outline:2px solid #16718d;outline-offset:3px}
      body.mode-home #forecastDetail .hour-cell{border-radius:14px;min-height:181px;padding:14px 13px;background:#f5f9fc;border-color:#dfe9ee;box-shadow:0 2px 5px rgba(20,45,65,.02)}
      body.mode-home #forecastDetail .hour-time{font-size:12px;color:#5a7586}
      body.mode-home #forecastDetail .hour-icon{font-size:29px;margin-top:7px}
      body.mode-home #forecastDetail .hour-temp{font-size:24px;color:#18384b;letter-spacing:-.03em}
      body.mode-home #forecastDetail .hour-cond{font-size:11px;min-height:29px;line-height:1.35}
      body.mode-home #forecastDetail .hour-meta{line-height:1.55;border-top:1px solid #e0e9ef;padding-top:8px;margin-top:10px;font-size:10px}
      body.mode-home #forecastDetail .forecast-day-heading{margin-top:25px}
      body.mode-home #forecastDetail .day-grid{margin-top:0;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
      body.mode-home #forecastDetail .day-card{border-radius:15px;background:#f9fbfc;border-color:#dde7ed;padding:16px}
      body.mode-home #forecastDetail .day-title{color:#18394c}
      body.mode-home #forecastDetail .day-meta{line-height:1.5}
      body.mode-home #forecastDetail .home-model-outlook{margin-top:19px;margin-bottom:0;background:#f4f7f9;border-color:#e0e9ef}
      body.mode-home .home-stations{margin-top:18px;padding:20px 21px;border-radius:20px;background:#fff}
      body.mode-home .home-stations .section-title h2{font-size:21px;font-weight:800;letter-spacing:-.025em}
      body.mode-home .home-stations-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
      body.mode-home .home-station-item{background:#f8fafc;border-radius:13px;padding:14px;border-color:#e1eaf0}
      body.mode-home .home-station-item b{font-size:13px;color:#25485c}
      body.mode-home .home-station-observation{font-size:20px;letter-spacing:-.025em;color:#173a4d;font-variant-numeric:tabular-nums}
      body.mode-home #homeAlertCard{margin-top:16px;border-radius:15px}
      body.mode-home #homeAlertCard.home-alert-compact{background:#f4f8f6;color:#2d604c}
      body.mode-home #homeObservationStrip{border-radius:15px;background:#f7fafc;border-color:#dce7ee;margin-top:22px;padding:14px 16px}
      body.mode-home #homeObservationStrip .home-observation-main{font-size:11px;font-weight:650;line-height:1.55}
      body.mode-home #homeObservationStrip .home-observation-chip{font-size:10px;color:#526c7c}
      @media(max-width:940px){
        body.mode-home .quick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
        body.mode-home .home-stations-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
        body.mode-home .weather-top{grid-template-columns:88px minmax(0,1fr);gap:17px}
        body.mode-home .weather-icon{width:88px;height:88px;min-width:88px;font-size:54px}
        body.mode-home .weather-badge{grid-column:1 / -1}
      }
      @media(max-width:650px){
        body.mode-home .wrap{padding:13px}
        body.mode-home .hero{align-items:flex-start}
        body.mode-home .weather-main-inner{padding:19px}
        body.mode-home .weather-main{border-radius:20px}
        body.mode-home .weather-top{grid-template-columns:68px minmax(0,1fr);gap:13px}
        body.mode-home .weather-icon{width:68px;height:68px;min-width:68px;font-size:43px;border-radius:17px}
        body.mode-home .weather-place{font-size:10px;margin-bottom:8px}
        body.mode-home .weather-temp{font-size:clamp(49px,11vw,69px)}
        body.mode-home .weather-description{font-size:clamp(18px,4.2vw,23px)}
        body.mode-home .quick-grid{gap:8px;margin-top:19px}
        body.mode-home .quick{padding:12px;min-height:106px;border-radius:13px}
        body.mode-home .quick .k{font-size:10px}
        body.mode-home .quick b{font-size:19px}
        body.mode-home #forecastDetail{padding:18px 14px}
        body.mode-home #forecastDetail .home-nowcast{padding:15px}
        body.mode-home #forecastDetail .home-nowcast-signals{grid-template-columns:repeat(2,minmax(0,1fr))}
        body.mode-home #forecastDetail .hourly-strip{grid-auto-columns:minmax(144px,44vw)}
        body.mode-home .forecast-block-hint{max-width:108px}
        body.mode-home #forecastDetail .day-grid{grid-template-columns:1fr}
        body.mode-home .home-stations{padding:17px 14px}
        body.mode-home .home-stations-grid{grid-template-columns:1fr}
      }
      @media(max-width:390px){
        body.mode-home .weather-top{grid-template-columns:56px minmax(0,1fr);gap:10px}
        body.mode-home .weather-icon{width:56px;height:56px;min-width:56px;font-size:36px}
        body.mode-home .weather-temp{font-size:47px}
        body.mode-home .quick{padding:10px 9px}
        body.mode-home .quick-icon{width:24px;height:24px;flex-basis:24px}
      }
      @media(prefers-reduced-motion:reduce){
        body.mode-home .mode-btn,body.mode-home .weather-main *{transition:none!important}
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
    const footer = document.querySelector('main .foot');
    if (!footer) return;

    let strip = byId('homeObservationStrip');
    if (!strip) {
      strip = document.createElement('section');
      strip.id = 'homeObservationStrip';
      strip.className = 'home-only home-observation-strip';
      strip.setAttribute('aria-label', 'Riferimenti e fonti delle osservazioni');
      footer.before(strip);
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
    const modelContext = document.createElement('div');
    modelContext.className = 'home-observation-main';
    const modelBasis = data?.home_summary?.source || 'modello non disponibile';
    modelContext.textContent = `Nowcast osservativo 0–3 h · Previsione oraria: ${modelBasis}`;
    strip.appendChild(modelContext);

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

  function currentSkyConsensus(data) {
    const rows = Array.isArray(data?.model_details) ? data.model_details : [];
    const clouds = rows
      .filter(row => row?.ok && row?.current)
      .map(row => num(row.current.cloud_cover))
      .filter(value => value != null && value >= 0 && value <= 100)
      .sort((a, b) => a - b);
    if (clouds.length < 2) return null;

    const mid = Math.floor(clouds.length / 2);
    const median = clouds.length % 2 ? clouds[mid] : (clouds[mid - 1] + clouds[mid]) / 2;
    const spread = clouds[clouds.length - 1] - clouds[0];
    const night = (() => {
      try {
        const hour = Number(new Intl.DateTimeFormat('en-GB', {timeZone:'Europe/Rome', hour:'2-digit', hourCycle:'h23'}).format(new Date()));
        return Number.isFinite(hour) && (hour >= 19 || hour < 7);
      } catch (_) {
        return false;
      }
    })();

    if (spread >= 35) {
      return {value:median, spread, count:clouds.length, label:'Cielo variabile', icon:night?'☁':'⛅', kind:'cloudy', disagreement:true};
    }
    if (median >= 80) return {value:median, spread, count:clouds.length, label:'Cielo molto nuvoloso', icon:'☁', kind:'cloudy', disagreement:false};
    if (median >= 45) return {value:median, spread, count:clouds.length, label:'Cielo parzialmente nuvoloso', icon:night?'☁':'⛅', kind:'cloudy', disagreement:false};
    return {value:median, spread, count:clouds.length, label:'Cielo poco nuvoloso', icon:night?'☾':'🌤', kind:'calm', disagreement:false};
  }

  function renderCurrentSky(data) {
    const card = byId('weatherMain');
    if (!card || card.classList.contains('rain') || card.classList.contains('storm')) return;
    const sky = currentSkyConsensus(data);
    if (!sky) return;

    const description = byId('homeDescription');
    const icon = byId('weatherIcon');
    const cloud = byId('homeCloud');
    const cloudText = byId('homeCloudText');

    card.className = `card weather-main ${sky.kind}`;
    if (description) {
      description.textContent = sky.label;
      description.title = `Consenso modellistico corrente: mediana ${fmt(sky.value)}%, spread ${fmt(sky.spread)} punti su ${sky.count} modelli.`;
    }
    if (icon) icon.textContent = sky.icon;
    if (cloud) cloud.textContent = `${fmt(sky.value)} %`;
    if (cloudText) cloudText.textContent = sky.disagreement
      ? `Consenso ${sky.count} modelli · forte variabilità`
      : `Consenso ${sky.count} modelli`;
  }

  function renderForecastHeader(data) {
    const section = byId('forecastDetail');
    const titleWrap = section?.querySelector('.section-title');
    if (!section || !titleWrap) return;

    const heading = titleWrap.querySelector('h2');
    if (heading) heading.textContent = 'Prossime ore · Oggi e domani';
    const source = titleWrap.querySelector('.forecast-source');
    if (source) {
      source.hidden = true;
      source.textContent = '';
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
    const verifiedLow = ['low', 'green', 'none', 'clear'].includes(level);
    card.classList.toggle('home-alert-compact', verifiedLow);
    const symbol = card.querySelector('.home-alert-symbol');
    const title = byId('homeAlertTitle');
    if (verifiedLow) {
      if (symbol) symbol.textContent = '✓';
      if (title) title.textContent = 'Nessuna allerta meteo ufficiale attiva';
    } else if (!active) {
      if (symbol) symbol.textContent = '◷';
      if (title) title.textContent = 'Allerta ufficiale non verificabile';
    }
    const home = card.parentElement;
    const forecast = byId('forecastDetail');
    const stations = byId('homeStationsOverview');
    if (active && home && forecast?.parentElement === home) {
      home.insertBefore(card, forecast);
    } else if (!active && home && stations?.parentElement === home) {
      home.insertBefore(card, stations.nextSibling);
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
    renderCurrentSky(data);
    const status = byId('homeStatus');
    if (status?.parentElement) status.parentElement.hidden = status.textContent.trim() === 'Tranquillo';
    renderObservationStrip(data);
    renderForecastHeader(data);
    renderAlert(data);
  }

  const original = window.renderForecastDashboard;
  window.renderForecastDashboard = data => {
    if (typeof original === 'function') original(data);
    render(data);
  };
})();
