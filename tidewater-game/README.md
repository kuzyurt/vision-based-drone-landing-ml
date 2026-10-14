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
the simulation worker. IndexedDB stores the compiled model; its key covers map,
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
  move the articulated camera. Use the Take off, Hover and Land controls.
- Boat: **P** switches automatic/manual motors; **W/S** controls both throttles,
  **A/D** steers differentially. Sliders set individual motors.
- Lower the platform before closing the lids; open both lids before raising it.
  Wait for physical settling between movements. Occupied lids can contact the
  actual drone geometry; exercise complete mechanism strokes with an empty bay.
- **C** retries the simulated SX1262 link after restoring range/line of sight.
  These are estimates, not readings from radio hardware.
- **Home**, Reset, and Retry replace the browser simulation and restore spawn.

The boat follows a terrain-validated closed route. Buoyancy, orbital water
velocity, drag, propellers, cabin drainage, retained-water mass, and lift/lid
actuators operate on the original physical bodies. The speed needle uses km/h.
Four physical wave components have a 5 cm combined crest-to-trough bound.

## Verification and developer rebuilds

No browser was opened for this work. See
[the browser verification notes](wasm/README.md) for reproducible headless tests,
source-build pins, measured results and a manual browser checklist. Node worker
pacing and message latency are not browser FPS or rendered visual measurements.
The Windows PowerShell launcher still needs manual execution on Windows.

The optional native Python/PX4 service and its independent benchmarks remain in
`simulation/`. They are reference developer tools. Browser gameplay selects the
WASM worker and reports failures explicitly.

[Flight benchmark reports](benchmarks/flight-parity/) include independently
computed native and WASM traces. [Distributed licenses](app/public/licenses/)
cover PX4, MuJoCo and the translated NumPy RNG routines. Additional game/asset
notices accompany their models and textures.
