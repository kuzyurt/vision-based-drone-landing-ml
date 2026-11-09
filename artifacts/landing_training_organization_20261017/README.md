# AERODOCK airborne landing training

This third folder combines the existing drone and boat models in one MuJoCo
simulation, runs native PX4, and supplies an expert, review recordings, gated
dataset collection and a recurrent imitation policy.

**Current stage: environment review. No training dataset or trained weights have
been produced.** Review recordings are permanently labelled `review` and cannot
be used by the training loader. User approval of all videos and recorded data is
required before collection or training.

## Review the exported result

The latest corrections and five supplementary stress videos are in
[the stress review page](outputs/stress_review/index.html), with the measured
[speed/weather report](outputs/stress_review/speed_report.json). Boat visuals use
the original AERODOCK CAD meshes. Drone legs remain visible and collidable;
the expert turns the aircraft toward the boat during approach, then selects a
front/back deck heading before descent. The grey box is the fixed takeoff pad;
it is unchanged.

The calm-water speed screening covered 1.4, 1.45, 1.475, 1.49, 1.5, 1.55, 1.6,
1.8 and 2 m/s targets, in both directions. The highest confirmed setting is
**1.5 m/s (5.4 km/h)**: 30/30 fresh seeded flights landed, covering all five map
types, both directions, starts 10/20/40/60 m away and 2.5/4/6/8 m high. Actual
mean speed over each flight's final five seconds was approximately 1.500–1.510
m/s. At 1.55–1.8 m/s the tested aircraft made contact but PX4 did not confirm
landing; at 2 m/s it could not close the approach and aborted. This is a measured
limit of the configured simulator/controller, not the real drone's physical
maximum or a reliability guarantee for other conditions.

The strong-weather videos use the original model's maximum 0.5 m wave-height
parameter, 4.5 s period, and/or gusty wind with an 8 m/s mean. The combined fast
case uses a separately tested 1.4 m/s boat target. The 3 s wave-period experiments
aborted and remain in the report; no success is claimed for them. All five
requested video scenarios passed native PX4 preflight trials. The report retains
65 current-controller trial results, including failures. A render-only water
background and external near-plane update is documented separately; hashes
verify that control, physics, CAD assets and the PX4 binary did not change during
those visual updates.

The original ten videos below are retained as the historical baseline. Their
source fingerprints predate these corrections and cannot approve the current
runtime. The five supplementary experiments do not authorize collection or
training. A current baseline bundle must still be explicitly verified before
collection; regenerate it into a new directory with the documented review
command when proceeding to that stage.

Open [the review page](outputs/review_bundle/index.html). It links all ten MP4s,
the contact sheet, scenario configurations, JSONL input/output rows, HDF5 RGB
records, qualification report, recording audit and the complete proposed
collection plan. Generated artifacts are ignored by Git; retain/download this
folder separately when moving the source checkout.

Every video is 1280 × 720 at 25 fps and contains:

- An external view of the actual physics simulation.
- The actual 640 × 360 onboard image used for that recorded step.
- A side panel containing all 32 numeric policy inputs and six executed outputs,
  with units, validity and age. Angles are displayed in degrees for readability;
  stored angles are radians.
- Evaluation values such as clearance and weather, explicitly marked as
  privileged and excluded from policy inputs.

The ten cases cover island, beach, city, gravel and rock maps, each with a
forward and reverse traversal of the same seeded route geometry. World
rotation, aircraft bearing, altitude, yaw, wave height/period/direction and wind
direction vary. Reverse cases start without the camera aimed at the boat and
contain airborne search. City reverse additionally has an initial 1.5 s camera
blackout. The rock cases start 40/60 m away at 6/8 m clearance and include
80/160 ms camera delay plus brightness, contrast and blur variation. This small
review matrix qualifies a baseline; it does not establish
success across the entire proposed collection envelope.

Both sliding lids are open at 0.46 m and the landing platform is raised at
0.40 m **before recording begins and throughout every episode**. Joint brake
constraints hold their prepared positions while transmitting contact loads into
the freely moving boat. A deviation over 8 mm fails the episode. Readiness faults
change the telemetry permission flag; they never close a lid or lower the plate.

### User verification checklist

