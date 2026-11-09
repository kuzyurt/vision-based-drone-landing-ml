# Teacher behaviour and scenario failure specification

Status: analysis/specification only. No repaired controller, qualified teacher, new flight, or training run is claimed by this document. The user stopped execution and then approved this sequential analysis. Simulation, queues and training remain stopped.

Method: examine one situation, write its numbered behaviour and a matching edge-case list, save it, then independently examine the next situation. Existing evaluated sources, recordings and exclusions are preserved. An eventual implementation must use new versioned sources. This is a systematic catalogue of foreseeable failures, not a claim that every possible bug has been predicted.

Evidence labels:

- **Observed:** supported by an existing configuration, source, or closed recording named in the situation.
- **Required:** proposed behavioural or scenario requirement; not proof that the current code implements it.
- **Unresolved:** requires a measured decision or additional evidence. Do not invent a numerical threshold or a success result to close it.

Scope and common constraints:

- Actual onboard RGB is **640×360** in the current Windows runner. Do not confuse this with network crop sizes or assume small/distant boats are recognizable.
- Actions may use RGB, own telemetry, camera encoders and declared static calibration/map/CAD priors. Dynamic target truth, segmentation, instance IDs and scorer labels are observer-only. Scenario construction may use simulation geometry; the task actor may not.
- The original CAD is still the target design when its marker is hidden. That permits identity, not blind descent. A different boat with a copied cross is wrong design. A cold marker-only crop does not prove identity. The reduced clone remains identity-unscored where its design is ambiguous.
- Scenario purpose, sensible decisions, capture/action integrity and actual physical outcome are **separate requirements**. A touchdown cannot cancel a behavioural failure. The failed historical static recognition qualification remains failed.
- Teacher demonstrations and learner→teacher rescues are different products. The learner's actions, teacher's shadow proposal, executed owner, disturbance and safety intervention must remain separate. No action imitation is currently implemented merely by saving these vectors; a perception-only update does not train the explicit search/controller logic.
- All existing reviewed/quarantined raw recordings stay ineligible. A future per-frame action mask must exclude disturbance, learner, emergency override, unnecessary waiting and demonstrably harmful teacher actions; it must not be derived from hidden target coordinates for the acting controller. Perception labels and action labels need separate admission decisions. Do not automatically discard all useful negative RGB because an action was wrong, or automatically admit a whole failed episode because its RGB labels are valid.
- No new return-home/land-home rendering or training. Physical contact/scoring, ceilings, task budgets and disturbance bounds are not weakened to obtain a demonstration.
- Numerical limits for acceptable wobble, interruption latency, verification dwell, progress and recovery must be declared and justified before evaluation. An unspecified limit is an open implementation item, not an implicit pass.

## E01 — Initially visible nearby boat: purposeful acquisition, approach and stable landing

### Evidence and intended distinction

Observed local job: `../local_curriculum_20261020/review_batch_v1/jobs/E01_nominal_cpu_v3.json`. Beach; requested distance8m and height6m; boat0.3m/s; waves0.03m; no injected fault; expert owns task actions. The job's actual accepted distance interval is5–20m, much broader than its8m name implies. This is a nominal visible-start task, **not** an initial search task.

Observed rejected recording: `../local_curriculum_20261020/review_batch_v1/E01_nominal_cpu_v3/`. At frame0 the target is visible, with a learned boat proposal. The expert performs a scan until18.6s. At18.6–24s selected track1 lies on `decoy_buoy`, while the target remains visible. At20s that track has `boat=true`, target probability about0.000006, and its pixel lies inside the buoy's annotation box. Target inspection begins24.68s; camera-axis alignment begins30.16s; descent begins38.08s; intermittent inspection/visibility holds occur later. The flight eventually lands, but the user rejected its behaviour. The old technical audit's `passed` is not behavioural approval.

Relevant current sources: `../local_curriculum_20261020/sources/target_learning/protocol_elevation_v39.py`, `protocol_memory_elevation_v39.py`, `expert_adapter_windows_v1.py`, `camera_axis_continuity.py`; `../local_curriculum_20261020/run_windows_review_cpu_v3.py`. The survey path can force completion before inspecting an unconfirmed candidate; plausible-candidate admission can accept a buoy mislabelled by the detector. The complete reason the visible target lost selection priority is **unresolved**; the buoy association itself is observed.

### Intended sequence — E01 steps1–12

1. Prepare a physically valid airborne start; record the first task camera image only after real preparation. Keep the nearby target and sufficient boat structure visible. Record actual range, camera pose and owner without supplying target coordinates to the actor.
2. Examine the current RGB before starting a search. Detect and maintain plausible boat hypotheses; distinguish target identity evidence from a generic object/boat proposal. Do not rotate away merely because the identity confidence has not reached its confirmation threshold.
3. Keep the strongest relevant visible boat opportunity under observation and obtain additional distinct views. If its design is recognizable, confirm identity from those views. If genuinely ambiguous, inspect at safe stand-off; do not require a blind full360 first.
4. Compare alternative candidates explicitly. A yellow buoy, debris or a cross-only board must not outrank a visible plausible boat solely through detector confidence, age, apparent nearness or accumulated repeated observations. If evidence is contradictory, maintain uncertainty rather than assert a target or a known-wrong identity.
5. Approach the chosen boat-like candidate using current bearing and bounded range uncertainty, maintaining obstacle clearance and useful camera framing. Reassess all visible candidates during the approach. A newly recognizable target interrupts an unresolved lower-priority inspection through a controlled transition.
6. Confirm target design and separately acquire fresh pad geometry. If the target has no usable pad view, reposition to observe it at safe clearance; do not classify the boat as wrong merely because its pad is hidden. If it is proven a different design, stop the target approach and enter a documented reject/search branch.
7. Establish relative tracking and the minimum camera/body alignment actually required for reliable landing. Retain a consistent symmetry branch. Translate and rotate smoothly with visible feedback rather than introduce a separate large cosmetic camera rotation.
8. Begin descent when identity history, current pad geometry, tracking, camera synchronization and physical clearance support it. Reduce lateral error while tracking boat motion; maintain camera/vehicle synchronization throughout decreasing height.
9. Continue a smooth, feedback-driven descent. Small transient uncertainty receives a bounded response; real geometry loss arrests descent. Use distinct capture times and hysteresis appropriate to the physical dynamics so one marginal frame does not cause repeated opposing phase commands.
10. If real loss or growing alignment error occurs, arrest unsupported descent, retain only still-valid observable memory, and execute local reobservation/recovery within certified clearance. Reacquisition returns to tracking/alignment before descent. This is an exception branch, not an invented disturbance for nominal E01.
11. Commit to touchdown only with appropriate near-deck support and actual PX4/contact evidence. Confirm stable physical support and ordinary disarm. Camera near-field occlusion after genuine contact must not trigger a needless takeoff/recovery; a timeout or a painted cross alone is not landing evidence.
12. Review the whole trajectory and each learning segment. Accept E01 as nominal only if it demonstrated a sensible visible-start acquisition and stable landing without a pointless survey, buoy pursuit, manufactured disturbance or unnecessary delay. Preserve a failed recording with explicit reasons even if it lands.

### Per-step edge cases, failure mechanisms and required checks

**E01.1 — Initial state and purpose.** Check actual final-effect RGB, not only commanded yaw or projected target centre: the centre may be in frame while boat structure is clipped, self-occluded, overexposed or too small. Preparation can move the boat before task frame0, so compute actual task-start range and visible structure then. Do not hide/teleport/resize the boat to force visibility. No intersecting CAD, spawn on deck, initial contact, overlapping decoy or offboard preparation action may leak into a nominal task label. Tighten the distance contract to its intended difficulty rather than accepting5–20m as equivalent to8m without justification.

**E01.2 — Initial perception.** A detector's `boat=true` is not proof of category or identity. Glare, a buoy and a copied cross are explicit false-proposal tests. Conversely a clearly boat-like target with subthreshold identity should yield further inspection, not be discarded. Count distinct captures rather than processing one delayed image several times. Do not give the actor the observer's target box to solve this; audit the selected proposal's actual instance afterwards.

**E01.3 — Evidence gathering without losing the opportunity.** Rotating the camera upward or performing an obligatory360 can destroy the evidence needed to confirm the object. Ensure the view is held or improved, not merely held for a fixed timer. Boat motion, blur and ego-rotation can split a track and erase accumulated evidence; association must preserve genuine continuity without merging separate boats. A wrong candidate must not acquire target votes from a nearby target. A tiny/ambiguous crop cannot be forced into target identity by prolonging dwell. Measure time-to-useful-inspection and whether the initial opportunity was deliberately abandoned.

**E01.4 — Candidate choice.** Reproduce the observed target-plus-buoy view and require an auditable selection reason. Test high-confidence buoy false positives, partial target views, a more central wrong object, bright copied crosses, and a legitimate nearby unknown boat. Do not repair this by banning yellow pixels or by privileging simulator instance IDs. Range projected onto a nominal plane is an interval, not exact target distance. A persistent wrong-object proposal must not gain priority just by being old; unresolved and visually established non-boat/wrong-design need distinct states. Log why each visible alternative was retained, selected or dismissed.

**E01.5 — Approach.** Test body/camera frame signs, yaw wrap, gimbal limits, image latency, estimated range bias and moving boats. An unknown candidate may not authorize descent. A safe-looking image can hide a mast/collision envelope; preserve certified static clearance and conservative structural bounds. A target can enter the view while inspecting another object: either construct the dedicated scenario to avoid unintended target exposure before its intended branch, or explicitly score the interruption branch. Never ignore the visible target, hide it mid-flight, or use truth-triggered actor switching to keep a storyboard intact.

**E01.6 — Identity versus pad.** Test target with marker hidden, target seen only in a cold marker crop, different boat with copied marker, reduced clone and actual wrong boat. Structural design and marker readiness must be independent labels. A pad fit on another object must not inherit the selected boat's identity. Old identity memory cannot justify descent onto a newly overlapping board. If safe viewing cannot recover geometry, stop the demonstration as unsuccessful; no blind descend-to-find-marker shortcut.

**E01.7 — Alignment and synchronization.** Check fourfold cross/square ambiguity, axis branch retention, yaw±π and near-nadir pan singularity. A reference that slowly rotates3°/s may create a long unnecessary alignment hold; the current speed is a source fact, not a justified desired value. Determine whether body yaw, camera pan, tilt or lateral position actually needs correction. Avoid integrating the same correction twice through the actor and wrapped inner controller. Measure camera/world reference error, pad-centre error and command reversals together; a cosmetically stable video must not be substituted for stable actual control.

**E01.8 — Descent permission.** Do not use old or repeated geometry as fresh evidence. Check age against capture time after delay and effects. Synchronization at the top must persist through changing perspective and boat heading. Correct body-frame tracking of boat velocity; vertical sign errors and wave motion must not create a false-clearance descent. Starting unnecessarily high or far due to setup drift can inflate the nominal trajectory and teach needless manoeuvres.

**E01.9 — Chatter, wobble and waiting.** The actual brief `inspect_candidate` interruptions during descent require causal explanation, not a new name for a pass. Test thresholds near boundaries, alternating marker fits, occlusion by own CAD, noisy encoders and wave-induced variation. Quantify amplitude/frequency of lateral/camera oscillation and duration/reason of holds before choosing limits. Do not penalize a necessary arrest of real uncertainty merely to shorten a video. Exclude unnecessary hold/action segments from future action supervision; distinguish them from valid negative/uncertain perception examples.

**E01.10 — Recovery.** An E01 fault-free recording cannot prove injected-loss coverage. Recovery must not aim at the horizon after memory expiry, climb without clearance, follow stale boat position, or oscillate indefinitely. Test valid memory versus expired/contradictory memory, geometry loss versus identity loss and a target moving out of the old ray. A completed recovery does not retroactively make the preceding harmful teacher commands good labels.

**E01.11 — Contact and termination.** Distinguish proximity, first contact, bouncing, full supported contact, PX4 landed and actual disarmed. Wrong-object feet contact is still a failure. Never change scorer/contact settings, set landed/disarmed flags, or use privileged truth to send a disarm task command. Account for the model/camera's finite near-focus view: the boat filling the image near deck is not itself a fault. Preserve complete terminal evidence even if those stationary confirmation frames are not useful action-training targets.

**E01.12 — Learning and reporting.** Required evidence: actual normal-speed acquisition/alignment/descent video, selected-instance associations throughout the mission, rejected-alternative reasons, progress/hold history, exact RGB/action ownership, and physical contact/disarm record. Existing RGB/command audits pass yet miss the buoy pursuit; add the behavioural failure independently. Do not relabel this recording approved because its landing scorer says success. A static recognition score, a16-frame runtime parity probe and an eventual touchdown cannot jointly substitute for teacher competence. Define how future perception-only and any future action-supervision consumers use the same episode; do not claim the explicit controller learns improved search merely from retraining a verifier.

### E01 unresolved implementation decisions / blockers

- Explain with full candidate eligibility/ranking/cooldown evidence why the target was not selected instead of the buoy; current selected-track association is conclusive but not a complete root-cause proof.
- Define observable boat-category plausibility and target-opportunity priority without rejecting legitimate distant/ambiguous boats or introducing truth into actions.
- Establish measured stable-alignment, progress, chatter and reacquisition limits; do not lower confidence or safety thresholds just to obtain a shorter recording.
- Rejected local E01 remains excluded. No repair or new rollout is authorized by the word `passed` in its historical technical audit.

