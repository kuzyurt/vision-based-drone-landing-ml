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
transports. Linux needs no separately running boat server, drone server or WSL.
Windows rendering uses WSL for PX4 as described below.

## Benchmark collection on your computer

Run [collection_benchmark.py](collection_benchmark.py) from the repository root.
Linux/WSL uses native PX4; Windows Python renders and records natively while an
owned PX4 process runs in WSL. This command does not collect production training
data, approve a review, or train a model.

```bash
landing_training/.venv/bin/python -m landing_training.collection_benchmark \
  --workers 1,2,3 --repeats 3
```

The default quick mode takes off using PX4, then measures a short expert approach
through the same worker and recording code as production collection. It renders
**only the 640 × 360 drone camera**, records at 25 decisions per simulated second,
and writes lossless LZF HDF5 RGB and matching JSONL/HDF5 metadata. It does not
render overview frames, diagnostic screenshots, or video. The 10 s scenario limit
reaches the expert's 5 s timeout reserve and ends after about 5 recorded seconds.
These deliberate aborts measure throughput, not normal-flight landing reliability.
**Quick mode no longer projects full-dataset collection time.** The legacy
`--mean-episode-seconds` option is accepted for command compatibility but does not
control projections.

Reports include the actual graphics renderer, effective CPU capacity, worker
memory, recording FPS, repeat-to-repeat variation, simulated seconds per wall
second, and complete episode pipeline throughput. Per-worker timings separate
initialization, physical preparation, camera capture, observations/decisions,
recording writes, physics, PX4 synchronization, sensor transmission, and shutdown.
Some timings are explicitly nested: expert time is part of observation/decision
time, and preparation physics/synchronization are parts of preparation time.
Camera capture includes scene construction, wave updates, GPU upload, rendering,
and readback. Worker-second totals for parallel runs must not be added to obtain
elapsed batch time. Recorded spans exclude takeoff and renderer creation;
complete batch costs include worker startup, takeoff, final flush, shutdown,
and the artifact hashing also required by collection. Benchmark-only raw audits
are reported separately. Shared model precompilation is reported separately too.

Each run creates a new output directory containing `report.json`, `results.csv`,
and review-only recordings. The raw audit checks 25 Hz timing, frame/row order,
finite inputs, airborne starts, open/raised dock joints, terminal supervision
masking, and landed/disarmed PX4 states when a flight lands. Existing outputs
are never overwritten. Memory figures do not include GPU VRAM; Windows worker
CPU/RAM measurements exclude the additional WSL PX4 processes.

For complete flights and empirical collection time estimates:

```bash
landing_training/.venv/bin/python -m landing_training.collection_benchmark \
  --mode full --workers 1,2 --repeats 20
```

Full mode cycles 20 seeded cases spanning five maps, four weather groups, three
distance bands, and both route directions. The first five cases visit all five
map families. Fewer repeats explicitly measure only that prefix. Projection uses
measured complete episode pipeline cost, including failures, rather than an
assumed flight duration. It remains a sample estimate, not a measurement of the
entire 1,200-episode distribution or a landing reliability qualification.
The report recommends the measured worker count with highest complete episode
pipeline throughput. Larger unmeasured counts are not extrapolated.

Inspect the printed **renderer**. `llvmpipe`/`softpipe` means CPU rendering even
when `nvidia-smi` lists an RTX. Linux/WSL defaults to `--gl egl`; `--gl glfw` needs
a working desktop display. Native Windows defaults to `glfw`. Compare runs on
the same backend, power settings, output filesystem, and scenario matrix.
Workers own independent physics states, PX4 ports, and files. `--instance-base 40`
selects another port range. Ctrl+C or SIGTERM requests worker cleanup and saves
a cancelled benchmark report.

### Automatic resource scan and worker tuning

Install the updated locked dependencies first (the tuner uses `psutil==7.2.2`):