Inspect every video and its corresponding raw rows, not just the contact sheet:

1. Map/route variation, coastal side, and airborne starting position are sensible.
2. Search/reacquisition, gimbal motion, approach, descent, contact and disarming
   are visible and appropriate.
3. The lids remain open and the platform remains raised.
4. Camera images, input/output numbers, units and timestamps match the behaviour.
5. Terminal labels distinguish deck contact, confirmed landing, water strike,
   collision, abort and timeout.
6. Review the physics checks, recording audit, limitations below and all proposed
   ranges in `planned_collection.json`.

`approval.template.json` is deliberately `pending`. After explicit user
verification, an `approval.json` decision must identify the reviewer, approve the
exact manifest hash and cover every episode. The agent must not approve its own
recordings. Source, CAD, textures, dependency versions, PX4 binary or reviewed
artifact changes invalidate approval. Collection is a separate explicit command
and never starts automatically when review export finishes.

## Reproduce the environment

Commands below run from the repository root. Linux prerequisites: Git, GCC/G++,
Make, `uv`, FFmpeg/FFprobe, DejaVu fonts, and an EGL implementation (Mesa software
rendering works in the prepared cloud machine). No GPU is required for review.
Python 3.12 is used in the prepared environment.

```bash
export UV_CACHE_DIR=/tmp/aerodock-uv-cache
uv venv --python 3.12 landing_training/.venv
uv pip install --python landing_training/.venv/bin/python -r landing_training/requirements-lock.txt
uv pip install --python landing_training/.venv/bin/python -r landing_training/requirements-training.txt
landing_training/.venv/bin/python -m landing_training.setup_px4
```

Use an existing `.venv` rather than recreating it. `requirements-lock.txt` freezes
the installed core/build dependencies; the separate training requirements pin
CPU PyTorch and Torchvision from the official PyTorch index. The native PX4 build
uses official v1.16.0 commit `6ea3539157ca358c70a515878b77077af7d4611d`.
The runner uses MAVLink without an external Gazebo or DDS server. Optional
transport modules can remain enabled through PX4's Kconfig defaults; effective
flags are reported in `build/px4_build.json`. Estimation, controllers, land
detection, arming and failsafes remain. A documented local
battery decoding patch fixes temperature units and unknown time remaining.
No real flight controller firmware is flashed.

`bash landing_training/setup.sh` repeats these preparation steps idempotently.

```bash
export PYTHONDONTWRITEBYTECODE=1
export MUJOCO_GL=egl
export XDG_CACHE_HOME=/tmp/aerodock-xdg-cache
landing_training/.venv/bin/python -m landing_training.qualify
landing_training/.venv/bin/python -m landing_training.qualify --flights
landing_training/.venv/bin/python -m landing_training.review --output landing_training/outputs/review_bundle
landing_training/.venv/bin/python -m landing_training.audit landing_training/outputs/review_bundle
```

Review export resumes complete episodes only when runtime provenance matches.
For changed runtime code or failed exports, use a new output directory; the
runner refuses to replace recorded data. Each runner owns and stops its own PX4
process. TCP 4560+instance and dedicated UDP 18000/19000+instance are local
transports. No separately running boat server, drone server or WSL is required.

## Benchmark collection on your computer

Run [collection_benchmark.py](collection_benchmark.py) from the repository root
in Linux, or inside WSL2 on Windows. Native Windows Python cannot run this Linux
PX4 build. Prepare the environment above first; the benchmark does not install
drivers, dependencies, or firmware, and does not run ML training.

```bash
landing_training/.venv/bin/python -m landing_training.collection_benchmark \
  --workers 1,2,3
```

The default quick mode runs native PX4 takeoff and short expert approach
recordings through the current collection pipeline: both actual camera views,
25 Hz decisions, JSONL rows, and compressed HDF5 RGB. Video encoding is disabled.
The 10 s scenario limit deliberately reaches the expert's 5 s timeout reserve
and aborts after approximately 5 recorded seconds. These probes measure
throughput; their aborts are not evidence of landing failures in normal-length
scenarios. All recordings remain `review` / `training_eligible=false` and cannot
release the training-data approval gate.