End of E01 iteration. Subsequent sections are appended in separate evidence/reasoning iterations.

## E02 — Search among hard distractors, inspect uncertainty, reject copied crosses

### Evidence and intended distinction

Observed job: `../local_curriculum_20261020/review_batch_v1/jobs/E02_distractors.json`. Hard scene; requested20m horizontal distance,6m height, initial pan140°/tilt35°, moving boat0.3m/s, glare strength1.4. Actual initial receipt reports20.117m and zero target pixels. Scene receipt includes similar/dark/red boats, a reduced clone, copied-cross boat and board, buoy and debris. These are simulated distractors, not all automatically acceptable inspection candidates.

The local recording stopped for RAM after2153frames, about86task seconds. It has valid capture/history joins but no completed outcome. Do not call it a completed search failure or a successful demonstration. Historical v31 E02 was presented as landed in its earlier hard scene; that does not establish this new scenario's behaviour. TrackBank's own docstring says uncertain evidence resets identity, whereas its current implementation retains bounded distinct strong votes: tests must inspect implementation and actual diagnostics rather than trust that stale sentence.

Required distinction: this situation exercises **search plus competing-object discrimination**, including safe unknown-boat inspection and avoidance of copied-cross landings. A nominal landing with a decoy somewhere offscreen does not cover it.

### Intended sequence — E02 steps1–12

1. Generate a physically separated target/distractor scene and an airborne view with the target outside the initial actual camera image, not removed from the world. Select a safe search height/corridor and a feasible target route.
2. Check the current image for recognizable target evidence or plausible boats. If the target is already recognizable, record a purpose mismatch for this search variant; the actor must still respond sensibly rather than obey an instruction to ignore it.
3. If target identity is not established, conduct a first full360 recognition survey using actual camera bearing coverage. Observe distinct images, retain candidate observations and their uncertainty, and avoid chasing buoy/debris peaks. A target recognized during the survey interrupts it; do not finish a ceremonial rotation first.
4. If the completed first survey has not identified the target, start an active-inspection survey. In the user's requested sequence, inspect the **first eligible boat-like candidate encountered on this pass**, including a distant/unknown boat. Keep rejected non-boats separate from unresolved boats. Do not silently substitute nearest remembered object from the first survey.
5. Reorient smoothly to that candidate, reacquire it in a fresh image and approach only through a certified safe corridor. Preserve a useful view of its structure. Continue evaluating other visible objects during the approach.
6. As its design becomes observable, branch: target design→target inspection; clearly wrong design→reject; still ambiguous→improve the view within bounded safe effort. A copied cross cannot turn a wrong boat or board into the target.
7. For a clearly wrong boat, if a safe overflight is feasible, move above it at maintained certified clearance so it is below the drone, then begin a new full360 survey from that viewpoint. If unsafe or insufficiently localized, do not force an overflight; record the exception and choose another safe search action. Do not descend onto it.
8. For unresolved inspection, distinguish lack of evidence from wrong identity. Track observable progress; a bounded unresolved inspection may be deferred and revisited when a genuinely new viewpoint/evidence exists. It must not become an endless inspect/scan/inspect cycle of the same ghost.
9. At every stage, a newly recognizable target takes priority over an unresolved inspection or wrong-object overflight. Transition smoothly, retaining collision clearance. If the nominal storyboard requires a wrong-boat inspection first, scenario generation must arrange the sightlines accordingly instead of disabling this interrupt.
10. Once target design is established, obtain its own fresh pad geometry, synchronize camera/body tracking, align and descend using E01's supported approach/landing requirements. Keep the copied-cross objects in the perception checks; their pixels must not supply the target's metric fit.
11. If no target can be found/qualified within the unchanged task budget, terminate as incomplete/failed search without generating return-home training/rendering. Record coverage, actual inspected objects, rejection reasons and why the target remained unresolved.
12. Admit this as a useful hard-discrimination demonstration only when the intended ambiguity/decoy interaction actually occurred, every selection and rejection was sensible, and the final target landing/contact/disarm was genuine. Grade each search branch separately; no target landing can erase an earlier buoy pursuit or wrong-object descent.

### Per-step edge cases, failure mechanisms and required checks

**E02.1 — Geometry and visual purpose.** Use real camera calibration, viewport, camera-to-body transform, body yaw, pan/tilt limits and full object extent, not merely an initial bearing140°. Check after physical preparation and image effects. Check collision radii, moving-route swept clearance and coast margins; pairwise initial distance alone is insufficient. The existing random placements check routes, but their presence does not prove useful simultaneous visibility. Reject a draw that makes the wrong boat indistinguishable by the declared CAD distinction, or label the reduced clone unscored; do not demand an impossible visual decision.

**E02.2 — Early target visibility.** The target may enter the initial view due to preparation drift, boat motion or a wider-than-assumed FOV. Either reject/relabel the draw before claiming search coverage or score a visible-start branch; do not black out/hide the boat. A few target pixels are not necessarily recognizable identity. Record extent, clipping and useful structure; require human-reviewable evidence for the intended first recognition opportunity.

**E02.3 — Full first survey.** Integrating commanded body yaw is insufficient when the gimbal counterrotates. Account for actual optical bearing, altitude/tilt band and distinct capture timestamps. Oscillations and yaw wrap cannot count as a full rotation. Fast rotation, glare and frame delay can leave unobserved angular sectors despite360° motion. Scan tilt must actually cover plausible boat elevations. No forced full survey after a recognizable target appears. Current code's forced completion for unconfirmed candidates is not blanket approval of that behaviour.

**E02.4 — Second-pass ordering.** Keep explicit survey/pass and inspection-queue state. Deduplicate the same boat under several tracks without merging separate boats. Define first eligible sighting by actual camera encounter on the active pass, not detector-array order, track ID, posterior maximum or privileged distance. Known buoy/debris is ineligible; a legitimate far boat with uncertain design remains eligible. The current first-pass nearest-interval ranking is an observed implementation, not the user's requested two-pass behaviour. Freeze the intended ordering before implementation/evaluation.

**E02.5 — Approach path and sightline.** Use offline scene construction to check the intended camera sweep and approach corridor against both candidate and target extents, with tolerances for movement/lag. A static initial FOV check cannot guarantee the target stays out of view later. If it becomes recognizable anyway, the actor must redirect; those frames must not teach ignoring it. Do not provide simulator-derived candidate coordinates to steer the actor. Range projection onto nominal water/boat height can misorder a low buoy and a tall boat; keep uncertainty and require visual progress.

**E02.6 — Classification and geometric association.** Test a target with hidden pad, a clear copied cross on another design, a board with only a cross, dark/similar wrong boats, tiny partial boats and the reduced clone. Distinguish category, design identity, observability and marker readiness. A high-confidence detector false positive remains possible even after many frames. Require observer-only selected-instance association across the entire approach, not only at landing. Reject a teacher action segment that confidently pursues a non-boat as an intended boat inspection. Do not make marker absence evidence of wrong design.

**E02.7 — Wrong-object overflight.** A simple centroid range<0.8m does not itself prove safe above-object placement or adequate clearance. Check full hull/mast geometry and own dynamic constraints; actor uses declared bounds/observed range, scorer verifies true swept contacts offline. Do not fly through a mast to satisfy the storyboard. Rejecting a wrong object need not consume an overflight when recognition occurs at a safe long distance and the overflight is infeasible; label that as a different branch rather than fake completion. Clear survey coverage for the new viewpoint; do not reuse old coverage to claim a fresh360.

**E02.8 — Unresolved memory.** Stale rays, lost moving boats, track aliases and a long cooldown can create permanent ghosts or erase viable targets. Unknown is not wrong. Do not renew measurement age by ego-motion prediction, repeated crops or negative observations of the wrong ray. Reset no-progress only for meaningful fresh evidence, not a new track number. Test multiple unknowns, contradictory classification, object crossing and a previously rejected boat entering a genuinely better view. No endless timer resets by tiny range noise.

**E02.9 — Target opportunity interrupt.** A current selected candidate must not suppress a newly identifiable alternative. Conversely a single unqualified target spike must not cause repeated switching. Record evidence before/after the switch and camera/vehicle commands. Test the target appearing beside, behind and partly overlapping the candidate. Do not artificially constrain deployment logic to the scenario script. For training, either verify the desired discovery ordering or explicitly classify this as an interruption case; it cannot be called the same intended branch while ignoring the target.

**E02.10 — Landing discrimination.** Audit the marker-fit object and selected-identity object at every descent-permitted frame. Box masking alone can include a different overlapping object. Keep target-history association through close-up views without treating a cold marker-only view as proof of design. Check partial occlusion, similar colours, glare-driven fits and a wrong boat moving through the target box. Enforce E01 synchronization, hold and physical termination checks; the hard scene is not permission for wobbly or unnecessarily delayed alignment.

**E02.11 — Failure and budgets.** Resource/setup interruption, search exhaustion, physical collision and observer-contract failure are distinct outcomes. The current2153-frame interrupted recording is not a completed benchmark denominator. Never extend timeouts repeatedly, move the target into view, or remove distractors mid-flight to manufacture coverage. Preserve useful actual diagnostics and exclude unjustified action targets. Stop before unwanted home-command data.

**E02.12 — Dataset coverage.** Require actual visible copied-cross/distractor encounters, not object count in a scene file. At least one successful target-only route does not establish all wrong-design/unknown/reject branches. Report a branch matrix with executed/not-triggered/failed/interrupted states. Maintain world/family/trajectory splits before selecting frames; the failed validation scenario cannot silently become training data. Training a verifier on correctly labelled negatives does not establish repaired planner selection or qualified teacher actions.

### E02 unresolved implementation decisions / blockers

- Formalize the requested first-recognition-survey then first-eligible-active-inspection-pass semantics; specify how an already visible unresolved candidate is retained and revisited without an unnecessary initial scan in nominal E01.
- Establish observable category eligibility and priority rules robust to buoy false positives while keeping genuinely distant boats investigable.
- Scene feasibility needs swept visibility/clearance checks and an interrupt branch; neither an omniscient teacher nor hiding the target is an acceptable shortcut.

End of E02 iteration.

## E03 — Physical camera-pan disturbance: synchronization without teaching wobble

### Evidence and intended distinction

Observed job: `../local_curriculum_20261020/review_batch_v1/jobs/E03_yaw.json`. Hard scene, visible start,8m/6m request, boat0.3m/s. Physical `gimbal_pan` disturbance:40°/s for1.2s, scheduled from fresh public pad/pose evidence below0.65m estimated clearance. It has **no** requirement for actual metric loss. The runner overrides camera-pan/tilt command components, then bounds/supervises the command. Therefore nominal40°/s×1.2s is not proof of executed encoder excursion.

Earlier v31 E03 audit/gallery reports30 disturbance frames in an older scenario with initial pan140°, not the current visible-start scenario. Historical near-nadir pan testing demonstrated rotation/resynchronization, not necessarily target loss or recovery climb. No new Windows E03 flight has run.

### Intended sequence — E03 steps1–10

1. Establish the declared visible-start task with a valid moving boat, distinct wrong objects and a camera/vehicle state capable of the intended pan excursion without mechanical saturation.
2. Acquire and approach the actual target through the sensible E01 path; settle relative tracking and synchronized descent before any disturbance. A faulty acquisition is still a failed teacher prefix, even if a later disturbance works.
3. Trigger the bounded external camera-pan disturbance only from fresh public geometry while airborne and before terminal contact commitment. Keep the task actor unaware of privileged trigger truth; record intended, bounded and actual executed commands separately.
4. Observe actual camera encoder change and actual RGB. Determine whether the effect is image rotation with retained geometry, geometric uncertainty, or genuine loss. Do not decide the recovery branch from the scenario name.
5. If geometry remains valid, retain target identity and smoothly re-establish the camera reference/axis branch. Arrest descent only when the synchronization/uncertainty actually makes descent unsupported. Avoid an unnecessary full scan or climb.
6. If geometry genuinely becomes unusable, arrest unsupported descent and run the same bounded local recovery requirements as E04; do not use the old pad location as a fresh measurement.
7. Once the external command override ends, return control to the teacher continuously. Re-establish useful framing and heading synchronization with bounded corrective motion; account for actual actuator lag and boat movement.
8. Resume supported descent after fresh evidence and stable synchronization. Small remaining corrections should settle rather than produce repeated opposing pan/body-yaw commands or a long alignment ritual.
9. Complete actual target contact, stable support and ordinary PX4 disarm without confusing a rotated marker with another object or forcing touchdown through missing geometry.
10. Package the complete context plus a normal-speed disturbance/recovery window. Mark the injected cause separately from the teacher's corrective response. Qualify only the branch actually observed: yaw resynchronization alone is not loss/climb or learner-rescue coverage.

### Per-step edge cases, failure mechanisms and required checks

**E03.1 — Disturbance feasibility.** Check real pan joint range, initial pan, body yaw, near-nadir geometry and camera model. A commanded pan at nadir mainly rotates the image; it need not point away from the pad. A joint already at a limit can make the disturbance ineffective. No image rotation/warping may substitute for physical camera motion. Scene generation must not put a copied cross inside the expected target box along the excursion without explicitly testing that ambiguity.

**E03.2 — Prefix quality.** The initial boat must not be ignored, and a buoy inspection cannot be excused by calling the whole episode a yaw test. Verify every selected-instance association and hold reason before the fault. The pad must be physically reachable with a useful pre-fault tracking interval; an immediate fault on the first dubious fit skips the intended synchronized-descent state. Do not delay near touchdown indefinitely just to obtain a trigger.