```bash
UV_CACHE_DIR=/tmp/aerodock-uv-cache uv pip install --python landing_training/.venv/bin/python -r landing_training/requirements-lock.txt
landing_training/.venv/bin/python -m landing_training.autotune
```

The tuner scans CPU affinity and quota, physical/logical CPU topology, available
RAM and container limits, output disk capacity, and visible NVIDIA GPU/VRAM data.
It probes OpenGL backends in fresh processes before importing MuJoCo in workers,
prefers hardware rendering (NVIDIA first), and records the actual renderer.
Linux tries EGL, desktop GLFW when a display is available, then OSMesa; Windows
uses GLFW and the existing WSL PX4 launcher. Backend probes verify rendering
availability; they do not benchmark every backend's performance.

It starts with one worker, grows concurrency geometrically, and tests intermediate
counts around the measured throughput peak. The default ceiling is the detected
CPU allocation; RAM/VRAM measurements can lower it. `--max-workers` overrides the
CPU-based ceiling, while resource guards still apply. The strongest candidates
are compared on full flights through the same collector. Default confirmation
uses three cases from the full map/weather matrix; `--confirm-scenarios 20`
uses all 20. `--confirm-repeats 2` repeats that matrix for stronger confirmation.
Counts within 3% of the best throughput prefer fewer workers; change this with
`--tie-margin`. The objective is complete episode pipeline throughput, including
worker startup, physical takeoff preparation, recording, shutdown and artifact
hashing. Short-probe aborts are intentionally not production time estimates.

```bash
# GPU rental: refuse accidental CPU software rendering, limit tuning time/cost.
landing_training/.venv/bin/python -m landing_training.autotune \
  --require-gpu --max-minutes 20 --hourly-price 0.128 --budget 0.10

# A shorter validation: two counts, one full-flight case for each finalist.
landing_training/.venv/bin/python -m landing_training.autotune \
  --max-workers 2 --confirm-scenarios 1 --max-minutes 15

# Inspect the environment without starting PX4 or running flights.
landing_training/.venv/bin/python -m landing_training.autotune --scan-only

# Compare only 32 and 64 workers, without smaller counts or short probes.
landing_training/.venv/bin/python -m landing_training.autotune \
  --worker-counts 32,64 --confirm-scenarios 1 --max-minutes 40 --require-gpu
```

`--worker-counts` skips adaptive search and runs complete flights only for the
listed counts. It permits intentional CPU oversubscription, while live RAM,
VRAM, disk and time guards still apply. Use a longer budget or more confirmation
cases when needed. A stopped trial is reported explicitly; it is never replaced
with an unrequested lower count. If `--max-workers` is also supplied it must
cover every requested count.

The price and budget must use the same currency (`--currency USD` by default).
Cost estimates cover the stated compute rate only; storage, bandwidth, deposits,
payment fees and time before launching the script are not included. The time
budget requests cooperative cancellation, so startup/cleanup can extend beyond
the deadline. A RAM or identified-device VRAM headroom violation also requests
cancellation. Every result says whether full confirmation finished; a budget-
limited search recommends only the best configuration actually measured and
never claims an untested global optimum. All runs remain review-only, and no
approval or production dataset is created.

Reports are saved under a new `landing_training/outputs/autotune_*` directory:

- `summary.md`: recommendation, actual renderer, CPU/RAM/VRAM figures and a
  collection command requiring an approved review bundle.
- `recommended_configuration.json`: machine-readable worker/backend settings.
- `report.json` and `results.csv`: all candidates, scenario coverage, throughput,
  stage timings, CPU usage, resource limits, unsuccessful trials and stop reasons.
- Per-batch `resources.json`: sampled CPU/RAM and NVIDIA utilization/VRAM details.

CPU use is reported as CPU-seconds per wall-second (logical core equivalents),
plus sampled peaks; it is not a claim of exclusive physical cores. RAM is summed
process-tree RSS and can count shared pages more than once. NVIDIA counters are
**device-wide**, including unrelated workloads; unsupported counters are null.
An identical-name multi-GPU system may not permit identifying the selected
physical GPU from OpenGL's renderer string, so selected-device VRAM summaries
remain unknown in that case. Workers use the selected OpenGL device; multi-GPU
load balancing is not implemented. Windows accounting excludes Linux PX4 inside
WSL. Samples can miss very brief usage peaks.

