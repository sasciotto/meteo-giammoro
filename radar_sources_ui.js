(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const SOURCES = [
    {
      id: 'weather-sicily',
      label: 'Weather Sicily',
      title: 'Weather Sicily · mappa live',
      kind: 'iframe',
      url: 'https://maps.weathersicily.it/',
      openUrl: 'https://maps.weathersicily.it/',
      note: 'Mappa meteo live della Sicilia con stazioni e livelli osservativi. La vista esterna viene caricata solo quando apri questa scheda.'
    },
    {
      id: 'meteo-radar',
      label: 'Meteo & Radar',
      title: 'Meteo & Radar · Giammoro',
      kind: 'iframe',
      url: 'https://www.meteoeradar.it/radar-meteo/giammoro/9429567?center=38.28%2C15.36&placemark=38.2037%2C15.3067&zoom=9.33&tz=Europe%2FRome',
      openUrl: 'https://www.meteoeradar.it/radar-meteo/giammoro/9429567?center=38.28%2C15.36&placemark=38.2037%2C15.3067&zoom=9.33&tz=Europe%2FRome',
      note: 'Radar meteo centrato sull’area di Giammoro. Se il sito impedisce la visualizzazione incorporata, usa “Apri originale”.'
    },
    {
      id: 'windy-radar',
      label: 'Windy',
      title: 'Windy · radar meteo',
      kind: 'iframe',
      url: 'https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=%C2%B0C&metricWind=km%2Fh&zoom=7&overlay=radar&product=radar&level=surface&lat=38.2018&lon=15.31816&detailLat=38.2018&detailLon=15.31816&detail=false',
      openUrl: 'https://www.windy.com/-Weather-radar-radar?radar,38.2018,15.31816,7',
      note: 'Widget radar Windy centrato su Giammoro. Il logo e i controlli della fonte restano visibili nella vista incorporata.'
    },
    {
      id: 'meteociel-mtg',
      label: 'Satellite MTG',
      title: 'Meteociel · animazione satellite MTG',
      kind: 'image',
      url: 'https://modeles20.meteociel.fr/satellite/animsatsandvisirmtgit.gif',
      openUrl: 'https://modeles20.meteociel.fr/satellite/animsatsandvisirmtgit.gif',
      note: 'Animazione satellitare MTG fornita da Meteociel. È una vista satellitare, non una misura diretta della pioggia al suolo.'
    }
  ];

  function ensureStyles() {
    if (byId('radarSourcesStyles')) return;
    const style = document.createElement('style');
    style.id = 'radarSourcesStyles';
    style.textContent = `
      .radar-only{display:none}
      body.mode-radar .radar-only{display:block}
      .radar-sources-view{margin-top:0}
      .radar-sources-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:12px}
      .radar-sources-head h2{margin:0;font-size:24px}
      .radar-sources-head p{margin:5px 0 0;color:var(--muted);max-width:760px}
      .radar-source-tabs{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}
      .radar-source-tab{border:1px solid var(--line);background:var(--surface2);color:var(--text);border-radius:999px;padding:8px 12px;font:inherit;font-size:13px;font-weight:740;cursor:pointer}
      .radar-source-tab.active{background:var(--accent);border-color:var(--accent);color:#fff}
      .radar-source-panel{display:none}
      .radar-source-panel.active{display:block}
      .radar-source-card{padding:0;overflow:hidden}
      .radar-source-meta{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;padding:16px 17px;border-bottom:1px solid var(--line)}
      .radar-source-meta h3{margin:0;font-size:18px}
      .radar-source-meta p{margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.45;max-width:780px}
      .radar-source-frame-wrap{position:relative;background:#dfe6ea;min-height:560px}
      .radar-source-frame{display:block;width:100%;height:560px;border:0;background:#dfe6ea}
      .radar-source-image-wrap{display:flex;align-items:center;justify-content:center;background:#09131d;min-height:560px;overflow:auto}
      .radar-source-image{display:block;max-width:100%;height:auto;min-height:280px;object-fit:contain}
      .radar-source-loading{display:flex;align-items:center;justify-content:center;min-height:560px;color:var(--muted);padding:24px;text-align:center}
      .radar-source-fallback{display:flex;align-items:center;justify-content:center;min-height:420px;text-align:center;padding:28px;color:var(--muted);line-height:1.5}
      .radar-source-external{white-space:nowrap}
      .radar-source-disclaimer{margin-top:10px;font-size:11px;color:var(--muted);line-height:1.45}
      @media(max-width:700px){
        .radar-sources-head,.radar-source-meta{display:block}
        .radar-source-external{display:inline-block;margin-top:10px;white-space:normal}
        .radar-source-frame,.radar-source-frame-wrap,.radar-source-loading{height:470px;min-height:470px}
        .radar-source-image-wrap{min-height:360px}
      }
      @media(max-width:430px){
        .radar-source-tab{flex:1 1 calc(50% - 7px);text-align:center}
        .radar-source-frame,.radar-source-frame-wrap,.radar-source-loading{height:420px;min-height:420px}
      }
    `;
    document.head.appendChild(style);
  }

  function sourcePanel(source) {
    const media = source.kind === 'image'
      ? `<div class="radar-source-image-wrap"><div class="radar-source-loading" id="radarLoading-${source.id}">Caricamento animazione…</div><img class="radar-source-image" id="radarMedia-${source.id}" data-radar-src="${source.url}" alt="${source.title}" hidden referrerpolicy="no-referrer"></div>`
      : `<div class="radar-source-frame-wrap"><div class="radar-source-loading" id="radarLoading-${source.id}">Caricamento mappa esterna…</div><iframe class="radar-source-frame" id="radarMedia-${source.id}" data-radar-src="${source.url}" title="${source.title}" loading="lazy" allow="geolocation; fullscreen" referrerpolicy="strict-origin-when-cross-origin" hidden></iframe></div>`;

    return `<section class="radar-source-panel" id="radarPanel-${source.id}" role="tabpanel" aria-labelledby="radarTab-${source.id}">
      <article class="card radar-source-card">
        <div class="radar-source-meta">
          <div><h3>${source.title}</h3><p>${source.note}</p></div>
          <a class="source-link radar-source-external" href="${source.openUrl}" target="_blank" rel="noopener noreferrer">Apri originale ↗</a>
        </div>
        ${media}
      </article>
    </section>`;
  }

  function ensureView() {
    ensureStyles();
    const switcher = document.querySelector('.mode-switch');
    const footer = document.querySelector('footer.foot');
    if (!switcher || !footer?.parentElement) return null;

    let radarBtn = byId('radarBtn');
    if (!radarBtn) {
      radarBtn = document.createElement('button');
      radarBtn.id = 'radarBtn';
      radarBtn.type = 'button';
      radarBtn.className = 'mode-btn';
      radarBtn.textContent = 'Radar';
      switcher.appendChild(radarBtn);
    }

    let view = byId('radarSourcesView');
    if (!view) {
      view = document.createElement('section');
      view.id = 'radarSourcesView';
      view.className = 'radar-only radar-sources-view';
      view.innerHTML = `
        <div class="card">
          <div class="radar-sources-head">
            <div>
              <div class="k">CONSULTAZIONE ESTERNA</div>
              <h2>Radar e satellite</h2>
              <p>Mappe aggiuntive per confrontare rapidamente le osservazioni attorno a Giammoro. Queste viste non alimentano il motore di nowcasting e non modificano le metriche del progetto.</p>
            </div>
          </div>
          <div class="radar-source-tabs" role="tablist" aria-label="Sorgenti radar e satellite">
            ${SOURCES.map((source, index) => `<button class="radar-source-tab${index === 0 ? ' active' : ''}" id="radarTab-${source.id}" type="button" role="tab" aria-selected="${index === 0 ? 'true' : 'false'}" data-radar-source="${source.id}">${source.label}</button>`).join('')}
          </div>
          <div class="radar-source-disclaimer">I contenuti appartengono ai rispettivi fornitori e vengono caricati dal loro sito solo quando selezioni la relativa scheda. Per decisioni operative restano prioritari i dati e gli avvisi ufficiali indicati nella dashboard.</div>
        </div>
        <div class="section" id="radarSourcePanels">
          ${SOURCES.map(sourcePanel).join('')}
        </div>`;
      footer.parentElement.insertBefore(view, footer);
    }

    return {view, radarBtn};
  }

  function loadSource(sourceId) {
    const source = SOURCES.find(item => item.id === sourceId);
    const media = byId(`radarMedia-${sourceId}`);
    const loading = byId(`radarLoading-${sourceId}`);
    if (!source || !media || media.dataset.loaded === 'true') return;

    media.dataset.loaded = 'true';
    const finish = () => {
      if (loading) loading.hidden = true;
      media.hidden = false;
    };

    if (source.kind === 'image') {
      media.addEventListener('load', finish, {once: true});
      media.addEventListener('error', () => {
        if (!loading) return;
        loading.className = 'radar-source-fallback';
        loading.innerHTML = `Animazione non disponibile nell’anteprima. <a class="source-link" href="${source.openUrl}" target="_blank" rel="noopener noreferrer">Apri Meteociel</a>.`;
      }, {once: true});
      media.src = media.dataset.radarSrc;
      return;
    }

    media.addEventListener('load', finish, {once: true});
    media.src = media.dataset.radarSrc;
  }

  function selectSource(sourceId) {
    const valid = SOURCES.some(source => source.id === sourceId) ? sourceId : SOURCES[0].id;
    document.querySelectorAll('.radar-source-tab').forEach(button => {
      const active = button.dataset.radarSource === valid;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    document.querySelectorAll('.radar-source-panel').forEach(panel => {
      panel.classList.toggle('active', panel.id === `radarPanel-${valid}`);
    });
    loadSource(valid);
  }

  function activateRadarMode() {
    document.body.className = 'mode-radar';
    byId('homeBtn')?.classList.remove('active');
    byId('expertBtn')?.classList.remove('active');
    byId('radarBtn')?.classList.add('active');
    selectSource(document.querySelector('.radar-source-tab.active')?.dataset.radarSource || SOURCES[0].id);
  }

  const created = ensureView();
  if (!created) return;

  created.radarBtn.addEventListener('click', activateRadarMode);
  byId('homeBtn')?.addEventListener('click', () => created.radarBtn.classList.remove('active'));
  byId('expertBtn')?.addEventListener('click', () => created.radarBtn.classList.remove('active'));
  document.querySelectorAll('.radar-source-tab').forEach(button => {
    button.addEventListener('click', () => selectSource(button.dataset.radarSource));
  });
  selectSource(SOURCES[0].id);
})();
