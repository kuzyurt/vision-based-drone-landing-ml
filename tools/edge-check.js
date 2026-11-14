({
  visibility: document.visibilityState,
  focused: document.hasFocus(),
  app: !!window.__app,
  ui: !!window.__ui,
  startHidden: document.querySelector('#flight-start')?.hidden,
  startText: document.querySelector('[data-bind="start-status"]')?.innerText,
  loader: document.querySelector('#loader')?.innerText?.split('\n').slice(0,8),
})