By default, audited disposable RGB/JSONL files from this tuner are removed after
each batch to avoid accumulating large review datasets; scenarios, summaries,
audits, hashes and resource reports remain. `--keep-recordings` retains the raw
review files. Existing directories and production datasets are never overwritten
or cleaned. Free disk is checked against each batch's worst-case raw RGB size.
The script does not reduce camera resolution, physics accuracy, policy frequency
or scenario coverage to improve its throughput score.

### Native Windows rendering with WSL PX4

This host path is implemented but has not been exercised on a Windows machine in
the cloud validation. It follows the existing drone simulator's Windows/WSL
split. Fully native Windows PX4 is not supplied.

Build the pinned `px4_sitl_landing` target using `landing_training/setup.sh` in
WSL Ubuntu 22.04 first. In Windows PowerShell, from this repository:

```powershell
py -3.12 -m venv landing_training/.venv-windows
landing_training/.venv-windows/Scripts/python -m pip install -r landing_training/requirements-lock.txt
landing_training/.venv-windows/Scripts/python -m pip install -r landing_training/requirements-training.txt
$env:PX4_WSL_DISTRO = "Ubuntu-22.04"
# If firmware was built in a separate Linux checkout, use its Linux vendor path:
$env:LANDING_PX4_WSL_ROOT = "/home/YOUR_USER/vision-based-drone-landing-ml/landing_training/.vendor/PX4-Autopilot"
landing_training/.venv-windows/Scripts/python -m landing_training.collection_benchmark --gl glfw --workers 1,2 --repeats 3
```

Omit `LANDING_PX4_WSL_ROOT` if the target was built in this checkout through WSL.
The launcher resolves paths using `wslpath`, discovers the Windows gateway from
WSL's default route, creates instance-specific startup files, and records the
WSL firmware hash in provenance. Windows must permit WSL connections to the
Python process's TCP simulator and UDP telemetry ports. Each launcher stops only
its recorded process after verifying its executable and runtime-directory
arguments; it never issues a blanket PX4 kill.

### Approved parallel dataset collection

Production collection still requires explicit verification of a current review
bundle. These source changes invalidate earlier review approvals. Generate and
verify the current ten-video bundle before starting production collection.

```bash
MUJOCO_GL=egl landing_training/.venv/bin/python -m landing_training.collect \
  --review landing_training/outputs/CURRENT_APPROVED_REVIEW \
  --output landing_training/datasets/expert --max-episodes 60 --workers 2
```

Use the best measured worker count for your machine. Collection checks available
RAM and disk headroom, uses the same spawned-worker scheduler as the benchmark,
and retains the same train/validation/test scenario plan. Only the coordinator
writes the manifest, under a collection-directory lock. Completed recordings are
hashed before atomic manifest updates. A completed episode omitted from the
manifest during interruption can be recovered only if its scenario, source,
role, checkpoint, and record counts match. Partial or incompatible episodes are
retained and refused, never overwritten. Workers load independent policy state
when `--checkpoint` is used for DAgger collection.

### Google Cloud: legacy collection-only launcher

For the complete collect→train→evaluate workflow, use
`start_cloud_pipeline.sh` in the final section below. The launcher in this
section collects only and reserves no feature-cache/evaluation budget.

The prepared L4 VM measured 64 workers as the best tested setting. This launcher
uses that count, requests all remaining episodes in the 1,200-episode plan, and
requires GPU rendering. Run from the repository root after updating the
`codex/landing-training` branch:

```bash
tmux new-session -d -s landing-data 'bash landing_training/start_cloud_collection.sh'
tmux attach-session -t landing-data
```

