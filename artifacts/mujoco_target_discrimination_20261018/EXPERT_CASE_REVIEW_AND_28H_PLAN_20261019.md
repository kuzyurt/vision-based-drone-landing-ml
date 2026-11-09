# Expert demonstration review: E01–E12 and the remaining VM budget

19 October 2026. This report records the user's review, checks it against saved traces and audits, and specifies the next changes. It does not claim those changes have been implemented or qualified.

**Decision: preserve the existing recordings, use selective supervision masks, and collect a small set of corrected demonstrations after repairing the expert. Do not regenerate the entire historical dataset, fine-tune indiscriminately on the buggy behavior, or re-render disconnected camera frames.** The 59 new experimental recordings and their derivatives/checkpoints remain quarantined. This report does not release them.

## What the training actually consumes

The historical dataset contains 1,200 expert episodes; the user's concern is that the descent-camera problem may affect many of them. The affected count and usable fraction have not yet been measured. It would be incorrect to mark every historical frame defective or assume every action label can be salvaged.

The current deployed system is hybrid: learned vision, calibrated geometry, explicit search/alignment/recovery control and PX4. Its current alignment oscillation is not being learned from new teacher action vectors; those commands come from explicit control. The most recent experimental fine-tuning trained the RGB verifier, not a neural flight-action policy. The original sequence-action trainer still exists, but is not the deployed runtime.

This distinction changes the repair:

- Fix camera synchronization, approach damping and unnecessary alignment delay in the controller itself.
- For any action-supervised training, mask invalid or problem-causing commands rather than imitate them.
- For perception training, a disturbed image can remain valuable if its capture-time identity/pose labels are valid and observable. A bad command does not automatically make its image label bad.
- Keep truthful disturbed observations and the commands actually executed in sequence history. Excluding their action loss must not pretend that those moments never happened.
- The legacy new-review expert-action field contains zero placeholders. It must never be mistaken for the observable teacher's proposed command.

## E01 — Basic search, approach and touchdown

**Problem.** The user accepts the overall maneuver but reports excessive wobble during `target_align` and an unnecessarily long near-touchdown wait. The recording physically landed in 55.20 seconds. Its 1,091 alignment rows amount to about 43.64 seconds at 25 decisions/s; that is total alignment/descent time, not a measured 43.64-second stationary wait.

**Required behavior.** Settle lateral position and relative velocity with small, damped corrections. Maintain a continuous camera orientation while descending, compensating for aircraft rotation without chasing an unstable azimuth near straight-down viewing. Begin or continue descent when the existing geometry, relative-motion and visibility conditions are satisfied. Any extended hold must have a recorded reason.

**Data treatment.** Exclude unnecessary oscillation-driving commands and unexplained holds from action targets. Retain valid observations and genuine corrections. Add separately labeled disturbance-and-realignment examples rather than putting deliberate wobble into the nominal landing demonstration.

**Additional notes.** Measure camera motion separately from drone lateral motion: an image can rotate while the marker center remains almost stationary. The saved V25 diagnostic, from a different flight, already confirms that this class of problem is real: roughly 194 degrees of camera pan change with almost unchanged body yaw near nadir. It does not establish the exact cause or magnitude in E01. Do not remove required physical support, contact confirmation or disarm waiting to make a video appear faster.

## E02 — Hard distractors and landing

**Problem.** The overall maneuver and final alignment look better to the user, but the same excessive alignment wobble remains. The expert landed in 70.56 seconds; 929 alignment rows represent about 37.16 seconds, including descent.

**Required behavior.** Preserve the useful distractor handling and terminal behavior while applying the same continuous camera orientation and damped alignment as E01.

**Data treatment.** Evaluate good and bad intervals independently. Do not accept the entire episode merely because the landing succeeded, and do not discard valid identity/perception labels solely because a later control interval wobbles.

**Additional notes.** E02 is a useful comparison for E01's final descent. It is not proof that all unknown-boat inspection, glare rejection or copied-cross rejection cases are solved. Compare physical states and gate reasons, not just total video duration.

## E03 — Yaw disturbance and resynchronization

**Problem.** Deliberately injected camera motion is mixed visually with ordinary teacher control. The user correctly requires correction examples without teaching the actions that caused the disturbance.

