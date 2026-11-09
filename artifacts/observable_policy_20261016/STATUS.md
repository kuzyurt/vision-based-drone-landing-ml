# Active autonomous work

## COMPLETED AND DELIVERED R8, 2026-10-17 13:27 UTC

Final administrative confirmation13:28UTC: heartbeat finish-radio-free-drone-training
PAUSED through app tool, and explicit goal status COMPLETE through update_goal.
All owned experiment processes stopped naturally; no further work remains.

Defined simulation goal ACHIEVED and all evidence audits passed:
58/60 fresh B boat landings(96.7%),2physical home landings,0collisions/water strikes;
target-absent6/6physical home landings; targeted development4/4boat landings.
All5maps; 4/4inland;60m18/20, all3–40m40/40. Two misses: both directions of
city world10230204 at60m/.9m/s, no reliable acquisition by60s, safe return/disarm.
Do not hide this acquisition weakness or claim hardware/universal reliability.
No tuning on B results. All original data/approvals/checkpoints/revisions preserved.
No additional training-data collection; same c299 pose/new b432 spatial head.

export_qualified_r8.py completed source/input/training/physical audits and package.
VM qualified_delivery_r8_receipt.json status qualified_evidence_audited.
Archive8511817bytes SHA279081760542b61e5d24cd33040ac56ffa69e509a20cde7c76c25169a25c0c4d.
Downloaded here to delivery_r8/qualified_delivery_r8.tar.gz, extracted folder
delivery_r8/qualified_delivery_r8; all76manifest files hash-verified. Transfer15.36s,
including extraction/verification20.34s. Local delivery_r8/download_receipt.json.
Actual onboard RGB10s timelapse qualified_r8_actual_onboard_10s.mp4,2.05MB,
encoded onVM4.81s, downloaded14.31s, hash-verified; video_download_receipt.json.
FINAL_REPORT.md contains measurements, all-map/far/inland breakdown, methods,
failed revision history, missing-radio boundary, unchanged physical criteria and
finite-sample/hardware limitations. Also copied to VM FINAL_REPORT_R8.md.

Work is finished. Disable heartbeat and mark goal complete after final delivery
receipt; do not launch further flights/training on an automatic continuation.
If already disabled/completed, do nothing. User may explicitly request new work.

## Current final B-suite R8, 2026-10-17 12:28 UTC

R8 development4/4boat landed and no-target fallback6/6physical home landed.
Fresh B suite AUTOMATICALLY RUNNING since12:03:49UTC, max8workers. At12:27:38,
18/60 complete, ALL18 boat landed,0otheroutcomes/collisions. Do not change candidate
or evaluated sources, inspect/tune individual holdout outcomes, or duplicate work.
R8 coordinator263811 remains responsible; qualification_r8_state.json latest.
Let suite finish; monitor aggregate only after meaningful waits (~20min).
Goal not yet complete until >=57/60,0collision and audits/export/download/report.
R8 provenance already passed (pre-qualification physics/source hashes recorded).
export_qualified_r8.py ready and requires final qualified state; audits all3cohorts
and candidate/data source hashes, packages candidate/runtime snapshots/reports
including R5 first-suite56/60 history. Preserve all failed revisions, no newcollection.

## Latest stage R8, 2026-10-17 11:53 UTC

R8 targeted development **4/4 BOAT LANDED**, including all4 A-suite failures:
island63.56s, beach87.80s, gravel112.08s, city114.64s. Horizontal-speed correction
resolved the .9m/s fast-boat equilibrium. Dense reverse fitting retained/solved
near-deck lock. No radio, teacher actions or changed physical scoring.
Coordinator263811 now runs target_unavailable_spatial_r8, then automatically
fresh_holdout_spatial_r8 using untouched frozen B60 if6/6 physical home landings.
Initial R8 provenance audit PASSED. Keep immutable R8 source/weights/snapshots.
Only monitor at meaningful intervals, handle actual failures, no unnecessary tests.
R7/R6/R5 entries below are historical. Goal not yet achieved: final B60 not run
as of this status. Audit/export R8 scripts described below must precede completion.

## Latest R8 continuation, 2026-10-17 ~11:42 UTC

R7 development finished7/8landed,1abort (fresh_gravel_04_0). NO B suite run.
Dense reverse fitter DID fix close-plane failure and other7 cases landed.
Remaining case diagnosed from trace: unit3D viewing ray gives horizontal speed
2*sin(view angle). At height5.6m, range2.8m, command~.9m/s equals boat speed. Drone
then follows forever without closing/descending, occasional isolated fits never
confirmed. No radio/truth needed to identify this geometry; exact3D trace verifies.