The script prints effective CPU capacity, memory, the actual OpenGL renderer,
frames per wall-clock second, parallel speedup, measured maximum process RAM,
and estimated time for 1,200 episodes averaging 60 recorded seconds. Each run
uses a new timestamped directory in `landing_training/outputs/`, containing
`report.json`, `results.csv`, and raw review recordings. Existing output
directories are never overwritten. Predictions use the explicitly supplied
mean duration and measured preparation overhead; they do not guarantee the
speed of unmeasured maps/weather or larger worker counts. RAM measurements do
not include GPU VRAM peaks.

Try four workers or change the sizing calculation:

```bash
landing_training/.venv/bin/python -m landing_training.collection_benchmark \
  --workers 1,2,3,4 --repeats 2 --mean-episode-seconds 90
```

For normal-length expert flights, use `--mode full`. With `--repeats 3`, each
worker count cycles calm near/middle/far starts; these take longer and reserve
the raw worst-case disk budget before starting.

```bash
landing_training/.venv/bin/python -m landing_training.collection_benchmark \
  --mode full --workers 1 --repeats 3
```

For an RTX benchmark, inspect the printed **renderer**. A name containing
`llvmpipe` or `softpipe` means CPU rendering even if `nvidia-smi` lists an RTX.
On a desktop or WSLg session, `--gl glfw` provides an alternative to default
`--gl egl`; it requires a working graphical display. The report records the
backend and actual renderer. Compare timings with the same rendering backend,
AC power, and laptop power settings.

Workers use separate physics states, PX4 ports and output files; model-cache
access is locked. `--instance-base 40` selects different ports if the default
range is in use. Ctrl+C stops this run's worker processes and their PX4 instances
and saves a cancelled report. The ordinary production collector remains serial;
this script supplies review-only measurements for implementing its scheduler.

## Shared physics and clocks

There is one `MjModel`, one `MjData`, gravity 9.80665 m/s² and a 1 ms physics
timestep. Water, buoyancy, drag, propellers, drainage, drone aerodynamic forces,
rotor reaction, gimbal and rigid contacts contribute to the same state. Forces
are cleared once per step and then added. Neither vehicle follows a replayed
pose trajectory. Named free-joint addresses and boat subtree mass avoid counting
the aircraft as boat mass.

Boat dry mass is 218.965001 kg; drone mass is 2.066218 kg. The qualification
checks transferred support load by comparing settled displaced water volume
with drone mass / water density, within 1%. It also compares 1 ms and 0.5 ms
unloaded integration over 0.25 s. These are consistency checks rather than a
complete contact convergence study.

PX4 receives HIL IMU at 250 Hz, barometer/magnetometer at 50 Hz and GNSS at
approximately 20.8 Hz. Its own estimator reports attitude and velocity. Physics
advances in timestamp lockstep with PX4; boat and drone cannot drift onto
different simulation clocks. Expert/policy decisions and camera recordings use
25 Hz (40 physics steps). Each row precedes its action execution and a terminal
row records the result without issuing another command.

The 600 × 600 mm contact plate is attached to the actual raised platform. Drone
support uses the four EVA foot CAD parts. Separate lid/mast/support collision
geometries preserve the open landing cavity. The deck is split around its CAD bay
opening, with separate coaming rails, so touching another part of the deck is
classified as a collision rather than falling through the deck into the sea.
The outer hull collider is used
for shore contact, not as a solid box filling the drone landing bay. Render mesh
decimation affects appearance only; contact geometry and inertias remain the
original models. Boat visual meshes are preserved exactly; only drone render
meshes use decimation. Analytical waves are also rendered in an observer-centred
buffer, preventing a target-centred water patch from revealing boat location.

Ocean detail uses the original boat simulator's seamless 256 × 256 procedural
RGB tile. The appended wave mesh binds that texture explicitly; assigning a
material alone leaves a manually appended MuJoCo scene geometry untextured.
Mesh UVs tile every 12 world metres and remain anchored to world coordinates.
The cosmetic ripple texture refreshes at 5 Hz, with pixels generated once and
uploaded once per camera context per refresh. Analytical wave geometry remains
unchanged at 10,201 vertices / 20,000 triangles, with reflections and shadows
disabled. Small texture ripples do not add physical wave forces.