**E03.3 — Trigger and ownership.** The present helper schedules the start one decision tick later; audit the actual executed interval, not merely `triggered=true`. Check fresh capture/pose age, armed/not-landed state, supported contact exclusion and exact owner after final safety/slew limiting. A supervisor can override or clip the injected command; that must not count as a full disturbance. Fault commands are external causes, not teacher action targets. The actor must receive the exact previous executed fault command, not the pre-fault proposal.

**E03.4 — Measured effect.** Associate visible pad/design through rotation and self-occlusion; encoder motion alone does not establish loss. Distinct frames with a valid metric fit, missing metric frames and recovery-active commands are separate counters. Do not infer a48° excursion from a48° command integral. Check units, pan-versus-tilt captions, task time versus preparation-inclusive time and actual frame indices in the clip.

**E03.5 — Geometry retained.** Cross/square symmetry can jump the heading by90°/180° without physical boat rotation. Retain a supported branch and camera world reference rather than rotate the vehicle to chase fit ambiguity. Counteracting pan with body yaw must not double the intended rotation or create a feedback fight. Necessary synchronization hold has an observable reason; a tiny residual heading error must not cause seconds of gratuitous hovering. Thresholds must be measured before declaring wobble acceptable.

**E03.6 — Real loss.** Camera sync loss is not automatic permission to climb. Use own state, last valid observable geometry, memory age and certified upward clearance. Do not continue descent with stale geometry, restart an unrelated360 scan, aim at the horizon, or keep replaying the fault command after its end. A recovery may be unsafe near contact; distinguish supported touchdown continuation from an airborne loss using actual own/contact evidence, not target truth.

**E03.7 — Handover after override.** Check slew history against what was actually sent during the disturbance. A controller integrator can wind up while its camera output is overridden, causing a second large excursion when released. Preserve the correct reference or reinitialize only justified internal camera state without resetting learner/mission history. Do not snap the gimbal, reset the drone pose or use simulator target coordinates to make the recovery look smooth.

**E03.8 — Corrective learning.** The user permits deliberately generated wobble only when learning from its useful corrections. Exclude injected disturbance commands and harmful teacher oscillation. A valid correction cannot be classified solely by whether the next noisy frame's pixel error decreased: actuator lag, braking and boat motion can require a temporary non-monotonic response. Define a validated observable correction window with action ownership, lag and synchronization/relative-error evidence; otherwise keep its action labels unavailable. Do not claim a verifier fine-tune learns these camera corrections.

**E03.9 — Terminal safety.** A rotation can move the pad out of a box without changing clearance. Conversely a still-centred cross can be from a wrong board. Require current qualified object/geometry association, and keep all wrong-object contact failures. A fault triggered after landing/disarm is missing coverage, not a successful disturbance test.

**E03.10 — Honest coverage and videos.** Show enough pre-fault context, actual command ownership and post-fault settling at normal task speed. Stabilizing or time-compressing the only correction view can hide wobble and delay. An untriggered fault or encoder-only perturbation with no synchronization problem does not cover the intended repair. Record separately: actual pan disturbance, geometry-retained resync, genuine loss, successful recovery and final landing. No automatic whole-episode action eligibility.

### E03 unresolved implementation decisions / blockers

- Establish which observable synchronization errors actually require descent arrest, and measured acceptable settling/wobble limits; do not add a climb merely to satisfy a video label.
- Validate post-override controller state handling and the correction-window admission rule before using any intentionally disturbed sequence as action supervision.

End of E03 iteration.

## E04 / E04a — Close-range physical tilt loss and bounded local recovery

### Evidence and intended distinction

Observed job: `../local_curriculum_20261020/review_batch_v1/jobs/E04_close_loss.json`. Hard scene, visible8m/6m start, boat0.3m/s, actual camera-tilt override toward the horizon at40°/s for1.6s. The declared purpose requires actual metric loss. The public trigger requests estimated clearance≤0.65m while geometry/pose are valid. No local Windows E04 has run; it cannot inherit historical recovery results.

Observed implementation: `local_downlook_v22.camera_only_downlook` aims80° down when memory is unusable, using own encoders; it changes camera/body-yaw commands, not XY/Z. The adapter calls this in both native-active and camera-only recovery branches. Historical V21 failed because a correction was installed only on an inactive branch; placement of a helper is not evidence its failing execution path uses it. Historical v31 E04 reports40 fault frames, but new coverage must be measured independently.

E04a is a normal-speed detail of the **same E04 flight**, not another scenario, independent trajectory or train/test sample. Its frame interval must be derived from actual fault/recovery events, not a guessed task timestamp.

### Intended sequence — E04 steps1–12

1. Construct a moving-target scene with a feasible acquisition, landing region and upward/local recovery envelope. The intended near-deck disturbance must be physically executable before terminal contact.
2. Perform a sensible teacher acquisition/approach and synchronized descent. Establish target identity history and fresh relative pad geometry before injecting any loss.
3. Trigger the bounded physical tilt override at the declared public state; tag its actual executed command ownership. Keep normal physics and image production running. Do not hide the target or insert black frames to manufacture loss.
4. Verify actual encoder excursion and RGB/geometry loss. If the camera remains on the pad, or loss lasts only a non-meaningful instant, report missing loss coverage rather than a successful recovery demonstration.
5. On unsupported geometry loss, arrest further commanded descent promptly; account for existing downward velocity and actuator/controller response. Keep safe lateral tracking only when supported by bounded observable memory and uncertainty.
6. Use short-lived valid local memory and own camera pose to reobserve the target. Point toward the remembered local region; if memory is expired/unusable, perform a genuine local downlook using encoders instead of aiming at the horizon.
7. If local reobservation fails and upward clearance permits, perform a bounded recovery climb to widen the useful view. If clearance or near-contact state makes ascent unsafe, follow the supported safe exception rather than force a climb.
8. At the recovery view, inspect locally and attempt fresh target/geometry reacquisition. Do not interpret a stale prediction or the disturbance ending as a new observation. Reconcile the new track with identity history without accepting a wrong nearby cross.
9. Once reacquired, synchronize camera/vehicle, update moving-target tracking and deliberately re-enter supported descent. Avoid repeated recovery→descent→recovery cycles caused by the same unresolved geometry or branch discontinuity.
10. If bounded local attempts fail, transition to a justified broader search only when feasible within remaining mission/clearance limits, otherwise terminate the boat task without home-training/rendering. Do not call this a recovered landing.
11. Complete actual supported target touchdown and ordinary disarm. If contact already occurred before a supposed loss intervention, identify that as terminal handling, not an airborne rescue.
12. Review E04's full behaviour and extract E04a's event-centred normal-speed window with before-loss evidence, actual disturbance, arrested descent, reobservation, any climb, reacquisition and settled continuation. Apply action masks by owner and useful corrective behaviour; preserve excluded harmful/cause frames.

### Per-step edge cases, failure mechanisms and required checks

**E04.1 — Feasible recovery envelope.** A nominal vertical column test alone may not cover lateral following of a moving boat, own braking distance, masts or a tilted vehicle's swept volume. Verify declared conservative bounds and offline true swept clearance independently. Setup must not spawn already on the deck or beyond a safe ceiling. Keep the original≤2s disturbance bound; do not extend it to six seconds just to force failure. A no-clearance case needs its own safe-exception label, not an impossible required climb.

**E04.2 — Prefix validity.** Require actual acquisition and a measurable synchronized descent interval, not merely one noisy metric fit. The actor must not reach the prefix through the E01 buoy bug. A late near-deck trigger may occur after actual contact; check body/feet support, actual PX4 airborne state and terminal-commit logic. Do not hover indefinitely above the deck to wait for a designed disturbance.

**E04.3 — Correct physical disturbance.** Pan and tilt have different effects at nadir. Check actual final command component, sign, duration, saturation and encoder trace; the helper's generic name/setting is insufficient. A final safety limiter may suppress the override; count what actually reached PX4/gimbal. Record teacher proposal before override, exact fault command and subsequent observation history separately. Annotation must join the final actual RGB after effects, including during the fault.

**E04.4 — Loss definition.** Target identity can remain valid while pad geometry is lost; those are different events. Do not clear correct boat identity solely because the camera points away. Conversely a marker-only reappearance cannot establish a new target identity without valid history. Measure missing geometry, visible target/marker, pose freshness and commanded recovery together. Invalid-image flags must describe real sensor validity rather than be toggled to trip the recovery code. Untriggered or ineffective loss is a purpose failure.

**E04.5 — Descent arrest.** A zero-down command does not instantaneously stop real downward motion. Measure response latency, true vertical motion offline and public velocity used by the controller; declare an appropriate bound from dynamics. Do not demand impossible instantaneous zero velocity or train a false emergency reaction to every noisy pixel. Lateral memory following must remain bounded; zeroing XY can let a moving boat escape, but blindly chasing a stale point can send the drone into another object. Neither extreme is a general solution.

**E04.6 — Active versus inactive recovery paths.** Exercise both branches of the adapter and the original recovery controller; helper unit tests alone missed the earlier active-path bypass. Check actual resulting tilt toward downlook, not only `expert_expired_memory_downlook=true`. Near-nadir pan is not an unambiguous yaw/aim correction. Memory validity must use original observation time, covariance/uncertainty and motion bounds; do not refresh it by command execution or track alias. A valid local aim must not be overridden by a generic80° tilt when a safe oblique view is needed.

**E04.7 — Climb conditions.** A configured2–3m recovery intention is not measured height gain, safe clearance or success. The protocol and native recovery may disagree about height/phase; identify which owns actual Z. Check ENU-up versus body/NED-down signs, ceiling and start height measured from own state. No available upward clearance means no ascent permission. Avoid repeated climb budgets resetting on identity flicker. Do not climb off a supported deck because a close camera is occluded.

**E04.8 — Reacquisition.** Verify distinct fresh actual images after the loss, matching boat structure/history and target-pad metric association. Repeated delayed frames cannot count as new evidence. Test moving boat beyond old aim, another copied cross beneath the camera, partial target reappearance, a cropped marker and saturated glare. Truth labels may audit which object was reacquired but must never select it for the actor. Record if camera-downlook works but the target is genuinely no longer there; that is not proof of an aim bug or a completed recovery.

**E04.9 — Smooth continuation.** Reset only the control state justified by evidence, not the whole mission/history. Old camera references and slew histories can cause a large jump after reacquisition. Require stable public evidence before descent and hysteresis so one good fit does not cause a brief plunge. A recovery that succeeds only by excessive wobble/long holds is still unsuitable as a smooth teacher example. Check E01's synchronization and waiting requirements again after, not only before, the disturbance.

**E04.10 — Bounded failure.** Track spent local attempts and mission time in simulated capture time, not video playback time. A low-clearance failure must not escape into unrestricted global yaw sweeps, horizontal pursuit or unguarded ascent. Unknown design/geometry is not a permanent wrong-boat rejection. Diagnostic termination is not physical fallback success. Do not render/train home phases excluded by the user.

**E04.11 — Contact.** Loss after first contact, bouncing, landed-but-armed and stable-disarmed are distinct states. A `recovery_active` label after contact cannot count as an airborne rescue. Preserve strict wrong-object and water-contact scoring. No forced disarm, contact flag injection or target-coordinate-assisted touchdown. Show the whole physical ending outside E04a if the detail clip ends earlier.

**E04.12 — Learning and E04a provenance.** Bad motion causing the loss, injected overrides and harmful overshoot cannot be teacher action targets. Retain the observation history needed to understand the correction even when its preceding actions are masked. Define useful correction by validated observable error/progress over a response window, not single-frame monotonicity. E04a must reference the same raw episode/frame IDs and stay in the same data split. No temporal crop chosen to omit a harmful preceding action may turn an otherwise rejected full teacher trajectory into an unqualified success claim.

### E04 unresolved implementation decisions / blockers

- Define measured loss/arrest/recovery completion bounds and distinguish valid close-contact terminal continuation from unsupported airborne descent.
- Verify exact code paths and actual output ownership through native recovery, adapter, synchronization wrapper, safety supervisor and physical fault override.
- Validate a correction-only action-admission rule independently of simulator truth and of merely passing the physical landing scorer.

End of E04/E04a iteration.

## E05 — Initial target-opportunity handling and competing-candidate priority

### Evidence and intended distinction

Observed job: `../local_curriculum_20261020/review_batch_v1/jobs/E05_visible_start.json`. It is functionally the same visible8m/6m basic-scene task as E01, except seed/name/instance; **there is no current distinct behavioural contract**. Historical v31 E05 additionally executed18 physical fault frames and its gallery described a camera disturbance. Current Windows E05 has `fault=null`. These definitions must not be conflated.

Required proposed purpose: make E05 the explicit regression for the user's original complaint, **do not discard a useful first-frame boat opportunity or prefer an implausible distractor**. Its decision checks are stricter than merely landing in another E01 seed. The final distinct configuration is unresolved; do not claim coverage diversity from a rename. No Windows E05 has run.

### Intended sequence — E05 steps1–9

