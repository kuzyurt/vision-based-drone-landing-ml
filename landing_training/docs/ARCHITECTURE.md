# Architecture and training details

Reference for readers who want the mechanics behind the [overview](../README.md):
the training world, the teacher, the R15 landing policy and the search head.

Names used in the overview: the **main network** is the R15 pose model below
(about 1.55 million parameters: encoder and recurrent pose branch), the **search
head** (about 45,000 parameters) is described at the end, and the **pad finder**
is R15's spatial acquisition branch (about 45,000 parameters). The search head
started from the pad finder's weights.

## Versions

There is one final version. Everything else is history kept as evidence.

| Version | Networks | Runs where | Benchmark |
|---|---|---|---|
| **Final** (`student.onnx`, 19 Nov) | Main network + search head | Realistic browser game; natively via `benchmark.harness.tidewater_run` | 79.9, 18 / 20 ([evidence](../../benchmark/evidence/final/summary.json)) |
| Search student `fresh-search-f62c10a2` (8 Nov) | Main network + pad finder + search head, radio blocked | Benchmark only | 72.8, 18 / 20 |
| R15 | Main network + pad finder | Benchmark only | 47.5, 11 / 20 |
| Radio-robust (15 Oct) | Earlier hybrid | Benchmark only | 44.4, 7 / 20 |

The final version's control code is
[`tidewater-game/app/public/policy/reference/`](../../tidewater-game/app/public/policy/reference/):
search and radio approach in [`student_radio.py`](../../tidewater-game/app/public/policy/reference/student_radio.py)
and [`student_runtime.py`](../../tidewater-game/app/public/policy/reference/student_runtime.py),
glare, near scan and near-deck rules in
[`tidewater_guidance.py`](../../tidewater-game/app/public/policy/reference/tidewater_guidance.py),
and the frozen R15 landing controller underneath. Where the pad finder used to
override the main network's pad point, the final version uses the main
network's own estimate.

The R15 sections below describe the frozen base model and its controller.

## Training environment

| Part | Role |
|---|---|
| MuJoCo world | Original vehicle CAD, rotor thrust, buoyancy, drag and physical deck contact |
| PX4 | State estimation and low-level flight control |
| Variation | Five coastal map types, seeded routes, camera starts, wind, waves and appearance |
| Inputs | 640 × 360 onboard RGB, own telemetry and gimbal state; optional boat radio in the R15 lineage |
| Outputs | Forward/right/down velocity, yaw rate and camera pan/tilt rate at 25 Hz |
| Landing success | Stable, disarmed support on the target deck for at least two seconds |

Physics advances at 1 ms with 250 Hz sensor/actuator lockstep. The current search
dataset adds similar and dissimilar decoy boats, with no boat-radio input to
the learner.

## Learning from the teacher

The privileged teacher uses exact visible-instance pixels and simulator labels
to demonstrate search, inspection and landing. Visibility and resolution rules
limit which boats it can inspect and when identity labels become available.
Hidden boats do not enter its search controller. This extra information supplies
**training labels, never student inputs**.

Recordings synchronize RGB, sensors, commands and outcomes. The current curated
dataset has **60 episodes: 48 training, 6 validation and 6 test**. Validation
selects the checkpoint; test data is excluded from optimization. The learner
must then fly independently—teacher-assisted flights do not count as its successes.

Training is supervised. Early action imitation failed in flight, leading to
separate learned perception, geometric localization and explicit control.

## Policy architecture

R15 is the evaluated hybrid policy. Its neural components estimate the target
and its motion; calibrated geometry and explicit control turn those estimates
into a landing. The network does not directly predict motor commands.

[![R15 system: camera, own telemetry and radio through perception, tracking and control to PX4, gimbal and drone](../../docs/media/policy-architecture-detailed.png)](../../docs/media/policy-architecture-detailed.svg)

| Signal | From | To |
|---|---|---|
| RGB frame | Onboard camera | Image encoder and metric marker registration |
| Image capture timing | Camera observation | Capture-motion compensation and metric tracking |
| Own pose, velocity, attitude and gimbal state | PX4 estimates and camera-joint feedback | Recurrent perception, geometric tracking and landing control |
| Boat position/velocity, packet age and uncertainty | Boat radio | Bounded position/velocity fusion |
| Reported dock readiness | Boat radio | Command safety checks |
| Target image bearing and learned pose | Spatial head and recurrent pose model | Metric registration and tracking |
| Pad pose and deck motion | Accepted geometric measurements and tracking | Landing controller |
| Three velocity commands and yaw rate | Landing controller and supervisor | PX4 flight control, then motor actuation |
| Pan and tilt rates | Landing controller and supervisor | Gimbal joints, changing the next camera view |