`outputs/ocean_texture_preview/comparison.mp4` compares the previous and current
renderers using identical fixed vehicle poses. It is a render diagnostic, not
an expert flight or a training recording. `report.json` records paired capture
timings, artifact hashes, and renderer/controller provenance. To reproduce with
a saved previous renderer:

```bash
MUJOCO_GL=egl landing_training/.venv/bin/python -m landing_training.ocean_preview \
  --baseline landing_training/build/ocean_baseline_rendering.py
```

The cloud comparison measured 100 paired captures per case, including both
cameras and texture uploads. Median capture overhead was 0.7% for calm water,
2.9% for high waves, and 0.7% for the wind/high-wave diagnostic (about 245–259 ms
per capture pair). These are local render timings, not a real-time guarantee or
a benchmark of the onboard computer. All 29 qualification checks passed.

Historical review videos remain unchanged. The new renderer must be included in
the current review bundle before the user approves actual data collection.

## Policy contract and expert

The exact field order and frames are in [schema.json](schema.json).

| Input | Source |
| --- | --- |
| RGB 640 × 360 | Onboard camera; stored without video overlay |
| Velocity, attitude, angular rates and ages | PX4 estimator telemetry |
| Gimbal pan/tilt | Explicit synthetic encoder reference pending real interface |
| Coarse boat position/velocity, age, validity, readiness | Synthetic 1 Hz radio beacon reference |
| Previous executed action, decision interval, image age/validity | Causal onboard bookkeeping |

Velocity and beacon vectors use estimated heading forward/right/down. World
truth uses ENU; PX4 attitude uses NED/FRD. The radio beacon has declared 0.25 m
position noise and 0.025 m/s velocity noise. It is a testable protocol reference,
not a measured SX1262 performance claim.

Six outputs are forward/right/down velocity, NED yaw rate, and gimbal pan/tilt
rates. Limits are 2 m/s horizontal vector magnitude, 1 m/s upward, 0.7 m/s
downward, 0.5 rad/s yaw, 50°/s pan and 40°/s tilt. PX4 closes the motor and
attitude loops. The student never directly emits rotor commands or an unsafe
unconditional disarm request.

The expert physically takes off and moves to the requested airborne start before
recording. Unsafe coastal bearings are rotated in 15° increments; requested and
achieved bearings are recorded rather than silently treating them as identical.
The straight preparation path is checked over clear water; its time budget scales
with travel distance and height instead of failing longer starts after 45 s.
Starting height and distant search use vertical height relative to the deck
centre. Within 2 m of the target, descent uses distance along the deck normal.
Both heights are recorded; a tilted plane is not extrapolated to measure distant
flight altitude.
Blind search uses the coarse beacon and camera control. Visible approach and
deck matching use privileged current simulation state for labels; future route
waypoints and future wave state are excluded. The expert slows the final descent,
recovers if alignment is lost, and requests ordinary disarming only after PX4
observes an airborne-to-landed transition. The square marker permits four 90°
heading branches; no unique heading is invented. The expert chooses only the
front/back pair, which keeps the camera away from the side leg corridor. Descent
also requires heading alignment. Marker visibility includes the visible aircraft
meshes; only the optical body's own interior/back faces are excluded from ray
tests, matching the clear rendered optical view. Legs are never excluded.

During contact, a downward velocity setpoint lets the native PX4 land detector
reduce thrust and detect ground contact. This setpoint is not the physical impact
velocity; the platform contact stops the aircraft. Ground truth classifies
outcomes but cannot authorize PX4 disarming.

### Outcome definitions

- `stable_contact`: at least three supporting EVA feet, centre of mass inside
  their support polygon, all feet at least 20 mm inside the plate edge, relative
  horizontal velocity below 0.1 m/s, normal velocity below 0.05 m/s, relative tilt
  below 5° and relative angular speed below 5°/s for one continuous second.
- `landed`: the same support remains stable while PX4 is disarmed for two
  continuous seconds. Brief contact alone is not successful landing.
- `water_strike`: a sampled aircraft collision-geometry/rotor edge point passes
  more than 3 mm below the analytical water surface. This is a geometry sampling
  approximation, not complete water/triangle intersection or post-crash flotation.