Detach with **Ctrl+B, then D**. Collection continues when SSH disconnects.
Reattach using the same command. A finished session closes, but its files remain.
If `landing-data` already exists, reattach instead of starting a second job.
The launcher also rejects concurrent launches using its own lock.

The script finds an already approved **current** review bundle automatically;
an explicit bundle may be supplied as its first argument. It does not approve
recordings or bypass qualification. If none exists, it runs the physics/software
qualification and exports ten current review videos to the launch directory's
`current_review/` folder, then exits with `user_review_required` before dataset
creation. Inspect that folder's `index.html`, recordings, qualification and plan;
after explicit verification, create the matching `approval.json` as described
above and rerun the launcher. Source/dependency changes invalidate previous
approvals. Historical review files are ignored by Git and do not accompany a clone.

Data lives in `landing_training/datasets/expert/` by default. Set
`AERODOCK_DATASET_DIR` to change the location. The launcher enforces
`--max-dataset-gb 1500 --min-free-gb 32`: **decimal GB**, including previously
collected and partial data in the dataset limit. It reserves uncompressed RGB,
metadata and log space for each in-flight episode before admitting another,
rather than reserving the worst case for all 1,200 upfront. Near the limit, it
reduces active concurrency and lets admitted flights finish. An independent
0.5-second free-space check and 5-second dataset-size check cancel active work
if space drops unexpectedly. A shutdown buffer is added to the 32 GB floor, so
collection intentionally stops before the limit. These are cooperative checks,
not a filesystem quota; unrelated processes or a machine failure can defeat them.

Live process-tree RAM and available memory are guarded, along with selected
NVIDIA device VRAM. Finished episodes are validated, hashed and committed using
an atomic, fsynced manifest. With `--quarantine-partial`, incomplete previous
attempts move to `partial_attempts/` before retrying; their space still counts.
They are retained, not used for training. Incompatible complete files are refused.
Restart the same launcher to resume; completed indexed episodes are skipped.

Each invocation saves separate reports and the full console log under
`landing_training/outputs/collection_launch_.../`. The path of the latest launch
is retained in `outputs/latest_collection_launch.txt`:

```bash
AERODOCK_LAST_RUN="$(cat landing_training/outputs/latest_collection_launch.txt)"
cat "$AERODOCK_LAST_RUN/launch_status.json"
cat "$AERODOCK_LAST_RUN/results/latest.json"
tail -n 30 "$AERODOCK_LAST_RUN/console.log"
```

`results/latest.json` is updated after every completed episode and every 30
seconds; a timestamped JSON report is retained too. Reports include status/stop
reason, start/end/update times, elapsed hours, episode/frame counts, train/val/test
counts, landing/failure outcomes, total bytes/GB/GiB, indexed HDF5 bytes, disk
headroom, actual renderer, maximum active workers, sampled CPU/RAM and device-wide
GPU/VRAM measurements. `launch_status.json` also captures preflight failures.
On normal completion, storage stop, Ctrl+C, SIGTERM or a handled error a final
report is saved. Forced termination/power loss can prevent finalization; the last
atomic progress report and previously completed episodes remain.

The cloud launcher records each stage (`gpu_probe`, `approval_check`,
`qualification`, `review_export`, `collection`), its duration and actual child
exit code in `launch_status.json`. Stage boundaries also appear in `console.log`.
SIGINT, SIGTERM and SIGHUP are recorded explicitly with exit codes 130, 143 and
129 respectively. The launcher forwards a cleanup request to its owned child,
drains its output and waits for cleanup before writing its final status. It never
reports an interrupted launch as a successful exit merely because the previous
stage passed. Review export also handles SIGTERM so its own PX4 and recording
resources can close cleanly.

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
Configured starting height uses vertical height relative to the deck centre.
During search, the teacher uses the delivered coarse beacon height instead of
the scenario’s target height; when that beacon is stale it scans while climbing
at 0.3 m/s. Within 2 m of the target, descent uses distance along the deck normal.
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
in the same split. The first 240 episodes are the expert pilot: 120 training and
120 validation episodes, each covering every map × distance band × weather group
× route direction. Test worlds follow and remain excluded from pilot/model
selection. Review recordings are excluded entirely.

