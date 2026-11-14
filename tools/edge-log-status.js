(() => {
  const log=window.__diagLog, rows=log?.rows||[], last=rows.at(-1)||null;
  const policyRows=rows.filter(r=>r.diagnostics);
  return {
    installed:!!log,
    rows:rows.length,
    policy_rows:policyRows.length,
    marks:log?.marks||[],
    last:last?{
      wall_ms:last.wall_ms,
      sim_s:last.sim_s,
      phase:last.phase,
      control_phase:last.diagnostics?.control_phase,
      pre360:last.diagnostics?.pre360_phase,
      search_mode:last.diagnostics?.search_mode,
      search_phase:last.diagnostics?.search_phase,
      handoff:last.diagnostics?.handoff_latched,
      proposals:last.diagnostics?.search_proposals,
      search:last.search,
      drone:last.drone,
    }:null,
  };
})()