Separate immutable bundle_spatial_r8 copies R7. New coarse approach computes
approx horizontal range from own altitude + declared static sea/deck plane + RGB
bearing, then controls horizontal speed min(2m/s,range_m), rather than scaling by
unit3D ray. This avoids the far equilibrium. No coarse descent/metric lock bypass;
existing confirmation/landing criteria unchanged. Prior absent -> old conservative
action, qualification supplies explicit priors through own-home mission wrapper.
MissionSafety R8 counts accepted metric fits as established evidence ONLY when
metric_confirmed. Previously sporadic fits kept a stalled unconfirmed approach
alive forever. Keeps prior5s finish memory/3s reserve hysteresis. No physics/model
weight changes; c299 pose / b432 head same, training data untouched.

R8 coordinator PID263811 qualify_r8.py. qualification_r8_state.json/launch/log.
Runs4 targeted A failures concurrently, then6 no-target fallbacks, then60 untouched
B flights only if perfect earlier gates. Max8workers (actual4/6/8 by cohort size).
Separate evaluate_r8.py/mission_safety_r8.py; frozen source manifest per bundle.
Do not edit evaluated sources, duplicate work, or stop at routine results.
Initial audit_provenance_r8.py invoked after launch; inspect result if needed.
B SHA3f425b3827b690fb30f6f3dcb3c3256c0703bb8fee8705c8ecfdb7774c6b3810 unchanged.
Audit/export R8 scripts ready, require4/4+6/6+>=57/60 and0collisions, include prior
R5 first-fresh56/60 history. User wants sustained autonomy and completion only.

## Latest active work: R7, 2026-10-17 ~11:15 UTC

IMPORTANT: R6 normal-refinement hypothesis was DISPROVED on recorded-frame probes.
Do NOT promote or resume R6. It was externally stopped after only a few simulated
seconds. r6_diagnostic_stop.json and all partial RGB/traces remain preserved.
SIGINT let owned workers close their H5/PX4; final native-process check empty;
two orphan idle workers251788/251789 then SIGTERM'd. No other processes touched.
Earlier note calling1.6deg an error was incorrect: that was estimated tilt;
actual error against scoring truth was0.43deg. User was told hypothesis failed.

REAL CLOSE-RANGE CAUSE VERIFIED: reverse registration residual queried only the
same sparse240 edges used for forward fitting. With a large marker, sparse-point
spacing created3.8–4.5px reverse error even at correct pose. Three exact recorded
failed frames: old overall RMS2.53/3.00/2.72; full-border reverse cloud gives
0.443/0.458/0.479px,100% precision/recall,1–2mm relative pose errors vs offline
scoring truth. Forward residual unchanged. dense_reverse_registration_probe.json
preserves comparisons. This is measurement correction, not threshold relaxation.

Separate immutable bundle_spatial_r7 copies R5 (NOT R6). Changes: strong
above-horizon target rejection from R6, native C++ full-border reverse KD tree;
original forward240 samples/solver/RMS2.5/precision/recall and physical scoring
unchanged. No normal-refinement code in R7. Pose c299/head b432 unchanged.
MissionSafety R7 retains5s completion-evidence memory and3s sustained reserve
pressure, fixing one-frame RTH interruption. Separate evaluate_r7.py and
mission_safety_r7.py, canonical per-cohort snapshot names as R6. No R5 sources edited.

R5 first fresh suite FINAL:56/60boat landed,2home_landed,1abort,1timeout,0collision.
A suite explicitly retired before tuning; all cases preserved. Audit R5 first
suite process256537, audit_r5_first_suite.log -> cohort/evidence_audit.json.

R7 coordinator PID256536 qualify_r7.py, qualification_r7_state.json/launch/log.
Runs8 targeted dev (4 A failures +4 controls),6 no-target physical fallback, then
60 untouched B cases only if both gates perfect. Uses8workers based on previous
throughput benchmark and measured8vCPU/32GB memory capacity; target6 naturally6.
Do not duplicate or change frozen R7 sources. New B still untouched at launch;
same condition grid as A,30 NEW worlds; SHA3f425b3827b690fb30f6f3dcb3c3256c0703bb8fee8705c8ecfdb7774c6b3810.
R7 initial provenance audit invoked immediately after launch; inspect its result.
audit_provenance_r7.py / audit_flight_results_r7.py / export_qualified_r7.py ready.
Exporter requires qualified state, audits source/data/scoring, packages models,
operational snapshots, reports AND prior R5 56/60 history. Verify local archive
SHA and download under5min, report finite-sample limits, then disable heartbeat
and mark goal complete ONLY if actual goal met. Continue independently otherwise.