**Required behavior.** Following the disturbance, recover the established camera reference smoothly and resume stable alignment. A deliberate disturbance must never appear as normal nominal alignment.

**Data treatment.** The saved audit records 30 actual camera-fault frames. Their injected commands receive no expert action loss. Keep the resulting observations as context and train only valid subsequent expert corrections. If a shadow expert command is used during a disturbance, it must be separately recorded, observation-supported and validated; the executed disturbance command is not that label.

**Additional notes.** The disturbance did not actually cause metric target loss in this run. E03 demonstrates yaw resynchronization, not target-loss recovery or a rescue from a failed learner. Ordinary wobble outside the disturbance interval still requires repair.

## E04 — Near-deck marker loss, climb and reacquisition

**Problem.** The recovery idea is acceptable to the user, but the ordinary alignment behavior still has E01's wobble/delay defects.

**Required behavior.** Arrest unsupported descent after marker loss, preserve bounded target identity, inspect below, and climb only with valid clearance authorization. Reacquire usable geometry before descending again. Return to the same continuous camera-reference convention after recovery.

**Data treatment.** Exclude the 40 injected tilt-command frames from expert action targets. Keep verified recovery commands and correctly labeled disturbed views. Separate recovery intervals from nominal descent so repeated recovery footage does not dominate normal alignment training.

**Additional notes.** This flight genuinely lost the metric target and recovered: 154 metric-missing rows, 151 recovery-active rows, and approximately 2.21 m of height gain in the audited recovery window; it later physically landed. That useful recovery does not approve every alignment command. It was expert-only disturbance recovery, not a learner rescued by a separate expert.

## E04a — Normal-speed detail of E04

**Problem.** Same alignment concerns as E04; the slower presentation makes the behavior easier to judge.

**Required behavior.** Identical to E04. Review small corrections and camera continuity at normal simulation speed.

**Data treatment.** E04a is a second export of the same source episode, not another training episode. Deduplicate by source capture identity and keep both exports in the same split. Do not count them as two independent recoveries.

**Additional notes.** The clip covers task seconds 55–78 and ends before touchdown. The full E04 recording supplies the later physical landing evidence.

## E05 — Visible boat skipped; acquisition fails

**Problem.** This is a major failure, not acceptable teaching behavior. The actual first saved image contains the target boat prominently. Later views turn toward other hypotheses and the run stops without confirmed identity or a metric landing pose. The user identifies the missed opportunity correctly. No recovery fault triggered, so the case is not recovery coverage.

**Required behavior.** A plausible boat must remain an investigation candidate even when design confidence is insufficient. Initial scanning must build a persistent candidate list rather than erase earlier sightings. Prefer a confirmed target when available; otherwise finish the full survey and actively inspect a plausible candidate at safe height. Approach to improve observability without granting permission to descend.

**Data treatment.** Reject the skipped-target search actions as positive demonstrations. The initial boat views are potential perception examples only after separate label/provenance validation; quarantine is not automatically lifted. Preserve the original failure as a fixed regression case.

**Additional notes.** The first image proves visual opportunity; it does not reveal whether the underlying failure was proposal generation, identity voting, selection or memory. Instrument those stages separately. An offline checker can use annotations or human judgment to flag the opportunity; the running actor must still use RGB and its own state, not simulator identity.

## E06 — Failed scan and candidate inspection

**Problem.** The user reports the same fundamental search failure as E05. Saved evidence shows scanning/reorientation/inspection without successful target acquisition. A previously examined stale-reorientation path could monopolize the search; selected later successful flights did not prove that the watchdog correction generally solved it.

**Required behavior.** Track unresolved candidates across camera turns, make bounded approaches that improve the view, and distinguish unresolved from genuinely rejected. Track-ID changes must not turn the same stale region into endlessly new work.

**Data treatment.** Exclude repeated stale pursuit and unproductive scan-reset actions from imitation. Keep valid visual labels separately. Treat this as a second acquisition regression, not evidence of successful recovery.

**Additional notes.** Older rows lack explicit ownership tags. Recover teacher provenance from the frozen harness and reject ambiguous action labels rather than invent ownership. A watchdog alone cannot teach which plausible boat to approach next.

