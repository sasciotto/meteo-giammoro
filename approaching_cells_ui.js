(() => {
  'use strict';

  const previousRender = window.renderForecastDashboard;
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

  function ensureStyles() {
    if (byId('approachingCellsStyles')) return;
    const style = document.createElement('style');
    style.id = 'approachingCellsStyles';
    style.textContent = `
      .approach-monitor{margin-top:14px}
      .approach-monitor .section-title{margin-bottom:11px}
      .approach-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
      .approach-summary{font-size:13px;color:#40505b;line-height:1.45;margin:4px 0 0}
      .approach-badge{white-space:nowrap;border:1px solid var(--line);background:var(--surface2);border-radius:999px;padding:6px 9px;font-size:11px;font-weight:760;color:#40505b}
      .approach-badge.active{background:#fff8e9;border-color:#ead8aa;color:#654c13}
      .approach-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:12px}
      .approach-cell{border:1px solid var(--line);border-radius:13px;padding:12px;background:var(--surface2)}
      .approach-route{font-size:15px;font-weight:780}
      .approach-meta{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.45}
      .approach-projection{font-size:12px;color:#40505b;margin-top:8px}
      .approach-confidence{font-size:10px;color:var(--muted);margin-top:6px;text-transform:uppercase;letter-spacing:.03em}
      @media(max-width:650px){.approach-grid{grid-template-columns:1fr}.approach-head{display:block}.approach-badge{display:inline-block;margin-top:8px}}
    `;
    document.head.appendChild(style);
  }

  function ensureSection() {
    ensureStyles();
    let section = byId('approachingCellsSection');
    if (section) return section;

    section = document.createElement('section');
    section.id = 'approachingCellsSection';
    section.className = 'section card approach-monitor';

    const forecast = byId('forecastDetail');
    if (forecast?.parentElement) {
      forecast.parentElement.insertBefore(section, forecast);
      return section;
    }

    const alertCard = byId('homeAlertCard');
    const homeSection = alertCard?.parentElement;
    if (homeSection && alertCard) homeSection.insertBefore(section, alertCard);
    return section;
  }

  function confidenceLabel(value) {
    if (value === 'high') return 'associazione alta';
    if (value === 'medium') return 'associazione media';
    if (value === 'low') return 'associazione bassa';
    return 'qualità in valutazione';
  }

  function render(data) {
    const section = ensureSection();
    if (!section) return;

    const monitor = data?.approaching_cells || {};
    const cells = Array.isArray(monitor.cells) ? monitor.cells : [];
    const status = String(monitor.status || 'unavailable');
    const active = status === 'detected' && cells.length > 0;
    const dominant = monitor.dominant_from_label || monitor.dominant_from;
    const badge = active
      ? `${cells.length} ${cells.length === 1 ? 'cella' : 'celle'} · da ${esc(dominant || 'settore non definito')}`
      : status === 'insufficient_history'
        ? 'Traiettoria in acquisizione'
        : status === 'none'
          ? 'Nessuna in avvicinamento'
          : 'Dato non disponibile';

    const cellHtml = cells.map(cell => {
      const from = cell.approach_from_label || cell.approach_from || 'settore non definito';
      const toward = cell.movement_toward_label || cell.movement_toward || 'direzione non definita';
      const closest = num(cell.closest_approach_km);
      const eta = num(cell.eta_minutes);
      const peak = num(cell.peak_value);
      const unit = monitor.unit || '';
      const projection = closest == null
        ? 'Minima distanza non ancora stimabile.'
        : `Minima distanza proiettata ~${fmt(closest,1)} km${eta == null ? '' : ` · ingresso entro 5 km ~${fmt(eta)} min`}.`;
      return `<div class="approach-cell">
        <div class="approach-route">Da ${esc(from)} → verso ${esc(toward)}</div>
        <div class="approach-meta">Distanza ${fmt(cell.distance_km,1)} km · velocità ${fmt(cell.speed_kmh,1)} km/h · avvicinamento ${fmt(cell.approach_rate_kmh,1)} km/h${peak == null ? '' : ` · picco ${fmt(peak,1)} ${esc(unit)}`}</div>
        <div class="approach-projection">${esc(projection)}</div>
        <div class="approach-confidence">${esc(confidenceLabel(cell.confidence))}</div>
      </div>`;
    }).join('');

    const summary = monitor.summary || (
      status === 'unavailable'
        ? 'Monitor delle traiettorie radar temporaneamente non disponibile.'
        : 'Nessuna informazione aggiuntiva disponibile.'
    );

    section.innerHTML = `
      <div class="approach-head">
        <div>
          <div class="section-title"><div><h2>Celle in avvicinamento</h2><div class="forecast-source">Radar-DPC · confronto tra scansioni successive</div></div></div>
          <div class="approach-summary">${esc(summary)}</div>
        </div>
        <div class="approach-badge ${active ? 'active' : ''}">${badge}</div>
      </div>
      ${cellHtml ? `<div class="approach-grid">${cellHtml}</div>` : ''}`;
  }

  window.renderForecastDashboard = data => {
    if (typeof previousRender === 'function') previousRender(data);
    render(data);
  };
})();