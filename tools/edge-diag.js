(() => {
  const policy=window.__app?.flightOps?.bridge?.policy,d=policy?.latestDiagnostics||{};
  const keys=['control_phase','search_mode','search_phase','selected','confirmed','search_identity_confirmed','scan_passes_completed','search_warning','warning_code','warning_time_s','warning_terminal','coverage_deg','pre360_phase','pre360_done','radio_active','radio_age_s','handoff_latched','intervention','metric_confirmed','estimated_clearance_m','estimated_lateral_error_m','boat_radio'];
  const warning=document.querySelector('#drone-hud [data-bind="policy-warning"]');
  return {keys:Object.fromEntries(keys.map(k=>[k,d[k]])), warningHidden:warning?.hidden, warningText:document.querySelector('#drone-hud [data-bind="policy-warning-text"]')?.textContent, banner:document.querySelector('#drone-hud [data-bind="ml-banner-note"]')?.textContent, route:document.querySelector('#drone-hud [data-bind="route-status"]')?.textContent, state:window.__app?.flightOps?.state?.ml};
})()