## Current revision, 2026-10-17 11:12 UTC

R5 first fresh suite A missed goal: at least4 nonlandings, all preserved. Do not
promote. holdout_A_retirement_decision.json explicitly retires it to development
BEFORE tuning. Last6 active flights are finishing unchanged; R5 coordinator199251.
At last check57/60 complete:53 boat landed,2 home_landed,1 abort,1 timeout,0collision.

Measured causes (actual saved RGB and exact offline R5 replay, no training):
- island01_1: high-confidence TREETOPS above horizon locked camera; no metric fits.
  Actual montage r5_island_false_target.jpg. R6 rejects above-horizon strong targets
  before locking camera, not only before moving. Existing tentative gate retained.
- city04_0/gravel04_0: one-frame support dip interrupted progressing approach.
  R6 keeps valid completion estimate5s and requires3s continuous reserve pressure.
- beach05_0_inland: full marker visible; fixed learned normal biased~1.6deg made
  close fit RMS2.5–3.4px fail original2.5px gate. Replay2138frames matched ALL metric
  outcomes,44 rejects gate5. r5_close_registration_diagnosis.json, log and montage
  r5_beach_close_loss.jpg. R6 proposes small plane-normal refinements from actual
  RGB, keeps ORIGINAL RMS/precision/recall/conditioning gates and final scoring.
  Accepted normal is propagated as a visual estimate. No new training/collection.

Separate immutable bundle_spatial_r6 built, same c299 pose/b432 spatial weights.
R5 evaluated source files NEVER edited. R6 uses evaluate_r6.py and
mission_safety_r6.py; runner maps them to canonical snapshot filenames
evaluate_development.py/mission_safety.py under each cohort/mission_sources.
Its source freeze bundle_spatial_r6_qualification_sources.json is separate.

R6 coordinator PID251427, qualify_r6.py/log/qualification_r6_state.json. It waits
until R5 cohort AND R5 coordinator finish, then runs8 targeted development cases
(4 A failures after retirement +4 controls spanning5maps), then6 target-absent
physical fallbacks, then independent60 suite B only if both gates perfect.
Fresh B plan frozen BEFORE any R6 policy execution: fresh_holdout_B60.json SHA
3f425b3827b690fb30f6f3dcb3c3256c0703bb8fee8705c8ecfdb7774c6b3810.
Same condition grid/criteria as A/v2,30 independent worlds,4 inland starts,
vertical own-home takeoff, setup feasibility only; freeze_holdout_B.log success.
Never tune on B outcomes then call it fresh. Preserve failed revisions/recordings.

R6 audit/export scripts uploaded: audit_provenance_r6.py,
audit_flight_results_r6.py,export_qualified_r6.py. Run initial provenance audit once
R6 source freeze exists, BEFORE final evidence audit/export compares pre-run
physics hashes. Export only on qualified state, download compact verified archive
under5min, include honest first-suite R5 history as well as new final results.
Goal remains >=57/60 fresh boat landings,0collisions, strict touchdown/disarm,
separate6/6 physical fallback. User asks sustained autonomy, no routine final/stop.

## Current final-suite run, 2026-10-17 10:01 UTC

R5 passed12/12 development and6/6 visually absent-target physical home landings.
Coordinator PID199251 automatically launched fresh_holdout_spatial_r5 at09:39:35UTC.
At10:01UTC13/60 finished:12 boat landed,1 safe home_landed. Remaining47 run on6workers.
This is the untouched frozen60 plan, SHA4130d96a...eeefa6; keep all evaluated
sources unchanged. Do not tune based on these intermediate/final holdout outcomes.
User wants quiet autonomous progress. Read aggregate state after a meaningful wait,
not everyfewminutes. If >3 nonlandings (or any collision) makes qualification
impossible, inspect/stop only this owned cohort safely to avoid unnecessary work,
preserve all partial evidence, retire suite to development before fixing, then
freeze a truly independent replacement. Never suppress failures or claim success.
Otherwise let all60 complete. export_qualified_r5.py only runs after qualifying
state and audits all traces/provenance/snapshots before creating compact delivery.

## Latest measured stage, 2026-10-17 09:34 UTC

