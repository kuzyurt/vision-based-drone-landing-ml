# Radio-free robustness iteration, 16 October 2026

## Latest update, 18:31 UTC: final bounded iteration and delivery

User wants only the final completion message. V3 finished **2/4** hard development
flights: both gravel cases landed; both city cases aborted before any metric acquisition.
Its conditional 14-flight follow-up correctly did not run.

Verified further: `pad_visibility` performs occlusion ray tests against real boat/drone
geometry. The acquisition target had meant "marker visible," although acquiring the
boat requires continued tracking when its landing marker is occluded. This is a plausible
remaining city acquisition weakness; do not claim it is fully solved.

Last revision **V4** trains the same image-only acquisition head to also recognize visible
boat structure. It reuses existing training/validation caches and RGB only for relabeling
some negative, in-image teacher projections: require actual cyan paint and white hull
near the projected boat. The teacher projection stays strictly in training labels;
runtime does not receive truth or a segmentation mask. No test images were used.
`train_boat_acquisition.py` finished in about a minute; original targets were not changed.

`candidate_bundle_v4` is now running **four final flights**: the two previous city
development failures and two independently seeded city scenes. No further training
or flight expansion is queued. State `v4_state.json`; coordinator `advance_v4.py` PID115714;
flight receipt `evaluation_v4_final.log.process.json`; log `evaluation_v4_final.log`.
This is the last iteration inside the approximate 18:45 UTC budget. Even 4/4 would be
limited targeted evidence, not broad reliability qualification.

**Automatic report/delivery coordinator is already running**: `finish_delivery.py`,
PID117525, waits for V4 final flights, then writes `final_results.json`, `RESULTS.md`,
`delivery.tar.gz`, `delivery_result.json`. It preserves broadly tested baseline and last
experimental bundle separately, full compact reports, source, checksums and explicit
goal-unmet limitations. Do NOT duplicate it. If it errors, inspect `finish_delivery.log`
and repair reporting only. No more expensive flight tests are needed within this budget.

Next heartbeat: inspect V4/reporting process and final results. Once delivery is ready,
download `delivery.tar.gz`, `delivery_result.json`, `RESULTS.md`, and `final_results.json`
into local artifacts/domain_training_20261016; verify archive SHA256 and extract locally
using the native Windows tar/Python (safe known generated archive). Report concise real
results to the user and link the local RESULTS.md / archive. **Stop the heartbeat.**
Be explicit that the broad reliable-no-radio goal remains unmet: reference got 10/10
existing regressions but 15/20 (75%) fresh varied scenes. Do not combine percentages
across different revisions. Include the final V4 small-cohort results without promotion
or guarantees. All 160 demonstrations, original 1,200 records, approvals and epoch
checkpoints remain preserved on the VM.

## Latest update, 17:52 UTC: image-only acquisition head

User explicitly said to continue independently and notify **once finished**. The
heartbeat prompt was updated to avoid routine progress notifications.

First candidate is fully evaluated: **10/10 regression**, **15/20 fresh varied scenes**,
five aborts, no infrastructure errors. V2's four *different, harder validation-seed*
development scenarios all aborted; this does not establish a direct regression versus
the first candidate because it never flew these four cases. All data and revisions remain.
The conditional V2 follow-up correctly did not launch.

Diagnosis now verified at pixel level: learned recurrent pixel centre can be 80+ pixels
from the actual visible boat, and can remain confident after target loss. The neural
pose loss heavily weights near-deck samples, where the boat is usually centred, and
the recurrent prediction can remain locked to that framing. This motivates a separate
image-only head trained on balanced off-centre/negative views from the SAME existing
training features, with validation-only selection. No test image enters this training.

**Correction to the previous altitude interpretation:** inspected true drone altitude,
PX4 altitude and `vertical_clearance_m`: altitude remained stable in the gravel failure.
`clearance_m` measures distance to an infinite *tilted deck plane*, which can become
negative at 150 m horizontal separation without the drone touching water. Thus the
earlier negative-clearance observation is NOT evidence of water penetration or actual
altitude drift. V2's bounded own-altitude stabilization is retained but is not a proven
failure cause or claimed fix.

`train_acquisition.py` completed quickly (about 20 seconds in its training timing;
preserved provenance/history). It trains a 1728→256→128→3 image-only MLP on shared
frozen RGB spatial features, with no telemetry or recurrent state. Stratified existing
training samples emphasize negative and off-centre views. On 57,009 selected validation
frames: pixel RMS 8.73 px, off-centre RMS 16.42 px, false positives at probability .8
2.28%, recall 98.05%. These are offline metrics, not landing reliability.

**V3 now active**: `advance_v3.py`, PID113268, waits for acquisition training, exports
`candidate_bundle_v3` (same main pose weights, separate `acquisition.pt`), runs the same
four hard validation-seed development flights, and ONLY on 4/4 landings runs 14 follow-up
flights (four known failures, two 60 m regressions, eight fresh worlds). Its primary state
is `v3_state.json`; logs `advance_v3.log`, `evaluation_v3_development.log`,
`evaluation_v3_followup.log`. Process receipts end `.log.process.json`.

