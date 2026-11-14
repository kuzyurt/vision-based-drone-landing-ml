(() => {
  const old = window.__diagLog;
  if (old?.timer) clearInterval(old.timer);
  const log = window.__diagLog = {started: Date.now(), rows: [], marks: [], last: '', timer: null};
  const number = value => typeof value === 'number' && Number.isFinite(value) ? value : null;
  const searchSummary = search => {
    if (!search) return null;
    const heat = search.search_heat, presence = search.search_presence;
    if (!heat?.length) return null;
    let max = -Infinity, top = 0, above = 0;
    for (let i = 0; i < heat.length; i++) {
      const value = heat[i];
      if (value > max) { max = value; top = i; }
      if (value >= Math.log(.36 / .64)) above++;
    }
    const evidence = search.search_evidence, identity = search.search_identity;
    const at = (array, offset) => array?.length ? number(array[top + offset * heat.length]) : null;
    return {
      presence: number(presence?.[0]),
      heat_max: number(max),
      heat_top_row: Math.floor(top / 80),
      heat_top_col: top % 80,
      heat_above_036: above,
      evidence_raw: [at(evidence, 0), at(evidence, 1), at(evidence, 2), at(evidence, 3)],
      identity_raw: [at(identity, 0), at(identity, 1)],
    };
  };
  const drone = state => state?.drone ? {
    position: state.drone.position,
    velocity: state.drone.velocity,
    yaw: number(state.drone.yaw),
    heading: number(state.drone.heading),
    roll: number(state.drone.roll),
    pitch: number(state.drone.pitch),
    speed: number(state.drone.speed),
    armed: state.drone.armed,
    landed: state.drone.landed,
  } : null;
  const boat = state => state?.boat ? {
    position: state.boat.position,
    velocity: state.boat.velocity,
    heading: number(state.boat.heading ?? state.boat.yaw),
    speed: number(state.boat.speed),
  } : null;
  const sample = () => {
    const ops = window.__app?.flightOps, state = ops?.state, policy = ops?.bridge?.policy;
    if (!ops || !state) return;
    const d = policy?.latestDiagnostics;
    const key = d ? `policy:${d.policy_elapsed_s}:${d.control_phase}` : `state:${number(state.time_s)?.toFixed(3)}:${state.ml?.phase}`;
    if (key === log.last) return;
    log.last = key;
    log.rows.push({
      wall_ms: Date.now() - log.started,
      sim_s: number(state.time_s),
      phase: state.ml?.phase ?? null,
      action: state.ml?.action ?? null,
      drone: drone(state),
      boat: boat(state),
      route: state.route ?? null,
      radio: state.radio ?? null,
      policy_status: policy ? {enabled: policy.status?.enabled, loading: policy.status?.loading, error: policy.status?.error} : null,
      diagnostics: d ?? null,
      search: searchSummary(policy?.latestSearch),
      timings: policy?.latestTiming ?? null,
    });
    if (log.rows.length > 20000) log.rows.splice(0, log.rows.length - 20000);
  };
  log.mark = (name, extra = null) => { log.marks.push({wall_ms: Date.now() - log.started, name, extra}); };
  log.sample = sample;
  log.timer = setInterval(sample, 50);
  sample();
  log.mark('logger_installed', {schema: null});
  return {installed: true, rows: log.rows.length};
})()
