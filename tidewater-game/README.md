# Tidewater game

The browser game lives in [app](app/README.md). Tidewater-specific code, runtime support, archived
renders, benchmark captures, and dated update material stay inside this folder. Drone-training and
landing-policy experiments remain in the repository's root `artifacts/` folder.

To run the game locally:

Install the app dependencies once, then launch both the browser renderer and the local PX4/MuJoCo
service from the repository root (Node.js, Python with MuJoCo, and Ubuntu-22.04 in WSL are required):

```powershell
cd tidewater-game/app
npm ci
cd ..
./Start-TidewaterGame.ps1
```

Open `http://127.0.0.1:5189/` in a WebGPU-capable browser. The first flight session sends the
generated Tidewater heightfield to MuJoCo so boat routing and SX1262 line-of-sight estimates use the
same coast and obstacles visible in the game. The on-screen SX1262 figures are estimates; no radio
hardware is connected.

The launcher starts the two local services and leaves opening the browser to you. After entering
the game, wait for the original vehicle camera and physics service. Take off is enabled
when both are ready. The boat holds still during aircraft launch, then follows its validated
524 m closed water loop. Switching to the boat also allows starting its route or using manual
motors. A failed simulation displays its cause and a **Retry simulation** button; **Reset** and
**Home** also restart a failed simulation.

## Physics and performance

The game uses the original Holybro X500 V2 and AERODOCK CAD models, inertias,
collision shapes, motor/propeller curves, buoyancy cells and drag coefficients.
MuJoCo runs locally inside WSL with its original implicitfast solver and 80 iterations.
Numba compiles the original force equations. A small Windows localhost relay carries
the game UI traffic; no browser is launched by the scripts.
The relay also supplies the Windows clock. The service calibrates its WSL clock
against it so platform speeds and aircraft motion use the browser's real time.

The default game runs the original PX4 firmware and estimator with the original
keyboard pilot code, flight parameters, motor forces and 1 ms MuJoCo integration.
The sensor/actuator exchange remains in strict 250 Hz lockstep. PX4 logs and its
working state live on WSL's Linux filesystem to reduce flight-loop I/O stalls.
Numba compiles the force calculations without fast-math or changed gains.
Rendering remains independent: CAD poses and camera transforms are interpolated
from 20 Hz updates. Browser FPS and simulation speed are separate measurements.

The reference pilot commands 1 m/s horizontal speed (including normalized diagonal
input), 0.6 m/s climb/descent target changes and 0.5 rad/s yaw. The articulated
camera uses the original joint damping and actuator law, with a 1 mm near plane.
The optional legacy local controller is selected with `TIDEWATER_CONTROLLER=native`;
it is not the reference flight implementation.

See [the flight benchmark](benchmarks/flight-parity/README.md) for independent PX4
traces, original-versus-original repeatability, recorded samples and source hashes.
The measured flight response difference was at most 19.9 mm displacement,
0.00593 m/s velocity and 0.064 degrees attitude in the recorded maneuver sequence.
The original repeat run differed by up to 10.7 mm. Identical calm motor inputs
agree to floating-point precision; the gust case has a small reported residual.
These results cover the tested scenarios and do not claim universal exact identity.

The four wave components are shared by rendering and the original buoyancy equations.
Their maximum combined crest-to-trough height is 0.05 m. Boat roll, pitch and heave
come from water forces. The original full platform stroke takes 8 simulation seconds
and each full lid stroke takes 5.75 simulation seconds. Mechanism interlocks prevent
closing the lids with the platform raised or moving two mechanisms at once.
Physical mechanism settling can add a small delay to the commanded servo stroke.
The original short-wave FFT texture also supplies optical ripple normals, gust/slick
variation and fine reflection detail, updated at 30 Hz in flight mode. These shading
details add no surface displacement. Shoreline foam follows the shared physical wave
phase and actual wet depth; the former large breaking-surf displacement stays disabled.

Use **B** to change vehicle, **U** to change boat camera, **P** for auto/manual boat
motors, **W/S** for both throttles, **A/D** for differential steering, and the visible
motor sliders for individual throttle. **Home** resets both vehicles. Drone controls:
**WASD** horizontal movement, **R/F** climb/descend, **Q/E** yaw, arrow keys or mouse
for the original articulated camera. **C** retries the estimated SX1262 link.

Verification scripts are in `simulation/tests/benchmark_flight.py`,
`simulation/tests/verify_live.py`, `app/test/tidewater-controls.mjs` and
`app/test/tidewater-water-shader.mjs`. The benchmark executes the unmodified
original `Simulation.physics` and `Simulation.setpoints` as its reference,
audits physical parameters, replays identical motors and runs independent PX4
maneuvers. Full-scene live checks separately measure simulation pacing, takeoff,
keyboard and camera movement, boat motors, mechanism timing and reset.

The latest full-scene headless check measured **0.984× real time on the deck** and
**0.992× in flight**. Forward motion covered 2.47 m in 3 seconds, descent 0.59 m
in 2 seconds, platform lowering took 8.31 wall seconds (8.02 simulated), and lids
closed in 5.83 wall seconds (5.80 simulated). Camera movement, repeated camera and
vehicle switches, manual boat motors, the 5 cm wave limit and reset passed.
See `benchmarks/flight-parity/live-game-verification.json` for these measurements.
Performance varies with machine load; this check does not measure browser FPS.