V3 shares the image encoder once per image. It overrides only acquisition visibility
and pixel location while metric tracking is absent/stale; the existing recurrent pose
model and close landing controller remain active after continuous metric lock. It
retains V2's verified timing/odometry math changes and horizon-inclusive search. Treat
the result as a hybrid learned image/pose perception, geometric visual registration and
PX4 controller. Test results must be reported separately by revision/cohort.

Next heartbeat: inspect `v3_state.json` and processes first; do not duplicate or restart
successful stages. Approximate end budget 18:45 UTC (20:45 Berlin). If V3 fails, inspect
the actual traces and use remaining time for a focused fix, otherwise preserve the
best verified first candidate and report that robust reliability remains unmet. On
completion, consolidate/download compact reports and the selected bundle to local
artifacts, write RESULTS.md with explicit limitations and stop the heartbeat.

## Update at 17:20–17:40 UTC: targeted controller revision

The 160 demonstrations and all 16 training epochs completed. Best epoch 14, compact
checkpoint SHA256 `c2990e69e254cbeddde8dd57d4cf481a2c7daa37735cd96083c7f3095512f5f7`.
Original candidate completed **10/10 no-radio regression landings**. Its fresh 20-scene
evaluation is still running; first eight results were five landings and three mission
timeouts, with another gravel case stuck in search. Do not claim broad reliability.

Traces establish: approaches reach 5–10 m from the boat, then lose continuous metric
registration and waste time searching. City traces accept only 2–3 intermittent metric
fits before losing the boat, sometimes subsequently following a false visual positive.
A gravel case never acquired the distant boat, and clearance decayed from 3 m to below
water during search. Existing camera search excluded the horizon, and bearing servo
used delivery-time camera attitude despite delayed images. Track propagation used a
learned relative velocity before visual boat velocity was established.

Preserved `candidate_bundle`; created **`candidate_bundle_v2`**, with exactly the same
trained weights, via `revise_acquisition.py`. Changes: propagate accepted metric track
with own GPS/velocity and visual boat velocity (stationary boat assumption only for
individual prediction steps before motion is known); transform image bearings using
capture-time attitude; sweep 0/25/50/75 degrees; slow approach for downward bearings;
stabilize initial own measured altitude during search. No hidden boat position, no new
NN training on test images, no change to final touchdown requirements. Diagnostics now
include the learned pixel centre. Ten recorded validation frames loaded successfully.

Four targeted development flights with **validation seeds**, perturbed to 50 m starts
and gusty wind, run under `evaluation_v2_development` (PID108225). They cover city and
gravel in both directions; they are not a claimed held-out reliability sample.

`advance_v2.py` is detached and waits for these four development results. Only if all
four land does it automatically start `evaluate_v2_followup.py`: four original failure
regressions, the two original 60 m water/inland regressions, and **eight newly seeded
held-out worlds** covering all five maps. Cohorts are reported separately. This is
necessary targeted follow-up, not another training run. Its state is `v2_state.json`;
receipts are `advance_v2_launch.json` and `evaluation_v2_followup_launch.json`.

On the next heartbeat inspect **both original pipeline state and v2_state.json** and
active processes. Do not duplicate either. If development fails, the advance script
stops with needs_model_iteration so inspect the actual failed trace. If it passes,
follow-up runs automatically. Budget ends around 18:45 UTC (20:45 Berlin). Preserve
all prior candidates and results. Original `pipeline_state.json` may say needs_model_iteration
after its first candidate finishes; this must not hide the active independent v2 work.

Remote experiment:
`/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/domain_training_20261016T134939Z`

Connect as `hxhshsh7gyg@34.87.180.165`, with the existing Windows SSH identity,
BatchMode, IdentitiesOnly, and strict host checking. Identity was verified.
Never display private key material. Rendering and training remain on the VM.

## Running work

- Collection PID 28853: 160 additional episodes, 8 workers, native PX4, 640×360 RGB.
- Feature extraction PID 35785: encodes completed training/validation episodes concurrently; excludes test images.
- Coordinator PID 40469: advances collection → features → training → export → closed-loop evaluation automatically.
- Quiet follow-up automation: `finish-radio-free-drone-training`, every 30 minutes in this chat. Disable once reporting is finished.
- Last observed: 19 completed demonstrations, all landed. This is teacher collection, not learner evaluation.
- Current collection projection: approximately 2–2.3 hours from collection launch. Whole task budget is 4–5 hours from approximately 13:45 UTC.

Inspect `pipeline_state.json` first. Do not start duplicate jobs. Logs are `collection.log`,
`features.log`, `pipeline.log`; subsequent stages write `training.log`,
`evaluation_regression.log`, and `evaluation_heldout.log`.