| Variable | Planned range/coverage |
| --- | --- |
| Maps | Island, beach, city, gravel, rock; seeded geometry and rotation |
| Airborne horizontal distance | 0–5, 5–20, 20–60 m; area-weighted within each band |
| Configured height above deck centre | 2–8 m; actual foot clearance is recorded separately |
| Boat target speed | 0.1–1 m/s |
| Boat route start | Uniform fraction of the usable interior; paired directions share the physical start and have opposite headings |
| Wind | Calm, steady, breeze, gusty; mean 0–4 m/s; all directions |
| Waves | Height parameter 0–0.15 m; period 2–5 s; all directions and seeded phase |
| Appearance | Brightness/contrast 0.85–1.15; blur 0–0.5 px |
| Camera timing | 0–200 ms synthetic delay; initial camera aimed at/away from boat, 50/50 in each split |
| Fault coverage | 70% nominal, 10% camera blackout, 10% radio dropout, 10% readiness delay |

All splits include nominal and fault cases. The wave parameter is the original
simulator's bounded multi-component height parameter, not significant wave
height. Wind bounds refer to mean wind; gusts can exceed the mean. Wavelengths
follow the shared gravity and Airy dispersion relation, rather than varying
height, wavelength and period inconsistently. Sea current is supported explicitly
within 0.3 m/s but stays zero in the initial collection plan.

An episode starts airborne, ends at an outcome or 180 s, and retains failures.
The trainer masks action imitation for expert flights ending in water strikes or
forbidden collisions; their visibility/contact labels remain available. DAgger
teacher corrections on failed student flights remain supervised. RGB, raw and bounded teacher actions,
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
includes validation in the initial 240 pilot flights and prioritizes test
worlds before further training collection. Use staged limits matched to available storage.

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
excluded from action imitation. Default run budget is ten epochs, with early
stopping after three validation epochs without improvement. Validation loss uses
dataset-wide denominators for each component, so one-frame terminal chunks do
not receive disproportionate weight. Reports include the previous-action
persistence baseline and visibility/contact coverage. Each epoch saves atomic
latest/best checkpoints, optimizer state and RNG state. Test worlds
never choose weights. Offline loss alone does not qualify autonomous landing;
run closed-loop held-out evaluation and inspect failures before deployment.

The default frozen encoder is evaluated once per recording. Its 1,728 spatial
features are cached in FP32 before the trainable vision projection; no image
resolution or feature precision is reduced. Epochs then train the projection,
telemetry network, GRU and heads without repeatedly decoding RGB or running the
same CNN. Eight equal-length lanes share one recurrent batch; shorter final
chunks retain their original loss weight and episode state. Fine-tuning uses the
RGB path and cannot reuse fixed features.

Feature preparation uses bounded spawned readers, capped by CPU availability,
RAM and shared memory. Each cache file is checksummed, keyed by source contents,
encoder/preprocessing and supervision mask, and published atomically. Original
recordings remain intact. The production cache reserves 32 GB free space and
costs approximately 7,108 bytes per frame plus file metadata: about 11.5 GB for
1,080 training/validation episodes averaging 60 s. Test episodes are not cached.
There is no image augmentation during cached epochs; appearance variation is
already recorded in the scenarios. New per-epoch visual augmentation requires
the RGB path or a separately qualified cache scheme.

`--loader-workers auto` selects bounded raw readers; cached epochs always read
features in-process. Use the benchmark's measured reader setting for raw/cache
preparation if appropriate for the pilot.
`--feature-cache off` retains RGB training. `--resume` restores `latest.pt`,
including optimizer and RNG state, against exactly the same approved dataset.
Resume starts after the last complete epoch and replays any interrupted epoch.
An existing training output requires resume or a new output directory.
`--patience 0` disables early stopping. `--epochs` is the total epoch budget,
including resumed epochs. [TRAINING_DESIGN.md](TRAINING_DESIGN.md) records the
model rationale, verified checks and remaining production-readiness gaps.

