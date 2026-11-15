> Preserved technical reference from the workspace before the 25 October 2026 documentation refresh.
> Start with the current folder README for the project overview.

# Tidewater — browser PX4 and MuJoCo

The original Holybro X500 **V2** and AERODOCK models run with MuJoCo 3.14.0
and the original PX4 v1.16.0 flight stack in browser workers. The player opens
a static URL. Physics, estimation and controllers run on the player's machine.
The original drone CAD and source simulator remain the reference.

For local hosting, use Node.js 22 or newer (Node 24 was tested). From the
repository root, prepare and serve the production package:

```sh
cd tidewater-game/app
npm ci
npm run build
npm start
```

Open `http://127.0.0.1:5189/` **manually**. The server serves static files with
COOP/COEP headers; it does not run a physics process. Players using a hosted
package only need the browser. On Windows, `./Start-TidewaterGame.ps1` builds a
missing `dist/` and serves it in the foreground. Use `-Dev` for Vite. After source
changes, run `npm run build` again. These launchers never open a browser.

Use a recent WebGPU-capable Chrome/Edge and sufficient memory for the original
CAD world and PX4 pthread pool. SharedArrayBuffer requires HTTPS (or localhost)
and these response headers on the page, workers, modules and WASM assets:

```text
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Resource-Policy: same-origin
```

Static hosting must support those headers. Ordinary GitHub Pages does not
provide the required header configuration. Vite dev/preview and the included
Node static server provide it. The package supports a same-origin subdirectory.

## First load and offline operation

The first visit compiles the rendering shaders and the original collision CAD
with the actual Tidewater heightfield and obstacles. World compilation runs in
a temporary worker, which is terminated before the compiled model is loaded into
the flight worker. This releases the compiler's peak WebAssembly memory without
changing the collision model. IndexedDB stores the compiled model; its key covers map,
collision asset hashes and model versions. Corrupt entries rebuild; unavailable
storage or quota exhaustion falls back to compilation.

A production build includes a versioned SHA-256 offline asset manifest. The
service worker caches the app, original CAD/textures, collision meshes, audio,
PX4 and MuJoCo WASM, worker modules and licenses. Wait for **Offline files ready**
before disconnecting. The compiled collision cache uses additional storage;
allow room for it and for updates. Development mode does not register offline
caching. Failed cache installation preserves the previous complete version.
Close existing game tabs and reopen to activate a downloaded update. Browser
storage clearing or eviction requires another complete online load.

Simulation runs independently of rendering with 1 ms physics, strict 250 Hz
sensor/actuator lockstep, and 25 Hz pilot decisions. Timestamped CAD, camera and
hull poses are interpolated on one presentation clock; physical wave phases use
that same clock. Reset/retry waits for PX4 pthread shutdown before replacing the
runtime. A shutdown timeout asks for a page reload rather than creating a
second unconfirmed runtime.

## Controls and deck operation

- **B** switches drone/boat; **U** switches the two original boat cameras.
- Drone: **WASD** moves, **R/F** climbs/descends, **Q/E** yaws. Arrow keys or mouse
  move the articulated camera. **T** takes off and lands.
- Boat: **P** switches automatic/manual motors; **W/S** controls both throttles,
  **A/D** steers differentially. Sliders set individual motors.
- Lower the platform before closing the lids; open both lids before raising it.
  Wait for physical settling between movements. Occupied lids can contact the
  actual drone geometry; exercise complete mechanism strokes with an empty bay.
- **C** retries the simulated SX1262 link after restoring range/line of sight.
  These are estimates, not readings from radio hardware.
- **Disable SX1262** stops simulated packets and zeros the ML beacon input.
  The link stays off until **Enable SX1262** is pressed; retry cannot override it.
  Local video and vehicle controls remain available.
  Missing radio input does not inhibit flight commands. The browser controller
  can use accepted visual marker poses without a radio reference; camera,
  estimator, command bounds and visual landing checks still apply. Unknown dock
  readiness is zero input, rather than a reported dock fault. A valid radio
  packet reporting an unready dock still inhibits flight commands.
  With no metric pose, **visual_acquire** uses the network's image bearing for
  horizontal approach and gimbal aiming while holding vertical velocity at zero
  (subject to the existing slew limits). **visual_search** searches with the
  gimbal when no confident target is visible. Known paint dimensions initialize
  metric range independently of the zeroed radio position. Successive accepted
  camera poses and PX4 odometry provide boat velocity. The original geometric
  fit, paint precision/recall, conditioning and descent checks remain required;
  a neural visibility score alone never enables descent.
- **Home**, Reset, and Retry replace the browser simulation and restore spawn.

The boat follows a terrain-validated closed route. Buoyancy, orbital water
velocity, drag, propellers, cabin drainage, retained-water mass, and lift/lid
actuators operate on the original physical bodies. The speed needle uses km/h.
Four physical wave components have a 5 cm combined crest-to-trough bound.

## Verification and developer rebuilds

No browser was opened for this work. See
[the browser verification notes](../wasm/README.md) for reproducible headless tests,
source-build pins, measured results and a manual browser checklist. Node worker
pacing and message latency are not browser FPS or rendered visual measurements.
The Windows PowerShell launcher still needs manual execution on Windows.

The optional native Python/PX4 service and its independent benchmarks remain in
`simulation/`. They are reference developer tools. Browser gameplay selects the
WASM worker and reports failures explicitly.

[Flight benchmark reports](../benchmarks/flight-parity) include independently
computed native and WASM traces. [Distributed licenses](../app/public/licenses)
cover PX4, MuJoCo and the translated NumPy RNG routines. Additional game/asset
notices accompany their models and textures.
## Trained drone landing policy

