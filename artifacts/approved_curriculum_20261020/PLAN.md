# Approved curriculum, correction masks, training and verified local export

Human authorization: 20 October 2026 around 00:33 Europe/Berlin. V31 expert
demonstrations approved, subject to task-purpose corrections. User clarified:
the target must remain normally present in the world, initially OUTSIDE the
camera FOV in search tasks. Never hide/remove/black out the target to manufacture
search. Some searches must start farther away. Verify every scenario's purpose.
No new return_home/land_home rendering or training. Prior rejected recordings and
checkpoints remain quarantined; this approval is not a release of that history.

User-supplied remaining VM life: 17 hours from the request. Conservative planning
deadline 20 October 2026 15:33 UTC / 17:33 Europe/Berlin. No purchased extension.
Plan selected checkpoints and resume packages locally well before the last hour.

## Measured basis and allocation

Original manifest verified: 1,200 episodes (960 training,120 validation,120 test).
Metadata-only twelve-training-episode probe decoded 12,065 rows in 3.99 seconds;
this is NOT a validated-mask or RGB decode throughput measurement. Original test
images were not read. Do not rerender 1,200 episodes. Create versioned derivative
per-head masks, preserve sequence history and original split membership. Mask
home/return, invalid labels, disturbances as positive actions, and problem-causing
camera actions. Do not infer that disturbed images have invalid perception labels.
Legacy zero action placeholders must never supply expert actions. The deployed
hybrid trains visual components; explicit control fixes are code, not neural action
imitation. Do not train an obsolete action policy merely to call it retraining.

Last complete annotated native eight-worker batch:20,027 recorded camera rows /
2,310.12 wall seconds =8.669 rows/s, including startup and the long absent-target
flight. User's47fps is not demonstrated for this full workload. Keep8workers with
4GiB RAM/1GiB VRAM reserves; no further worker-count sweep. Omit overview videos
during collection; retain actual onboard RGB, exact capture labels and commands.

Target64 new useful curriculum episodes:48training/16validation, disjoint worlds.
First eight purpose pilots may count only if all applicable admission checks pass;
failed/precondition-mismatched attempts do not count as useful delivered episodes.
Hard collection time allocation5hours; reduce quantity if longer far-search/recovery
episodes consume the budget. Never blindly increase epochs or episode counts.

| Work | Allocation |
|---|---:|
| Purpose corrections, initial actual-camera gates, masks/source checks | 1–2h |
| Existing data mask derivation/validation, no rerender (overlap collection) | 0.5–2h |
| Target64 new episodes, 8workers | 4–5h |
| Applicable vision fine-tuning, cache and validation | 1–2h |
| Freeze candidate;18paired native scenarios (36test flights), bounded external Tidewater tests | 3–4h |
| Final export/report plus repair reserve | 2h |

Stages overlap; expected total12–15h,17h upper work limit. Estimates are conditional
on actual semantic/physical readiness, not a reliability claim. No new model training
started at plan creation. Full cold-static recognition failure remains in evidence.

## Task-purpose matrix

E01 nominal calm approach:actual stable approach/alignment/physical touchdown.
E02 distractors/glare:actual wrong-object views and correct target landing, no
copied-cross wrong-object metric/descent. Initial visibility separately declared.
E03 camera yaw:actual injected pan and encoder/image response,resynchronization;
do not require/claim loss when rotation merely preserves the marker in view.
E04 close-loss:actual metric loss,arrested descent,clearance-gated recovery and
reacquisition. E04a is the SAME flight detail.
E05 visible-start regression:first actual valid image includes target; retain and
investigate the opportunity rather than discard it for an unnecessary full scan.
E06 search:target physically present but no target pixels in first delivered RGB,
later discovered after useful actual camera bearing movement;5–20m actual start.
E07 search:the same initial-FOV/discovery checks at20–40m actual start.
E08 search:the same checks at40–60m actual start; do not assume identity is
recognizable at any universal distance just because pixels are present.
E09 terminal:physical supported touchdown/disarm,no unnecessary post-contact takeover.
E10/E11 learner-to-expert rescue:actual learner-owned struggle,latched subsequent
expert commands and valid recovery; already-progressing independent learner
recovery or expert-only flights never count as a learner rescue. Verify active
and expired-memory paths. Missing coverage stays missing and does not pass admission.
E12 old absent-target/home case:EXCLUDED from new collection/training/rendering.
Prolonged search with a present target is covered by E06–E08. Preserve historical
E12 evidence without generating another return/home video.

Native home/emergency mechanisms remain available for simulator cleanup/safety,
but collection cancels on the first fallback decision with a zero hold, before a
home-return command executes. Mark failure,exclude that stop row,never report it
as a target landing. No boat-radio/hidden truth/task oracle enters the controller.

## Gates and progression

New producer is a derivative of immutable reviewed V31,with identical actor and
weights. It adds observer-only first-frame/range gates,actual camera bearing trace,
and cancel-before-home. RawH5 remains ineligible; a separate explicit approved
derivative admission is required. Scoped new gates must not disable the old
TRAINING_QUARANTINE_20261019 guard or reuse rejected checkpoints/retired tests.

1. Eight bounded development pilots:visible,near/mid/far search,distractors,yaw,
   tilt-loss,and learner struggle. All target geometry remains present and unchanged.
2. Inspect actual receipts,RGB,exact capture joins,executed ownership/commands,
   physical events and task-purpose assertions. Known oldE06 first-frame6131target
   pixels must fail the new search checker. No bulk queue until the relevant gates pass.
3. Before five-map bulk collection verify actual map/model/world consistency:
   V31's fixed basic/hard cache is ONLY known development scenery. Do not pretend
   Scenario.kind changes a frozen cached model into a different physical map.
   Build/reuse matching cached scenes per planned world and retain physics hashes.
4. Admit explicit valid perception derivatives,derive original masks,freeze world
   splits and seed inventory. Training/validation only;no retired or heldout imagery.
5. Train separate visual candidates mixing corrected original and new data. Require
   validation improvement and no false-object regression. Save best/latest atomically
   in this experiment under model_training or candidate_exports,with code/config/
   optimizer/RNG/provenance. Independent local backup watcher collects these files.
6. Freeze model/controller before independent native paired tests. Tidewater is
   EXTERNAL transfer only,no training or model selection from game examples. If a
   heldout suite fails,retire it BEFORE tuning and don't call reused worlds fresh.
7. Export final and last-resumable model even if qualification fails; keep experiment
   labels honest. Do not install/promote an unsupported candidate into production.

## Local backup already in effect

Independent Windows hidden Python watcher PID recorded in backup_watcher.pid,
checks every300seconds until15:30UTC. First97-file baseline/repaired-source package
verified locally,11.4MB,download+verification9.734s. Every changed stable best/latest
policy snapshot gets an immutable ZIP plus SHA/size/member verification and local
receipt. Endpoint:policy_backups/LATEST_VERIFIED.json. Training completions should
also trigger backup_watcher.py --once immediately. Laptop must remain powered and
online for local copying. Do not rely on the last scheduled minute before VM expiry.

Heartbeat every30min:read STATUS and this plan,latest process/state first,do not
duplicate jobs. Continue independently;notify only material results/failures or final
delivery. Delete heartbeat after final report/deadline,keep verified local archives.