1. Construct a visible target-opportunity scene with a nearby competing non-boat or wrong object where the intended relative visual difficulty is recorded. Keep physically valid separation and enough target structure for meaningful observation; do not manipulate the recognizer's answer.
2. On the first actual image, evaluate the visible boat candidate and alternatives. Keep a potentially identifiable boat in view while accumulating distinct evidence, instead of beginning an unconditional360 scan.
3. If the boat is already recognizable as the target, establish identity and retain it. If its design is genuinely ambiguous, perform bounded safe verification of that boat-like candidate. A buoy/board detector false positive must not win merely because its objectness is higher.
4. If the initial candidate is actually a different boat, identify the wrong design only when visible evidence supports it, then take the safe rejection/search branch. If it is the target with an unseen pad, retain design identity and seek the pad view instead.
5. If the view is genuinely insufficient for any plausible boat decision, widen observation purposefully through a controlled camera/viewpoint change. Keep candidate history and explicitly explain why a global search is needed. Do not convert initial ambiguity into a forced search routine.
6. During any candidate inspection, immediately reconsider when another candidate becomes a recognizable target. Preserve safe transition dynamics; do not train continuation toward the original object merely because it was selected first.
7. Once the correct target is qualified, approach, synchronize and descend smoothly under E01's fresh-geometry/physical landing requirements. Nominal E05 has no artificial disturbance; any optional disturbance variant must be separately specified and must not mask acquisition defects.
8. If the initial opportunity cannot be used, record the reason and outcome accurately. A later accidental reacquisition and touchdown cannot turn a skipped-target episode into a passed initial-opportunity regression.
9. Present full initial acquisition at normal speed and all competing-object decisions. Keep E05 distinct by measured decision coverage or merge its accounting with nominal E01; do not count two labels as two independently tested skills.

### Per-step edge cases, failure mechanisms and required checks

**E05.1 — Purpose versus seed.** Current E01/E05 differ mostly by random seed; explicitly choose the competitive view the regression requires before generating replacement data. Offline check target and competitor apparent size, clipping, contrast and ordering, not just their world positions. A frame containing only a few boat pixels does not establish a fair immediately-recognizable-target test. A target artificially hidden after frame0 would defeat the purpose. Do not move it to the centre at run time using truth.

**E05.2 — First-frame causality.** Preparation can rotate the camera after the nominal spawn, and image delay may deliver an earlier frame. Define frame0 as the actor's first actual delivered task image and record its capture time. Check classification/tracking before a scan command is issued; do not give the search logic priority just because `started` is unset. A single frame need not justify identity, but it can justify retaining a plausible observation opportunity.

**E05.3 — Evidence and priority.** The observed local E01 target proposal had substantial but subthreshold target evidence while the buoy had strong objectness. Do not fix this by equating objectness with target identity, lowering identity thresholds, or hardcoding the target's colour/position. Compare category plausibility, design evidence, observability and safe information gain. Verify the actual selected instance offline at every decision; a correct detector box elsewhere in the frame is not proof the controller used it. Uncertain classification should elicit a useful view, not a predetermined timer.

**E05.4 — Wrong initial boat and marker absence.** Include explicit negative controls where the centred first boat is wrong, has a copied cross, lacks a visible marker, or is a reduced clone. The target without marker stays same design. The wrong boat with marker stays wrong design. A rule saying always approach the centred initial object can replace one bug with another. Do not train a definitive wrong-design label from an unscored ambiguous clone or poor view.

**E05.5 — Controlled verification.** A brief camera movement may improve structure visibility; a sweep away from the candidate may erase evidence. Check actual framing along the movement and the resulting candidate age. Track splits and changing proposal centres must not create a fake new initial opportunity. A bounded local inspection may legitimately fail; log it instead of forcing target recognition. If global search is necessary, demonstrate the visual reason and follow E02's full-survey/active-inspection semantics.

**E05.6 — Opportunity interruption.** Test target appearance on the image edge, behind a competitor, while the camera turns and after a wrong-object rejection. A recognizability/priority decision must use observable evidence, not simulator annotation. If scenario construction intended the target to appear later, check its swept visibility; if it appears early anyway, follow the target or reject the scenario-purpose claim. Never admit teacher actions that visibly ignore it merely to preserve the planned wrong-object segment.

**E05.7 — Shared landing defects.** Do not let fixing early acquisition leave the original excessive alignment wobble or near-deck waiting untouched. Apply synchronization during the entire descent, identity/metric object association, justified holds and ordinary physical disarm. If a later perturbation is added, it becomes a named variant with separate executed-disturbance evidence and correction masks, not an undisclosed change to nominal E05.

**E05.8 — Negative regression result.** Measure time and trajectory from the first useful visible opportunity to purposeful verification, time looking away, rejected alternatives and actual approach association. Numerical acceptable latency remains to be established, not invented here. A whole-episode landing score or a capture-integrity pass cannot replace those decision checks. Current unrun E05 cannot be reported passed; old v31's18 fault frames do not belong to it.

**E05.9 — Learning coverage.** Preserve raw exclusions and distinguish test variants by actual branch evidence, not filename. Do not increase nominal sampling so much that the learner learns target-always-centred or always-present shortcuts. Include balanced, physically feasible wrong-initial-object controls and search cases in a future split-frozen curriculum. E05 is a regression test definition, not proof that any existing teacher data has become eligible.

### E05 unresolved implementation decisions / blockers

- Formalize the new distinct E05 competitive initial-opportunity configuration; current seed-only duplication is inadequate.
- Freeze observability/priority and response-latency evidence requirements without using a privileged target ID in the actor.

End of E05 iteration.

## E06 — Nearby target outside initial view: genuine search and find

### Evidence and intended distinction

Observed job: `../local_curriculum_20261020/review_batch_v1/jobs/E06_search_near.json`. Basic scene, requested8m range/6m height, initial pan140°/tilt35°, target physically present, no blackout, no fault, boat0.3m/s. The current accepted range band5–20m overlaps E01 and wider search variants; initial invisibility and actual discovery must carry the purpose, not its name. No local Windows E06 executed.

Calibration evidence: the frozen policy declares vertical FOV36.1°. `landing_training/expert.py:camera_projection` uses the actual model camera matrix and FOV,640×360 image centre(320,180), depth=-cameraZ and `f=180/tan(FOVy/2)`. Future geometry checks must verify this against the actual render model/camera conventions; an assumed body-bearing minus pan angle is insufficient.

Required distinction: target **outside the initial camera view**, not an invisible/removed target. A nearby target may legitimately become recognizable early in the first survey; this covers search discovery, not necessarily the distant/unknown-inspection branch. Do not force second-pass inspection when the target is already identified.

### Intended sequence — E06 steps1–13

1. Generate a nearby moving target and initial airborne orientation with no target structure in the actual first task image. Keep it physically visible from feasible later viewpoints, safely separated from launch/route obstacles and decoys.
2. Confirm that the actor genuinely needs to search: no valid target memory carried from preparation, another episode, a prefix or a target-pointing setup command. Record actual first-view visibility, distance and initial own camera/body pose for the observer.
3. Begin a recognition survey of the surroundings. Move the camera/vehicle bearing smoothly through previously unobserved directions at a useful elevation. Track plausible boats without declaring every detected object a boat or target.
4. If a recognizable target appears on this first survey, stop the survey and verify/track it from distinct fresh views, then take step11. If it is merely an unresolved boat candidate, retain it while finishing meaningful first-pass coverage.
5. If a genuine full360 survey completes without target identification, begin the active-inspection pass. Choose the first eligible boat-like sighting on that pass, including an unresolved candidate from the previous survey when freshly encountered. Do not wait for the same recognition evidence that was impossible at the original distance.
6. Reorient and approach that candidate at safe height using fresh RGB bearing and range uncertainty. Keep observing the surroundings and candidate structure. Do not descend during identity inspection.
7. If the candidate is the target, establish design identity and fresh pad geometry, then take step11. If it is a clearly wrong boat, take step8. If still ambiguous, use bounded view-improving inspection; defer as unresolved if progress fails instead of falsely declaring wrong identity.
8. For a wrong boat, perform a safe above-object reposition only when feasible using observable localization and conservative structural bounds; keep the wrong boat below rather than land on it. Start a new full survey from that changed viewpoint, with genuine new coverage.
9. If the target becomes recognizable during any lower-priority inspection/reposition, safely redirect to it. For the dedicated wrong-first-boat branch, scenario sightlines must avoid accidentally revealing the target before the intended inspection; if they do not, label a different branch or reject the purpose claim.
10. Repeat full-survey/first-eligible-inspection branches only with meaningful new information/viewpoints and within the unchanged budget. Do not repeatedly inspect the same unresolved ghost or alternate full scans and pointless downlooks.
11. Approach the qualified target, establish stable relative tracking and camera synchronization, and descend with fresh correct-object geometry. Apply E01's alignment, wobble, delay and terminal requirements, not a special permissive search landing controller.
12. If actual geometry is lost, perform justified local recovery; if no target can be acquired within the feasible task, stop as incomplete rather than fabricate discovery or include home training/rendering.
13. Verify the actual learning sequence: initial target absent from camera→own search action→first target opportunity→appropriate candidate decision→supported tracking/landing. Accept only the search branch actually exercised; report whether unknown inspection and wrong-boat overflight were absent, failed or observed.

### Per-step edge cases, failure mechanisms and required checks

**E06.1 — Initial FOV and geometry calculation.** For each target bounding-mesh extent, project using actual camera extrinsics including camera offset, gimbal rotation, vehicle attitude and preparation drift. Check positive depth and the complete640×360 frustum; centre out-of-frame is not enough if a mast/hull is visible. Vertical and horizontal FOV differ: for square pixels `FOVx=2 atan((640/360) tan(FOVy/2))`; verify intrinsics rather than hardcode the number across renderers. Validate with actual final RGB/observer segmentation at task frame0. Do not change render visibility groups, mask pixels, hide the model or put an unmodelled wall in front of it. Initial outside-view is a scenario contract, not a command to the actor to ignore visible target pixels.

**E06.2 — No preparation/history shortcut.** Initial positioning can use environment truth for declared preparation, but its target-facing motion/history cannot silently teach the actor where the target is. Freeze an explicit task-start observation/history contract; do not indiscriminately reset a live learner in rescue cases. For ordinary E06, initialize memory without target observations and verify the actor did not receive a beacon or simulator target coordinate. Fixed spawn bearing, camera pan or seed must not become an implicit universal search-direction label across training and evaluation.

**E06.3 — Survey actually sees surroundings.** Check measured optical bearing, fresh-image coverage and useful camera elevation. Gimbal counterrotation can cancel body yaw; fast turning plus latency can skip a narrow nearby boat. A scan that spends its useful view on own airframe or sky is not effective search. Coast scenery is not a boat. Existing scan-band constants are current implementation details; choose search geometry from feasibility and evaluate coverage, not from the desire to finish360 on a timer.

**E06.4 — First encounter response.** Do not preserve an obligatory full scan after target evidence becomes adequate. Do not demand one-frame identity from a small partial view. If target appears only momentarily, retain bounded evidence/bearing without treating predicted geometry as current. An opportunity can be visually useful before a strict posterior threshold; observer review must catch an actor that simply turns away from every useful chance. First-pass early discovery is a valid E06 branch even if less than360° was needed; it is not full-survey completion coverage.

**E06.5 — Second pass.** Define what counts as first eligible boat-like encounter, how tied/overlapping candidates are ordered and how already rejected non-boats are skipped. A second survey must change the decision from remote recognition to safe information-gaining inspection; endlessly asking the same distant classifier is not progress. Counterexample: a buoy with high detector confidence encountered first must not become the inspection object merely through `boat=true`. Do not use privileged actual class/range to choose a nicer candidate. Record evidence and uncertainty for the selected opportunity.

**E06.6 — Approach visibility planning.** Before a designed wrong-first-candidate episode, compute the candidate approach corridor and likely camera frusta over a conservative envelope of own/boat motion, camera tracking and yaw. Include whole target hull/mast, not only the pad point. If target and candidate lie on nearly the same bearing, a target-visible-after-approach shortcut is likely. Reject/reposition the scene offline if the intended branch cannot be isolated safely. Exact learned trajectories are not known in advance: postflight purpose checks are still required. Never keep a wrong-candidate label when the target becomes recognizable and the teacher ignores it.

**E06.7 — Information versus movement.** Approach must increase useful structural evidence, not only reduce projected range or enlarge a false cross. Body/camera calibration, plane-height uncertainty, self-occlusion and motion blur can make the object less identifiable while nominal range decreases. Permit a bounded alternative viewing angle when safe. Keep unresolved separate from wrong-design rejection; missing marker does not change target design. A cloned structure lacking distinguishing hatches cannot be forced into a definitive identity label.

**E06.8 — Wrong boat below.** Safe above-object position depends on height, camera visibility, swept footprint, mast bounds and own drift; image centring alone is insufficient. A wrong design identified at a distance need not be flown over through an unsafe path. Record an exception instead of relaxing collision/ceiling rules. When repositioning changes the viewpoint, reset coverage appropriately while retaining meaningful wrong-object identity memory. Do not clear all memory and immediately choose the same wrong boat again.

**E06.9 — Accidental target exposure.** Distinguish appearance of unidentifiable boat pixels from recognizable target evidence. The actor cannot know a distant boat is the target from an observer's label. However it must not ignore a genuinely recognizable target to honour previous selection. Test both isolated inspection and intentional target-opportunity interruption variants. Scene rejection/relabel decisions are observer-only, immutable evidence; they must not change the camera feed or actor commands mid-episode.

**E06.10 — Loop prevention without ignorance.** Track survey epoch, actual covered bearings, selected object/viewpoint, distinct observation age and reason for revisiting. Same-image processing, track renumbering and slight position jitter cannot reset progress. Rejection expiry must permit genuinely improved evidence rather than schedule recurring wasted inspections. Distinguish a complete new search from a partial scan interrupted for good reason. A global360 after every brief local loss can throw away valid target knowledge; use local recovery where appropriate.

