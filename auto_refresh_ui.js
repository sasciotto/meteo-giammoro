(() => {
  'use strict';

  const CHECK_INTERVAL_MS = 60_000;
  const STATE_KEY = 'meteo-giammoro:auto-refresh-state';
  let knownStamp = null;
  let checking = false;

  function dataStamp(data) {
    return data?.meta?.last_check_iso || data?.meta?.generated_at || null;
  }

  function currentViewState() {
    const mode = document.body.classList.contains('mode-events')
      ? 'events'
      : document.body.classList.contains('mode-radar')
        ? 'radar'
        : document.body.classList.contains('mode-expert')
          ? 'expert'
          : 'home';
    const radarSource = document.querySelector('.radar-source-tab.active')?.dataset.radarSource || null;
    return {
      mode,
      radarSource,
      scrollY: Math.max(0, Math.round(window.scrollY || 0)),
    };
  }

  function saveViewState() {
    try {
      sessionStorage.setItem(STATE_KEY, JSON.stringify(currentViewState()));
    } catch (_) {}
  }

  function readViewState() {
    try {
      const raw = sessionStorage.getItem(STATE_KEY);
      if (!raw) return null;
      sessionStorage.removeItem(STATE_KEY);
      return JSON.parse(raw);
    } catch (_) {
      return null;
    }
  }

  function restoreViewState() {
    const state = readViewState();
    if (!state) return;

    if (state.mode === 'events') {
      document.getElementById('eventsBtn')?.click();
    } else if (state.mode === 'radar') {
      document.getElementById('radarBtn')?.click();
      if (state.radarSource) {
        document.querySelector(`[data-radar-source="${CSS.escape(state.radarSource)}"]`)?.click();
      }
    } else if (state.mode === 'expert') {
      document.getElementById('expertBtn')?.click();
    } else {
      document.getElementById('homeBtn')?.click();
    }

    if (Number.isFinite(state.scrollY) && state.scrollY > 0) {
      requestAnimationFrame(() => window.scrollTo({top: state.scrollY, behavior: 'auto'}));
    }
  }

  function reloadWithFreshUrl() {
    saveViewState();
    const url = new URL(window.location.href);
    url.searchParams.set('_refresh', Date.now().toString());
    window.location.replace(url.toString());
  }

  async function checkForUpdate(initial = false) {
    if (checking || document.hidden) return;
    checking = true;
    try {
      const response = await fetch(`data.json?_=${Date.now()}`, {
        cache: 'no-store',
        headers: {'Cache-Control': 'no-cache'},
      });
      if (!response.ok) return;
      const data = await response.json();
      const stamp = dataStamp(data);
      if (!stamp) return;

      if (initial || !knownStamp) {
        knownStamp = stamp;
        return;
      }

      if (stamp !== knownStamp) {
        knownStamp = stamp;
        reloadWithFreshUrl();
      }
    } catch (_) {
      // Un errore di rete non deve interferire con la dashboard già caricata.
    } finally {
      checking = false;
    }
  }

  window.addEventListener('load', () => {
    restoreViewState();
    checkForUpdate(true);
    window.setInterval(() => checkForUpdate(false), CHECK_INTERVAL_MS);
  });

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) checkForUpdate(false);
  });
})();
