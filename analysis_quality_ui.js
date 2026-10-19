(() => {
  'use strict';

  const previousRender = window.renderForecastDashboard;
  const byId = id => document.getElementById(id);
  const num = value => {
    if (value === null || value === undefined || value === '') return null;
    const x = Number(value);
    return Number.isFinite(x) ? x : null;
  };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function metric(label, value, note = '') {
    return `<div class="metric"><div class="k">${esc(label)}</div><div class="mv">${esc(value)}</div>${note ? `<div class="ms">${esc(note)}</div>` : ''}</div>`;
  }

  function statusClass(label) {
    const value = String(label || '').toLowerCase();
    if (value.includes('molto alta') || value === 'alta') return 'online';
    if (value.includes('media') || value.includes('acquisizione')) return 'warning';
    if (value.includes('bassa') || value.includes('non disponibile')) return 'elevato';
    return 'unknown';
  }

  function ensureDetail(qualityCard) {
    let detail = byId('qualitySeparation');
    if (detail) return detail;
    detail = document.createElement('div');
    detail.id = 'qualitySeparation';
    detail.className = 'tracking-grid';
    detail.style.marginTop = '12px';
    qualityCard.appendChild(detail);
    return detail;
  }

  function render(data) {
    const score = byId('confidenceScore');
    const badge = byId('confidenceBadge');
    const note = byId('confidenceNote');
    const fill = byId('confidenceFill');
    if (!score || !badge || !note || !fill) return;

    const card = score.closest('.card');
    const title = card?.querySelector('.section-title h2');
    if (title) title.textContent = 'Qualità dell’analisi';

    const quality = data?.analysis_quality || data?.analysis_confidence || {};
    const trajectory = data?.trajectory_reliability || {};
    const predictive = data?.predictive_confidence || {};
    const qualityScore = num(quality.score);

    badge.className = `badge ${statusClass(quality.label)}`;
    badge.textContent = quality.label || '—';
    score.textContent = qualityScore == null ? '—' : `${Math.round(qualityScore)}/100`;
    fill.style.width = `${Math.max(0, Math.min(100, qualityScore || 0))}%`;
    note.textContent = quality.note || 'Qualità tecnica delle fonti e dell’analisi; non è una probabilità previsionale.';

    const components = byId('confidenceComponents');
    if (components) {
      const cc = quality.components || {};
      components.innerHTML = [
        metric('Freschezza radar', cc.radar_freshness == null ? '—' : `${cc.radar_freshness} pt`),
        metric('Cross-check radar', cc.radar_crosscheck == null ? '—' : `${cc.radar_crosscheck} pt`),
        metric('Stazioni', cc.station_support == null ? '—' : `${cc.station_support} pt`),
        metric('Modelli', cc.model_availability == null ? '—' : `${cc.model_availability} pt`),
        metric('Fulmini', cc.lightning_support == null ? '—' : `${cc.lightning_support} pt`),
      ].join('');
    }

    const detail = ensureDetail(card);
    const trajectoryScore = num(trajectory.score);
    const trajectoryValue = trajectoryScore == null
      ? (trajectory.label || '—')
      : `${Math.round(trajectoryScore)}/100 · ${trajectory.label || ''}`;
    const calibration = num(predictive.calibration_progress_percent);
    const predictiveValue = predictive.label || 'Non calibrata';
    detail.innerHTML = [
      metric('Affidabilità traiettoria', trajectoryValue, trajectory.note || ''),
      metric('Confidenza previsionale', predictiveValue, predictive.note || ''),
      metric('Calibrazione eventi', calibration == null ? '—' : `${Math.round(calibration)}%`, `${predictive.event_samples ?? 0}/${predictive.minimum_event_samples ?? 20} campioni evento minimi`),
    ].join('');
  }

  window.renderForecastDashboard = data => {
    if (typeof previousRender === 'function') previousRender(data);
    render(data);
  };
})();
