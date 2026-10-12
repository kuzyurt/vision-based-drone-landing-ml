# Browser-only PX4/MuJoCo port — implementation checkpoint

## Required outcome

Run the existing Holybro X500 flight model, original PX4 controller and MuJoCo
physics entirely in the browser. Players must not need WSL, Python, Docker, a
native simulation service, or a hosted physics service. Keep drone handling as
close as possible to the original simulator and avoid input stutter.

**Do not open or start a browser.** The user explicitly requires opening it
manually. Do not replace or edit the existing drone CAD/source simulator.
The local reference model is X500 V2, despite earlier requests calling it V4.

## Completed and measured

- Original PX4 v1.16.0 revision
  `6ea3539157ca358c70a515878b77077af7d4611d` compiled to WebAssembly, including
  EKF2, commander, uORB, sensors, multirotor controllers and control allocator.
  The platform/transport adapters are in `wasm/`; source control algorithms
  remain upstream. Binaries are in `app/public/landing/wasm/`.
- Official `@mujoco/mujoco` pinned to **3.14.0**, matching the native reference.
  Original collision meshes, body inertias, joints, actuator laws and motor
  curves exported into `app/public/landing/physics/`.
- `BrowserForces.js` translates the existing forces in double precision with
  1 ms integration and 250 Hz motor/sensor exchange. Original PCG64/Ziggurat
  noise matches NumPy exactly across 20,000 normal samples.
- `BrowserPX4.js` boots PX4 and flies using the original pilot equations.
  Strict actuator lockstep now waits asynchronously with `Atomics.waitAsync`,
  so thread proxies and input messages can run while awaiting PX4.
- `BrowserWorld.js` compiles the actual game heightfield and obstacles in a
  worker; attempts IndexedDB caching of the compiled world. Actual route
  candidates are checked against terrain depth and colliders.
- `BrowserGame.js` adds boat route/manual motors, deck interlocks, radio
  estimates, HUD packets and original drone/dock/navigation camera transforms.
- `BrowserSimulationWorker.js` schedules simulation independently of rendering.
  `SimulationBridge.js` now connects to this worker instead of localhost HTTP
  and WebSocket physics. It sends keyboard changes immediately and renders
  timestamp-interpolated CAD/camera/hull poses with synchronized wave phase.
- Vite has COOP/COEP headers and ES module workers configured.

Recorded results (headless Node; **not a browser FPS measurement**):

| Check | Result |
| --- | --- |
| Original motor replay: throttle, differential motors, camera | Maximum position error about `1.14e-12 m` |
| Independent native PX4 vs WebAssembly closed-loop sequence | Max displacement error **26.2 mm**, velocity **0.0134 m/s**, attitude **0.605 degrees** |
| Closed-loop compute throughput | **17 simulated seconds / 7.55 wall seconds**, about **2.25× real time** |
| Full collision world compilation | **1,676 geoms**, about **10 seconds** on this machine |
| Boat water/route run | 10 simulated seconds / 6.07 wall seconds; speed **2.48 m/s**, route error **2.12 m** |
| Platform and lids | Headless lowering/closing assertions passed |

Reports: `benchmarks/flight-parity/browser-replay.json`,
`browser-closed-loop.json`, `browser.csv`. These are independently computed
traces, not two plots of the same state. They establish tested parity, not a
universal percentage guarantee.

## Remaining work — in order

1. **Exercise the final worker integration.** The source bridge is switched,
   but the complete game worker has not been tested end to end after the last
   asynchronous lockstep change. Check keyboard delivery under a 25 FPS render
   schedule, takeoff/hover/movement/descent/landing, B/U switching, all CAD poses,
   wave synchronization, radio dropout/reconnect, mechanism interlocks and reset.
   Reset/retry must terminate every PX4 pthread worker before starting another
   runtime. Check shutdown during startup and avoid orphaned workers.

