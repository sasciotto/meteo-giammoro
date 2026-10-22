(() => {
  'use strict';

  const previousRender = window.renderForecastDashboard;
  if (typeof previousRender !== 'function') return;
  window.verificationHistoryEnhancer = true;

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
  const metric = (label, value, {unit = '', digits = 0, note = ''} = {}) => {
    const rendered = num(value) == null ? '—' : fmt(value, digits);
    return `<div class="metric"><div class="k">${esc(label)}</div><div class="mv">${rendered}${rendered === '—' ? '' : esc(unit)}</div>${note ? `<div class="ms">${esc(note)}</div>` : ''}</div>`;
  };

  function renderHistory(data) {
    const metricsEl = byId('verificationMetrics');
    if (!metricsEl) return;

    const summary = data?.verification?.summary || {};
    if (summary.metric_version !== 'local-event-v2') return;

    const rolling = summary.event_metrics || {};
    const cumulative = summary.cumulative_event_metrics || {};
    const legacy = summary.legacy_baseline?.event_metrics || {};
    const byHorizon = summary.cumulative_by_horizon || {};
    const samples = num(cumulative.samples) || 0;
    const eventSamples = num(cumulative.event_samples) || 0;
    const rollingEvents = num(rolling.event_samples) || 0;
    const legacyEvents = num(legacy.event_samples) || 0;

    const badgeEl = byId('verificationBadge');
    if (badgeEl) {
      badgeEl.className = `badge ${eventSamples >= 20 ? 'online' : samples > 0 ? 'warning' : 'unknown'}`;
      badgeEl.textContent = samples > 0
        ? `${fmt(samples)} campioni v2 · ${fmt(eventSamples)} eventi`
        : 'Metrica v2 in raccolta';
    }

    const introEl = byId('verificationIntro');
    if (introEl) {
      if (eventSamples === 0) {
        const baselineText = legacyEvents > 0
          ? ` La baseline precedente conteneva ${fmt(legacyEvents)} campioni evento con POD ${fmt(legacy.event_detection_percent, 1)}%, ma non è sommata alla v2 perché la definizione dell’evento locale è cambiata.`
          : '';
        introEl.textContent = `La metrica locale v2 ha ${fmt(samples)} campioni cumulativi e nessun evento maturato finora. Un’accuracy elevata nel campione recente non indica un miglioramento dimostrato.${baselineText}`;
      } else {
        introEl.textContent = `${fmt(eventSamples)} campioni evento su ${fmt(samples)} verifiche cumulative v2. Queste metriche non vengono più cancellate quando il rolling window di 300 risultati attraversa un periodo tranquillo.`;
      }
    }

    const horizonMetrics = [30, 60, 120].flatMap(horizon => {
      const row = byHorizon[String(horizon)] || {};
      const horizonEvents = num(row.event_samples) || 0;
      return [
        metric(`POD ${horizon} min`, row.event_detection_percent, {unit: ' %', digits: 1, note: `${fmt(horizonEvents)} eventi v2`}),
        metric(`FN ${horizon} min`, row.false_negative, {note: 'eventi mancati v2'})
      ];
    });

    metricsEl.innerHTML = [
      metric('Campioni cumulativi v2', samples, {note: `${fmt(cumulative.no_event_samples || 0)} non-eventi`}),
      metric('Campioni evento v2', eventSamples, {note: `${fmt(rollingEvents)} nel rolling corrente`}),
      metric('TP v2', cumulative.true_positive, {note: 'evento previsto e osservato'}),
      metric('FP v2', cumulative.false_positive, {note: 'falso allarme'}),
      metric('FN v2', cumulative.false_negative, {note: 'evento mancato'}),
      metric('POD v2', cumulative.event_detection_percent, {unit: ' %', digits: 1, note: 'event detection / recall'}),
      metric('FAR v2', cumulative.false_alarm_ratio_percent, {unit: ' %', digits: 1, note: 'false alarm ratio'}),
      metric('CSI v2', cumulative.csi_percent, {unit: ' %', digits: 1, note: 'critical success index'}),
      metric('Balanced accuracy v2', cumulative.balanced_accuracy_percent, {unit: ' %', digits: 1}),
      metric('Precision v2', cumulative.precision_percent, {unit: ' %', digits: 1}),
      ...horizonMetrics,
      metric('Accuracy v2 cumulativa', cumulative.accuracy_percent, {unit: ' %', digits: 1, note: 'secondaria; include i non-eventi'}),
      metric('Accuracy rolling', summary.accuracy_percent, {unit: ' %', digits: 1, note: 'ultimi 300 risultati; non usare da sola'}),
      metric('POD baseline v1', legacy.event_detection_percent, {unit: ' %', digits: 1, note: 'metrica precedente, non direttamente comparabile'}),
      metric('FN baseline v1', legacy.false_negative, {note: 'storico precedente al cambio semantico'})
    ].join('');

    const confidenceEl = byId('verificationConfidence');
    if (confidenceEl) {
      confidenceEl.textContent = summary.retention_note || 'Metriche cumulative v2 conservate separatamente dal rolling window.';
    }
  }

  window.renderForecastDashboard = data => {
    previousRender(data);
    renderHistory(data);
  };
})();