R5 extended development finished **12/12 boat landings**, including the rock
touchdown case that failed R4 and every original no-radio failure. No collisions.
R5 coordinator PID199251 remains active. Now target_unavailable_spatial_r5 runs
6 visually absent-target cases on6workers, evaluatorPID207634 (started09:28UTC).
No completed fallback cases yet at09:34. If6/6 physical home landings, coordinator
automatically launches untouched fresh_holdout_spatial_r5 (60cases/6workers).
Do not duplicate flights or edit frozen R5 controller/mission/harness sources.
Healthy progress: sleep, do not poll everyfewminutes. User wants completion only.

export_qualified_r5.py is uploaded but NOT run. Only accepts qualified final state,
audits provenance and all3 cohorts then builds separate qualified_delivery_r5 with
model/source/operational snapshots/frozen plans/reports/training provenance and
tar.gz+receipt. Audit compares pre-qualification physics/source hashes. Final
must verify download archive SHA and download compact artifacts to this Windows
workspace (<5min timeout), disable heartbeat and mark goal complete only when
actually achieved. If final outcome fails goal, inspect traces, retire that suite
to development before any tuning, freeze independent replacement suite.

## Current continuation, 2026-10-17 09:14 UTC

R4 extended development finished11/12 boat landings. All three former R3 failures
now landed, including city partial-edge target and both wrapper-interrupted
approaches. Rock14_0 physically touched the pad, then aborted: after .5s without
registration, outer policy stopped providing visual boat velocity and substituted
network relative velocity. This exceeded the touchdown commit's speed gate and
cancelled contact. Independent physical touchdown/disarm scoring was not weakened.
No target-absent or final60 flights were launched because the development gate held.

Verified no active training/evaluation before the new build. Separate immutable
bundle_spatial_r5 retains pose/head and all R4 code except bounded touchdown commit:
store last accepted visual world pad/motion at existing strict commit entry;
continue up to original8s using own odometry, bounded XY correction; retain original
speed/attitude bounds and add XY drift/height/telemetry cancellation. Never force
PX4 disarm. Native physical boat scoring unchanged. No new data collection/training.

R5 coordinator PID199251 (qualify_r5.py), qualification_r5_launch.json/log,
qualification_r5_state.json and global qualification_state.json. Runs extended12
then6 no-target fallback cases then untouched fresh60, only on perfect earlier
gates. Do not duplicate active work or edit frozen evaluated sources. Per-bundle
operational freeze bundle_spatial_r5_qualification_sources.json. Root harness and
mission helpers unchanged from R4. R4 final state copied before global update.
Use audit_provenance_r5.py and audit_flight_results_r5.py for final evidence checks.
Original final suite has NOT been run, still SHA4130d96a...eeefa6 below.

The old23:01UTC/R3/R1 entries below are historical. User authorizes continuing
autonomously until the goal or genuinely necessary human verification; no old
time deadline. Keep heartbeat prompt pointing STATUS rather than stale PIDs.

## Latest state, 2026-10-16 22:55 UTC

Update23:01UTC: R4 coordinator PID148495 running qualify_r4.py. R4 builds a new
immutable bundle_spatial_r4 with same pose/spatial weights; bounded camera-only
attention for moderate below-horizon partial detections, no translation on
tentative detections. Mission manager now tolerates brief metric gaps during
established visual tracking and plans estimated visual completion before return.
R3 root harness/mission/state copied to *.preserved_r3; per-cohort R3 snapshots
untouched. R4 operational source freeze bundle_spatial_r4_qualification_sources.json.
R4 pipeline runs extended12, then6 physically scored target-absent fallbacks,
then untouched fresh60 only if both gates perfect. Read qualification_r4_state.json
and active processes before any mutation. Don't duplicate running work. Don't
edit frozen R4 sources during qualification. provenance_audit_r4.json verifies
35 candidate source files, original pose/head hashes,1220 training/validation
sources,610 training worlds and zero overlap with30 final-suite worlds.
No new bulk collection. All epoch checkpoints retained.

All flights/coordinators are stopped, checked via SSH. The original R1 notes below
are historical. Active target remains >=57/60 fresh no-radio boat landings and
separate physical safe-home fallback. No final holdout has run.

R2b landed both beach15_1 and gravel15_0. Spatial acquisition head trained only on
existing approved training/validation RGB (54,657/9,235 frames), selected epoch9;
head SHA b432c1584b778d1959e950e855fcdf78c468d7f5ec7e86b71641f5052a6ce14b.
Original pose c299 unchanged. All epochs, original data and failed bundles kept.
R3 initial development landed beach15_1, gravel15_0, city14_1. Far gravel14_1
landed with full budget (initial diagnostic stopped it at60s, not policy failure).
Physical no-target fallback v2 home_landed at60.8s with ordinary PX4 disarm and
strict independent support/stability scoring.