2. **Finish boat/environment parity.** Cabin drainage/retained-water mass is
   not ported yet. The browser disables old procedural shore proxy boxes and
   uses actual tiled terrain instead; review boat shoreline collision behavior
   and masks. Check boat angular velocity/force reference points against native
   MuJoCo, speed-needle units, full closed-route laps and reset placement. The
   actual world test used the exported terrain/colliders, not an automated game
   browser capture. Audit configuration fields and IDs after world compilation.

3. **Finish offline support and static hosting.** No service worker, offline
   asset manifest, offline-registration helper or standalone static server has
   been implemented. The interrupted attempted patch created **none** of these
   files. Add offline caching of app, CAD, collision meshes, PX4/MuJoCo WASM and
   other needed assets. Verify IndexedDB model caching and storage-quota fallback.
   Serve COOP `same-origin` and COEP `require-corp`; SharedArrayBuffer requires
   these. Keep all physics local and avoid silent fallback to the native backend.

4. **Replace the default launcher.** `Start-TidewaterGame.ps1` still starts the
   old WSL backend/relay and Vite. Change it to start only static files or the
   frontend development server. Players should only open the URL; opening the
   browser remains manual. Retain native simulation as an optional reference
   benchmark, not a player dependency. Existing dev server is localhost:5189;
   legacy relay/backend are localhost:5195 and WSL:5195.

5. **Finish source notices and build reproducibility.** `wasm/NOTICE.md` names
   PX4 BSD-3-Clause, MuJoCo Apache-2.0 and NumPy BSD-3-Clause, but the actual
   license/copyright files still need to accompany the distributed assets.
   The developer build assumes a prepared Emsdk/PX4 cache; add a reproducible
   bootstrap/pin-check workflow. Review startup parameter extraction (it takes
   numeric commands from conditional rcS blocks) against effective native
   parameters. Uncompiled optional parameters and FlightTaskTransition warnings
   appear in startup logs; resolve or document them accurately.

6. **Rebuild and verify the final package.** The last successful production
   build predates asynchronous lockstep changes. Run a fresh build and headless
   checks after fixes. Benchmark startup, deck and flight headroom, input latency,
   worker resets and longer sessions. Test real browser behavior only if the user
   changes the explicit prohibition; otherwise provide a manual verification
   checklist and clearly label unverified browser performance.

7. **Update documentation/UI.** README and launcher instructions still describe
   WSL/native default operation. Change them after browser integration is stable,
   explain first-load compilation/offline cache requirements, document current
   measurements and preserve uncertainty. Some HUD copy still says native MuJoCo.

## Checks and developer environment

Run from repository root, without opening a browser:

```powershell
node tidewater-game/wasm/tests/browser-replay.mjs
node tidewater-game/wasm/tests/browser-closed-loop.mjs
node tidewater-game/wasm/tests/browser-world-smoke.mjs
node tidewater-game/app/test/tidewater-controls.mjs
node tidewater-game/app/test/tidewater-pose-timeline.mjs
cd tidewater-game/app
npm run build
```

Large generated `.mjb` test models and the optional `.mjb.gz` baseline are
excluded from Git; regenerate them before those tests. Runtime map fixtures are
also local/ignored: tests currently expect `simulation/runtime/live-map.json`
and `live-heights.bin`. Make clean-checkout fixture preparation reproducible.

Existing developer-only WSL cache on this machine:

- Emsdk 4.0.10: `/home/gamee/.cache/tidewater-game/emsdk`
- Pinned PX4 adapter checkout: `/home/gamee/.cache/tidewater-game/px4-wasm-source`
- Build: `/home/gamee/.cache/tidewater-game/px4-wasm-build`
- Native reference: `/home/gamee/.cache/smartdrone2/PX4-Autopilot`
- Python: `/home/gamee/.cache/tidewater-game/python/bin/python`

Developer scripts: `wasm/build_px4.sh`, `wasm/export_browser_assets.py`,
`wasm/tests/export-replay.py`, `wasm/tests/export-closed-model.py`.
The completed compiled PX4 artifacts are committed; players do not build them.
Do not stop unrelated training Python processes in this workspace.

This is an **unfinished implementation checkpoint**, not a completed release.