## E07 — Identity acquired, but usable landing geometry missing

**Problem.** The user finds most of the maneuver acceptable but reports excessive apparent alignment wobble. The saved audit adds an important limit: this older episode confirmed identity, never established valid metric geometry, and stopped diagnostically. Its logged phases are scan/target inspection, rather than a completed metric alignment and landing.

**Required behavior.** Stabilize the inspection view, maintain identity, and deliberately obtain a marker view suitable for geometry. No descent on design confidence alone. Avoid repeated re-centering or camera rotation that destroys the view needed for registration.

**Data treatment.** Do not label the episode as a successful landing. Retain only verified inspection corrections for any future action targets; maintain correct masks for absent or unobservable pose targets.

**Additional notes.** The distinction between target identity and landing readiness is essential. The user's camera observation remains relevant even though the internal phase label differs. Lowering metric confidence requirements would hide the problem rather than fix it.

## E08 — Earlier basic landing

**Problem.** No case-specific new defect or approval was supplied for E08. It is a historical expert landing, not evidence that the shared wobble problem is absent.

**Required behavior.** Apply the same nominal alignment requirements as E01: controlled damping, continuous camera orientation, justified holds and strict physical touchdown.

**Data treatment.** Keep quarantined pending the shared audit. Do not infer approval from the absence of user comments. Use it as a historical comparison, not an automatically clean training source.

**Additional notes.** Its recorded physical landing took 55.68 seconds. A final success label says little about whether intermediate actions are desirable. Older ownership metadata also needs explicit provenance checking before action reuse.

## E09 — Late terminal takeover

**Problem.** The educational takeover occurred after the learner was already physically supported/on its touchdown-commit path. It was not a useful rescue. Pixel-centering or apparent lack of motion was misinterpreted as struggle.

**Required behavior.** Respect actual contact and terminal-handshake states. Allow a supported learner to complete touchdown/disarm. Trigger educational takeover for a genuine unresolved struggle, while keeping emergency safety intervention distinct.

**Data treatment.** Do not use this as a successful struggle-and-rescue example. The short expert-only clip does not include the earlier learner context required to interpret the takeover; the full trace must remain attached.

**Additional notes.** A correct terminal hold is not the unnecessary airborne dwell criticized in E01. Later terminal-handshake development had a learner finish without educational takeover, but this does not retroactively make E09 good training data.

## E10 — Failed expert rescue after tilt loss, V19

**Problem.** Takeover interrupted a learner that was already making upward recovery progress. After takeover, the expert aimed near the horizon instead of inspecting below, failed to reacquire and eventually aborted. It is not a safe-landing demonstration.

**Required behavior.** Measure actual recovery progress before educational takeover. After a necessary takeover, preserve the real observation/action history, establish a useful down-looking camera view, and execute bounded clearance-aware recovery. If recovery fails, use the qualified fallback rather than invent a success label.

**Data treatment.** Reject the faulty expert commands and the false rescue-success interpretation. Disturbance and learner commands remain their own owners. Any valid perception observations require independent admission, not episode-wide action approval.

**Additional notes.** The initial loss timer was too simplistic for progressing recovery. The expert-only video starts after takeover; it cannot by itself justify when the learner needed help. This is exactly why full pre-takeover context must accompany DAgger examples.

## E11 — Failed expert rescue after tilt loss, V21

**Problem.** The learner was allowed a longer recovery attempt, but the expert still looked near the horizon. A proposed down-looking correction existed only in the inactive recovery branch; the actual failure used the active branch, so the correction never executed. The run aborted.

**Required behavior.** The camera recovery rule must run on every applicable active/inactive path while preserving valid visual-memory aiming. Verify actual encoder motion and the actual delivered view, not merely the requested intent or a unit test of a helper function.

**Data treatment.** Keep this failed revision excluded from expert action supervision and preserve it as a branch-coverage regression. Do not substitute commands from a later revision into its old trajectory.

**Additional notes.** Later V22 development exercised a corrected common camera path and landed after a prefix; that run did not establish a genuine successful post-struggle expert rescue. All later rejected examples remain quarantined until replacement review and technical qualification.

## E12 — Repeated full scan / look-down loop

