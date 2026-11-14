(() => {
  const root=document.querySelector('#drone-hud'), flight=document.querySelector('#drone-hud [data-action="flight"]'), ml=document.querySelector('#drone-hud [data-action="ml"]'), policy=window.__app?.flightOps?.bridge?.policy;
  return {
    droneHidden: root?.hidden,
    flight: flight ? {text:flight.textContent,disabled:flight.disabled} : null,
    ml: ml ? {text:ml.textContent,disabled:ml.disabled,pressed:ml.getAttribute('aria-pressed')} : null,
    policy: policy ? {status:policy.status,backend:policy.backend,adapter:policy.adapter,error:policy.status?.error,timing:policy.latestTiming,diag:policy.latestDiagnostics} : null,
    warning: document.querySelector('#drone-hud [data-bind="policy-warning"]')?.innerText,
    route: document.querySelector('#drone-hud [data-bind="route-status"]')?.innerText,
  };
})()
