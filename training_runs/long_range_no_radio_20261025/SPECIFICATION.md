# Next run: long-range visual discovery and boat discrimination

Date: 25 October 2026. Scope: discover the correct boat from onboard sensors at
60–100 m, distinguish similar and dissimilar decoys, then hand off to the
established R15 landing controller. Terminal landing is a retention constraint.
All recordings, labels, crops, features and validation/test data must be newly
generated with the currently connected privileged teacher. Existing weights
are initialization only; existing datasets are excluded.

**Execution status: specification and deterministic scenario manifest are
verifiable now; collection/training are NOT launchable through an existing
entry point.** The current teacher is connected to review/benchmark execution,
not a training collector. This file specifies the missing work precisely rather
than falsely advertising an existing training command. Complete the four
implementation prerequisites below before flight collection or optimization.
No training, collection, deployment or benchmark flights were launched by this audit.

## 1. Verified active dependency graph

Repository-relative paths below resolve against this checkout. `run_spec.json`
pins their actual SHA-256 values; `verify_spec.py` resolves and verifies them.

| Entry / component | Connected implementation and behavior |
|---|---|
| Current evaluation entry | `python -B -m benchmark run`; `benchmark/__main__.py` → `runner.run_trial` → pinned procedural scene and selected actor. `benchmark/suite.py` constructs the current explicit cases. `benchmark/environments/runtime.json` pins the six-decoy city MJB. |
| Current student selected in the comparison | `r15-archived-export-67a80a63` in `benchmark/models/inventory.json`; staged source is `artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15/code/landing_training`. The v39 directory name describes its container; the selected actor is its **base R15**, not the outer experimental teacher. Its policy manifest is byte-identical to `artifacts/landing_hardening_20261018/candidate_r15/policy.json`. |
| Student loading | `radio_robust_20261015/runtime.py:RadioRobustRuntime` → `native_marker.install` and `runtime_fixes.install` → strict `pose.pt` state load → strict spatial-head state load → `MarkerPosePolicy`. `acquisition.pt` is staged inventory baggage: this runtime does not load it. |
| Actual acquisition implementation | `runtime_fixes.install` replaces `policy.acquire_visual` with `controller/observable_acquisition.py:acquire_visual`. Do not mistake the locally defined but unused `acquire` function for the installed implementation. |
| Metric/landing path | `MarkerPosePolicy.act` → capture-time geometry, native marker fitter, height/innovation checks, persistent target and visual motion → confirmed metric lock → `MarkerLandingController` → final `finish` → stopping-distance limiter and inherited action guard → post-guard nearfield descent veto → supervisor → PX4. |
| Windows adapters | `artifacts/local_curriculum_20261020/local_paths.py` resolves preserved package sources and R15 mission sources. `windows_kernels.py` redirects the known marker `.so` binding to the source-verified Windows DLL. `fast_physics_windows.py` installs FP64 wave/cross-product equivalents without changing timestep or scoring. |
| Newest teacher | `benchmark/actors.py:PrivilegedReference` and `artifacts/teacher_scan_modes_20261024/run_privileged_review.py` import **root** `landing_training/privileged_teacher.py`; it imports root `smooth_landing.py`, `expert.py` and `environment.py`. Frozen `sources/` copies are evidence, not the implementation imported by these entries. |
| Teacher labels | Same frozen RGB frame → segmentation render → `target_learning.scenes.annotation_groups` → `VisibleBoatOracle.observe` → `BoatView` → `SearchDecision` → `PrivilegedTeacher.act`. Segmentation/object IDs/true positions are private to the teacher. |
| Physical world | `VerticalLaunchEnvironment` from the preserved R15 `mission_sources/mission_setup.py` → root `Environment` → sibling `AERODOCK_MuJoCo/usv/boat_sim.py` and `procedural_world.py`, plus sibling `px4-mujoco-drone-simulation/sim/environment.py` and `propulsion.py`. These sibling folders are required, not optional background. |
| Browser deployment | `PolicyControl.js` → `PolicyInferenceWorker.js` / `PolicyInference.js` → checksum-verified `public/policy/manifest.json`, `pose.onnx`, WebGPU network, marker kernel and Python reference controller. `PolicyTelemetry.js` supplies own sensors and an explicit missing-radio representation. Browser inference has 34 numeric inputs (32 plus two sigmas), 20 exported predictions and 128 recurrent values. It is a separate execution backend from Windows benchmarking. |