**Problem.** The user identifies repeated scan completion, down-looking and another scan without productive inspection. The episode eventually physically returned home in the absent-target case; this does not make the preceding search loop desirable teaching behavior.

**Required behavior.** A completed survey must move to a deliberate next state: inspect a queued candidate, change the certified search viewpoint, or conclude a bounded no-target search and return home. A local look-down should follow a real local-target/recovery need, not automatically erase a finished survey. A new scan needs an explicit reason and preserved candidate/rejection memory.

**Data treatment.** Exclude unproductive looping actions. Keep genuinely necessary search and safe-home/terminal actions separately assessed. A full 360-degree survey is valid behavior; a context-free repetition loop is not.

**Additional notes.** The clip is accelerated 5.46x. Confirm cycle timing from task timestamps, not playback. The user's search-until-found procedure applies while a target remains plausibly available and the mission has reserve; an absent-target case must still terminate safely. Do not extend the timer indefinitely or remove the fallback.

## The corrected search procedure

1. Establish a safe search altitude and viewing tilt. A 360-degree survey measures achieved camera-view coverage, not elapsed time, summed absolute oscillations or aircraft yaw alone. Near-vertical camera viewing cannot establish a useful horizontal survey.
2. Register plausible boat-like sightings, including low-identity-confidence candidates. Preserve bearings, observation times, uncertainty and inspection status. Seeing a target briefly must not disappear from the queue merely because the camera continues turning.
3. A confidently recognized target gets priority. Otherwise complete the first survey and select the nearest safely reachable unresolved candidate when range is sufficiently supported. If range is uncertain, do not invent an exact nearest ordering.
4. Approach at safe height to improve the view. Use fresh design evidence to accept/reject. A clearly distinguishable red boat can be rejected early; weak evidence means unresolved, not wrong boat. Glare is a separate hard negative: not every bright patch deserves a long approach.
5. For a boat inspected and confirmed wrong, follow the requested above-object viewpoint when clearance and visual localization allow it, then perform a new full survey with the rejected object below. Keep its rejection memory. Do not blindly fly over an uncertain obstacle, mast or moving hull with an unverified corridor.
6. If the survey still identifies no target, investigate the first plausible unresolved boat-like sighting encountered in the next scan, as requested. Do not require target-design recognition before inspection and do not simply revisit a known rejected boat. Earlier candidate memory remains available; stale bearings need fresh localization.
7. If there are no plausible candidates, change to a certified productive search viewpoint or finish the bounded no-target search. Require a reason for every repeat scan. Preserve the mission's physical fallback and reserve.

Inland starts need a certified land-to-water transition using declared static terrain/obstacle information. Simply deleting the water-only inspection guard would permit unverified paths through terrain, and more scan training would not remove that deadlock.

## Edge-case checks before random collection

Random collection needs explicit post-run assertions, not only a final landing score. Keep deterministic regressions for known failures alongside new random scenes.

| Check | What must be caught | Evidence |
|---|---|---|
| Visible opportunity retained | E05-like boat sighting discarded without investigation | Fixed first-view regression; offline visible-instance/human reference; proposal, recognition, selection and queue logs |
| Unknown means inspectable | Every candidate discarded merely because identity is uncertain | Ambiguous-distance scene; actual safe approach and improved observation support |
| Full scan really completed | Timer expires or oscillating yaw falsely counts as 360 degrees | Union of achieved view bearings at useful search tilt; gaps explicitly recorded |
| No empty state loop | Scan/downlook/scan repeats without candidate, viewpoint or evidence progress | State transition reason, search origin, covered bearings, candidate queue and actual motion |
| Wrong-object memory | Rejected boat immediately reselected through a new track ID | Spatial association with uncertainty, rejection evidence and bounded revisit policy |
| Safe above-object rescan | Wrong boat is not localized below, or overflight is unsafe | Actual RGB, own odometry, clearance evidence and full subsequent survey |
| Stable alignment | Camera branch flips, excessive oscillation, or unjustified near-deck dwell | Unwrapped encoder/body yaw, pad center/axes, relative speed, clearance, gate reasons and commands |
| Real disturbance coverage | Configured fault never actually happens | Executed fault rows, encoder response and actual target loss where required |
| Real rescue coverage | Takeover interrupts progressing recovery or happens after touchdown | Pre/post ownership, public progress, physical contact and terminal states |
| Correct recovery path | Requested downlook does not execute in the active branch | Actual setpoint/encoder/image trace in both branches |
| Truthful outcome | Safe home or assisted landing reported as independent boat landing | Native contact/disarm result plus exact command ownership |

