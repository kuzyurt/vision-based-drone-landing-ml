# Technical report: airborne landing on AERODOCK

## Objective and scope

The project develops a camera-based policy for a drone approaching a moving boat
from an airborne start. It combines the existing AERODOCK assembly and X500 V2
PX4 drone simulation, records an expert's decisions and trains a small recurrent
policy by supervised imitation. Boat-to-drone telemetry and the visible landing
marker are allowed parts of the task.

The implementation covers the complete simulated experiment: shared physics,
reviewable observations and actions, a varied dataset, reproducible training and
held-out flight evaluation. Hardware references are the Holybro X500 V2/Pixhawk
6C, ALLXF D-80Pro gimbal camera, Khadas Edge2 and SX1262 radios described in the
[drone documentation](../../px4-mujoco-drone-simulation/README.md). Their real
camera, radio and compute interfaces are not yet calibrated against this model.

## Phase 1 — Combine and qualify the environment

Both vehicles occupy one MuJoCo model and state, with gravity 9.80665 m/s² and a
1 ms timestep. Boat buoyancy, water drag, propeller thrust and drainage combine
with drone thrust, aerodynamic drag, rotor reaction and rigid-body contacts.
Forces are cleared once and then added; the boat and drone move through physics
rather than following replayed poses. Native PX4 v1.16.0 runs its estimator,
controllers and land detector in timestamp lockstep with the simulation.

PX4 receives IMU samples at 250 Hz, barometer/magnetometer at 50 Hz and GNSS at
approximately 20.8 Hz. Camera observations and expert/policy decisions use 25 Hz.
World state uses ENU coordinates; PX4 attitude uses NED/FRD. Policy velocity and
beacon vectors use estimated-heading forward/right/down coordinates.

The original boat visual meshes are retained. Separate deck, coaming, lid and
support collision pieces preserve the landing-bay opening. The raised contact
plate is 600 × 600 mm, and the drone's four EVA feet provide support. Boat lids
are held open at 0.46 m and the platform raised at 0.40 m before recording;
deviations over 8 mm fail the episode. Camera ray tests retain aircraft-leg
occlusion. The expert uses forward/backward camera corridors through aircraft
heading and gimbal motion.

Wave periods and wavelengths follow the water model's dispersion relation. An
observer-centred wave mesh prevents the water patch from revealing target
location. A small, world-anchored procedural ocean texture refreshes at 5 Hz;
those cosmetic ripples do not add physical forces. The renderer caches texture
work, uses bounded scenery and disables expensive wave reflections/shadows.

Qualification checks cover force addition, mass scope, buoyancy/support-load
transfer, dock contacts, route reversal/rotation, water and rotor strikes,
observation contracts and policy causality. Comparing 1 ms and 0.5 ms unloaded
integration checks consistency; it is not a full contact convergence study.

## Phase 2 — Define the policy and expert

### Observation and action contract

The actor receives the onboard **640 × 360 RGB** image and **32 numeric values**:
PX4 velocity, attitude/rates and estimator ages; gimbal angles; coarse beacon
position/velocity, age, validity and dock readiness; image age/validity; previous
executed action; and decision interval. [schema.json](../schema.json) documents
the contract; `recording.numeric_observation` fixes the numeric field order.
Exact simulation pose, deck normal, clearance, weather and expert phase remain
teacher/evaluation data and never enter the actor input.

The synthetic beacon updates at 1 Hz with declared 0.25 m position noise and
0.025 m/s velocity noise. These are protocol assumptions implemented for the
experiment, not measured SX1262 performance. Observation validity, age and
readiness let the supervisor handle missing or stale information.

| Command | Bound |
|---|---|
| Forward/right velocity | Horizontal vector magnitude ≤ 2 m/s |
| Down velocity | −1 m/s upward to +0.7 m/s downward |
| NED yaw rate | ±0.5 rad/s |
| Gimbal pan / tilt rates | ±50°/s / ±40°/s |

PX4 closes the attitude and motor loops. A shared observable supervisor handles
mission deadlines, stale estimator data and missing dock readiness; its overrides
are masked from action imitation. Policy contact confidence is advisory. The
physical support checks and PX4 land detector determine terminal confirmation
and ordinary disarming.

### Expert behaviour and outcomes