The root `landing_training/train.py`, `collect.py`, `evaluate.py` are the older
action-policy pipeline. They do not select R15 or the new teacher. The preserved
radio trainer checks the old dataset hashes; `train_fusion.py` explicitly loads
old mixed datasets and updates only `fusion_gate`. Neither is suitable for this
run. Older observable/neural teachers and their recognition checkpoints are
not the newest teacher and are not selected for initialization here.

## 2. Verified observation, architecture and action contract

Native model input is RGB uint8 `[360,640,3]`, the following 32 float values,
and separate position/velocity uncertainty `[sigma_p,sigma_v]`:

| Indices | Recorded numeric meaning |
|---|---|
| 0–2 | Own heading-frame forward/right/down velocity |
| 3–5 | Own NED roll/pitch/yaw |
| 6–8 | Own FRD angular rates |
| 9–10 | Measured camera pan/tilt |
| 11–13 / 14–16 | Received boat relative position / boat heading-frame velocity |
| 17–18 / 19 | Own position/attitude age / radio age |
| 20–22 / 23 | Own estimator valid, radio valid, dock ready / image age |
| 24–29 | Recorded previous executed six-command action |
| 30–31 | Decision dt / image valid |

`periodic_no_action_v1` replaces slots 24–29 with sine/cosine pairs for yaw,
pan and tilt, zeroing raw angle slots 5, 9, 10. Thus previous teacher actions
do not enter the visual recurrence. Own absolute PX4 position is available to
the geometric controller, not part of this 32-value neural tensor.

The network normalizes RGB, runs MobileNetV3-Small features, and compresses each
of 576 channels into spatial x/y expectations and mean activation: 1,728 values.
Visual projection is 1,728→256 with ReLU; telemetry is 32→64→64 with ReLU;
GRU input is 320 and hidden size 128. The used output head has 15 values:
visibility logit, relative position 3, relative velocity 3, modulo-pi heading 2,
normal 3, normalized pixel center 2 and contact logit. There is an additional
128→6 absolute visual position/velocity branch and a 2→64 uncertainty projection.
The old six-action linear head remains in the state dict but is not used to
produce the current flight commands.

Independent visual recurrence forces radio fields to missing. The separate
fusion MLP is 13→48→2 with SiLU; sigmoid fusion weights are capped at 0.35 and
multiplied by availability. For this run availability is always false and both
weights must be exactly zero. Unknown dock readiness is replaced with the stored
normalization mean, not a readiness signal.

The image-only `SpatialAcquisition` takes encoder maps at indices 3 (24 channels)
and 8 (48 channels), projects each to 24 channels, interpolates context, merges
with two 48-channel convolutions, and outputs a heatmap, bounded 2D offset and
presence logit. It replaces visibility/pixel center before lock or after a
0.5-second metric gap. It has **no explicit target/decoy identity output** and
decodes one highest-scoring location. The runtime actually uses the native
marker fitter, not just the unpatched Python registration definition.

The fitter rejects RMS above 2.5 px, fewer than 12 template samples, paint
precision below 0.7, recall below 0.65, and badly conditioned fits. Metric lock
requires at least three fits spanning 0.079 s, with freshness checks. Coarse
neural attention is not permission to descend. R15 retains short visual memory,
motion estimation, braking and bounded recovery around this lock.

Actions are six **setpoints**, not motor thrusts: forward/right/down m/s,
yaw rad/s, pan rad/s, tilt rad/s. `Expert.bounded` caps horizontal norm at 2 m/s,
vertical command to [-1,+0.7], yaw to ±0.5, pan to ±50°/s, tilt to ±40°/s.
R15 additionally applies its recorded per-axis slew limits and [-10°,90°] tilt
target guard. PX4 executes the setpoints. Physics is 0.001 s, simulated sensor
delivery every 0.004 s, and decisions every 0.04 s.

## 3. Newest teacher and present transfer boundary

`BoatView.detectable` requires 24 visible pixels and extent at least 8 px.
Recognizable evidence additionally requires range ≤35 m, at least 80 pixels,
and extent ≥24 px. Until then all boat types are `unknown_boat`. At 27–35 m,
target and similar decoys are `target_or_similar`; resolved dissimilar decoys
are `different_boat`. At ≤27 m a resolved similar decoy is `different_boat`.
The target becomes `target_boat` only with visible pad and pad extent ≥6 px.
Range here is horizontal range, not slant distance. These are authored teaching
rules, not measured student recognition limits.