- `collision_failure`: forbidden boat contact or a rotor strike.
- `contact_only`, `abort`, `timeout`: retained separately from success/failure
  mechanisms; terminal actions are masked out of imitation loss.

## Proposed collection, after approval

The deterministic plan contains 1,200 episodes: 960 training, 120 validation and
120 test. It uses 600 distinct world/path seed pairs, with both directions kept
in the same split. The first 60 episodes are a pilot covering every map, both
directions, all distance bands and calm/combined weather. Review recordings are
excluded entirely.

| Variable | Planned range/coverage |
| --- | --- |
| Maps | Island, beach, city, gravel, rock; seeded geometry and rotation |
| Airborne horizontal distance | 0–5, 5–20, 20–60 m; area-weighted within each band |
| Foot clearance | 2–8 m |
| Boat target speed | 0.1–1 m/s |
| Wind | Calm, steady, breeze, gusty; mean 0–4 m/s; all directions |
| Waves | Height parameter 0–0.15 m; period 2–5 s; all directions and seeded phase |
| Appearance | Brightness/contrast 0.85–1.15; blur 0–0.5 px |
| Camera timing | 0–200 ms synthetic delay; initial view visible or outside boat |
| Fault coverage | 70% nominal, 10% camera blackout, 10% radio dropout, 10% readiness delay |

All splits include nominal and fault cases. The wave parameter is the original
simulator's bounded multi-component height parameter, not significant wave
height. Wind bounds refer to mean wind; gusts can exceed the mean. Wavelengths
follow the shared gravity and Airy dispersion relation, rather than varying
height, wavelength and period inconsistently. Sea current is supported explicitly
within 0.3 m/s but stays zero in the initial collection plan.

An episode starts airborne, ends at an outcome or 180 s, and retains failures and
their preceding valid expert actions. RGB, raw and bounded teacher actions,
executed actions, intervention masks, timestamps, telemetry, seeded scenario and
privileged labels are stored. DAgger collection additionally retains the learner
proposal and checkpoint hash while labelling the learner's visited states.

Storage is significant: raw RGB is 17.28 MB/s, at most 3.11 GB per 180 s episode
or 3.73 TB for all 1,200 maximum-length episodes, before compression. HDF5 LZF
compression reduces actual use, but collection checks the worst-case raw budget
before flying. The current cloud disk is suitable for review and incremental
small batches, not the full raw maximum. Determine pilot durations, success
rates and compressed size before approving/scaling the main collection.

Only after approval and with sufficient storage:

```bash
landing_training/.venv/bin/python -m landing_training.collect --review landing_training/outputs/review_bundle --output landing_training/datasets/pilot --max-episodes 1
landing_training/.venv/bin/python -m landing_training.train --review landing_training/outputs/review_bundle --manifest landing_training/datasets/pilot/manifest.json --output landing_training/checkpoints/baseline --epochs 10
```

The trainer also requires held-out validation episodes. A one-episode pilot is
for collection inspection and cannot by itself start training. The full plan
prioritizes validation/test worlds after the initial 60 pilot flights and before
further training collection. Use staged limits matched to available storage.

## Architecture and training steps

MobileNetV3 Small extracts spatial features; spatial softmax retains location
through per-channel x/y expectations and pooled activation. A 32-value telemetry
MLP joins a 256-value vision embedding, followed by a causal 128-unit GRU and a
six-action head. Auxiliary heads predict visibility, marker centre, relative
position/velocity and stable-contact confidence. Contact confidence is advisory;
native PX4 and the contact supervisor handle confirmation and disarming.

Default training freezes an ImageNet-pretrained encoder initially. Optional
fine-tuning retains fixed BatchNorm statistics so future sequence frames cannot
change earlier frame features. Telemetry normalization uses training episodes
only. Checkpoints record the reviewed bundle and frozen dataset manifest hashes.