Motor actuation changes drone motion; simulated sensors update the PX4 estimate
and the camera renders the next view. The policy acts again on those observations.

### Neural architecture

[![R15 neural detail: shared encoder, spatial acquisition, visual memory and bounded fusion](../../docs/media/policy-neural-architecture.png)](../../docs/media/policy-neural-architecture.svg)

### Shared image encoder

The 640 × 360 RGB frame is normalized with the model's stored image statistics
and passed through **MobileNetV3-Small**. Both perception branches reuse this
encoder. Intermediate feature maps preserve local target detail; the final
576-channel map supplies the recurrent pose branch.

### Spatial acquisition branch

Fine and context maps with 24 and 48 channels are projected to 24 channels each,
aligned in image space, and merged by two 3 × 3 convolutions. The resulting
48-channel map predicts a **target heatmap, sub-cell offsets and presence**.
Decoding yields an image center to guide acquisition and camera aiming before
a reliable metric pad pose is available.

### Recurrent pose branch

For each of the final 576 channels, the encoder retains mean activation and
activation-weighted horizontal/vertical position. These **1,728 values** preserve
coarse spatial information and are projected to **256 visual features**.

The numeric observation follows a **32-value contract**. A two-layer MLP maps it
to 64 features. Periodic angle representations replace the baseline's previous
action inputs. Boat-radio values and status are masked before this visual
memory path, so they cannot supply a hidden target coordinate to the GRU.

The 256 visual and 64 numeric features form a **320-value input to a GRU with
128 hidden units**. Its state carries information between camera frames.
Linear readouts produce a 15-value pose representation, including visibility,
relative position and velocity, heading, deck normal, image center and contact
probability. A separate six-value visual readout supplies the position/velocity
estimate used when no radio reference is available.

### Optional radio fusion

Boat radio enters **after** visual recurrence. A small MLP (**13 → 48 → 2**)
uses visual/radio disagreement, reported uncertainty and packet age to predict
separate position and velocity weights. Each weight is capped at **0.35**;
invalid or stale radio receives zero weight. The fused estimate moves toward
the radio estimate by that bounded amount. Raw radio coordinates do not bypass
this fusion stage to steer the controller.

### Geometry and flight control

The controller receives RGB, own telemetry and the learned estimates. Known
pad markings and camera calibration support metric marker fitting. Accepted
measurements, tracking and own-motion compensation estimate deck position and
motion. A confident neural detection alone cannot enable descent.

Explicit control handles search, alignment, motion matching, descent and
touchdown, with command bounds and recovery logic. It emits six values at 25 Hz:
three velocity commands, yaw rate, camera pan rate and camera tilt rate. PX4
handles flight control; the final two commands move the camera gimbal.

Implementation: [encoder and GRU](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15/code/landing_training/policy.py),
[pose readout](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15/code/landing_training/radio_robust_20261015/parent_model.py),
[spatial head](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15/code/landing_training/radio_robust_20261015/spatial_acquisition.py),
[radio fusion](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15/code/landing_training/radio_robust_20261015/model.py),
[runtime](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15/code/landing_training/radio_robust_20261015/runtime.py).

### Search head

The current policy freezes the R15 model and adds a multi-boat search head on
its fine/context features. It initializes from the spatial acquisition weights,
then adds four-class evidence and two-class identity readouts to the shared
48-channel feature map. Heatmap, offsets and presence locate candidates;
evidence and identity decide which boat to inspect.

This head is feed-forward. The sensor-only search runtime maintains object
tracks and search state, then hands a confirmed target to the frozen R15
landing runtime. It learns acquisition rather than replacing PX4 or the landing
controller. [Search head implementation](../../training_runs/search_revision_20261025/model.py).

The run uses AdamW, a 0.0003 learning rate, batch size 8 and 15 configured epochs.
The resulting bundle is the benchmark's search policy (`fresh-search-f62c10a2`).
[Dataset and current trainer](../../training_runs/search_revision_20261025/README.md).