### Training time benchmark before production collection

`landing_training.benchmarks.compare_training` reads the ten review HDF5 files
and compares the previous serial RGB trainer, parallel RGB with batched recurrent
updates, and the new cached-feature production loop. It scans 0/4/8/16 raw reader
workers, capped by available resources, then reports the best measured cache-build
configuration. Cache preparation is measured separately and included once in
the total-time projection. It also fits a small fixed fragment for 100 updates
to verify that action imitation loss decreases. This diagnostic establishes
optimizer/label wiring, not held-out accuracy or landing reliability.

All temporary weights are discarded; no policy checkpoint or approval is
created. Source recordings remain unchanged and retain review-only eligibility.
No simulator or additional camera is rendered. The previous benchmark remains
available as `landing_training.benchmarks.training` for reference comparisons.

Defaults match the trainer's frozen ImageNet encoder, 640×360 images, FP32,
eight recurrent lanes, 64-frame chunks, Adam and gradient clipping.
Telemetry normalization is measured on the review workload. Two optimizer
updates and one validation chunk warm up the device and are excluded from
throughput. Twenty measured optimizer updates and twenty validation chunks
follow, with at least 15 measured seconds per optimized phase. CUDA timing
synchronizes the device. CPU threads default to four; use
the same thread setting for the eventual production trainer when comparing
speeds. `--sequence-steps`, `--lanes` and `--no-pretrained` are useful for smoke
tests but change the workload; reports flag deviations from production defaults.

On a configured Linux cloud VM, launch in detached tmux:

```bash
cd "$HOME/vision-based-drone-landing-ml"
tmux new-session -d -s landing-train-bench -c "$PWD" \
  'bash landing_training/benchmarks/start_training_benchmark.sh --device cuda'
```

The wrapper prevents duplicate benchmarks with `flock`, preserves the Python
exit code and saves `console.log`, `exit_code.txt`, `report.json` and `summary.md`
under `outputs/training_benchmark_...`. It automatically uses
`outputs/latest_collection_launch.txt/current_review`; pass `--review PATH` if
your review is elsewhere. The wrapper creates a pointer to the benchmark folder:

```bash
cd "$HOME/vision-based-drone-landing-ml"
AERODOCK_TRAIN_BENCH="$(cat landing_training/outputs/latest_training_benchmark.txt)"
cat "$AERODOCK_TRAIN_BENCH/summary.md"
tail -n 20 "$AERODOCK_TRAIN_BENCH/console.log"
```

CUDA is required by default, with no silent CPU fallback. Keep CUDA PyTorch on
the VM; installing `requirements-training.txt` would replace it with CPU wheels.
The first pretrained run downloads the standard torchvision MobileNet weights
into `outputs/weights/`. The twenty-minute limit is cooperative between chunks;
downloads or an individual CUDA operation can overrun it. Normal SIGINT/SIGTERM
save partial results; sudden power loss or SIGKILL can only retain the last
atomic progress report. Resource guards reserve RAM and GPU headroom.

Timed phases stop scheduling new reads and drain only the bounded prefetch
window before reader shutdown. This also applies when training exits early.
Measurements are saved before cleanup; each phase records
`reader_shutdown_completed`, so a cleanup failure retains its measurements while
the overall run stays failed. Worker fault handlers write abort diagnostics to
the console log. To repeat only the reader configuration already measured best,
pass `--reader-workers 4` (use your own measured winner).

The report includes train and validation frames/s, cache preparation speed for
each reader setting, loader wait and transfer/model/optimizer time, learning
sanity results, reference stage timings and parameter counts; CPU use and peak
RAM; CUDA device and PyTorch allocated/reserved VRAM; device-wide NVIDIA
utilization and VRAM. GPU telemetry can include other jobs. Run without concurrent
collection or training for an interpretable result.