One epoch visits every recorded step of every training episode exactly once,
shuffling episode order while retaining within-episode chronology. Episodes are
processed in eight lanes of 64 consecutive decisions (2.56 s). GRU state carries
across chunks within a lane and resets at an episode boundary; gradients are
truncated between chunks. One optimizer step accumulates the current eight lane
chunks, with shorter final chunks and fewer lanes when the epoch ends. Adam uses
1e-4, gradient norm clipping 1, normalized Huber action loss, and auxiliary
visibility/contact/regression losses. Invalid or terminal teacher actions are
excluded from action imitation. Default run length is ten epochs; each epoch
evaluates held-out validation loss and saves latest/best checkpoints. Test worlds
never choose weights. Offline loss alone does not qualify autonomous landing;
run closed-loop held-out evaluation and inspect failures before deployment.

```bash
landing_training/.venv/bin/python -m landing_training.evaluate --review landing_training/outputs/review_bundle --manifest landing_training/datasets/pilot/manifest.json --checkpoint landing_training/checkpoints/baseline/best.pt --split validation --output landing_training/outputs/validation --max-episodes 10 --videos
```

Closed-loop evaluation replays the scenario configuration of held-out episodes,
while the learner controls the simulated aircraft. It reports deck landings,
water strikes, collisions, aborts, timeouts and contact impact velocity. These
evaluation records retain their validation/test split and cannot enter the
training split. Inspect failures and search behaviour as well as success rate.

## Known physical and hardware limits

- Review-only stress scenarios support the original boat model's maximum 0.5 m
  wave parameter and stronger authored winds. This does not expand the planned
  production collection envelope. Speed screening retains unsuccessful attempts
  and uses measured boat speed. The 2 m/s horizontal action cap and native PX4
  1.5 m/s land-detector threshold remain unchanged. A finite trial set establishes
  a tested operating setting, not a physical maximum or real-world reliability.
- Camera projection is based on the existing simulated camera (36.1° vertical
  FOV). ALLXF D80 Pro live capture API, actual latency, zoom calibration and
  gimbal feedback are not verified. The current image/gimbal faults are explicit
  synthetic variations, not measured hardware distributions.
- PX4 GNSS HIL uses simulator truth rather than calibrated real GNSS errors.
  The coarse radio beacon adds declared synthetic noise. Boat Waveshare SX1262
  UART HAT / drone SX1262 SPI interoperability, payload and timing still require
  hardware validation.
- Platform/marker clipping near touchdown is retained in the images: the
  complete 60 cm platform leaves a nadir view below about 0.86 m foot clearance,
  and the complete 26 cm marker below about 0.34 m. A model must learn partial
  views rather than expect a whole marker at contact.
- Boat hydrodynamics remain the original moderate-wave approximation. Added
  mass, slamming, wake/rotor interaction and rotor ground effect are not modelled.
  Boat air-drag silhouette coefficients are authored estimates. Actual boat
  motion, camera and vehicle coefficients need calibration.
- Coastal terrain is rendered procedurally; the original shore collision pool is
  retained. Decorative trees/buildings do not all have physical colliders, so
  the initial task is restricted to clear over-water approaches.
- The initial boat target-speed limit is 1 m/s. Existing faster boat routes are
  unsuitable for the current 2 m/s drone action envelope and native absolute
  land-detection thresholds. No claim is made for faster decks or heavier seas.
- PyTorch runtime is implemented; Khadas Edge2 NPU conversion, target latency,
  camera driver and real flight integration are pending hardware validation.
  There is no trained or deployable model yet.

## Source map

`scene.py` composes CAD and contacts; `environment.py` combines forces/clocks;
`px4.py` owns native SITL; `expert.py` supplies supervision; `recording.py` and
`rendering.py` save synchronized data/video; `review.py`/`audit.py` export and
verify review; `gate.py` enforces verification; `collect.py` generates approved
datasets; `policy.py`/`train.py` implement the learning workflow; `qualify.py`
checks numerical consistency and intended failure conditions.

`benchmark.py` runs review-only speed/weather trials; `limits_report.py` assembles
their evidence; `stress_review.py` exports/audits the five supplementary videos.
For repeated experiments use fresh output directories. These commands never
approve collection:

```bash
landing_training/.venv/bin/python -m landing_training.benchmark --speed 1.5 --count 30 --seed 4100 --wide-starts --instance 0 --output landing_training/outputs/repeated_speed_trials
landing_training/.venv/bin/python -m landing_training.stress_review --report landing_training/build/speed_report.json --output landing_training/outputs/stress_review
```
