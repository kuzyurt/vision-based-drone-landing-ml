# Browser-only PX4/MuJoCo port — implementation complete, manual checks pending

## Required outcome and constraints

The existing Holybro X500 **V2**, original PX4 controller and MuJoCo physics now
run in browser workers. Players open a static URL; local Node is only a static
host/build convenience. The default launcher no longer starts WSL/native physics.
The original drone CAD/source simulator and boat reference code were not edited.

**Do not open or start a browser.** The user reserves opening it for themselves.
This remains an explicit constraint. Real browser visuals/FPS, browser storage
policy and PowerShell execution on Windows are manual checks, not claimed results.

## Completed since the previous checkpoint

1. Shared `BrowserRuntime` initializes and schedules the actual PX4/MuJoCo world,
   queues early input and cancels startup. Shutdown waits for pending factories,
   stops PX4 pthreads, joins the loop and frees MuJoCo model/data before acknowledging.
   The bridge waits for that acknowledgment before replacement, ignores old packets,
   shares pending CAD installation across resets and aborts downloads on close.
   A shutdown timeout prevents another unconfirmed runtime from being created.
2. `BrowserDrainage` ports the original four pickups, dual pumps, ingress/head/flow,
   retained-water mass and COM changes. MuJoCo state outputs use `DoubleBuffer`;
   ordinary JS arrays do not receive those output writes. Boat angular/COM velocity
   was compared against MuJoCo directly. The speed needle now resolves its actuator
   and uses km/h. Closed routes wrap correctly; spawn rotation preserves drone offset.
3. The physical asset exporter preserves source XML decimal precision. The former
   MjSpec serializer rounded it. Original motor replay again agrees to floating-point
   precision. World compilation remaps geometry masks/IDs, validates versions/state
   layout and handles IndexedDB hits, corrupted models and unavailable/quota storage.
   Real tiled terrain owns shoreline collisions; stale shore proxies stay disabled.
4. Production builds generate an SHA-256 offline manifest and versioned service
   worker cache. Failed hashes/quota installation preserve the last complete version.
   All required app, CAD/collision, audio, worker, PX4/MuJoCo and license files are
   included. The current package is about **144 MiB**; the compiled IDB model needs
   additional storage. Test-only MJB/gzip fixtures stay outside the player package.
5. A standalone Node static server supplies COOP `same-origin`, COEP `require-corp`,
   CORP `same-origin`, correct WASM MIME and safe file paths. The PowerShell launcher
   runs static hosting or Vite, with manual browser opening. Native simulation remains
   an optional developer reference. Vite uses the same isolation headers and port 5189.
6. A clean bootstrap pins PX4 v1.16.0 commit
   `6ea3539157ca358c70a515878b77077af7d4611d`, Emsdk 4.0.10 commit
   `62a853cd3b3134398ce85cde8bb5cbb2ef0194cb`, Python build requirements and submodules.
   A full source build succeeded; repeating it reported `ninja: no work to do`.
   `app/public/landing/wasm/provenance.json` records source and artifact hashes.
   Full PX4, MuJoCo, NumPy/PCG, dependency and runtime notices accompany the package.
7. All **49** explicit original flight/sensor parameters were read back successfully.
   The optional hardware defaults `TRIG_INTERFACE` and `GPS_UBX_DYNMODEL` are absent
   and recorded as warnings. The fresh build compiles/links `FlightTaskTransition`
   and includes its generated task constructor. VTOL operation is not tested.
8. Both ocean mip passes now fit the minimum four-storage-texture WebGPU limit;
   the fifth mip write moved to the second pass, preserving its reduction values.
   The WGSL test captures validation errors and passes with Dawn's null backend.
   This is shader/resource validation, not rendering/FPS. CPU fixture generation
   defers decorative GPU uploads and regenerates the actual app world reproducibly.
9. README, startup instructions, HUD wording and the manual checklist describe the
   browser default. No unrelated training process was stopped and no training data
   collection or model training was started.

## Latest measured evidence

These are headless Node measurements on this cloud machine, **not browser FPS**.
Independent native reference traces remain committed.

| Check | Latest result |
| --- | --- |
| Original motor/camera replay | Maximum position error about `1.14e-12 m` |
| Independent native vs freshly rebuilt WASM PX4 | Max displacement `20.3 mm`, velocity `0.00922 m/s`, attitude `0.369 degrees` |
| Closed-loop compute | 17 simulated seconds / 2.46 wall seconds, about 6.91× real time |
| Real full-world worker | 72.93 simulated seconds, about 1.003× paced real time |
| Cold worker startup | About 11.3 seconds |
| Keyboard message observation under 25 Hz presentation | Maximum 31.1 ms |
| Repeated startup/cancellation | Two started sessions and three startup cancellations; zero PX4 pthread workers after disposal |
| Full boat lap | 534 m travelled, max route error 4.11 m, 214.56 sim seconds / 41.44 wall seconds |
| Drainage/reference agreement | 120 samples, maximum scalar error about `2.22e-16` |
| Full collision world | 1,675 geoms; about 2.81 seconds compilation |

Reports are in `benchmarks/flight-parity/browser-*.json` and `browser.csv`.
The complete worker test covers actual takeoff, hover, forward/brake/return,
empty-bay platform/lid strokes, mechanism interlocks, repeated camera switches,
descent, landing/disarming, reset and shutdown during startup (including a pending
PX4 factory). Other checks cover actual shoreline contacts, waves, radio loss/manual
reconnect, cache recovery, bridge races, offline version/hash/quota behavior and
real static-server headers. No rendered video/screenshot was used for these claims.

## Reproduce without a browser

From the repository root:

```sh
cd tidewater-game/app
npm ci --cache /tmp/tidewater-npm-cache
npm run test:browser
npm run build
npm run test:offline
TIDEWATER_GPU_BACKEND=null node test/tidewater-water-shader.mjs
```

`test:browser` regenerates ignored fixtures before executing tests. It uses Node
and committed independent native references. To regenerate the separate drainage
reference, use the optional native Python environment and `wasm/tests/export-drainage.py`.
No old WSL cache, pre-existing map file or native simulation server is needed for
these Node checks. For source rebuild instructions and dependencies see
[`wasm/README.md`](wasm/README.md).

## Remaining manual checks

The full checklist is in [`wasm/README.md`](wasm/README.md#manual-browser-verification):
open the production URL manually, verify rendered CAD/cameras and handling on the
intended GPU, reduced-FPS input/wave synchronization, deck operation with an empty
bay, landing, radio recovery, repeated resets, and warm/cold offline reloads.
Execute `Start-TidewaterGame.ps1` on Windows. Record actual browser FPS/startup and
a longer rendered session before describing the release as browser-verified.

The cloud configuration draft preserves the landing-training setup, adds the
tested Node dependency installation/start instructions, and records
`storage.googleapis.com` for Emsdk artifact downloads; the current source build successfully downloaded them.
Draft changes still require review/save and publication in environment settings
for a reusable cloud configuration. No publication or fresh-task restore is claimed.