After taking off, press **L** to hand the drone to the workspace's
**vision-first radio-fusion** policy. The button changes to **Manual control**; press it
to resume piloting. **Land** also cancels ML control. Boat control is independent
of ML: route following keeps its normal 1.5 m/s target, and manual throttles,
steering, stop and auto/manual selection remain available while the policy flies.
The policy's existing 2 m/s horizontal command limit remains unchanged; it may
not catch or land on a faster boat.

The deployed model is exported from
`artifacts/vision_first_fusion_20261017/vision_first_fusion_delivery/candidate/pose.pt`
(SHA-256 `2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4`).
It receives a separate 640×360 onboard RGB camera and the original 32-value
estimator/beacon/gimbal observation contract, plus two reported radio uncertainty
values. Its visual recurrent memory receives no radio coordinates or radio status.
A learned gate blends radio into the pose estimate with a maximum weight of 0.35;
raw radio coordinates cannot steer the acquisition or controller directly.
Missing radio uses explicit validity and uncertainty, rather than a zero-metre
target. The spatial acquisition head finds image bearings; confirmed visual
registration is still required for descent and touchdown. ONNX executes every neural operation
on WebGPU in FP32 with a captured graph and persistent buffers. Unsupported GPUs
report an error; gameplay does not silently switch to CPU inference. The Python
landing controller and supervisor run in a separate Pyodide worker. The metric
registration uses a compiled FP64 implementation of the reference TRF solver,
loss, bounds, finite differences, samples and acceptance tests. Assets are local
and included in offline hosting.

The network shares the rendering GPU device and converts the sensor texture
directly to the original FP32 inputs. Neural execution overlaps full RGB
readback for the controller; it does not wait for a CPU image upload. The
original Python observation builder still supplies every numeric input.

Intel GPUs use the NCHW execution layout measured on this laptop's Intel UHD;
other GPUs retain NHWC. Both execute the same FP32 model and full sensor input.
Add `?gpu=integrated` to the game URL to request the browser's low-power adapter.
This is an adapter preference, not an OS-level GPU override: check the flight
HUD's **GPU intel** label or the timing report to verify the selected device.
The renderer and network share that selected device. No NVIDIA API is required.

The camera geometry adapter caches only exact, unchanged calibration/encoder
prefix matrices. Returned matrices remain independent and all matrix operations
keep the original FP64 order. The sensor renderer can reuse bounded GPU render
bundles for identical command streams; changing streams retain direct rendering.
Pixel parity and controller command parity are checked separately. These changes
do not reduce image size, precision, physics/control rates or render settings.
See `benchmarks/flight-parity/ml-igpu-20261015.md` for measured performance and
the remaining Intel UHD real-time limitation.

Decisions occur every 0.04 simulation seconds. Camera/inference overlaps physics;
each timestamped decision is applied at the following control boundary, with a
fixed 40 ms command delay. World velocity encoding uses the observation's heading,
and `ml.timings.command_age_s` exposes the delay. If inference overruns that boundary,
the simulation waits for the complete result; no policy decision is dropped or
physics step enlarged. The clock retains its deadline and catches up after transient
overruns; mode transitions start a new pacing period so slow ML does not speed
up later manual flight. The UI reports the actual real-time factor.
Only one frame/action can be pending. Manual takeover cancels pending actions
and releases neural buffers/session. Reset and shutdown release workers. Camera resources
are fixed in size and reused across toggles.

**Record timing (10 s)** saves bounded local performance samples and one synthetic
onboard frame for replaying visual registration. The included server retains
timestamped reports when launched with `--timing-file`; other hosts download JSON.

The **18 October hardening revision** adds uncertainty-aware visual memory,
braking before close approach, a geometry-based final descent veto and bounded
recovery with a clearance-gated climb. Neural weights are unchanged. In the
frozen fresh native suite it landed on the boat in **58/60 flights**, with two
home fallbacks and zero collisions/water strikes; separate safe-home checks
passed **10/10**. Actual Tidewater runtime checks landed on an unpowered boat in
**40.4 s** and an independently moving boat averaging **0.63 m/s in 47.7 s**.
Both used no boat radio position or velocity input. These are finite simulation
results, not a hardware or universal reliability guarantee. See the
[hardening report](../benchmarks/flight-parity/landing-hardening-20261018.md) and
[hash-bound certificate](../app/public/policy/qualification/r15_simulation_qualification_certificate.json).

**Additional Tidewater stress tests:** the unchanged policy subsequently landed
in 0/18 challenging search/start cases and 5/8 initially visible diagnostic cases.
With radio, ~1.00 m/s landed twice; ~1.35 m/s failed. Without radio, even ~0.35 m/s was
start-dependent. See the [new complete results](../../landing_training/docs/reports/TIDEWATER_TEST_RESULTS_2026-10-18.md).
The earlier two simple successes are not evidence of general Tidewater reliability.

A boat landing requires physical foot support and two seconds of stable,
disarmed deck contact. This boat-launch game has no authorized stationary home:
bounded recovery exhaustion or the mission deadline restores manual hold.
Handoff preserves the measured altitude even after a recovery above the normal
8 m manual ceiling. The declared static map only vetoes unsafe upward recovery;
the sea-level/nominal-deck prior supplies no dynamic boat position or touchdown
truth. Independent boat controls and the 1.5 m/s cruise remain unchanged.

Developer preparation: build `wasm/build_marker.sh` with the pinned Emscripten
runtime, then run `app/tools/export-vision-first-policy.py` with the training
dependencies, frozen candidate and native fixtures available, then `node tools/vendor-policy-runtime.mjs`
from `app/`. `npm run test:ml` runs the focused checks after export creates fixtures.
