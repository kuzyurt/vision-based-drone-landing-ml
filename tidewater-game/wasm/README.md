# Browser runtime build and verification

PX4 is pinned to `6ea3539157ca358c70a515878b77077af7d4611d` (v1.16.0).
Emsdk 4.0.10 is pinned to `62a853cd3b3134398ce85cde8bb5cbb2ef0194cb`.
The SDK resolves the official release `8103ffedfb0c42d231c6af6859a5a1a832260b43`.
MuJoCo is the official `@mujoco/mujoco` 3.14.0 package. Players use the committed
PX4 artifacts and the production package; they do not build the flight stack.

## Rebuild PX4 from a clean developer machine

Linux prerequisites are Git and Python 3 with venv support (Python 3.12 was tested). The bootstrap
creates an isolated build Python environment and installs the pinned build
requirements, Emsdk and selected recursively pinned PX4 submodules. Downloads
use GitHub, PyPI and `storage.googleapis.com` with normal verification enabled.

```sh
# From the repository root. This directory must be writable.
export TIDEWATER_WASM_CACHE=/workspace/tidewater-build
export TIDEWATER_BUILD_JOBS=4
bash tidewater-game/wasm/build_px4.sh
```

Use another cache path outside this cloud machine. An existing native reference
can optionally be supplied as `TIDEWATER_NATIVE_REFERENCE`; fresh builds do not
require that old WSL cache. Source and SDK pin mismatches fail before compilation.
`app/public/landing/wasm/provenance.json` records adapter/source hashes and shipped
artifact hashes. A complete source build and an incremental repeat were tested.
Flight algorithms remain upstream; platform/transport adapters and the existing
reference battery decoding correction are applied in the separate build checkout.

Startup uses numeric ROMFS defaults, followed by all explicit original X500
flight/sensor parameters. ROMFS extraction does not execute arbitrary shell
conditionals. `browser-parameters.mjs` reads back all 49 explicit effective
parameters and compares them with the original exported configuration. An
unavailable required parameter fails startup. The optional `TRIG_INTERFACE`
camera trigger and `GPS_UBX_DYNMODEL` hardware GPS defaults are absent in this
browser target and are recorded as warnings. The fresh source build includes
`FlightTaskTransition` in its generated task table and links its implementation,
resolving the earlier artifact's missing-task concern. VTOL flight is not tested. Compile-time precision warnings are retained
in the build output; no fast-math or controller gain changes are applied.

## Clean-checkout headless checks

```sh
cd tidewater-game/app
npm ci
npm run test:browser
npm run build
npm run test:offline
# Optional WGSL validation without a hardware GPU:
TIDEWATER_GPU_BACKEND=null node test/tidewater-water-shader.mjs
```

In a cloud workspace with a read-only home cache, use `npm ci --cache /tmp/tidewater-npm-cache`.

The fixture preparer regenerates ignored MuJoCo binaries and the runtime map
using the same terrain, village, vegetation, rock and debris CPU builders as the
app. Decorative GPU buffer uploads are omitted during fixture generation.
Independent native reference samples are committed; headless browser checks
need Node, not a native simulation service. The optional Python
`tests/export-drainage.py` regenerates the committed drainage reference directly
from the unmodified `CabinDrainage` implementation.

For physical-asset refresh, use the optional native reference environment to run
`simulation/prepare_physics.py` and `wasm/export_browser_assets.py`. The exporter
preserves original XML decimal precision. Test-only compressed binary models
stay under `wasm/tests/`, outside the player package.

Reports are under `benchmarks/flight-parity/`:

- `browser-replay.json`: independent original motor/camera replays.
- `browser-closed-loop.json` and `browser.csv`: actual WASM flight versus the
  independently computed native PX4 trace, with separate phase/error metrics.
- `browser-parameters.json`: effective required parameters and optional warnings.
- `browser-worker-integration.json`: real WASM worker startup, flight/landing,
  empty-deck strokes, interlocks, camera/vehicle switches, input delivery under a
  25 Hz presentation schedule, repeated startup and cancellation of pthread pools.
- `browser-environment.json`: a complete closed boat route and route error.

Additional tests cover native drainage agreement, force reference points,
actual shoreline collision, radio loss/reconnect, wave coordinates, IndexedDB
cache recovery/quota failures, bridge startup/reset races, offline cache updates
and the real static server's isolation headers. The WGSL test uses Dawn's null
backend for validation when requested; this verifies shaders and resource limits,
not GPU rendering or performance.

## Manual browser verification

The user explicitly reserves opening the browser for themselves. Browser FPS,
visual output, actual browser storage policies and Windows launcher execution
remain manual checks:

1. Launch the static server and open the URL manually. Wait for the original CAD
   view and **PX4 ready**, then Take off, hover, move, brake, yaw and descend.
2. Check immediate key release and smooth CAD/camera/hull motion at normal and
   reduced rendering FPS; check the water stays synchronized with the boat.
3. Repeat **B/U** switches. With the aircraft clear of the bay, lower the platform,
   close/open lids and raise it; verify disabled/interlocked actions and settling.
4. Return to the stationary boat and land. Inspect contact and disarming. Move
   out of radio range/behind terrain, return, and press **C** to reconnect.
5. Reset/retry repeatedly in flight and while startup is loading. Confirm there
   are no accumulating PX4 worker pools and that both vehicles restore their spawn.
6. Wait for **Offline files ready**, close the tab, disconnect the network and
   reopen/reload. Test both a warm compiled-world cache and a cleared IndexedDB
   model cache. If browser storage is denied, confirm explicit offline failure
   while online simulation still works.
7. Test the production package on the intended WebGPU hardware and record actual
   FPS, startup latency and a longer session. Headless Node measurements do not
   establish these hardware/browser results.