Evidence must persist for 0.16 s; gaps over 0.12 s reset support. Scan 1 holds
survey height, centers pan and aims tilt at 6°, turning at 0.35 rad/s once
gimbal errors are below 3°. Actual heading sweep, not elapsed time, determines
completion. Unknown far boats cannot interrupt scan 1. Ambiguous or confirmed
evidence can. Scan 2 inspects the first eligible currently visible boat; it
does not rank boats by hidden target identity. Rejection restarts scan 1.

During inspection the teacher can steer toward a visible boat's privileged
reference point. Lost sight stops horizontal translation and descent, with
last-view camera reacquisition for at most 3 s. Unresolved inspection restarts
after 12 s without 0.5 m progress or after 90 s. An identified, visible pad gates
the privileged smooth-landing pilot; physical-contact continuation has its own
branch. The pilot follows deck velocity, aligns to the platform axis, requires
0.6 s settling before descent and limits acceleration. Teacher truth-derived
actions are demonstrations, not proof that the student can recover the same
information from RGB.

Currently the review writer sets `action_supervision_valid=False`, `role=review`
and `training_eligible=False`; benchmark output also disallows training. There
is no current imitation/DAgger handoff from these entries into R15 weights.
Do not relabel those old files. Build a fresh collection entry point and labels.

## 4. Initialization: existing and load-verified

Use the exact real local files, not nonexistent loose weights beside the
canonical candidate manifest:

* Base pose: `benchmark/models/weights/2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4.pt`.
  SHA-256 is its filename stem; schema `aerodock.landing.radio_robust_pose.v1`,
  epoch 8. Strict load passed with the benchmark-selected R15 model; 1,553,149
  parameters. A missing-radio forward probe returned finite `[1,1,15]` output,
  `[1,1,128]` hidden state and fusion weights `[0,0]`.
* Spatial initialization: `benchmark/models/weights/b432c1584b778d1959e950e855fcdf78c468d7f5ec7e86b71641f5052a6ce14b.pt`.
  SHA-256 is its filename stem; schema `observable_landing.spatial_acquisition.v1`,
  epoch 9, 45,380 parameters; strict load passed.
* Controller/calibration: the benchmark-selected base R15 manifest/source tree
  above; policy SHA-256 `5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35`.

Reason: these weights implement the currently deployed visual pose and landing
interfaces, including independent no-radio memory. Preserve them while teaching
the missing acquisition/discrimination skill. A newer timestamp on a standalone
recognition checkpoint does not make it a newer complete student policy.
Initialize all new identity/evidence parameters from seed 20261025; do not
silently import old recognition weights or old feature caches.

## 5. Exact fresh collection budget and curriculum

Collect **1,200 new teacher-controlled task episodes**: **960 training,
120 validation, 120 sealed test**. This is a proposed engineering budget, not a
count inferred from historical data or a promise of sample sufficiency. Each
episode has up to 240 s / 6,000 executed decisions at 25 Hz. Therefore at most
**7,200,000 decision/RGB pairs**, including at most 5,760,000 training,
720,000 validation and 720,000 test pairs. Episode termination determines actual
step count; report it rather than calling the maximum a collected count.
No unsent terminal duplicate frame enters training. Store terminal state as
metadata. All task failures/timeouts remain in their assigned denominators.

| Distance (`Scenario.distance`, horizontal m) | All episodes | Training | Validation | Test | Collection share |
|---|---:|---:|---:|---:|---:|
| 60 | 120 | 96 | 12 | 12 | 10% |
| 80 | 360 | 288 | 36 | 36 | 30% |
| 100 | 720 | 576 | 72 | 72 | 60% |
| Total | 1200 | 960 | 120 | 120 | 100% |

Collect ascending distance. Train epochs 1–3 on the 96 training episodes at
60 m; epochs 4–6 on the 384 training episodes at 60/80 m; epochs 7–15 on all
960. Each eligible frame is visited once per epoch of its admitted stage,
with shuffled frame batches and no validation/test gradient updates. The final
unique training mix is 10/30/60%; cumulative curriculum exposure is different
and must be logged. Validation uses all 120 validation worlds each epoch.