Cache-build reader probes include startup and complete-file checksums in their
end-to-end speed, and also report steady throughput after warmup. Selection uses
steady throughput when available. A small review workload cannot prove that the
same reader count wins on cold production storage. Cache-build timing includes
encoding and cache writes, but source integrity hashing is reported separately.
The benchmark reserves 2 GB disk headroom; production preparation reserves 32 GB.

Projections use 960 training and 120 validation episodes per epoch; the 120 test
episodes are excluded. It shows the observed review mean and hypothetical
30/60/90/180-second production means at 25 records/s, including the terminal
record. Ten epochs are a budget, not a convergence claim. Full dataset hashing,
normalization, checkpoint writes and deployment evaluation add time. The review
workload fits in RAM more easily than the eventual dataset: disk-cache effects
can make estimates optimistic. Collection FPS is not training FPS.

The benchmark does not launch the production workflow. The separate
`start_cloud_pipeline.sh` launcher now enforces review, expert-pilot audits,
complete collection, compatible checkpoints and held-out policy evaluation.
Training-source changes invalidate an older full-source approval fingerprint.
If the simulation runtime fingerprint is unchanged, review export can reuse its
videos and regenerate current plan/audit metadata; the refreshed bundle still
requires explicit user verification before production. Interrupted review
attempts are retained under `partial_attempts` and retried without overwriting.

```bash
landing_training/.venv/bin/python -m landing_training.evaluate --review landing_training/outputs/review_bundle --manifest landing_training/datasets/pilot/manifest.json --checkpoint landing_training/checkpoints/baseline/best.pt --split validation --output landing_training/outputs/validation --max-episodes 10 --videos
```

Closed-loop evaluation replays the scenario configuration of held-out episodes,
while the learner controls the simulated aircraft. It reports deck landings,
water strikes, collisions, aborts, timeouts and contact impact velocity. These
evaluation records retain their validation/test split. Without `--videos`,
evaluation saves JSONL traces and summaries, not a second RGB archive. Camera
images are still rendered for the policy. PX4 continuous flight logging is
stopped after startup; a small bootstrap ULog can remain. Evaluation traces
are not training-eligible. Inspect failures and search behaviour as well as success rate.

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


## Reviewed cloud collection → training → evaluation

On the existing Linux L4 VM, keep its working CUDA PyTorch environment. The
launcher does not reinstall dependencies or replace it with CPU wheels.

```bash
cd "$HOME/vision-based-drone-landing-ml"
git switch codex/landing-training
git pull --ff-only
if ! tmux has-session -t landing-pipeline 2>/dev/null; then
  tmux new-session -d -s landing-pipeline -c "$PWD" \
    'bash landing_training/start_cloud_pipeline.sh'
fi
```

It first checks hardware EGL and CUDA. With no current approved bundle it
runs qualification and exports ten current videos in four workers, then exits
with `user_review_required` (code 2). It neither approves its own output nor
creates production data. Read the review path from the persistent state. After
the user verifies all videos/data and explicitly approves that matching bundle,
rerun the same launcher to proceed. The VM's dependency/PX4 fingerprint is part
of approval, so a bundle from a different environment is not automatically valid.

A running tmux session survives an SSH disconnect. Outside tmux, use
`tmux attach -t landing-pipeline`; inside tmux use
`tmux switch-client -t landing-pipeline`. Restart the launcher after a stop;
completed recordings, caches and checkpoints remain intact. The wrapper uses
the existing VM-wide collection lock; direct module launches also lock their
persistent state. Do not run a separate benchmark/collector concurrently.

The persistent report is `landing_training/outputs/pipeline_state.json`;
`latest_pipeline_launch.txt` locates this attempt's `console.log` and
`pipeline_report.json`. Reports save every stage and every 30 seconds, including
cumulative wall time, stage durations, indexed episode/split counts, total
stored dataset GB, checkpoint/cache GB, remaining disk space, pilot size/duration
projection, audit outcomes, checkpoint paths and held-out evaluation results.
Collection reports separately retain measured FPS/resource use and partial
attempts. A forced kill or machine loss can prevent the final write; the last
atomic report remains. Completed collection with a storage stop is reported as
stopped, never as training-ready.