Before recording, the expert physically takes off and reaches the requested
start. Preparation rejects insufficient clear water; unsafe starting bearings
are rotated in 15° increments, with requested and achieved bearings retained.
Paired route directions start at the same canonical interior position, with
opposite headings and enough route length for the mission.

During search, the expert uses the delivered coarse beacon and scans the camera;
a missing beacon triggers scanning with a fixed ascent command. Visible approach,
velocity matching and descent use privileged current scene state as teacher
information. Future route/wave state is excluded. The expert aligns the drone
with a front/back deck heading, slows descent and recovers when alignment is lost.

`stable_contact` requires at least three supporting feet, the centre of mass
inside their support polygon, feet 20 mm inside the plate edge, relative
horizontal speed below 0.1 m/s, normal speed below 0.05 m/s, tilt below 5° and
relative angular speed below 5°/s for one second. `landed` additionally requires
stable support while PX4 is disarmed for two seconds. Water strike, forbidden
contact/rotor strike, abort, timeout and contact-only outcomes are kept distinct.
The water-strike detector samples collision geometry; it does not model complete
post-crash flotation or exact water/triangle intersection.

## Phase 3 — Review and collect expert data

Human review precedes production collection. Ten videos cover both directions
of all five map families, including longer starts and fault cases. Each combines
an external view, the actual onboard frame and a numeric input/output side panel.
Raw rows, qualification evidence, scenarios and artifact hashes accompany the
videos. The approval identifies a reviewer and exact manifest; review recordings
are excluded from training.

The deterministic production plan uses **600 world/path pairs**, each traversed
in both directions: **960 training / 120 validation / 120 test episodes**.
All episodes of a world stay in one split. Seeds recreate the same map/route;
each episode initializes its own simulation. Reverse partners reuse the geometry
and switch the coast's side relative to the boat.

| Variation | Production coverage |
|---|---|
| Maps | Island, beach, city, gravel, rock; seeded geometry and rotation |
| Airborne horizontal start | Area-weighted samples in 0–5, 5–20 and 20–60 m bands |
| Height above deck centre | 2–8 m; actual foot clearance is recorded separately |
| Boat target speed | 0.1–1 m/s |
| Route start | Seeded usable interior, reserving speed × mission duration + 20 m at each end |
| Wind | Four profiles, mean 0–4 m/s, varying direction; gusts may exceed the mean |
| Waves | Height parameter 0–0.15 m, period 2–5 s, varying direction/phase |
| Camera | Brightness/contrast 0.85–1.15, blur 0–0.5 px, delay 0–200 ms |
| Initial camera aim | 50% aimed toward / 50% away from boat in each split |
| Scenario faults | 70% nominal; 10% blackout, 10% radio dropout, 10% readiness delay |

Sea current is supported within 0.3 m/s but is zero in this plan. Wave height is
the original multi-component model parameter, not significant wave height.
Initial camera aim does not guarantee marker visibility. Mission duration is
capped at 180 s. Separate stress trials do not expand production ranges: calm
water trials confirmed a 1.5 m/s boat setting in 30/30 specified flights, while
strong-weather reviews explored the original 0.5 m wave parameter and 8 m/s mean
wind. Those are simulator experiments, not real-aircraft operating limits.

Each episode stores lossless LZF HDF5 RGB and metadata, matching JSONL rows,
scenario/summary files and PX4 provenance. Teacher proposals, bounded teacher
commands and executed actions are distinct. Terminal/intervened actions are
masked. Failed nominal flights receive at most three same-scenario retries;
originals and retry evidence remain on disk. Repeating a seed may repeat a failure.

The selected nominal flights must land in at least 98% of the training and
validation splits. Safe non-landings within that allowance require three checked
retries and an action-imitation mask. Test expert success is reported without
gating fitting; its failures remain in final policy evaluation. Unsafe flights,
corrupt data and missing coverage still block the production workflow.

The first 240 episodes form a balanced expert pilot. Its measured storage and
duration support scaling decisions. Independent collection workers own their
physics, PX4 ports and files; only the coordinator publishes the manifest.
Audits check every metadata row in bounded batches with up to 32 processes and
at most four simultaneous retry checksum streams. They do not decode indexed
RGB; the trainer verifies every indexed HDF5 checksum before optimization.