There are five equally represented procedural map kinds: island, beach, city,
gravel and rock, **240 episodes each** (192/24/24 by role). Each distance is fully
crossed with three weather levels and four decoy densities. At each
distance/weather/density combination create 1, 3 or 6 blocks respectively;
each block contains ten independently seeded worlds, two per map. Assign eight
training, one validation and one test episode by the rotation defined in
`verify_spec.py`. This guarantees all marginal counts without sharing a world,
path or reverse-pair sibling across roles. `episodes.jsonl` is the exact plan.

| Weather level | `wave_height` m | `wave_period` s | `wind_profile` | `wind_mean_m_s` | Episodes |
|---|---:|---:|---|---:|---:|
| W0 | 0.00 | 3.0 | calm | 0.0 | 400 (320/40/40) |
| W1 | 0.05 | 3.0 | breeze | 2.0 | 400 (320/40/40) |
| W2 | 0.15 | 4.5 | gusty | 4.0 | 400 (320/40/40) |

Directions are independently sampled uniformly [0°,360°). W1 adds the existing
0.35 m/s horizontal OU fluctuations and up-to-1 m/s smooth gust; W2 uses 0.8
m/s horizontal OU fluctuations and up-to-2 m/s gust. Vertical OU sigma is half
horizontal sigma. Mean wind is not a maximum instantaneous wind. W2 is an
unqualified acquisition stress tier, not claimed solved landing performance.

Waves use four components at direction offsets [0,.38,-.52,.9] radians, period
multipliers [1,.72,1.31,.52] and amplitudes
`wave_height * .5 * [.55,.23,.15,.07]`. `seed+10` samples phases, `seed+20`
drives wind. Waves affect actual buoyancy/water drag/propulsion; wind affects
both aircraft and boat. These settings are not measured significant wave height.

| Density | `target_boats` plan alias | `false_boat_similar` | `false_boat_unsimilar` | Episodes |
|---|---:|---:|---:|---:|
| D0 control | 1 | 0 | 0 | 300 (240/30/30) |
| D1 easy distractors | 1 | 0 | 3 | 300 (240/30/30) |
| D2 hard distractors | 1 | 3 | 0 | 300 (240/30/30) |
| D3 mixed dense | 1 | 3 | 3 | 300 (240/30/30) |

These are **plan aliases**, not kwargs accepted by `Scenario`. The current
scene has exactly one dynamic target body `boat`, annotation group `target`,
and three static mocap decoys of each named class. Keep target count at one;
zero/multiple target worlds and moving decoys are unsupported in this run.
Density subsets require disabling every excluded decoy geom's render group
and collision masks and removing that group from the oracle. Do not merely
hide its annotation or move it underwater.

Reuse the six current hull/cabin/mast/colour/scale designs from the city scene;
do not retain its single fixed city map/start or its truth-relative search legs.
Regenerate procedural maps with new seeds. Use `review_helpers.place_distractors`
for seeded placement, sampling offsets 6+radius to 24+radius m around the
target, requiring water clearance 5+radius, route clearance
radius+target_radius+0.5, and pairwise clearance radius_a+radius_b+0.5.
It makes up to 3,000 proposals per object and fails closed on infeasibility.
This is placement radius, distinct from aircraft spawn range. D1/D2/D3 use the
same six-boat model and placement algorithm, with exclusions applied afterward.
Randomize decoy yaw uniformly [-pi,pi) in the fresh adapter; record it.
The existing authored similar boats resemble colour/silhouette, not exact CAD
clones. This run cannot establish discrimination against unseen clone designs.

Other exact settings: height 6 m; boat_speed 0 or 0.6 m/s, 600 episodes each;
current_x=current_y=0; stress_test=False; brightness=contrast=1; blur=0;
camera delay/blind duration=0. Both route directions are used, 600 each.
Random world rotation, requested spawn bearing and aircraft yaw offset are
uniform; initial_camera_target=False; pan U[-90°,90°], tilt U[-10°,90°].
Use the generated samples without resampling to make the target visible.
No target-bearing hint, pre-aimed camera or `SEARCH_LEGS` reaches the student.
Record actual visibility/occlusion and achieved bearing, since the water-safe
spawn selector may rotate the requested bearing in 15° increments.

Seeds are allocated per episode by role: training scenario/world/path from
10,000,000/20,000,000/30,000,000; validation from
40,000,000/50,000,000/60,000,000; test from
70,000,000/80,000,000/90,000,000, incrementing per-role episode ordinal.
All are uint32. Reserve a new output root; reject any world/path seed already
present in historical manifests before collection. No prior corpus is admitted
even if it used a different seed. Record deterministic RNG/library versions.

