(() => {
  'use strict';

  const style = document.createElement('style');
  style.id = 'radarLoadingUiStyles';
  style.textContent = `
    .radar-source-frame-wrap .radar-source-loading{
      inset:auto auto 12px 12px!important;
      min-height:0!important;
      width:auto!important;
      height:auto!important;
      padding:7px 10px!important;
      border:1px solid rgba(255,255,255,.72);
      border-radius:999px;
      background:rgba(255,255,255,.9)!important;
      color:#40505b!important;
      font-size:11px;
      line-height:1.2;
      box-shadow:0 3px 12px rgba(20,32,42,.16);
      backdrop-filter:blur(8px);
      pointer-events:none;
    }
    .radar-source-frame-wrap:fullscreen .radar-source-loading{
      inset:auto auto 16px 16px!important;
      min-height:0!important;
    }
  `;
  document.head.appendChild(style);

  const revealFrame = frame => {
    if (!(frame instanceof HTMLIFrameElement) || !frame.classList.contains('radar-source-frame')) return;
    if (frame.hidden) frame.hidden = false;
  };

  document.querySelectorAll('.radar-source-frame').forEach(frame => {
    if (frame.getAttribute('src')) revealFrame(frame);
  });

  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      if (mutation.type !== 'attributes' || mutation.attributeName !== 'src') continue;
      revealFrame(mutation.target);
    }
  });

  document.querySelectorAll('.radar-source-frame').forEach(frame => {
    observer.observe(frame, {attributes: true, attributeFilter: ['src']});
  });
})();