**E06.11 — Landing quality after search.** Search success does not excuse a wobbly descent, a stale target identity bound to another marker, or an excessive alignment hold. The boat may have moved substantially during the scan; update current relative motion from observations. Avoid using the original spawn target position. Do not train on the incorrect search portion merely because final alignment is good; action and perception segment decisions are separate.

**E06.12 — Unsuccessful branch.** A safe diagnostic stop does not establish a safe-home landing. A target missed because the setup made it unreachable is a scenario feasibility failure, not necessarily a policy failure. A feasible target missed through wrong decisions is a behavioural failure. Preserve both with explicit labels. Do not manufacture success by respawning the target, extending the budget or dropping scenery/collision geometry.

**E06.13 — Coverage certificate.** Require actual initial absence, measured own-camera search, actual later target opportunity and sensible selected-object association. No privileged truth movement trigger may control the task. Record first target-visible and first target-recognizable events separately; their distinction needs observable criteria/human review, not a hidden label shortcut. Initial absence alone is not enough: a task can still skip search through preparation memory or a deterministic target-pointing command.

### E06 unresolved implementation decisions / blockers

- Replace broad overlapping range acceptance with justified near/mid/far purpose bands verified at task start.
- Define the first-pass recognition versus second-pass active-inspection state transition and branch-specific coverage checks.
- Implement conservative offline swept-frustum feasibility checks plus actual postflight interruption auditing; neither can be replaced by a single initial-angle assertion.

End of E06 iteration.

## E07 — Mid-distance search: close the information gap before recognition/landing

### Evidence and intended distinction

Observed current job: `../local_curriculum_20261020/review_batch_v1/jobs/E07_search_mid.json`. Basic scene,28m request, accepted20–40m band,6m height, pan140°/tilt35°, target initially outside camera, boat0.3m/s, no physical fault. No current Windows E07 ran. Historical `../expert_fix_review_20261019/delivery_v31/v31_full/E07/scenario.json` instead describes an8m visible-start scene. Its nominal alignment video does **not** demonstrate current mid-distance search.

Prior evidence in `../approved_curriculum_20261020/PERCEPTION_REPAIR_V52_SUBPLAN.md`: V46mid/far stopped at100s; mid target tracks already had3+objectness confirmations153/159 times, while all six strong mid target-ID assertions associated with `decoy_dark`, not the target. That disproved the earlier insufficient-dwell explanation in those recordings. It is not a measured result of the unrun Windows E07. Subsequent rejected models do not cure this by declaration.

### Intended sequence — E07 steps1–11

1. Generate a genuinely mid-distance, initially out-of-view target with a feasible safe route from launch/search position. Verify actual range and visual size after preparation, and ensure its later recognition cannot be solved by a memorized fixed spawn direction.
2. Survey with a useful optical elevation and fresh angular coverage. Recognize a target if the evidence is genuinely sufficient; otherwise retain a distant boat hypothesis without demanding design detail that the640×360 image does not contain.
3. After a completed recognition survey without identification, enter the active-inspection pass and select the first eligible boat-like encounter. Separate boat presence from target identity, and separate category uncertainty from known non-boat rejection.
4. Reacquire the candidate at its current bearing and approach cautiously to improve angular size, structural view and classification reliability. Use public uncertainty and static clearance, not known target coordinates or a fixed28m travel command.
5. Continuously decide whether the view is becoming more informative. If identity remains ambiguous but evidence is improving, continue within bounded safe effort. If not, change a feasible viewpoint or defer the unresolved candidate with an explicit reason.
6. If a visible wrong design becomes clear, stop target pursuit and use the safe reject/above-object/new-survey branch. If target design becomes clear, interrupt remaining search and track it. A wrong-object target-classifier spike cannot bypass independent object/structure/metric consistency.
7. During inspection, handle a newly recognizable target elsewhere by safe reprioritization. Scenario generation must account for target/candidate camera geometry so a claimed wrong-first inspection is not accidentally a teacher ignoring a clear target beside it.
8. When target identity is established, approach further only as needed for reliable pad geometry and tracking. Do not start descending from distant coarse bearing/nominal-plane range alone.
9. Align and descend with synchronized camera/body tracking and actual boat motion, preserving the E01 stability and physical touchdown criteria. Searching longer must not lead to rushed or blind final descent to beat the budget.
10. On uncertainty/loss, use the locally justified recovery or bounded unresolved-search path; stop honestly when remaining budget/clearance is insufficient. No home-return rendering/training is added.
11. Audit that actual mid-distance uncertainty was resolved by purposeful viewing/approach and correct identity association. Record whether first-survey recognition, second-pass inspection, wrong-boat rejection, opportunity interrupt and final landing actually occurred; they are not interchangeable evidence.

### Per-step edge cases, failure mechanisms and required checks

**E07.1 — Distance and route feasibility.** Requested28m is not actual task-start slant range or pixel size. Track boat motion during preparation, camera/body displacement and coast/terrain crossing. Existing water-only approach permission may prevent any horizontal translation when launch is over land; do not delete that guard blindly. A mid-distance overland-to-water route needs a separately certified static transition and clearance contract before claiming the scenario is solvable. Reject infeasible draws; do not blame the actor for an impossible corridor.

**E07.2 — Presence versus recognition.** Full yaw motion can miss the boat if the camera elevation/framing is wrong. A target with enough pixels for objectness may lack enough structure for identity. Lowering identity confidence or adding dwell does not create missing visual detail. Conversely repeated high-confidence false identity on a dark decoy cannot be repaired merely by scanning slower. Audit proposed/selected boxes against actual instances and distinguish detector coverage, association, verifier classification and planner use.

**E07.3 — Active inspection eligibility.** Current raw detector `boat=true` can include buoys/boards. Define an observable shape/category plausibility test with uncertainty; do not hardcode minimum size that excludes legitimate far boats. First-encounter order must be stable under frame delay, detection ordering and track split. A target-negative posterior is not proof of non-boat, and wrong design is not the same as non-boat. A plausible wrong boat remains a legitimate safe inspection candidate; a known buoy does not.

**E07.4 — Approach direction and distance.** Nominal-plane range grows uncertain near the horizon and for tall objects. Use bounded speed, observation freshness, target framing and actual information gain. Test wrong signs/frame transforms, body yaw during tracking, moving candidates and camera offset. A remembered bearing cannot justify a long blind translation. Declared static water corridor at the current point does not certify every future segment; check the planned/swept path conservatively and audit actual physical clearances offline.

**E07.5 — Progress criteria.** A fresh frame, a new track ID or0.01m noisy range improvement must not reset a no-progress timer indefinitely. Apparent scale can increase because camera tilt changes or a different object is associated, not because the intended boat is being inspected. Maintain identity-continuity and uncertainty evidence. Do not discard a viable target solely because a fixed identity dwell expired while its view was improving. Predeclare bounded progress and stopping rules using measured dynamics/recognizer behaviour.

**E07.6 — Dark/similar decoy failures.** Include wrong dark/similar boats under both BASIC and HARD scene appearances; model/cache domain changes may affect visual negatives. The prior all-six-wrong-ID finding is a concrete regression target, not permission to exclude those frames from evaluation. Cross markers, shadows and silhouette can trigger false target scores. Require actual design evidence and target-pad consistency without privileged truth at runtime. Preserve the original failed recognition result; no demo success or recalibrated point rewrites it.

**E07.7 — Competing opportunities.** Calculate offline initial and approach camera frusta for moving target/candidate envelopes, then verify actual exposure postflight. If target recognition becomes possible mid-inspection, continuing toward a wrong/unknown object is a teacher failure even if eventual landing succeeds. A first sighting too tiny for identity can be logged without forcing a switch; record why a later view crosses the observable evidence requirement. Neither target visibility alone nor selected-candidate persistence is an automatic priority rule.

**E07.8 — Transition to landing geometry.** Design recognition may happen well before a pad fit is feasible. Keep altitude/collision clearance while obtaining the pad; do not chase a high-confidence copied cross on a nearby object. A cold close-up marker cannot establish identity without its own valid trajectory history. Check delayed capture/object association after approaching: the old distant box must not mask the wrong current object. Do not resize the rendered image or target CAD to make the detector easier unless separately specified as a different sensor/domain experiment.

**E07.9 — Final control after long approach.** Relative boat motion and camera/body yaw may differ significantly from initial values. Do not reuse initial plane intersection as a target position. Retain a stable symmetry branch and justified holds; avoid new alignment oscillations when the object changes scale rapidly. Task-budget pressure must not relax strict physical contact, support/disarm or uncertainty gates. A mid-search episode with a poor landing tail is not good action supervision end-to-end.

**E07.10 — Loss and bounded termination.** Distinguish target leaving the camera, an association error, marker occlusion, unavailable image and impossible corridor. Each warrants a different correction; a global scan is not a universal recovery. A local-memory aim has an expiration and uncertainty bound. Safe stopping, resource interruption and native collision are distinct statuses. A diagnostic stop at100s in an older experiment cannot be counted as the current180s scenario's completed result or as safe-home coverage.

**E07.11 — Learning distribution.** Confirm actual mid-distance visual evidence rather than a scenario name or distance field. Random seed changes with the same beach/path/route are not independent world diversity. Freeze family/world/trajectory splits and reserve independent tests. Do not train on retired held-out failures and later call the same worlds fresh. Correctly labelled hard-negative perception frames may be useful in a separately authorized admission path, but do not qualify the failed teacher's search actions.

### E07 unresolved implementation decisions / blockers

- Define measured visual observability/approach-progress criteria and category plausibility across the actual BASIC/HARD appearance domains.
- Resolve any land-to-water route feasibility with a declared static safety contract; current beach placement alone does not prove it.
- Preserve scenario lineage: old E07 nominal8m is not evidence of current E07 mid-distance competence.

End of E07 iteration.

## E08 — Far target: broad search followed by information-gaining approach

### Evidence and intended distinction

Observed current job: `../local_curriculum_20261020/review_batch_v1/jobs/E08_search_far.json`. Requested52m horizontal range/8m height, accepted40–60m band, basic beach scene, pan140°/tilt35°, moving target0.3m/s, no injected fault. No current Windows E08 ran. Historical v31 E08 used a visible-start8m scenario; it does not certify far discovery.

The known-development far diagnosis described in `../approved_curriculum_20261020/PERCEPTION_REPAIR_V52_SUBPLAN.md` did not support simply adding objectness dwell. `inspection_feedback_v51.py` repairs a completed-survey transition callback so the existing elevation transition actually occurs. That source change and a logged counterfactual are not proof that far-search behaviour or candidate priority is now correct.

### Intended sequence — E08 steps1–12

1. Construct a truly far, initially out-of-view but physically observable moving target, with a feasible route and camera elevations covering its apparent position. Verify actual initial range and image scale, not merely52m in a config.
2. Establish search altitude/clearance and scan calibration from own state and declared static priors. Start with no hidden target coordinates or pre-acquired target history.
3. Conduct the first recognition survey using genuine optical coverage at useful elevations. Keep plausible small boat candidates even when target-design detail is insufficient; discard established non-boats without pretending every tiny object is classifiable.
4. If the target becomes recognizable, interrupt searching and verify it. If a completed recognition survey does not identify it, start active inspection and select the first eligible boat-like encounter on that pass rather than endlessly repeating remote recognition.
5. Reorient to a fresh candidate bearing and begin a bounded safe approach that increases useful visual evidence. Move only with adequate public bearing/range uncertainty and certified path clearance. Do not wait for a close-range identity threshold before permitting every inspection approach.
6. Reobserve while approaching, adjusting the camera elevation/framing as apparent angle and scale change. Keep evaluating alternative targets and reject deteriorating/stale candidate estimates rather than blindly travelling a stored distance.
7. If a different boat is identified, take a safe reject/new-view survey branch; perform an above-object reposition only when physically feasible and useful. If still unresolved, improve the view or defer boundedly. If the target is identified, take step9.
8. If no eligible candidates are found, use a bounded new survey elevation/viewpoint with explicit new coverage. Honour completed-survey transitions and actual progress; stop rather than loop forever through the same empty evidence.
9. Once target identity is qualified, acquire its current pad geometry at a suitable stand-off and track actual relative motion before descending. Do not extrapolate far-range plane intersection into a touchdown solution.
10. Synchronize and perform the same smooth, supported approach/descent/contact/disarm sequence as E01. Preserve remaining task time for a real landing; do not rush or bypass geometry because the search was long.
11. If target evidence is lost or safe progress becomes infeasible, perform appropriate bounded local reobservation/search or terminate the boat task. A safe diagnostic stop is not target landing or physical-home success.
12. Verify that actual far-range ambiguity was overcome by useful observations and sensible movement. Record executed survey/inspection/rejection/interruption branches, sensor/input provenance and final physical outcome separately. No camera zoom/render resolution change may silently remove the intended far-range difficulty.

### Per-step edge cases, failure mechanisms and required checks

**E08.1 — Far visibility and feasibility.** Use full3D camera projection, apparent hull extent, image contrast, clipping and static occlusion checks. Horizontal52m and8m height do not imply the boat is inside the initial35° tilt's vertical view. Test whether selected survey bands actually cover the target's angular elevation after preparation. Target motion and coastline curvature may move it behind terrain. Ensure the task is solvable within original ceilings, speeds and budget; no target teleport, scale enlargement or route shortcut to manufacture a far example.