## Phase 4 — Train the recurrent policy

MobileNetV3 Small produces spatial x/y expectations and mean activation per
channel. This retains location information instead of using only a global
classification vector. A 1,728→256 visual projection combines with a 32→64
telemetry MLP; a causal GRU with 128 hidden units predicts six bounded actions.
Auxiliary heads predict marker visibility/centre, relative position/velocity
and stable-contact confidence. Total parameters: **1,550,768**, with **623,760
trainable** when the ImageNet encoder is frozen.

The default frozen encoder is evaluated once per frame and its FP32 features
cached before the trainable projection. Spawned readers decode independent
chunks with bounded queues. Cache identity includes recording, encoder,
preprocessing and supervision; complete caches are checksummed and atomically
published. RGB remains available for audits, further collection and fine-tuning.
Fresh per-epoch image augmentation requires the RGB path; fine-tuning disables
feature caching and retains fixed BatchNorm statistics for temporal causality.

One epoch visits every training recording once, shuffling episodes while keeping
frame order. Eight recurrent lanes process up to 64 frames each per Adam update
(2.56 s per lane). Hidden state carries between chunks; gradients stop at chunk
boundaries and state resets at episode boundaries. Learning rate is 1e-4 and
gradient norm is clipped to 1. Normalized action Huber loss is combined with
visibility (0.1), contact (0.05) and visible regression (0.05) losses. These are
baseline hyperparameters, not proven optima.

Normalization uses training worlds only. Validation uses dataset-wide loss
component denominators and reports an action-persistence baseline. Previous
executed action is an input, so low one-step error can reflect repeating the last
command; closed-loop flights are essential. Teacher flights with unsafe outcomes
are excluded from action imitation; auxiliary labels remain available. DAgger
support retains oracle labels on student-visited states, but the default
production workflow does not automatically add DAgger rounds.

## Phase 5 — Evaluate and retain the result

After complete collection/audit, the pipeline trains for up to three epochs and
runs a stratified 12-flight validation pilot. At least one landing and zero
unsafe outcomes are required to continue. This is a minimum learning check,
not a reliability qualification. Failure preserves weights and traces with
`needs_model_iteration` for diagnosis.

Training then resumes up to ten total epochs, with early stopping after three
unimproved validation epochs. The validation-selected best policy flies all 120
validation and 120 test scenarios. Reports retain landing/failure counts,
touchdown measures and map/distance/weather/camera-aim breakdowns. Paired routes
are related trials. Test worlds never fit normalization or select weights.

Outputs include the audited dataset, `latest.pt`/`best.pt`, optimizer/RNG resume
state, feature caches, chronological loss CSVs and flight reports. Stage timing
separates collection, audits, training/preparation and evaluation. Atomic state
updates and detached tmux preserve progress across SSH loss. Checkpoint resume
replays an interrupted epoch from the last complete one. Ownership journals,
locks and retained partial attempts prevent silent overwriting.

Storage admission reserves in-flight shutdown space plus feature/evaluation
capacity, with a 1,500 decimal GB dataset cap and a 32 GB base free-space floor.
The current plan requires about 95 GB total collection reserve before in-flight
margin. No dataset evidence is deleted automatically. Approvals and compatible
runtime/data/configuration hashes are required on resume.

## Evidence and remaining limits

Regression suites exercise data integrity, split isolation, causal state,
cache equivalence, finite gradients, checkpoint/optimizer/RNG recovery, early
stopping and cancellation. Retained [collection reports](../reports/README.md)
record specific optimization experiments. Training comparisons distinguish raw
RGB throughput, one-time feature preparation and cached epochs; a repeated tiny
fragment only checks that the learning path is wired correctly.

Run-specific timings and landing rates must come from saved production reports.
The simulated buoyancy, aerodynamic coefficients, camera FOV/latency, radio
payload/noise, gimbal feedback and Edge2 inference latency still need hardware
validation. The water model does not include slamming, added mass, wakes or
rotor-water interaction. Neither a fast benchmark nor completion of ten epochs
establishes real-world safety or reliable landing under untested conditions.

See the [operating guide](operations.md) for reproduction commands and artifact
locations, and the [source map](source_map.md) for implementation responsibilities.