The first 24 training episodes chosen by the verifier are the pilot: two per
weather/density combination. They count toward 960, not an extra dataset.
Inspect and validate the actual new pilot's RGB/labels and physical conditions
before continuing; never recycle an earlier review's approval fingerprint.

## 6. Proposed learnable change and supervision schedule

This is a **new acquisition adapter**, not an assertion about current code.
Freeze R15 encoder, telemetry MLP, GRU, pose heads, fusion and all landing
geometry/control parameters for all 15 epochs. Train a separate search module:

1. Copy the spatial head's fine/context/merge convolutions and heat/offset/
   presence weights. Change its training semantics to proposals for **any
   detectable boat**, allowing multiple heatmap peaks. Keep the frozen original
   spatial head available for metric handoff and regression comparisons.
2. Add 48→4 per-cell evidence logits, ordered unknown_boat,
   target_or_similar, different_boat, target_boat; add 48→2 resolved identity
   logits (different, target). Initialize new convolutions with the fixed run
   seed. These heads use RGB features only, without teacher phase/range/IDs.
3. Train heatmaps at visible instance bbox centers (sigma 1.5 heatmap cells),
   offsets in [-0.5,+0.5], and frame presence. Use every `detectable` boat for
   proposals; do not turn distant true boats into background. Exclude instances
   below the teacher's detectability threshold from positive labels and ignore
   their occupied pixels rather than teaching them to be background.
4. Evidence CE uses `BoatView.evidence` at positive cells. Resolved identity CE
   is masked by `identity_supervision_valid` and by the teacher decision's
   0.16-second continuous-view support. Do not expose `truth_class` as resolved
   supervision when evidence is unknown/ambiguous. For overlapping positive
   centers that map to one cell, ignore conflicting identity/evidence targets.
5. Loss = heatmap focal loss + offset smooth-L1 + 0.1 presence BCE + evidence CE
   + resolved-identity CE. Focal alpha=.25, gamma=2; each term normalized by its
   eligible count; an empty identity mask contributes zero, never NaN. Offset
   loss applies only at positive centers. Evidence and identity losses macro-
   average represented classes; log target/similar/dissimilar counts separately.
   Heat negatives exclude ignored cells. No true pose regression on unseen boats.
6. AdamW, lr=0.0003, weight_decay=0.0001, batch=64 frames, max 15 epochs,
   gradient norm cap=1, seed=20261025. Final partial batches are allowed.
   Cache only new frame features with new source/model hashes; no old features.
   Stop on nonfinite losses/gradients. No automatic early success stop.

Teacher owns 100% of fresh collection actions in every split. Record proposed,
bounded and actually sent actions, ownership and interventions, but use **zero
action-imitation loss**: R15 does not execute its old neural action head.
Teacher actions, exact visible ranges and positions may be labels/diagnostics
only. No DAgger intervention is hidden inside this collection or student test.
Teacher failure does not convert a timeout into a successful demonstration;
valid visible perception labels may remain useful and are retained with outcome.

The new student acquisition adapter must decode multiple proposals (top 7
local maxima, 3×3 NMS, proposal probability ≥0.5) and maintain its own tracks
from image bearings/own odometry. Runtime track keys must never be simulator
object IDs. Match angular innovation within the existing 12°+40°/s*dt gate;
ambiguous matches remain unconfirmed rather than inheriting an identity.
Apply the teacher's scan-1/scan-2/inspection ordering to **predicted evidence**,
with evidence probability ≥0.8 continuously for ≥0.16 s. Resolved target or
rejection additionally needs corresponding identity probability ≥0.98 for that
interval. Unsupported proposals stay unknown. These are proposed operating
thresholds; validate them without changing the sealed test.

Approach range for the student comes from calibrated image bearings, own
altitude and the declared static nominal boat plane (0.45 m ENU, uncertainty
0.4 m), never `BoatView.range_m` or position. A horizontal/above-horizon ray or
insufficient geometric support permits camera search, not a fabricated waypoint.
Rejection memory uses the student's tracks and resets uncertainty on ambiguous
association. Lost view stops approach/descent; reacquire only last sensor-based
estimate. Target identity alone cannot authorize descent. New target identity
plus fresh R15 marker registration must gate handoff to unchanged R15 metric
confirmation/control. Feed the selected target's observed pixel as the R15
registration ROI during handoff/reacquisition; do not let an unrelated global
heatmap maximum switch the chosen identity. Preserve the 15-value pose tensor
contract and original fit acceptance rules. Serialize the new module separately (`search.pt`, new
schema/decoder metadata) and retain the original R15 weight hashes.