**E08.2 — Search setup safety.** A boat route can be safe while the drone's direct land-to-water approach crosses tall static rock/trees. Certify a declared static transit route if necessary; a water-only guard should not be blindly removed because it blocks movement. Do not start above the allowed ceiling to see farther. Initial camera targeting from dynamic truth would leak the answer; actual frame0 must remain target-outside-view for this variant.

**E08.3 — Small-object evidence.**640×360 pixels and the detector's resized inputs constrain which structure is observable. A24px implementation size condition is not proof of identity at every shape/contrast. Distinguish proposal absence, category ambiguity, wrong classification and lost association. Tiny glare peaks and dark boats can accumulate repeated false confirmations. More dwell cannot resolve a systematic false classification; retain distinct fresh evidence and visual uncertainty. Do not declare a target wrong simply because its marker is subpixel or absent.

**E08.4 — Active-inspection transition.** Test full first-survey completion, target-recognized interruption, no-candidate completion, wrong-object completion and stale-candidate retirement separately. Current code can select a retained nearest object after the first survey rather than the requested first encounter on an active second pass. Formalize the intended order before changing code. Unconfirmed target design must not block all safe exploration; conversely generic objectness alone must not authorize pursuit of a buoy.

**E08.5 — Uncertain far range.** Near-horizon rays make plane-height errors produce large range errors; low buoys and elevated superstructures violate a common point-height assumption differently. Require conservative bounds and fresh visual feedback, not exact range faith. No negative/infinite range, horizon crossing, wrong yaw sign or image-coordinate convention may generate a long uncontrolled translation. A single-point current water check is not full corridor certification. Explain every unsafe-to-approach veto so a frozen drone is not presented as intelligent searching.

**E08.6 — Scale and viewpoint changes.** As a boat grows in the image, detector boxes split, pad centres become visible and dominant features change. Association must not jump from a target hull to a nearer wrong cross or refresh stale range through own-motion prediction. Camera tilt suitable at far range may be poor near the boat; adjust with continuity and actual framing, not sudden fixed-angle snaps. Survey reference/body yaw and camera-pan conventions must agree. If a recognizable target enters while pursuing another candidate, it must interrupt safely; check swept scene visibility offline and actual decisions afterwards.

**E08.7 — Wrong and unresolved boats.** A distant different design may remain unknown until close; this is legitimate inspection, not a false target success. Once strong wrong-design evidence appears, stop target pursuit. A wrong-object overflight through unknown tall geometry is not justified by the user-requested storyboard; use safe bounds or score a different rejection branch. Retain useful rejection/viewpoint memory without permanently suppressing the actual target because of an alias. No identity labels for ambiguous reduced-clone views.

**E08.8 — Scan/downlook loops.** Verify actual optical sector coverage and elevation index transitions, not only an incremented epoch or a log saying new survey. After an inspected stale ray is retired, `inspection_feedback_v51` calls `_new_survey` only in certain conditions; audit whether that path executes and whether other paths still bypass it. Repeated360s with identical elevation/viewpoint and no candidate processing do not teach active search. A downlook that cannot see far boats should not automatically reset an already completed useful scan. The exact elevation schedule needs evidence, not blind timer changes.

**E08.9 — Target and metric ownership.** A learned target probability can be wrong, especially on a similar dark decoy. Check qualified identity over observable structure and independent metric consistency; offline association catches false teacher labels but must not drive actor selection. Do not treat a copied marker as identity or a nominal-height coarse range as precise pad pose. Retain valid target history into near-field partial views while refusing unsupported cold marker-only acquisition.

**E08.10 — Time and final alignment.** Use actual simulated mission progress, not wall-time benchmark speed, to establish feasibility. Distant transit, wrong inspections and recovery consume real task budget. Do not extend the mission until one seed succeeds, omit slow failures, or increase descent speeds to hide search inefficiency. Alignment/wobble and unnecessary waiting are still unacceptable after successful search. Preserve actual terminal contact/disarm evidence without training long stationary waiting as a manoeuvre.

**E08.11 — Bounded failure diagnosis.** Distinguish scene infeasibility, insufficient perceptual detail, missed detector proposals, false identity, bad candidate choice, corridor veto and feedback integration loops. Each requires different evidence; a generic extra epoch/confidence relaxation cannot solve them all. Resource interruption is separate from a completed policy failure. No unexecuted branch can be counted from a configured setting. Exclude unsupported actions even when useful negative RGB may later be admitted under a separate contract.

**E08.12 — Actual far skill and splits.** Verify actual range distribution at task frame0, first useful boat observations at distance, purposeful approach and recognition improvement. Camera crop/zoom augmentation does not constitute a physical far-search demonstration. Same route/palette with different seeds is not five-map coverage. Old E08's8m nominal video must remain historically labelled and cannot satisfy this purpose. Keep failed/retired evaluation worlds outside future training and report partial coverage honestly.

### E08 unresolved implementation decisions / blockers

- Prove safe information-gaining approach and scan-elevation coverage in the actual generated far geometry; current config alone is insufficient.
- Replace whole-flight success anecdotes with a causal breakdown of proposal, association, classification, selection, motion permission and visual progress failures.
- Validate all survey-transition entry points and explicit first-eligible inspection ordering; one fixed helper path is not a repaired search system.

End of E08 iteration.

## E09 — Supported terminal landing: teacher demonstration versus healthy learner handoff

### Evidence and intended distinction

Observed current job: `../local_curriculum_20261020/review_batch_v1/jobs/E09_terminal_handoff.json`. Basic visible-start8m/6m scene, no fault, `mode=dagger`, `prefix=true`, requires no unnecessary assistance after handoff. `dagger_v48.py` runs learner and teacher on the same actual RGB/history, physically flies a teacher prefix and releases to the learner after3distinct qualified images at public clearance0.75–1.5m. The learner is the original R15 runtime, not a new action policy trained from V47 verifier data. No local Windows E09 ran.

Historical v31 E09 audit instead has1732 **expert-owned** rows and no learner handoff. The gallery explicitly called it a teacher-only demonstration. These are different products. Required naming before repair: **E09-T** for teacher terminal demonstration, **E09-H** for healthy learner handoff/false-intervention regression. The current job is E09-H, not the expert-only video requested by the user. Do not silently replace one with the other or claim either is an observed rescue.

### Intended sequence — E09 steps1–12

1. Declare whether this run is E09-T or E09-H, its owner semantics and exactly which terminal skill it tests. Use a physically reachable moving target and normal preparation, without faults, teleportation or cold-reset tricks.
2. Have the teacher acquire the correct boat, approach and synchronize through a sensible E01 prefix. Both prefix quality and intended terminal setup must pass; landing later cannot forgive a pointless scan or buoy pursuit earlier.
3. For E09-T, keep the qualified teacher driving through touchdown and skip step4's learner release. For E09-H, keep the learner observing/processing the same actual images, timestamps and executed action history throughout the real teacher prefix.
4. In E09-H only, release control to the learner when near-deck public geometry, framing, motion and own state genuinely support the intended terminal task. Record the exact transition and previous executed command. Do not let the teacher land first and then call the remainder a learner test.
5. Monitor actual terminal progress and uncertainty. If the current owner is making supported progress toward correct-target contact, preserve its control; a pixel-centre drift or slow visual appearance change alone is not evidence it needs rescue.
6. Distinguish normal descent, first contact, touchdown commitment, stable support, PX4 landed and disarmed. Allow legitimate supported terminal commitment without demanding an impossible full-boat image at centimetres above the pad.
7. If genuine airborne failure develops before supported contact, use the justified safety/educational-assistance branch with correct ownership and evidence. In E09-H this is a failure of the healthy-handoff purpose even if assistance lands; preserve it rather than relabel as nominal success.
8. Continue supported contact confirmation and ordinary PX4 disarm with no gratuitous recovery climb, reorientation or return-to-search. Do not force disarm to shorten the clip.
9. End only on the strict physical outcome/terminal record or an honestly declared task failure. Do not continue collecting stationary rows just to fill an episode length.
10. Audit every final command through learner/teacher, wrapper, slew/bounds, supervisor and PX4 path, including the terminal no-command frame. The owner label describes what actually drove, not which component produced a convenient diagnostic.
11. Present E09-T as an expert terminal demonstration and E09-H as teacher-prefix→learner terminal control, with normal-speed context around handoff/contact. Do not call the latter an independent full learner flight or either one a rescue without a genuine preceding struggle.
12. Apply separate segment eligibility to useful teacher correction/terminal actions, learner actions, prefix, supervisory overrides and stationary confirmation. Preserve the full historical context for audits even when a consumer excludes unnecessary action targets.

### Per-step edge cases, failure mechanisms and required checks

**E09.1 — Product identity.** A filename E09 has meant teacher-only and mixed ownership in different revisions. Freeze scenario/owner lineage in the manifest, overlay and outcome report. Human review of an expert video cannot approve a later different learner-handoff process by implication. A near-deck prefix test and a teacher terminal demonstration need distinct coverage rows and cannot be double-counted as two independent landings from one trace.

**E09.2 — Prefix behaviour.** Do not allow the E01 visible-target skip or buoy priority failure to create a supposedly good terminal start. Prefix geometry must belong to the actual selected target. Excessive wobble, unnecessary holds or repeated reorientation before handoff are still teacher defects. True initial airborne state and valid own observations are required; no XYZ reset onto an ideal approach point.

**E09.3 — Recurrent/history continuity.** Both actors must consume the same delayed actual image and actual previous executed prefix command, not the learner's unexecuted proposal. No reset of learner visual memory/GRU/filter/controller at handoff to manufacture a perception failure. Conversely repeated processing of a capture must not add new evidence. Teacher inference while learner owns is shadow work, not actual driving; logging must distinguish it. Memory/side effects in wrappers must not secretly make one actor's state appear to be the other's.

**E09.4 — Handoff readiness.**3frames at25Hz span only a short interval; the existing count is an implementation fact, not proof of settled dynamics. Check actual relative motion, view quality, delay and distance from physical contact. A0.75–1.5m public clearance fit can be wrong or from another object; audit association offline. A handoff that occurs after landing, during a fault, while the learner lacks necessary actual history, or just before a safety override skips the intended healthy terminal task. Do not use true clearance to decide actor handoff.

**E09.5 — Progress and false takeover.** Correct lateral tracking can move the marker in the image while vertical clearance decreases. A stationary pixel watchdog can interrupt healthy descent/contact. Measure fresh public progress and uncertainty, not a fixed central-pixel condition alone. The existing terminal/vertical-progress exemption must be tested in the actual active ownership path. Do not exempt every `touchdown_commit` string without checking whether the landing is supported and associated with the right boat; a learner can claim a terminal phase on a wrong cross.

**E09.6 — Contact state machine.** One foot touching, a bounce, water contact, wrong-board contact and stable support are distinct. Near-field camera saturation/occlusion is expected in some supported terminal states and must not automatically erase target identity or trigger search. Airborne geometry loss is not normal terminal occlusion. Keep existing native physical support/contact checks and public PX4 indicators; no hidden truth in control. Do not assume a controller phase alone proves physical landed state.

**E09.7 — Genuine exception.** Emergency safety may still be necessary; the healthy-handoff scenario is not permission to disable it. An educational intervention requires observed struggle, not a tiny initial requested descent or mere disagreement with the teacher. If the teacher is itself wrong/unready, do not use it as an oracle. Record safety, educational assistance, failed handoff and assisted terminal landing distinctly. Retain this as negative regression evidence, not a passed healthy learner terminal example.

**E09.8 — No terminal false recovery.** Old tests took over after the vehicle was already supported; that does not save a landing. Check active/inactive recovery branches, camera-reference expiry and timeout handlers when actual landed but still armed. A lost marker after stable support must not restart a360 or command ascent. Ordinary disarm retries need bounded timing and real PX4 land-detector evidence; forced arm flags are prohibited.

**E09.9 — End-of-episode semantics.** PX4 landed/disarmed and strict stable target support are separately recorded. Preserve enough frames for actual confirmation, then stop; do not interpret user dislike of unnecessary waiting as authorization to remove physical confirmation. Stationary safety-required frames can remain audit evidence without being action-imitation targets. Diagnostic timeout or process termination is not contact/disarm success.

**E09.10 — Actual command ownership.** The runner bounds/supervises actions after the selected actor. Check whether an outer limiter changes a policy/teacher command and whether that change is recorded as an override instead of being silently attributed to the actor. The final sent command must be the next observation's previous action; terminal rows must explicitly say no command was sent. Legacy zero expert fields are unusable; shadow expert labels are not identical to executed learner actions. Hash-bind the exact learner and teacher weights used.

**E09.11 — Honest human review.** Overlay actual owner every frame, including expert prefix, learner, safety and terminal no-command. A video predominantly showing teacher prefix is not learner-only reliability. A teacher-only video is not DAgger rescue evidence. Show handoff/contact at normal task speed and retain the full flight so a terminal crop cannot conceal earlier bad decisions. Historical v31 teacher-only evidence must remain labelled as such.

**E09.12 — What actually learns.** Perception training can use admitted RGB labels under its own criteria; it does not learn terminal state-machine timing or improve explicit control by seeing saved actions. If future action imitation is added, define its observation/history/action contract, override masks and useful-response windows separately. Do not admit failed teacher prefixes, unnecessary pauses or all healthy learner outputs as expert targets. No home-phase data. No eligibility release simply because a technical command audit passed.

### E09 unresolved implementation decisions / blockers

- Resolve E09-T versus E09-H scope explicitly before implementation/video generation. Current mixed job cannot stand in for an expert-only demonstration.
- Define measured readiness/progress and supported-terminal evidence, then test false intervention and unsafe-terminal-claim counterexamples together.

