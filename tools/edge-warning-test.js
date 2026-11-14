(() => {
  const ops=window.__app?.flightOps, policy=ops?.bridge?.policy;
  if(!policy) return {error:'no policy'};
  policy.latestDiagnostics={...(policy.latestDiagnostics||{}),search_warning:'search_pass_2_no_identity',scan_passes_completed:2,search_identity_confirmed:false};
  ops._refreshUI();
  const warning=document.querySelector('#drone-hud [data-bind="policy-warning"]');
  return {hidden:warning?.hidden,text:document.querySelector('#drone-hud [data-bind="policy-warning-text"]')?.textContent,route:document.querySelector('#drone-hud [data-bind="route-status"]')?.textContent};
})()