The fixed default stages are:

1. Verify current user approval and the reviewed 1,200-scenario plan.
2. Collect the balanced 240-episode expert pilot with 64 workers. Audit all
   metadata/HDF5 rows for airborne starts, timing, previous-action alignment,
   bounded outputs, open/raised dock, terminal masks and PX4-confirmed landings.
   Every nominal expert flight must land; every expert flight must avoid water
   strikes and forbidden collisions. Fault cases may safely abort/timeout. A
   failure stops scaling rather than silently changing the acceptance rules.
3. Project full storage from that measured pilot with a 25% size margin; stop
   if disk/capacity is inadequate. Collect the remaining episodes and require
   the exact complete plan. Audit all episodes and world/split isolation.
4. Train on the completed dataset for up to three epochs using four image
   readers, frozen FP32 encoder features and eight recurrent lanes. The trainer
   hashes all indexed HDF5 files before optimizer work, fits normalization on
   training worlds only, and retains the validation-selected best checkpoint.
5. Evaluate a stratified 12-world validation pilot in eight workers, covering
   all maps, distance bands and weather groups. Require at least one landing
   and zero unsafe pilot outcomes before continuing the epoch budget. This is
   a minimum learning check, not a reliability qualification. A failed check
   stops with `needs_model_iteration` and preserves traces/weights for diagnosis.
6. Resume up to ten total epochs, with validation early stopping after three
   unimproved epochs. Evaluate all 120 validation and all 120 test scenarios.
   Test episodes never select weights. A successful pipeline reports measured
   reliability and failures; it does not authorize real flight deployment.

Defaults cap the dataset at **1,500 decimal GB** and leave at least **32 GB**
for shutdown/headroom. The collection stage additionally reserves worst-case
space for the 1,080 train/validation feature caches, JSONL evaluation traces,
logs and checkpoints: currently **95 GB total free space**, before its additional
in-flight/shutdown reservation. Thus collection can stop before reaching
1,500 GB. With 1,532 GB initially free, roughly 1,437 GB is available for dataset
writes before those margins. Actual episode durations/compression determine
whether all 1,200 fit. No recordings are automatically deleted to meet the cap.
Dataset, checkpoints and reports must share the guarded filesystem. Evaluation
rechecks space before every attempt; retained interrupted attempts count against
actual free space. These are admission/live guards, not a filesystem quota.

Configuration and source/review hashes are frozen for resume. Restore those
settings or use a fresh state/output/checkpoint directory after a substantive
change. Interrupted child stages are journalled with PID, process start time and exact
command; restart verifies that identity and stops the owned job before
quarantining recordings. Unverifiable/reused PIDs are refused. Partial episode
attempts are quarantined and retried; optimizer state resumes from the last
complete epoch. Completed policy-pilot checks and final
assessments are reused when compatible; an evaluation of changed weights gets
a fresh trace directory. User approval remains mandatory after source changes.

Boat starts reserve `boat_speed * duration + 20 m` at both ends of each route.
Forward/reverse partners use the same canonical interior point with opposite
headings. Launch-coast queries use that progress, and preparation rejects
insufficient clear water. The existing standalone boat default still spawns
at progress zero. Mission-deadline ascent, missing dock readiness and stale PX4
state are handled by `supervision.supervise_action` using observable state and
the caller's monotonic mission clock. Those commands are masked from imitation;
a real deployment integration must call the same supervisor.

The L4 benchmark measures the training pipeline, not these flight evaluations.
At a hypothetical 60 s mean production episode, the earlier measurements suggest
about 5 h of collection plus 30–44 min of feature preparation/training. Pilot
and final closed-loop evaluation, integrity reads and writes add time; their
actual duration is retained in the stage report. No precise end-to-end promise
is justified until the diverse production pilot has run on this VM.