Failed assertions quarantine the new episode automatically and stop collection for safety/source violations. An offline missed-opportunity assertion must not leak its simulator annotations into the actor. Thresholds for acceptable wobble, evidence support and hold duration need calibration on normal-speed traces and geometry; this report does not invent universal tolerances. A finite checker cannot guarantee that every future random scene is covered.

## Dataset decision: selective supervision, not disconnected re-rendering

**Primary choice: the user's first option, implemented as loss masks rather than deleting sequence frames. Add a limited corrected curriculum afterward.** Fine-tuning on corrected examples alone leaves the original contradictory targets active. Re-rendering only a camera view would change what the controller should have observed without changing its recorded response, position, gimbal state or later history. A valid corrected rollout requires re-simulation from a saved state, and compatible snapshots are not yet established.

Build a new, versioned derivative manifest without altering original recordings, approvals or split membership. Each capture needs separate validity for perception labels, translation commands, camera commands, descent permission and terminal handling. A camera error need not invalidate an otherwise correct braking command. A rejected action interval does not automatically erase its useful recovery observation.

“Corrective” cannot mean “the next image happens to look more centered.” Boat motion, camera rotation, image delay and braking can temporarily increase image error while a command improves physical safety. Classify short, capture-aligned control windows using camera-reference continuity, pose uncertainty, relative velocity, predicted stopping behavior and clearance. Preserve valid damping, motion matching and necessary holds. Mark doubtful windows unusable for action loss rather than guess the correct action.

Pass disturbed observations and actual previous commands through recurrent history, with their action loss masked. Otherwise the learner receives a fictitious history and has no basis for the later correction. For perception heads, enforce observability masks; do not demand a unique yaw from a symmetric cross-only image or invisible target.

Deliberate wobble should be a separate curriculum: controlled camera or flight perturbation, bounded physical limits, explicit disturbance ownership, then qualified expert recovery. Start with small perturbations and retain some nominal calm examples. Do not make difficult wobble the dominant training distribution. Disturbance commands are excluded as positive teacher action labels; corrective labels require valid expert provenance.

Audit a small stratified slice of the historical 1,200 recordings first. Report retained fractions by phase, map, near-deck condition and supervision head. Do not extrapolate a global usable percentage from a few attractive clips. If the original teacher used hidden boat truth, filtering camera wobble alone does not make its search actions observable from RGB.

The existing new-experiment quarantine is still binding. A proposed derivative mask is not permission to silently re-admit rejected raw episodes. Replacement derivatives need explicit eligibility, source hashes, validated masks and reviewed behavior. Held-out and retired evaluation failures remain diagnostic evidence, never added to training.

## Budget: 28 hours as a hard planning envelope

The 28-hour VM lifetime is user-supplied; the provider's actual expiration time was not independently verified. Use the remaining time at execution start, including elapsed planning time, rather than promising 28 additional hours after this report. Keep the final hours available for downloads and honest reporting.

The 47 fps figure is not verified for the current workload. The latest exact annotated native measurement with eight workers recorded **8.636 unique delivered captures per active-recording wall second**. Including preparation, the short two-second cohort achieved **2.859 captures per total wall second**. Four workers achieved 7.202 active-recording captures/s; twelve were skipped because measured memory use did not leave reserve. These short-cohort rates are not guarantees for long varied flights.

For scale, at 25 recorded frames/s, 1,200 episodes averaging 60 task seconds require 1.8 million frames: approximately **57.9 hours at 8.636 captures/s before preparation**, versus 10.6 hours at an unverified 47 captures/s. A full regeneration therefore does not fit the defensible budget. Existing recordings can be audited and masked without new rendering, although disk I/O still needs measurement.