Select the epoch with lowest validation sum of mean proposal focal loss,
masked evidence CE and masked identity CE; tie chooses earlier epoch. Report
per-weather/distance/density recall, false identity acceptance and acquisition
latency. Validation/test feature caches are separate; test is opened only after
checkpoint, thresholds and manifest hashes are frozen.

## 7. Zero telemetry, physical validity, outcomes and edge guards

* Actor API is `(raw_rgb, allowlisted_observation)` only. Allow own PX4 fields,
  own encoders/issued gimbal commands, image timestamps/validity, previous own
  action, dt and fixed mission timing/static geometry priors. Exclude scenario
  name, random seeds, requested/actual target distance, route, decoy layout,
  selected teacher track, teacher phase, segmentation, annotation IDs, privileged
  labels and all scorer output. Diagnostic display overlays never enter RGB.
* Omit the public beacon field entirely; the student boundary fills missing
  numeric placeholders with valid=False, age_s=3.1, position/velocity zeros,
  sigma_p=100 and sigma_v=10, dock status unknown. Neither teacher nor student
  instantiates a radio link. The teacher's radio_coarse_guidance must always be
  false. Set allow_visual_landing=True using mission authorization, not a fake
  transmitted dock_ready=True. Preserve independent visual masking.
* Boat/dock preparation is an environment invariant: platform/lids open. Teacher
  internally passes dock_ready=True behind its privileged landing gate; that
  private pilot call is not a student radio packet. Own PX4 GNSS/odometry stays
  allowed. A global GPS blackout is not the requested condition.
* RGB and segmentation must share capture state, camera and occlusion, with no
  physics step between them; initialize appended scenery/water IDs correctly.
  Identity masks follow actual evidence/support, not hidden class labels. No
  student access to env, renderer, oracle, scorer or teacher object.
* Initialization/preparation can use simulator truth to place/physically fly the
  start. It must not aim at target, leak setup variables, carry teacher search
  state/boat packets into the task, or expose a target-derived waypoint. Reset
  GRU, all tracks, search state and buffers at task start; preserve only own
  issued previous action. After physical preparation, verify actual horizontal
  range within ±0.75 m and height clearance within ±0.15 m. Re-establish the
  intended start offset through PX4 if the moving boat drifted during takeoff,
  as the benchmark does; reject invalid delivered starts, never teleport.
* Use benchmark `make_scenario` to retain every `Scenario.validate` rule while
  permitting distance ≤100 m and duration ≤240 s. Do not set stress_test just
  to bypass distance validation. The review subclass's 80–90 m envelope is
  unsuitable for the full run. Height=6, speed≤0.6, wave≤0.15, mean wind≤4,
  periods 3/4.5 all satisfy the retained validator.
* Keep 1 kHz physics, 250 Hz sensors, 25 Hz commands and the unchanged boat/drone
  CAD/mass/forces. Record actual boat speed; after 10 s require ≥80% of samples
  within max(0.15 m/s,20% requested) of requested speed. Route completion or
  unsafe placement invalidates a condition. Early task failures still count;
  infrastructure/setup failures are separately reported, never successes.
* The nominal zero-speed target is a free physical boat, not welded in place;
  wind/waves may cause drift. Its actual motion must pass the same check.
  Scene infeasibility or failed condition delivery stops that shard and is
  investigated, not selectively resampled until an actor succeeds.
* Precision success uses original env `landed`: supporting feet/COM and all
  feet inside ±0.28 m; relative horizontal speed <0.1 m/s, vertical <0.05 m/s,
  drone/deck tilt <5°, angular-rate difference <5°/s, stable disarmed support
  ≥2 s. Ordinary PX4 airborne→landed disarm only; do not use the review
  harness's optional truth-based forced disarm. Collision, water strike,
  wrong-boat contact, home/manual fallback and timeout are failed target missions.
* Confirmed acquisition uses accepted metric estimate error ≤0.75 m for ten
  consecutive 25 Hz decisions (benchmark convention 0.4 s), by 120 s, with
  no accepted false acquisition >2 m error and no physical failure. Evaluate
  these against scoring-only truth after each decision. Also report discovery
  and correct-identity times separately so landing does not hide search failure.
