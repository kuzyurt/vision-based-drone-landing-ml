(() => {
  const ops=window.__app?.flightOps, s=ops?.state, p=ops?.bridge?.policy, d=p?.latestDiagnostics;
  const pos=s?.drone?.position, boat=s?.boat?.position;
  return {
    state_keys:Object.keys(s||{}),
    time_s:s?.time_s,
    ml:s?.ml,
    drone:s?.drone,
    boat:s?.boat,
    hull_pose:s?.hull_pose,
    camera:s?.camera,
    gimbal:{pan:s?.drone?.pan,tilt:s?.drone?.tilt},
    relative:pos&&boat?{dx:boat[0]-pos[0],dy:boat[1]-pos[1],dz:boat[2]-pos[2],distance:Math.hypot(boat[0]-pos[0],boat[1]-pos[1],boat[2]-pos[2])}:null,
    policy_status:p?.status,
    diagnostics:d,
    search_proposals:d?.search_proposals,
    latest_search:p?.latestSearch?{heat_len:p.latestSearch.search_heat?.length,presence:p.latestSearch.search_presence?.[0]}:null,
    latest_timing:p?.latestTiming,
  };
})()