## Measured optimization

20-second measured batches, with 16 PX4 workers prepared once and subsets activated:

| Active workers | Aggregate recorded frames/s |
|---|---:|
| 4 | 32.2833 |
| 8 | 47.2628 |
| 12 | 46.7114 |
| 16 | 46.19 |

Eight workers won. This is actual onboard RGB, recording and simulation throughput,
not display FPS. The physics optimization moved equivalent FP64 wave/cross arithmetic
into native code and skips rotor contact iteration only when no rotor contacts exist.
The brief 300-step equivalence check had maximum qpos error 1.08e-18 and qvel error
8.90e-16; measured speedup 1.406×. Physics step, forces and contacts remain intact.

The existing Tidewater registration kernel was bound natively for policy execution.
Four recorded-frame comparisons matched reference positions within 2.86e-9 m and
ran about 6–9× faster. `runtime_equivalence.json` records this limited check.

## Data and training

Five maps, independent world/path seeds, 120 training / 20 validation / 20 test episodes.
Water colour and the existing ripple pattern, procedural cloud/mountain skybox, light,
brightness/contrast, blur, camera delay, initial camera orientation, moving boats,
wind, waves up to 5 cm, and 2.5–60 m starting distances vary. `haze_distance_m` is
sampled metadata only; fog has not been implemented or claimed.

Search demonstrations precede privileged expert recovery. The recorded student
observation contains an explicitly absent/invalid radio packet with unknown dock
status. Privileged simulator truth is used only for teacher control and pose labels.
This experiment trains pose perception; recorded teacher action fields retained for
cache compatibility do not become action-imitation targets or previous-action inputs.

Original 1,200-episode data, its approvals, all checkpoints and raw recordings remain
unchanged. New collection uses the user's explicit current-session authorization,
recorded in `authorization.json`, without pretending that old video approval covers it.

Continue parent checkpoint SHA256:
`20709cee9c6ac66e15614e1162a7180aa0efb5f126996473c227484406df2749`.
Fine-tune recurrent/pose branches with frozen image encoder and action head, mixing
original features and new episodes (new training episodes weighted 3×), with 75%
missing / 15% degraded / 10% clean episode-level radio augmentation. New recordings
themselves have no positional radio, so clean/noisy modes retain their true absence.
Unknown dock status is neutralized to the training mean, matching runtime behavior.
Select using missing-radio validation only; never use test data for training or selection.
Maximum 16 epochs with early stopping and a time guard. Preserve every epoch.

One in-memory update on original plus new cache data passed; no source checkpoint
was modified. The established cache loader also expects actions/valid arrays, although
pose training does not consume them. `feature_compatibility.py` adds the actual recorded
arrays to new caches after feature extraction finishes and updates their manifest hashes;
the original cache manifest is saved before this compatibility upgrade. No raw recording
or original cached feature is changed. This is already invoked by `fine_tune.py`.

## Candidate and evaluation

Export to a separate `candidate_bundle`; retain the parent working bundle unchanged.
Keep the honest system description: learned perception + metric visual registration +
explicit velocity/yaw/camera control + native PX4. This is not end-to-end neural action
control and not RL.

Intentional controller changes are separate from equivalent math acceleration:
wait for visual motion evidence before initial heading decisions; allow conservative
coarse descent above 2.5 m when pose/speed/heading permit; retain brief RGB bearing
memory during reacquisition. Original close alignment and stable physical touchdown
requirements remain intact. Mission budget follows the actual 180-second flight budget.

Evaluate 10 previously used regression conditions (including two 60 m beach water/inland
starts), then all 20 fresh test worlds with varied rendering. Four simultaneous policy
workers, fresh process per flight, no rendered videos, no RGB recording. Standard expert
airborne preparation happens before the policy task; task control is entirely the candidate
and radio input is completely removed. Truth appears only in scoring/audit traces.

`pipeline_result.json` will distinguish observed sample target from broader reliability.
Provisional target is ≥9/10 regression and ≥19/20 fresh test landings, no collision/crash,
no infrastructure errors. Even meeting this sample target does not establish a near-zero
failure rate. If results fail, inspect traces and iterate on actual causes within the budget.
Do not train on held-out test episodes. Preserve failed candidates and evaluation traces.

The coordinator stops with `needs_model_iteration` or `needs_attention` for honest
follow-up if needed. It currently runs in memory: editing pipeline.py now only affects
future restarts. If resuming a failed stage, skip completed artifacts and preserve existing
directories; its initial main implementation does not automatically skip existing stages.

## Existing repository state

Original repository remains on its existing branch with intentional untracked source;
do not reset it. Isolated worktree is
`/home/hxhshsh7gyg/vision-based-drone-landing-radio-robust-20261015`, branch
`codex/radio-free-20261016`, base commit `2ca3759`. This experiment's source lives in
its separate output directory and locally here. Unrelated Windows Tidewater user changes
must remain untouched.