End of E09 iteration.

## E10 — Natural learner struggle on a copied-cross distractor, followed by a real teacher rescue

### Evidence and intended distinction

Observed current job: `../local_curriculum_20261020/review_batch_v1/jobs/E10_natural_rescue.json`. Hard scene, requested12m/6m visible target, foreground copied-cross board, original learner owns from task start, no expert prefix and no fault. It requires actual learner struggle followed by teacher control. No local Windows E10 ran. Its scene placement is not proof that the learner actually chooses the board.

Historical V48 `../approved_curriculum_20261020/vm_results/v48_learner_struggle_audit.json` records367policy rows then1164expert rows and a physical landing. Its takeover evidence at task14.68s describes6.92s of actual descent,1.463m observed height loss and174distinct captures without a qualified landing; it explicitly does **not** claim online knowledge of wrong identity. This is evidence of one mixed-control intervention, not universal teacher competence or proof the learner would crash.

Audit caveat: the exported original `learner_struggle_marker_object_association.json` reports19 teacher-owned marker associations on another object. The later `audit_offline_associations_v50.py` distinguishes unqualified internal fits from accepted target/descent geometry, but the presence of that source is not a completed replacement receipt. Reconcile the exact evaluated scope/receipt before saying those19 rows are either accepted wrong-target actions or harmless hypotheses. Never silently select the more flattering interpretation.

### Intended sequence — E10 steps1–12

1. Generate a physically feasible target-plus-copied-cross-board scene with the board plausibly encountered by the learner and a real reachable target available to an observable teacher. Preserve safe separation, real CAD/contact and final-frame camera geometry.
2. Start the learner in control with honest actual RGB/own-state history. Run the teacher as a same-observation shadow, not an oracle with current target truth, segmentation or a cleaner camera feed.
3. Allow the learner's actual decisions to reveal whether it handles the scene, inspects the wrong object harmlessly, or begins a sustained problematic pursuit/descent. Do not label a tiny startup command or simple teacher disagreement as a genuine struggle.
4. Accumulate public evidence of the problem: actual requested/executed motion, own measured progress/loss, image freshness and lack of qualified landing support. Use a wrong-design pursuit reason only when the acting system has observable evidence for wrong design, not because the evaluator knows it is the board.
5. Preserve an independent emergency-safety path for invalid sensors/commands or imminent unsafe motion. Do not let the learner approach collision merely to wait out an educational timer; classify a safety intervention separately from the intended genuine-struggle rescue.
6. Once a genuine bounded struggle is established and the teacher has a valid corrective strategy, latch teacher ownership. Record the exact evidence, owner transition, actual previous command and teacher proposal. If no trustworthy correction is available, perform the safe exception rather than hand control to a merely finite but incompetent teacher.
7. The teacher first arrests unsupported descent/pursuit and stabilizes the camera/vehicle as needed using observable state. It must not continue targeting a copied cross as if it were a valid landing pad. Localize/identify through current images and safe geometry, not hidden board/target coordinates.
8. Reassess visible boats and recognize the actual target, or perform a purposeful bounded search/inspection when the target is not yet identifiable. Prior learner mistakes must not contaminate teacher identity/metric memory or make the wrong board permanently count as the target.
9. Approach and land on the correct boat through smooth synchronized tracking/descent and strict contact/disarm. Preserve the actual recovery history; no reset, teleport or separate replacement flight may stand in for the rescue continuation.
10. If the learner handles the scene without struggle, keep that as a successful non-rescue/control case and mark rescue coverage missing. If the teacher fails, record an unsuccessful rescue. If the task stops for resources/setup, report interruption; none are interchangeable.
11. Present the learner-caused difficulty, takeover and teacher-driven correction at normal speed with explicit ownership. Also provide the teacher segment/full context so the user can inspect the expert's actual behaviour rather than mistake learner footage for a demonstration.
12. Admit only separately validated teacher/shadow labels on genuine learner-visited observations. Exclude learner, injected/safety/override actions and harmful teacher decisions from action targets. A teacher-assisted landing is never an independent learner success and is not proof that action training has occurred.

### Per-step edge cases, failure mechanisms and required checks

**E10.1 — Scene induces opportunity, not a scripted failure.** A foreground board can be offscreen after preparation, outside the learner's actual proposal, intersecting a route, or so obvious it is trivially rejected. Check real apparent size, view ordering, board-target separation and safe escape/recovery path. Do not move the board toward the learner mid-flight, change its geometry to disable collision, hide the target or force the learner's action to obtain a rescue. A scenario generator can select meaningful reviewed difficulty, but a configured trap is not an executed struggle.

**E10.2 — Same information and history.** Both actors must receive identical actual images/capture times, sensor validity, own telemetry and previous executed actions. Teacher shadow state evolves through learner control; it cannot be initialized from the target's true pose at takeover. Do not reset learner memory to create a cold close-up failure. Original R15 learner weights and new teacher/verifier weights must be recorded distinctly; the learner does not magically consume the new verifier merely because both are loaded in one process.

**E10.3 — Genuine difficulty.** A planned inspection of a plausible unknown boat can be sensible even if its true identity is wrong; do not interrupt it just for disagreeing with hidden truth. A tiny initial downward proposal without actual loss is not the rejected preventive-rescue example. Conversely unsupported actual descent can be a meaningful problem even when the learner reports a confident marker fit. Determine behaviour from actual commands, own measured motion, current image and qualified support, not phase names alone.

**E10.4 — Evidence boundaries.** `unverified_descent_v48.py` uses finite distinct-image persistence, real own height loss and lack of qualified teacher landing; its numerical thresholds are existing development settings, not a universally safe detection latency. Test capture gaps, stale pose, repeated frames, noisy altitude, normal boat/wave motion, legitimate terrain changes and supported terminal descent as counterexamples. Do not label unverified descent as visually known wrong identity. Teacher wrong-object classification itself can be wrong; offline association must challenge it.

**E10.5 — Safety before spectacle.** Educational persistence timers must fit available stopping distance/clearance; a low-altitude learner cannot wait for1m loss plus seconds of persistence. Keep an independent protective supervisor, but tag its actions and reason honestly. A safety hold followed by expert driving is assisted/safety recovery, not the same evidence as a natural prolonged struggle. Do not claim the learner would have collided without running an appropriately separate, safe counterfactual study; one actual trace cannot prove that prediction.

**E10.6 — Teacher readiness and latch.** Current `expert_ready` largely tests finite action and absence of an intervention; this does not prove semantic correctness. Readiness must mean the proposed arrest/recovery/search action is supported by observations and validated for the state, even if target identity is temporarily unavailable. Do not require a fully solved target pose for every safe recovery, or accept any finite zero vector as a skilled teacher. Avoid rapid learner/teacher toggling; preserve bounded takeover count and explicit release policy. Exact command owner after outer safety/limiting must match the recorded label.

**E10.7 — Corrective first action.** Test actual descent momentum, body-frame braking, camera tilt limits and boat/board relative motion. A shadow fit on the wrong board may be an internal rejected hypothesis or an accepted wrong target; inspect identity/descent permission and actual command, not only the fitted point. Bounding-box association alone is imperfect with overlapping objects; keep its stated scope and use exact capture evidence. A safety arrest is not automatically an action-imitation teacher label; validate ownership and useful correction separately.

**E10.8 — Recover the right goal.** Do not let teacher tracks inherit the learner's selected marker as confirmed boat identity. A visible target alongside a board must receive the proper priority; avoid E01's buoy/wrong-candidate bug. If geometry is unavailable, target identity and pad readiness stay separate. A target that moves out of the old view requires observable reobservation, not true-world pursuit. An initially wrong inspection can become useful negative perception data while its bad action labels remain excluded.

**E10.9 — Continuous physical rescue.** No teleport to a convenient teacher start, pose reset, target-relative velocity injection or replayed ideal teacher suffix. Both controller internal slew and actual vehicle velocity carry across ownership. Check that the teacher can recover from the learner's actual state rather than merely land from its own nominal prefix. Excessive alignment wobble, unnecessary waiting and repeated target loss remain defects even after a legitimate takeover. Verify all wrong-object contacts, water and strict final target support/disarm.

**E10.10 — Missing coverage and outcome accounting.** A learner-only success is welcome but does not prove expert rescue. A foreground board missed by the learner is not a failed policy; it is missing intended challenge coverage. A teacher landing after contact on the board is not a clean rescue. Resource failure is not policy failure. Preserve every attempted scene and branch count rather than cherry-pick only triggered/landed examples without reporting the denominator. Retire evaluation worlds before any tuning.

**E10.11 — Videos actually show the expert.** Keep enough learner context to demonstrate the difficulty, then visibly label the takeover and sustained teacher segment. A mostly learner video cannot answer the user's request for an expert demonstration; an expert-only rerun of the same starting scene cannot prove a rescue from the learner's difficult state. Provide both views with explicit provenance if both are needed. A teacher crop must not conceal how it selected a wrong object after takeover.

**E10.12 — Labels versus executed behaviour.** Shadow teacher proposals before takeover may be valuable only if independently qualified on those observations; learner actions never become teacher targets by relabelling owner. No generic `expert_label_valid=true` based on finiteness or fresh sensors may grant admission. The original legacy zero field is not the proposal. All current raw eligibility remains false; no new action/GRU/RL training exists. Perception-frame admission and any future causal action-supervision contract must stay separate, with history-preserving masks and explicit failed-segment reasons.

### E10 unresolved implementation decisions / blockers

- Qualify observable teacher readiness and educational trigger persistence together with safety stopping-distance counterexamples; do not trade safe operation for a dramatic rescue video.
- Reconcile historical association audit versions/receipts before making a blanket clean-teacher claim about V48.
- Define two deliverables explicitly: actual mixed-control rescue evidence and the clearly tagged teacher-driven correction segment. They must not be confused with an expert-only nominal rerun.

End of E10 iteration.

## E11 — Moving target, delayed camera, actual loss and expired-memory recovery

### Evidence and intended distinction

Observed current job: `../local_curriculum_20261020/review_batch_v1/jobs/E11_expired_memory.json`. Hard scene, requested8m/6m visible start, boat0.9m/s, waves0.05m, two decision frames of camera delay (nominal80ms at25Hz), teacher prefix followed by learner, bounded physical tilt disturbance2s. It requires actual metric loss and actual learner-struggle→teacher takeover. No current Windows E11 ran.

Observed historical failure: `../approved_curriculum_20261020/candidate_exports/experimental_v48_local_recovery/package/evidence/audit/expired_memory_audit.json` reports failure, zero policy rows, no triggered fault, no loss/recovery, no educational transition and zero post-takeover expired-memory-camera frames. That run never reached the intended situation. Calling it a rescue/expired-memory demonstration would be false.

Memory limits are not one universal timeout. The pinned original `persistent_target.py` separately exposes provisional seed validity≤0.25s, motion-hold≤1.5s, tracking prior≤2s, local aim≤4s, each with other conditions/uncertainty bounds. `camera_axis_continuity.py` has a separate8s reference-retention condition. A2s tilt command does not itself prove any particular memory expired. `local_downlook_v22.py` uses actual own encoders to request80° down only when local-aim memory is unusable, without granting XY/Z motion.

### Intended sequence — E11 steps1–13

1. Define and construct a physically feasible fast-moving-boat scene with delayed actual RGB, adequate recovery envelope and a meaningful opportunity to lose and reacquire the target. Keep the target physically present and the fault bounded; do not manufacture expiry through a clock jump or state reset.
2. The teacher acquires the correct boat, follows its motion and reaches a valid near-deck handoff state through a sensible physical prefix. Both learner and teacher process the same actual delayed images and executed command history.
3. Release to the learner only when the declared public readiness criteria hold. Record actual learner-owned motion before any disturbance. If handoff never occurs, stop/reject this purpose rather than presenting teacher-only acquisition as learner rescue.
4. While the learner genuinely owns control, trigger the bounded physical tilt fault from fresh public geometry before terminal contact. Record commanded and actual disturbance, actual camera motion and exact ownership; safety overrides remain distinct.
5. Measure what really happens: geometry loss, target visibility, learner response and the age/uncertainty/validity of each memory component. If loss does not occur or the learner reacquires without expiry, report that branch accurately rather than force the intended failure.
6. Let a supported, bounded learner recovery progress without premature educational takeover, while retaining independent emergency protection. Identify genuine sustained difficulty using current public evidence, not merely elapsed time since injection.
7. When an actual need for teacher correction is established and a valid corrective strategy is available, latch teacher ownership without resetting its observation history or target filters. Record whether local-aim memory is actually unusable at/after this transition.
8. With valid local memory, aim using its bounded prediction. With unusable memory, command a purposeful encoder-based local downlook instead of a generic horizon scan. Keep current XY/Z safety/recovery guards; a camera fix alone must not authorize following or climbing.
9. If safe and necessary, widen the useful local view with bounded recovery motion while tracking the moving-target uncertainty. Do not chase the last known position indefinitely or remain motionless while a predictable nearby moving boat leaves every plausible view.
10. Reacquire from distinct fresh actual images, reconcile target identity/history and obtain new correct-object pad geometry. Restore camera synchronization and tracking before supported descent; do not equate fault end with recovered perception.
11. Complete strict target contact/support/disarm, or record unsuccessful recovery when safe reacquisition is not possible within the unchanged budget. Do not create home-training/rendering or an artificial teacher landing suffix.
12. Show normal-speed learner struggle, actual takeover, the unusable-memory branch, camera aim and recovery continuation, with owner and event timing visible. If the requested primary artifact is teacher-only, additionally label its distinct teacher-driven demonstration; it is not evidence of a learner rescue.
13. Admit only the actual useful teacher correction segments under an independently qualified action contract. Keep fault causes, learner actions, failed prefixes, safety overrides, unnecessary waiting and harmful corrections excluded. Report each branch requirement separately; a final landing cannot stand in for expired-memory recovery coverage.