Extended R3 development completed 12:9 boat landed,1 home_landed,1 timeout,1 abort.
Do not promote it. qualification_state.json says needs_iteration. Exact failures:
- city15_0: partial boat at image top/edge; head peaked .667 but .8 threshold
  missed it. A .711 false building detection points above horizon. Need tentative
  camera-only attention below horizon, without translational authorization.
- gravel14_1: return_time_reserve incorrectly interrupted align at65.4s after
  only.6s registration gap despite strong visual evidence. Same bundle without
  safety wrapper landed. Fix mission evidence continuity and completion planning.
- dev_far60_water: descent interrupted by search_timeout at73.68s, ~.35m above
  pad, only.6s registration gap; mission wrapper confused brief recover with an
  exhausted search. Need separate acquisition timeout from established tracking.
  It then spent too long retracing high breadcrumbs, not a boat-control failure.

No current process should be duplicated. Next build separate R4 preserving R3;
correct these measured issues, then qualify necessary development/fallback gates
before untouched fresh60. Existing final plan fresh_holdout_60_v2.json SHA
4130d96a444ae6ea9807a9f05c2ffec329eaed2a10b8cc3a13c5c24b86eeefa6.
Physical home below airborne start, vertical PX4 takeoff; four inland starts.
R3 operational snapshots and source hashes in each cohort/mission_sources.
Future revisions must freeze their own operational source manifest.

Goal in GOAL.md and the active Codex goal is not yet achieved. User says to
continue independently until achieved or necessary human verification is pending.

VM root: `/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/observable_policy_20261016T203932Z`.
Verified identity: `hxhshsh7gyg` / `drone-test2-20261015-183521`.
SSH IP34.87.180.165, C:/Users/gamee/.ssh/id_ed25519, BatchMode=yes,
StrictHostKeyChecking=yes, IdentitiesOnly=yes. Never display private keys.

R1 bundle: `bundle_view_r1`, same c299 pose checkpoint and existing v4 acquisition
head, no new training. Code and control changes documented in candidate_r1.json
and bundle policy.json. Parent bundles and original recordings stay untouched.

Initial development launch PID127861 failed before flight because instance260
exceeded MAVLink's uint8 system ID. Preserved `development_r1` artifacts show
zero frames and infrastructure errors; not policy outcomes.

Corrected launch PID128199, log `development_r1_retry.log`, coordinator
`evaluate_development.py --cohort development_r1_retry`, four workers on instances
160–163. Inspect active processes and pipeline_state.json before launching anything.
Cases: nearby gravel15_0 (actual RGB recorded), successful beach15_1, city14_1,
far gravel14_1. Native PX4, no boat radio, expert solely standard airborne setup.
Development early stop after60s if no fit or last fit>20s old; other flights retain
180s budget and strict physical termination. These stops are not full-budget rates.

Preflight:200 actual-RGB recorded observations replayed without nonfinite/actions
outside contract; verified runtime imported from the new bundle. This is not flight
success validation.

R1 acquisition uses capture-time visual bearing, own-yaw turn into pan0/pi clear
camera sectors, counter-pan, persistence/innovation check, bounded0.28s loss memory,
and yaw-based scanning. Metric track uses own odometry with visual boat velocity
when ready; three fits confirm lock, coast trust0.6s. Final touchdown unchanged.

Next: inspect results/traces and fix actual failures. Do not train on development
flight RGB or old held-out test images. New 60-case holdout is being frozen by
freeze_holdout.py without policy execution; four inland setup checks only.
Keep that suite untouched until development is strong. If outcomes are inspected
then tuned, declare it development and freeze a new final suite.

Safe fallback still needs implementation/validation with public own-home mission
information. Existing environment has a physical launch pad at declared static
location; capture own PX4 position on that pad before takeoff as home reference.
Avoid hidden boat input. Boat touchdown criteria stay unchanged; home fallback
must be separately scored physical contact/disarm, not counted as a boat landing.
Native PX4 sends simulated battery status but observation lacks battery telemetry;
do not claim genuine battery-reserve control until added/verified. A time-budget
fallback is permissible if honestly labelled.

Heartbeat `finish-radio-free-drone-training` reactivated every30min with current
goal/root and quiet-progress instructions. Old18:45UTC deadline belonged to the
completed previous experiment; user now authorizes continuing this new goal.
Never stop at routine intermediate results. User must review necessary new expert
previews before new bulk collection. Render on VM only; avoid long videos/tests.
