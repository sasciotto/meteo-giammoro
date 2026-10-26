(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const SOURCES = [
    {id:'weather-sicily',label:'Weather Sicily',title:'Weather Sicily · mappa live',kind:'iframe',fit:'desktop',designWidth:1440,url:'https://maps.weathersicily.it/',openUrl:'https://maps.weathersicily.it/',note:'Mappa meteo live della Sicilia con stazioni e livelli osservativi. La vista viene adattata al contenitore mantenendo una tela desktop completa.'},
    {id:'meteo-radar',label:'Meteo & Radar',title:'Meteo & Radar · Giammoro',kind:'iframe',fit:'desktop',designWidth:1280,url:'https://www.meteoeradar.it/radar-meteo/giammoro/9429567?center=38.28%2C15.36&placemark=38.2037%2C15.3067&zoom=9.33&tz=Europe%2FRome',openUrl:'https://www.meteoeradar.it/radar-meteo/giammoro/9429567?center=38.28%2C15.36&placemark=38.2037%2C15.3067&zoom=9.33&tz=Europe%2FRome',note:'Radar meteo centrato sull’area di Giammoro. La pagina viene scalata nel frame per evitare tagli orizzontali; resta disponibile anche il collegamento originale.'},
    {id:'windy-radar',label:'Windy',title:'Windy · radar meteo',kind:'iframe',fit:'responsive',url:'https://embed.windy.com/embed.html?type=map&location=coordinates&metricRain=mm&metricTemp=%C2%B0C&metricWind=km%2Fh&zoom=7&overlay=radar&product=radar&level=surface&lat=38.2018&lon=15.31816&detailLat=38.2018&detailLon=15.31816&detail=false',openUrl:'https://www.windy.com/-Weather-radar-radar?radar,38.2018,15.31816,7',note:'Widget radar Windy centrato su Giammoro. Il widget è già responsive e usa direttamente tutta l’area disponibile.'},
    {id:'meteociel-mtg',label:'Satellite MTG',title:'Satellite MTG · Meteosat-12',kind:'external',openUrl:'https://www.meteociel.fr/accueil/satellite.php?mode=animation-visible-hd-mtg&region=it',secondaryUrl:'https://view.eumetsat.int/',secondaryLabel:'EUMETView ufficiale',note:'Animazione satellitare MTG/Meteosat-12 per l’Italia. La vecchia GIF diretta non è più usata: si apre la pagina Meteociel dedicata oppure il visualizzatore ufficiale EUMETView. Il satellite non misura direttamente la pioggia al suolo.'}
  ];

  function isMobileSafeMode(){
    const narrow=window.matchMedia?.('(max-width: 900px)').matches;
    const coarse=window.matchMedia?.('(pointer: coarse)').matches;
    return Boolean(narrow || (coarse && window.innerWidth<=1180));
  }

  function ensureStyles(){
    if(byId('radarSourcesStyles')) return;
    const style=document.createElement('style');
    style.id='radarSourcesStyles';
    style.textContent=`
      .radar-only{display:none}body.mode-radar .radar-only{display:block}.radar-sources-view{margin-top:0}
      .radar-sources-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:12px}.radar-sources-head h2{margin:0;font-size:24px}.radar-sources-head p{margin:5px 0 0;color:var(--muted);max-width:760px}
      .radar-source-tabs{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}.radar-source-tab{border:1px solid var(--line);background:var(--surface2);color:var(--text);border-radius:999px;padding:8px 12px;font:inherit;font-size:13px;font-weight:740;cursor:pointer}.radar-source-tab.active{background:var(--accent);border-color:var(--accent);color:#fff}
      .radar-source-panel{display:none}.radar-source-panel.active{display:block}.radar-source-card{padding:0;overflow:hidden}.radar-source-meta{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;padding:16px 17px;border-bottom:1px solid var(--line)}.radar-source-meta h3{margin:0;font-size:18px}.radar-source-meta p{margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.45;max-width:760px}
      .radar-source-actions{display:flex;align-items:center;justify-content:flex-end;gap:9px;flex-wrap:wrap}.radar-fullscreen{border:1px solid var(--line);background:var(--surface2);color:var(--accent);border-radius:999px;padding:7px 10px;font:inherit;font-size:12px;font-weight:760;cursor:pointer;white-space:nowrap}.radar-fullscreen:hover{background:#eef7fb}
      .radar-source-frame-wrap{position:relative;overflow:hidden;background:#dfe6ea;height:clamp(480px,74dvh,820px);min-height:480px;isolation:isolate}.radar-source-frame{position:absolute;top:0;left:0;display:block;border:0;background:#dfe6ea;transform-origin:top left;max-width:none}
      .radar-frame-loading{position:absolute;left:12px;bottom:12px;z-index:3;padding:7px 10px;border:1px solid rgba(255,255,255,.75);border-radius:999px;background:rgba(255,255,255,.92);color:#40505b;font-size:11px;line-height:1.2;box-shadow:0 3px 12px rgba(20,32,42,.16);backdrop-filter:blur(8px);pointer-events:none}
      .radar-source-frame-wrap:fullscreen{width:100vw;height:100vh!important;min-height:100vh;background:#101820}.radar-source-frame-wrap:fullscreen .radar-frame-loading{left:16px;bottom:16px}
      .radar-source-external{white-space:nowrap}.radar-source-disclaimer{margin-top:10px;font-size:11px;color:var(--muted);line-height:1.45}
      .radar-mobile-safe,.radar-external-only{display:flex;flex-direction:column;align-items:flex-start;gap:12px;padding:22px 18px;background:linear-gradient(135deg,#f5f8f9,#eef4f6);border-top:1px solid var(--line)}.radar-mobile-safe strong,.radar-external-only strong{font-size:15px;color:var(--text)}.radar-mobile-safe p,.radar-external-only p{margin:0;color:var(--muted);font-size:12px;line-height:1.55;max-width:720px}.radar-mobile-open,.radar-external-open{display:inline-flex;align-items:center;justify-content:center;border-radius:999px;background:var(--accent);color:#fff!important;padding:10px 14px;font-size:13px;font-weight:800;text-decoration:none}.radar-external-links{display:flex;gap:8px;flex-wrap:wrap}.radar-external-secondary{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--accent)!important;padding:9px 13px;font-size:12px;font-weight:780;text-decoration:none}.radar-mobile-open:active,.radar-external-open:active,.radar-external-secondary:active{transform:translateY(1px)}
      @media(max-width:700px){.radar-sources-head,.radar-source-meta{display:block}.radar-source-actions{justify-content:flex-start;margin-top:10px}.radar-source-external{white-space:normal}.radar-source-frame-wrap{height:clamp(440px,72dvh,680px);min-height:440px}.radar-mobile-safe,.radar-external-only{padding:20px 16px}}
      @media(max-width:430px){.radar-source-tab{flex:1 1 calc(50% - 7px);text-align:center}.radar-source-frame-wrap{height:clamp(400px,70dvh,600px);min-height:400px}.radar-mobile-open,.radar-external-open,.radar-external-secondary{width:100%;box-sizing:border-box}.radar-external-links{width:100%}}
    `;
    document.head.appendChild(style);
  }

  function externalPanel(source){
    const secondary=source.secondaryUrl?`<a class="radar-external-secondary" href="${source.secondaryUrl}" target="_blank" rel="noopener noreferrer">${source.secondaryLabel||'Fonte alternativa'} ↗</a>`:'';
    return `<section class="radar-source-panel" id="radarPanel-${source.id}" role="tabpanel" aria-labelledby="radarTab-${source.id}"><article class="card radar-source-card"><div class="radar-source-meta"><div><h3>${source.title}</h3><p>${source.note}</p></div></div><div class="radar-external-only"><strong>Visualizzazione satellitare esterna</strong><p>Questa sorgente non viene più incorporata nella dashboard. In questo modo evitiamo collegamenti diretti a file temporanei o pesanti e riduciamo il rischio di blocchi del browser.</p><div class="radar-external-links"><a class="radar-external-open" href="${source.openUrl}" target="_blank" rel="noopener noreferrer">Apri ${source.label} su Meteociel ↗</a>${secondary}</div></div></article></section>`;
  }

  function sourcePanel(source){
    if(source.kind==='external') return externalPanel(source);
    const mobile=isMobileSafeMode();
    if(mobile){
      return `<section class="radar-source-panel" id="radarPanel-${source.id}" role="tabpanel" aria-labelledby="radarTab-${source.id}"><article class="card radar-source-card"><div class="radar-source-meta"><div><h3>${source.title}</h3><p>${source.note}</p></div></div><div class="radar-mobile-safe"><strong>Anteprima disattivata su dispositivo mobile</strong><p>Questa sorgente può usare molta memoria e causare instabilità del browser quando viene incorporata nella dashboard. Per maggiore stabilità viene aperta direttamente nella scheda corrente, senza mantenere Meteo Giammoro e la sorgente radar attive insieme.</p><a class="radar-mobile-open" href="${source.openUrl}">Apri ${source.label} nella scheda corrente →</a></div></article></section>`;
    }
    const media=`<div class="radar-source-frame-wrap" id="radarWrap-${source.id}" data-radar-source="${source.id}"><div class="radar-frame-loading" id="radarLoading-${source.id}">Caricamento…</div><iframe class="radar-source-frame" id="radarMedia-${source.id}" data-radar-src="${source.url}" title="${source.title}" loading="lazy" allow="geolocation; fullscreen" referrerpolicy="strict-origin-when-cross-origin"></iframe></div>`;
    const fullscreen=`<button class="radar-fullscreen" type="button" data-radar-fullscreen="${source.id}" aria-label="Apri ${source.label} a schermo intero">Schermo intero ⛶</button>`;
    return `<section class="radar-source-panel" id="radarPanel-${source.id}" role="tabpanel" aria-labelledby="radarTab-${source.id}"><article class="card radar-source-card"><div class="radar-source-meta"><div><h3>${source.title}</h3><p>${source.note}</p></div><div class="radar-source-actions">${fullscreen}<a class="source-link radar-source-external" href="${source.openUrl}" target="_blank" rel="noopener noreferrer">Apri originale ↗</a></div></div>${media}</article></section>`;
  }

  function ensureView(){
    ensureStyles();
    const switcher=document.querySelector('.mode-switch');
    const footer=document.querySelector('footer.foot');
    if(!switcher||!footer?.parentElement) return null;
    let radarBtn=byId('radarBtn');
    if(!radarBtn){radarBtn=document.createElement('button');radarBtn.id='radarBtn';radarBtn.type='button';radarBtn.className='mode-btn';radarBtn.textContent='Radar';switcher.appendChild(radarBtn)}
    let view=byId('radarSourcesView');
    if(!view){
      view=document.createElement('section');view.id='radarSourcesView';view.className='radar-only radar-sources-view';
      const mobileNote=isMobileSafeMode()?'<div class="radar-source-disclaimer"><strong>Modalità mobile protetta:</strong> le anteprime radar incorporate sono disattivate per ridurre il consumo di memoria e prevenire blocchi del browser.</div>':'';
      view.innerHTML=`<div class="card"><div class="radar-sources-head"><div><div class="k">CONSULTAZIONE ESTERNA</div><h2>Radar e satellite</h2><p>Mappe aggiuntive per confrontare rapidamente le osservazioni attorno a Giammoro. Queste viste non alimentano il motore di nowcasting e non modificano le metriche del progetto.</p></div></div><div class="radar-source-tabs" role="tablist" aria-label="Sorgenti radar e satellite">${SOURCES.map((source,index)=>`<button class="radar-source-tab${index===0?' active':''}" id="radarTab-${source.id}" type="button" role="tab" aria-selected="${index===0?'true':'false'}" data-radar-source="${source.id}">${source.label}</button>`).join('')}</div><div class="radar-source-disclaimer">I contenuti appartengono ai rispettivi fornitori e vengono caricati dal loro sito solo quando selezioni la relativa scheda. Per decisioni operative restano prioritari i dati e gli avvisi ufficiali indicati nella dashboard.</div>${mobileNote}</div><div class="section" id="radarSourcePanels">${SOURCES.map(sourcePanel).join('')}</div>`;
      footer.parentElement.insertBefore(view,footer);
    }
    return {view,radarBtn};
  }

  const sourceById=id=>SOURCES.find(item=>item.id===id)||null;
  function frameVisualHeight(wrap){if(document.fullscreenElement===wrap)return Math.max(1,window.innerHeight);const h=parseFloat(getComputedStyle(wrap).height);return Number.isFinite(h)&&h>0?h:Math.max(400,Math.min(window.innerHeight*.74,820))}
  function fitFrame(sourceId){if(isMobileSafeMode())return;const source=sourceById(sourceId),frame=byId(`radarMedia-${sourceId}`),wrap=byId(`radarWrap-${sourceId}`);if(!source||source.kind!=='iframe'||!frame||!wrap)return;const availableWidth=Math.max(1,wrap.clientWidth),visualHeight=frameVisualHeight(wrap);if(source.fit==='desktop'){const canvasWidth=Math.max(Number(source.designWidth)||1280,availableWidth),scale=Math.min(1,availableWidth/canvasWidth);frame.style.width=`${Math.ceil(canvasWidth)}px`;frame.style.height=`${Math.ceil(visualHeight/scale)}px`;frame.style.transform=`scale(${scale})`;return}frame.style.width='100%';frame.style.height=`${Math.ceil(visualHeight)}px`;frame.style.transform='none'}
  function fitActiveFrame(){if(isMobileSafeMode())return;const active=document.querySelector('.radar-source-tab.active')?.dataset.radarSource;if(active)fitFrame(active)}

  function loadSource(sourceId){
    if(isMobileSafeMode())return;
    const source=sourceById(sourceId);
    if(!source||source.kind==='external')return;
    const media=byId(`radarMedia-${sourceId}`),loading=byId(`radarLoading-${sourceId}`);
    if(!media||media.dataset.loaded==='true'){requestAnimationFrame(()=>fitFrame(sourceId));return}
    media.dataset.loaded='true';
    requestAnimationFrame(()=>fitFrame(sourceId));
    const finish=()=>{if(loading)loading.hidden=true;requestAnimationFrame(()=>fitFrame(sourceId))};
    media.addEventListener('load',finish,{once:true});
    media.src=media.dataset.radarSrc;
    window.setTimeout(()=>{if(loading)loading.hidden=true},8000);
  }

  function selectSource(sourceId,shouldLoad=true){const valid=SOURCES.some(s=>s.id===sourceId)?sourceId:SOURCES[0].id;document.querySelectorAll('.radar-source-tab').forEach(button=>{const active=button.dataset.radarSource===valid;button.classList.toggle('active',active);button.setAttribute('aria-selected',active?'true':'false')});document.querySelectorAll('.radar-source-panel').forEach(panel=>panel.classList.toggle('active',panel.id===`radarPanel-${valid}`));if(!isMobileSafeMode())requestAnimationFrame(()=>fitFrame(valid));if(shouldLoad&&!isMobileSafeMode())loadSource(valid)}
  function activateRadarMode(){document.body.className='mode-radar';byId('homeBtn')?.classList.remove('active');byId('expertBtn')?.classList.remove('active');byId('radarBtn')?.classList.add('active');selectSource(document.querySelector('.radar-source-tab.active')?.dataset.radarSource||SOURCES[0].id,true)}
  function toggleFullscreen(sourceId){if(isMobileSafeMode())return;const wrap=byId(`radarWrap-${sourceId}`);if(!wrap)return;if(document.fullscreenElement===wrap){document.exitFullscreen?.();return}wrap.requestFullscreen?.().catch(()=>{})}

  const created=ensureView();if(!created)return;
  created.radarBtn.addEventListener('click',activateRadarMode);
  byId('homeBtn')?.addEventListener('click',()=>created.radarBtn.classList.remove('active'));
  byId('expertBtn')?.addEventListener('click',()=>created.radarBtn.classList.remove('active'));
  document.querySelectorAll('.radar-source-tab').forEach(button=>button.addEventListener('click',()=>selectSource(button.dataset.radarSource,true)));
  document.querySelectorAll('[data-radar-fullscreen]').forEach(button=>button.addEventListener('click',()=>toggleFullscreen(button.dataset.radarFullscreen)));
  window.addEventListener('resize',()=>requestAnimationFrame(fitActiveFrame),{passive:true});
  document.addEventListener('fullscreenchange',()=>requestAnimationFrame(fitActiveFrame));
  selectSource(SOURCES[0].id,false);
})();