### Per-step edge cases, failure mechanisms and required checks

**E11.1 — Feasibility without a scripted failure.** At0.9m/s the boat can travel substantially during setup, loss and recovery; verify actual state after physical preparation, route curvature, swept separation and available camera view. A2s tilt may not create long enough loss for local memory to become unusable; do not extend beyond the existing bound, reset memory or advance simulated time without physics to force that branch. Camera delay must use real capture/delivery queues and matching own-state history, not copied stale RGB with fresh timestamps. Scene selection may seek a meaningful feasible challenge but must report missing coverage when the learner handles it.

**E11.2 — Prefix can be the actual blocker.** The historical failed run never handed over. Verify initial opportunity handling, correct-object acquisition and boat-speed tracking before attributing failure to expired-memory logic. Faster motion and wave-induced camera/pose uncertainty may prevent the prefix readiness condition. Do not silently lower confidence, move the boat closer or add an oracle target lock to reach the desired test. A teacher that cannot reach this state has not demonstrated the skill needed to teach recovery from it.

**E11.3 — Handoff history.** The learner must not start with a cold cropped marker image and empty history after a teacher prefix. No reset of GRU, filter, controller or scene to induce failure. Exact actual teacher-prefix commands, not learner shadow proposals, enter subsequent history. Check that actual learner ownership persists long enough to establish the intended task instead of a same-tick handoff/takeover. Capture-based readiness must not count repeated delayed frames as separate evidence.

**E11.4 — Fault executes under the right owner.** Current runner restricts mixed-case fault execution to policy ownership; a setting can therefore exist but never act. Verify actual owner, final bounded/supervised tilt command, encoder excursion and meaningful airborne state. If teacher takeover occurs before the fault, label that different event and do not credit E11's disturbance branch. A trigger near actual contact may be terminal handling rather than loss recovery. Physical tilt is not image masking or pan rotation; check the correct axis/sign and captions.

**E11.5 — Distinct memory validity.** Log actual measurement age, position/velocity uncertainty, `tracking_prior_valid`, `motion_hold_valid`, `local_aim_valid` and camera-reference state separately. Prediction does not refresh measurement time. A memory can become unusable through uncertainty before a nominal age limit, or remain usable after the fault ends because fresh observations resume. A helper named expired-memory is not proof it ran. Distinguish target-design history from local geometric aim; loss of one does not necessarily erase the other.

**E11.6 — Learner progress and safety.** A learner climbing/reorienting with useful observable progress should not be interrupted by a short generic loss timer. Conversely a learner descending without support must not wait through a fixed long timer near deck for educational evidence. Current takeover code includes development bounds such as recovery gain/time; verify actual dynamics and active paths, not just those constants. Emergency safety remains separate and can make the intended educational branch unavailable. Do not call a successfully self-recovering learner an expert rescue.

**E11.7 — Qualified assistance.** Teacher readiness is not simply finite vectors or absence of an intervention string. It needs a supported safe arrest/reobservation strategy in the actual learner-visited state. A teacher whose geometry is tied to another cross must not be trusted because it has higher confidence. Its shadow history must be continuous from the same delayed images. Preserve latching/counts and record exact teacher takeover reason; do not reset the supervisor to make the transition appear cleaner.

**E11.8 — Downlook path and overrides.** Test both active-native-recovery and inactive/camera-only paths: earlier code corrected the wrong branch. Check actual output after wrappers, final guard and safety supervisor, not just the helper return flag.80° down is an existing fallback, not proof it always sees the moving boat; a valid local aim must not be overwritten unnecessarily. Pan wrap, gimbal limits, body yaw and near-nadir singularity can point elsewhere. No camera-only correction may silently change XY/Z or grant unguarded ascent.

**E11.9 — Moving-target recovery.** Old target velocity becomes uncertain; do not follow indefinitely or assume a stationary target. Hovering may be the only justified safe action when motion memory expires, but then acknowledge the loss of search opportunity rather than claiming optimal tracking. A wider view/climb requires conservative clearance and a finite budget; avoid trading a target-loss failure for a mast/terrain strike. Declared static priors cannot include hidden moving-boat state. Measure actual camera coverage and true clearance offline, without feeding truth into the actor.

**E11.10 — Delayed reacquisition.** An80ms-old image and fresh own pose cannot be combined as simultaneous geometry without proper history compensation. Reprocessing a pre-loss frame cannot restore identity/metric readiness. A new marker fit can belong to a different object; require valid structure/history and correct association. A still-valid design history may support a near-field view but cannot authorize blind descent. Synchronization references/filter state can jump after memory reinitialization; inspect actual settling and avoid new oscillations.

**E11.11 — Genuine outcome.** Post-takeover target landing needs continuous physical state from learner difficulty, not a separate ideal teacher run or reset. Strict contact/water/wrong-object failures remain active. If recovery fails, preserve the failed path and stop before excluded home phases. If no fault/handoff/expiry occurred, even a landing is only another branch, not the intended E11 pass. Resource interruption and actor failure stay distinct.

**E11.12 — Reviewable expert footage.** Mark prefix, learner, fault, safety, teacher correction and terminal frames. Show evidence of unusable memory and actual downlook alongside the camera, without obscuring the image. Derive windows from frame IDs and both capture/task clocks; previous pan/tilt and task/mission caption mistakes must not recur. A short clip omitting the failed prefix cannot establish scenario success. Expert-only demonstration and actual rescue should have explicit different artifact names.

**E11.13 — Learning eligibility and honest denominators.** Require separate checkboxes for prefix readiness, actual handoff, executed physical fault, meaningful loss, observed learner struggle, teacher takeover, actual unusable-memory path, reacquisition, sensible correction and physical landing. Missing one cannot be filled from another revision's results. Keep observation history when masking cause actions. No source-level test, configured duration or eventual scorer success grants teacher action eligibility. A perception-only update will not learn the expired-memory branch of the explicit controller.

### E11 unresolved implementation decisions / blockers

- Determine a feasible naturally occurring expired/unusable-memory branch under the existing2s disturbance bound, without memory resets or disabled safety. If this setup cannot exercise it, redesign the physically feasible scenario and report the change explicitly.
- Establish a teacher-only expired-memory demonstration contract separately from a learner-struggle→teacher rescue contract.
- Verify each memory state and every command-owning wrapper against exact actual capture history; do not use the8s camera-reference timeout as a universal memory-expiry label.

End of E11 iteration.

## E12 — Historical target-absent/search-loop case; home phases explicitly excluded

### Evidence, exclusion and intended distinction

Historical `../expert_fix_review_20261019/delivery_v31/v31_full/E12_audit.json` reports a4231-row `home_landed` episode including scan974, reorient384, inspect930 and explicit return-home/land-home/contact/disarm phases. Its gallery calls it target absent; the scenario file alone does not show the harness-level target-absence change. Do not infer the actual rendered target-presence state from that scenario file alone.

The user's later instruction explicitly excludes return_home and land_home rendering/training. The current local review plan has **no E12 job**. This section documents the original repeated360→downlook→360 failure and the boundary of scope, not authorization to regenerate a home demonstration or a claim that E12 is fixed. Any future negative/search-exhaustion diagnostic must be separately scoped without home-phase data.

### Intended sequence — E12 steps1–9

1. Identify which regression is being analysed: actual target absent in an explicitly declared negative environment, or target present but not yet found. Record observer truth separately; the actor must not receive an absence flag or know which variant it is in.
2. Begin with honest own-state/camera history and a physically valid scene. Search for a target using actual RGB and safe static priors, not a predetermined timer that already knows the answer.
3. Conduct a useful recognition survey and record actual optical coverage. If a recognizable target is observed in a present-target control, interrupt and pursue it sensibly; the negative-test name must not force the actor to ignore it.
4. When a recognition survey completes without identity, enter the first-eligible active-inspection branch for plausible boats. Inspect safe unknowns, reject known non-boats/wrong designs with evidence and retain unresolved uncertainty without fabricating a target.
5. After a wrong-object inspection/reposition or an empty completed survey, choose a genuinely useful new viewpoint/elevation or next candidate within finite mission limits. A local downlook is justified by a local lost-target/contact/recovery reason, not automatically by finishing every360.
6. Detect repeated no-information loops: identical coverage/viewpoint, same stale candidate, scan completion immediately erased by another controller path, or repeated downlook that cannot help the search. Reconcile survey, inspection and recovery state so each transition has a reason and actual new evidence opportunity.
7. If no qualified target can be found within the unchanged budget and feasible safe exploration, terminate the boat-task diagnostic as search incomplete/exhausted. Do not descend onto a wrong object or assert that the target does not exist from finite search alone.
8. At the recording/consumer boundary, exclude all return_home/land_home and their terminal subphases from new rendering/training. Preserve historical files intact and declare them excluded; do not silently remove physical failure evidence or reclassify old home touchdown as boat landing.
9. Report search behaviour and loop prevention separately from any historical home outcome. A finite stop proves boundedness only; it does not prove competent search, target absence or a safe flight-home capability.

### Per-step edge cases, failure mechanisms and required checks

**E12.1 — Environment truth versus controller input.** Explicitly document how a negative environment is constructed, which CAD/contact/render components differ and what is observed at capture time. A renderer-hidden target with still-active invisible collision geometry can create an incoherent scene. Preserve old evidence rather than retroactively reinterpret it. Target-absent controls must not leak their condition through filenames, beacon status, different task budgets, special initial commands or an actor-visible flag. A present-but-missed target remains a search failure/uncertainty, not a true-negative identity label.

**E12.2 — No scripted absence policy.** Do not initialize confirmed target memory in an absent-target task or erase useful memory in a present-target task merely to create a loop. Check camera calibration, actual view direction and sensor validity. No home-directed command or privileged target-absence signal may drive the search. Invalid sensors require an explicit safety status rather than fake evidence that360 found nothing.

**E12.3 — Complete versus ineffective scan.** Body yaw, gimbal pan and optical direction can disagree; only useful distinct camera bearings count. Check yaw wrap, elevation, repeated images, self-occlusion, glare and scene obstacles. A boat outside a single elevation band does not prove an empty environment. A recognized target in a control must preempt the scan; otherwise the bounded negative routine would teach ignoring valid targets. No invented completed-scan event at a fixed wall time.

**E12.4 — Inspection branch can still be useful.** A wrong boat with a copied cross is a negative identity example, not a landing target. A buoy or debris mislabelled by the detector must not dominate the queue. Distant unknown boats remain investigable; uncertainty does not justify permanent rejection. Audit first-eligible ordering, safe corridor, actual selected-instance association and decision reasons. Repeated stale bearings cannot substitute for fresh candidate inspection. Do not turn every failed search's RGB into confirmed non-target/empty-scene labels.

**E12.5 — Downlook has a causal purpose.** A local downlook after actual pad loss differs from a global survey elevation change. Do not couple them through a generic fallback that points down after each completed360 and immediately restarts the same survey. Retain completed coverage only while its viewpoint/time remains relevant; reset it when a genuine new-view survey begins. Do not relabel a repeated empty view as a new search simply by incrementing an epoch.

**E12.6 — Cross-module state.** Test protocol, negative-inspection feedback, camera-continuity wrapper, native recovery and safety timeouts together. Current V51 callback changes only one completed-survey transition; other exit/reentry paths can still leave stale `scan_completed`, `selected`, coverage or elevation state. A renamed track cannot reset no-progress forever. A bounded repeat with a genuinely different useful view is not inherently a bug; an endless unproductive scan/downlook loop is. Set measured progress/visit budgets before testing, not by extending them after failure.

**E12.7 — Honest exhaustion.** Finite exploration cannot prove universal absence. Log what was actually observed/inspected, remaining unresolved opportunities and the reason for stopping. A task-budget timeout caused by pointless loops must not be presented as good bounded search. Do not relax confidence to force a false target, or land on a visible cross simply to obtain a positive outcome. No return-home training/rendering is reintroduced as a convenient successful ending.

**E12.8 — Exclusion enforcement.** Check phase names, actual mission state, owner and executed command purpose rather than filtering just two literal strings; home_touchdown_commit/home_confirm/home_disarmed also belong to the excluded tail. Maintain prior observation history for audit while preventing unwanted targets from entering a consumer. Legacy annotations/old approvals cannot override the user's explicit home-data exclusion. Never delete the historical files or crop away collision evidence to make an old episode seem clean.

**E12.9 — No false coverage.** The old home_landed status is not target landing, repaired search-loop evidence, current Windows execution or teacher approval. The local plan deliberately omits E12. A future separately authorized search-exhaustion test may assess decision boundedness without home rendering, but it must distinguish correct negative exploration from failure to find a present target. No claim of full reliable search from one absent-target episode.

### E12 unresolved implementation decisions / blockers

- Keep home phases out of new work. If a bounded-search regression is later required, define it separately and preserve the absence/presence control and no-truth-input contract.
- Trace all survey/downlook transitions, including existing helper integration, before claiming the original repeated-scan defect is repaired.

End of E12 iteration. E04a is covered with E04, not a thirteenth independent situation.