| Stage | Maximum allocation | Required output / decision |
|---|---:|---|
| Data/consumer audit and mask pilot | 2 h | Trace label consumers, sample historical recordings, validate per-head masks and estimate full scan cost |
| Camera/alignment and search repairs | 7 h | Separate source revisions; continuous camera reference, damped control, justified holds, persistent full-scan/inspection state machine |
| Focused development flights and replacement previews | 4 h | Known E-case regressions, safe search/overflight, real loss/recovery, true rescue and absent-target behavior; stop dependent collection if these fail |
| Small corrected MuJoCo curriculum | 3 h | Start with 32–48 varied episodes, extend only from measured useful throughput and retained supervision; eight workers only while resource-safe |
| Applicable training and validation | 3 h | Train only consumers that actually use the corrected labels; compare masked-original and masked-plus-new on development/validation data |
| Frozen independent native evaluation and bounded Tidewater transfer | 5 h | Preserve physical/input/source checks; external game images never used to train/select; actual completed denominators only |
| Compact export and report | 2 h | Verified checkpoints, sources, manifests, masks, videos and known failures downloaded while VM remains alive |
| Failure/latency reserve | 2 h | Cover real problems; do not spend this on blind epochs or more random data |
| **Total ceiling** | **28 h** | Reallocate from measured progress; do not extend VM lifetime or claim unfinished checks passed |

At the optimistic active-recording rate, 32–48 episodes of 60 task seconds alone need approximately 1.54–2.32 hours, excluding preparation and longer recovery flights. Thus three hours is a capped collection window, not a guaranteed 48-episode delivery. Long flights or annotation costs may force a smaller useful set. Do not repeat worker-count sweeps unless the workload or resource measurements materially change.

The five-hour evaluation allowance is conditional. The earlier goal of 60 fresh boat cases plus 10 physical fallback cases may not fit after a late repair or long flights. Estimate completion from the first batch before launch, reserve fallback/transfer time, and report a partial qualification as partial. Do not turn a small successful development set into a reliability certificate. Candidate selection must freeze before a new independent evaluation; retire any failed test before subsequent tuning.

At each stage compare time remaining with the next stage plus export reserve. If a repair is still unverified, reduce new collection first. If teacher development fails, preserve the mask audit, fixes and failure evidence rather than generate more buggy episodes. Start compact exports well before shutdown; raw recordings should not be assumed transferable in the final minutes. No paid extension, new VM or budget increase is implied.

## Order of work and completion conditions

The first implementation priority is the shared E01/E02/E03/E04 camera/alignment issue and the E05/E06/E12 search state machine. E09–E11 then exercise real terminal and takeover/recovery branches. E07/E08 remain explicit regressions rather than being assumed clean. Prefer a few meaningful counterexamples over a large random run from an unverified teacher.

For the next review, show synchronized actual onboard/external views, task time, camera pan/tilt, command owner, target phase and the current hold/scan-transition reason. Include normal-speed windows around alignment, takeover and recovery; distinguish intentional faults from ordinary teacher commands. Compare original and replacement E-cases under matched scenarios without presenting exposed development cases as fresh tests.

Completion means corrected behavior was physically exercised and the actual training path honored the masks. A visually smoother video alone is insufficient. No controller, model or dataset eligibility was changed by this report, and no replacement demonstration has yet been produced.

## Evidence consulted

- EXPERT_BUG_REVIEW_20261019.md: exact E-to-source mappings, ownership, playback rates and coverage gaps.
- Saved actual camera contact sheets for E01, E03 and E05; existing per-case actual-preview/fault audits and historical status/subplans for E04 and E09–E11.
- CAMERA_AND_FAILURE_REVIEW_20261019.md: measured camera rotation, symmetry/branch limitations and separation from four later acquisition failures.
- vm_results/native_throughput_v22.json: actual eight-/four-worker throughput, preparation overhead and memory-based twelve-worker exclusion.
- landing_training/docs/CURRENT_POLICY.md and the historical development report: deployed hybrid versus original sequence-action pipeline, original 1,200-episode lineage and observable-teacher limits.
- landing_training/train.py and train_curriculum_verifier_v24.py: action-mask versus visual-verifier consumers. Inspection does not make the old action trainer the active runtime.
- NEXT_ITERATION_CONTRACT.md and EXPERIMENT_RESULTS_20261019.md: static terrain transition, failed search, preserved scoring and prior unqualified outcomes.
