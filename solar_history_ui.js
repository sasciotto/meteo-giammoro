(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const num = v => { const x = Number(v); return Number.isFinite(x) ? x : null; };
  const SERIES_COLORS = {
    'pace-del-mela': '#d97706',
    'archi-isanfi5': '#7c3aed',
    'scl087': '#2563eb',
    'lsa-saf': '#16a34a',
  };
  const FALLBACK_COLORS = ['#dc2626', '#0891b2', '#475569', '#be185d', '#9333ea'];
  let historyCache = null;
  let historyPromise = null;
  let selectedHours = 24;

  function seriesColor(id, index) {
    return SERIES_COLORS[id] || FALLBACK_COLORS[index % FALLBACK_COLORS.length];
  }

  function sourceTime(sample, source) {
    const candidates = [source?.observed_at, source?.retrieved_at, sample?.timestamp];
    for (const value of candidates) {
      const t = value ? new Date(value).getTime() : NaN;
      if (Number.isFinite(t)) return t;
    }
    return null;
  }

  function ensureStyles() {
    if (byId('solarHistoryStyles')) return;
    const style = document.createElement('style');
    style.id = 'solarHistoryStyles';
    style.textContent = `
      .solar-history{margin-top:16px}.solar-history-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
      .solar-range{display:flex;gap:6px}.solar-range button{border:1px solid var(--line);background:var(--surface);border-radius:9px;padding:7px 10px;font-weight:700;cursor:pointer}.solar-range button.active{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
      .solar-chart-card{margin-top:10px;border:1px solid var(--line);border-radius:13px;padding:12px;background:var(--surface2)}
      .solar-chart-title{display:flex;justify-content:space-between;gap:10px;align-items:baseline}.solar-chart-title b{font-size:14px}.solar-chart-title span{font-size:11px;color:var(--muted)}
      .solar-chart{width:100%;height:250px;margin-top:8px}.solar-chart svg{width:100%;height:100%;display:block;overflow:visible}.solar-axis{stroke:currentColor;opacity:.18;stroke-width:1}.solar-series{fill:none;stroke-width:2.6;vector-effect:non-scaling-stroke}.solar-series.alt{stroke-dasharray:6 4}.solar-legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:7px;font-size:11px;color:var(--muted)}.solar-legend span{display:inline-flex;align-items:center;gap:6px}.solar-legend i{display:inline-block;width:19px;border-top:3px solid var(--series-color);border-radius:2px}
      .solar-daily-table{width:100%;border-collapse:collapse;margin-top:10px;font-size:11px}.solar-daily-table th,.solar-daily-table td{padding:7px 6px;border-bottom:1px solid var(--line);text-align:right}.solar-daily-table th:first-child,.solar-daily-table td:first-child{text-align:left}
      @media(max-width:650px){.solar-chart{height:210px}.solar-daily-wrap{overflow-x:auto}}
    `;
    document.head.appendChild(style);
  }

  async function loadHistory() {
    if (historyCache) return historyCache;
    if (!historyPromise) {
      historyPromise = fetch(`solar_history.json?ts=${Date.now()}`, {cache:'no-store'})
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
        .then(d => (historyCache = d))
        .catch(err => ({error:String(err), samples:[], daily:[], catalog:{}}));
    }
    return historyPromise;
  }

  function ensurePanel() {
    ensureStyles();
    const content = byId('solarContent');
    if (!content) return null;
    let panel = byId('solarHistoryPanel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'solarHistoryPanel';
      panel.className = 'solar-history';
      panel.innerHTML = `<div class="solar-history-head"><div><div class="k">STORICO OSSERVAZIONI</div><div class="small muted">Timestamp osservativo della singola fonte; nessuna linea attraverso buchi lunghi.</div></div><div class="solar-range"><button data-hours="24" class="active">24 h</button><button data-hours="168">7 giorni</button><button data-hours="720">30 giorni</button></div></div><div id="solarHistoryBody" class="solar-chart-card"><div class="small muted">Caricamento storico…</div></div>`;
      content.appendChild(panel);
      panel.querySelectorAll('[data-hours]').forEach(button => button.addEventListener('click', () => {
        selectedHours = Number(button.dataset.hours) || 24;
        panel.querySelectorAll('[data-hours]').forEach(x => x.classList.toggle('active', x === button));
        renderHistory(historyCache);
      }));
    }
    return panel;
  }

  function seriesFor(history, hours) {
    const cutoff = Date.now() - hours * 3600 * 1000;
    const ids = Object.keys(history?.catalog || {}).filter(id => id !== 'lsa-saf');
    if ((history?.catalog || {})['lsa-saf']) ids.push('lsa-saf');
    return ids.map(id => {
      const points = (history?.samples || []).map(sample => {
        const source = sample?.sources?.[id];
        const t = sourceTime(sample, source);
        const y = num(source?.solar_wm2);
        return t != null && t >= cutoff && source?.status === 'ok' && y != null ? {t,y} : null;
      }).filter(Boolean).sort((a,b)=>a.t-b.t);
      return {id, name: history?.catalog?.[id]?.name || id, points};
    }).filter(s => s.points.length);
  }

  function segmentsFor(points, gapMinutes) {
    if (!points.length) return [];
    const maxGap = Math.max(1, Number(gapMinutes) || 45) * 60000;
    const segments = [[points[0]]];
    for (let i=1; i<points.length; i++) {
      const previous = points[i-1];
      const current = points[i];
      if (current.t - previous.t > maxGap) segments.push([]);
      segments[segments.length-1].push(current);
    }
    return segments.filter(segment => segment.length);
  }

  function pathFor(points, minT, maxT, maxY, width, height, pad) {
    return points.map((p, i) => {
      const x = pad + ((p.t-minT)/(maxT-minT || 1))*(width-pad*2);
      const y = height-pad - (p.y/(maxY || 1))*(height-pad*2);
      return `${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  }

  function chartSvg(series, history) {
    const points = series.flatMap(s => s.points);
    if (!points.length) return '<div class="small muted">Lo storico inizierà a popolarsi dai prossimi cicli di acquisizione.</div>';
    const width=900, height=250, pad=34;
    const minT = Math.min(...points.map(p=>p.t)); const maxT = Math.max(...points.map(p=>p.t));
    const maxY = Math.max(100, ...points.map(p=>p.y));
    const grid = [0,.25,.5,.75,1].map(f => { const y=height-pad-f*(height-pad*2); return `<line class="solar-axis" x1="${pad}" x2="${width-pad}" y1="${y}" y2="${y}"/><text x="4" y="${y+4}" font-size="10" opacity=".55">${Math.round(maxY*f)}</text>`; }).join('');
    const gap = history?.integration_gap_max_minutes || 45;
    const paths = series.map((s,i) => segmentsFor(s.points, gap).map(segment => `<path class="solar-series ${i%2?'alt':''}" d="${pathFor(segment,minT,maxT,maxY,width,height,pad)}" stroke="${seriesColor(s.id,i)}"/>`).join('')).join('');
    const start = new Date(minT).toLocaleString('it-IT',{timeZone:'Europe/Rome',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
    const end = new Date(maxT).toLocaleString('it-IT',{timeZone:'Europe/Rome',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
    return `<div class="solar-chart-title"><b>Radiazione solare · W/m²</b><span>${start} → ${end}</span></div><div class="solar-chart"><svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">${grid}<line class="solar-axis" x1="${pad}" x2="${pad}" y1="${pad}" y2="${height-pad}"/>${paths}</svg></div><div class="solar-legend">${series.map((s,i)=>`<span style="--series-color:${seriesColor(s.id,i)}"><i aria-hidden="true"></i>${s.name}</span>`).join('')}</div><div class="small muted">Le linee vengono interrotte quando il gap supera ${gap} minuti.</div>`;
  }

  function dailyTable(history) {
    const daily = (history?.daily || []).slice(-7).reverse();
    if (!daily.length) return '';
    const ids = Object.keys(history?.catalog || {}).filter(id => id !== 'lsa-saf').slice(0,4);
    if (!ids.length) return '';
    return `<div class="solar-daily-wrap"><table class="solar-daily-table"><thead><tr><th>Giorno</th>${ids.map(id=>`<th>${history.catalog[id]?.name || id}<br>max / kWh·m⁻²</th>`).join('')}</tr></thead><tbody>${daily.map(day=>`<tr><td>${day.date}</td>${ids.map(id=>{const s=day?.sources?.[id]||{}; const mx=num(s.solar_max_wm2); const e=num(s.energy_kwh_m2); return `<td>${mx==null?'—':Math.round(mx)+' W/m²'} / ${e==null?'—':e.toFixed(2)}</td>`}).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

  function renderHistory(history) {
    ensurePanel();
    const body = byId('solarHistoryBody');
    if (!body) return;
    if (!history || history.error) { body.innerHTML = `<div class="small muted">Storico temporaneamente non disponibile${history?.error ? `: ${history.error}` : ''}.</div>`; return; }
    const series = seriesFor(history, selectedHours);
    body.innerHTML = `${chartSvg(series, history)}${dailyTable(history)}<div class="small muted" style="margin-top:8px">Archivio avviato: ${history.started_at ? new Date(history.started_at).toLocaleString('it-IT',{timeZone:'Europe/Rome'}) : '—'} · grezzo ${history.raw_retention_days || 31} giorni · riepiloghi giornalieri conservati a lungo termine.</div>`;
  }

  async function refresh() {
    ensurePanel();
    renderHistory(await loadHistory());
  }

  const original = window.renderSolarMonitoring;
  if (typeof original === 'function') {
    window.renderSolarMonitoring = data => { original(data); refresh(); };
  } else {
    document.addEventListener('DOMContentLoaded', refresh, {once:true});
  }
})();