* Mission task limit=240 s. Search deadline=120 s is an evaluation cutoff,
  not permission to refresh hidden truth. Keep R15's mission/sensor supervisor,
  static recovery ceiling and bounded fallback semantics. Stale/invalid own
  estimates over 0.25 s arrest translation/yaw; stale/invalid images cannot
  authorize a new metric descent. Interventions are never action labels.
* Negative/occluded/empty views are required naturally within every episode.
  Do not silently delete them or fabricate a second valid target. Camera faults,
  stronger winds/waves, >100 m starts, inland starts, moving decoys and absent
  targets are outside this run, not implied coverage.

On 120 sealed fresh test worlds require ≥108 correct acquisitions by 120 s,
zero false acquisitions/wrong-boat contacts and zero collision/water strikes.
Report Wilson intervals and all strata even if this proposed gate fails.
Compare final student and unchanged R15 on the same 120 frozen worlds without
teacher assistance; no lower strict landing count is allowed. Those additional
student/R15 evaluation flights generate evaluation-only logs and are **not**
additional teacher-training data or part of the 1,200 collection budget.
No claim of hardware qualification or automatic deployment follows this gate.

## 8. Implementation prerequisites and execution order

1. **Fresh collector.** Add a separate entry using the current benchmark's
   scenario/start/backend setup, full RGB `Recorder`, newest teacher and
   matching-frame oracle. Accept this manifest and explicit role; apply decoy
   subsets/yaw variation; strip observation by allowlist; log supervision masks,
   action ownership and source hashes. Use ordinary PX4 disarm only. Never
   flip existing review files' eligibility flags. New role/approval provenance
   must describe this collector and teacher, not the old `run_episode` expert.
2. **Fresh label/cache adapter and trainer.** Implement multi-instance targets,
   sustained identity masks, ignore regions and the separate search module/loss
   above. Existing single-pad pose losses/old dataset assertions cannot be reused
   unchanged. Verify frozen R15 tensors are unchanged after optimizer steps.
3. **Student integration.** Implement sensor-only multi-proposal tracking/search
   and identity-gated handoff. Reusing oracle BoatView objects or teacher action
   commands at inference is forbidden. Keep the benchmark's receipt validation;
   register a new policy, never overwrite its frozen plan/runtime/inventory.
4. **Qualification before collection.** Check actual source/import provenance,
   frame synchronization, decoy counts/collisions, no-radio invariants, hostile
   hidden-state perturbations with fixed student observations, rollout reset,
   data split and ordinary disarm. The first 24 new pilot episodes are included
   in the fixed budget; review them and bind admission to their actual hashes.

Then collect remaining fresh episodes, verify all manifests, train under the
fixed curriculum, freeze validation-selected candidate, and run paired sealed
evaluation. Do not run old `collect.py`/`train_fusion.py` as a substitute. There
is intentionally no fictional collection/training CLI in this document.

The included command is safe and executable **now** and performs no flights:

```powershell
python -B training_runs/long_range_no_radio_20261025/verify_spec.py
```

## 9. Coherence and resource receipt

The verifier checks every pinned path/hash, the selected R15 inventory mapping,
policy/weight schema metadata, current source bounds, actual scenario
validation, exact counts/marginals, all unique seeds/IDs, role separation,
full weather×distance×density coverage, canonical generated manifest bytes,
and the pilot subset. It also checks active class counts from the scene XML.
It does not certify visual scene feasibility or nonexistent collector/trainer
integration. Those remain explicit prerequisites, not successful checks.

At the 7,200,000-frame maximum, RGB alone is **4,976,640,000,000 bytes** before
compression. Reserve **5,971,968,000,000 bytes** (20% headroom), plus labels,
features, models and simulator output. Do not estimate an unmeasured compression
ratio. Stream to bounded shards and archive only new data; provision storage
before collection. Actual episode lengths can reduce storage; do not shorten
the prescribed task budget silently to make it fit.

The existing teacher/smooth-landing unit suite passed 23 tests during this
audit. Base/spatial strict state loads and a no-radio neural forward probe
passed. These checks do not establish long-range flight success. The current
comparison summary was incomplete when inspected; no partial benchmark score
or older success rate is a qualification of this proposed run.
