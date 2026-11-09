# Observable no-radio expert: findings and proposed next experiment

This is a read-only audit and design proposal. No new teacher, training, collection,
flight controller or checkpoint was installed. Historical RGB clips were exported
on the VM and downloaded to Windows in 8.91 seconds; all four video hashes match.
Original recordings, checkpoints, approvals and failed revisions remain untouched.

## What the existing code actually does

The collection expert receives a synthetic boat-position radio packet and reads
simulator boat position, velocity and attitude. When the pad is not visible it can
translate toward the boat using that packet and point its camera toward the hidden
target. During visible approaches it uses true relative state for precise control.

The collection wrapper removes boat radio from the *recorded student observation*,
after the expert has already acted. Its initial 6–14 second camera sweep is driven
by a timer, including some frames where the pad becomes visible. It then switches
back to the privileged expert. This is not an observable camera-only expert.

This matters, but it does not prove the five policy failures have one cause. The
trained candidate learns visual pose rather than imitating the recorded expert
actions. The mismatch primarily affects which views and recovery situations the
training set contains. The action head is not the task controller in this candidate.
The deployed system is learned perception plus geometric visual registration,
explicit motion logic and native PX4, not end-to-end neural action control or RL.

Source inspected on the VM:

- `landing_training/expert.py`: `camera_action`, `prepare`, `act`, `Beacon.sample`.
- Original experiment `collect_domain.py`: `SearchDemonstrator` and `RadioFreeRecorder`.
- `landing_training/run_episode.py`: expert acts before recorder removes radio.
- `landing_training/policy.py`: full 640×360 RGB enters the encoder in the inspected
  path; there is no 224-pixel resize there. Fine distant-pad detail can still be
  lost in feature extraction. Target pixel size must be measured, not assumed.

The old visibility label means *at least one of five pad probes is in view and
unoccluded*. It is not whole-boat visibility, a boat bounding box, a percentage of
visible boat surface, or a guarantee that the pad has enough pixels for registration.
The audit clips label it accordingly. Aircraft structure visibly occludes substantial
parts of some camera views; camera mounting and usable gimbal coverage need review.

## Relevant recorded evidence

These are existing training demonstrations, not new learned-policy flights or
previews of a repaired expert. Their original terminal outcome was landed. A
successful privileged demonstration does not establish camera-only feasibility.

| Recording | Evidence from the full original trace |
|---|---|
| training_beach_00_0 | Visible reference approach and touchdown; no search/reacquire frames with pad invisible and XY command >0.2 m/s. |
| training_beach_01_0 | At task time 7.76 s search commands translation while pad is not visible; first pad-visible frame is 9.64 s. |
| training_beach_02_0 | Starts about 41 m from the boat. There are 17 pad-visible frames during the fixed sweep; later 53 pad-invisible recovery frames command XY >0.2 m/s. At the exported early sighting the projected pad is approximately 4.9×1.0 pixels. |
| training_city_07_1 | 99 pad-invisible recovery frames command XY >0.2 m/s, from 8.40–12.32 s. A recent sighting can justify limited prediction, but this expert additionally has hidden radio/truth assistance. |

Pad invisible does not establish that every part of the boat is invisible. The
clips provide the actual RGB so that distinction can be checked by a person.
XY command is commanded velocity, not measured aircraft velocity.

The five failed learned-policy traces also contradict a single low-confidence
explanation:

| Failed case | Maximum raw model visibility | Accepted geometric-pose frames | Descend-phase frames |
|---|---:|---:|---:|
| test_beach_14_1 | 0.999972 | 240 | 144 |
| test_city_14_0 | 0.999969 | 3 | 0 |
| test_city_14_1 | 0.999964 | 2 | 0 |
| test_gravel_14_1 | 0.531980 | 0 | 0 |
| test_gravel_15_0 | 0.999285 | 0 | 0 |

Confidence is a model score, not calibrated landing probability. A high score can
coexist with unusable pose or false acquisition. The beach failure did initiate
descent; the two city flights barely established accepted pose. This evidence does
not identify the specific cause of every rejected fit or blocked descent. Future
traces should log every gate explicitly rather than infer it from phase names.

## Proposed behavior and information boundary

1. **Search:** hold a useful altitude using own estimator; scan a documented camera
   pattern that covers the usable field of view without getting stuck against a
   gimbal limit or staring into aircraft parts. A valid sighting interrupts the scan.
   Initial search does not point or fly toward hidden boat coordinates. If needed,
   the aircraft follows a bounded coverage route in a public mission search area,
   rather than repeatedly scanning the same unproductive view.

2. **Verify and approach:** detect the *boat* separately from the *landing pad*.
   Require persistent, consistent visual evidence, target pixel size, image validity
   and a plausible track. Approach on visual bearing with speed appropriate to
   uncertainty. An off-centre or small boat should be centred and approached before
   demanding a precise pad pose. Include off-centre examples and distractors.

3. **Align and descend:** obtain a usable visual pad pose and relative motion before
   precision landing. Log position error, relative speed, heading, image age,
   tracking age, pose uncertainty and exactly which condition blocks descent.
   Use sustained readiness plus hysteresis to avoid flickering between hold and
   descend. Start coarse descent when justified, then tighten precision near the
   deck. Do not weaken physical contact, touchdown or disarm criteria.

4. **Target loss:** immediately stop unsupported descent and reduce approach motion.
   Allow only a short, uncertainty-bounded prediction from the last visual track;
   compensate for own movement using own estimator. Search around the last bearing,
   then widen to the documented search pattern. Do not keep flying along a stale
   direction or invent a new target from a false fit. The very final contact phase
   needs its own short commitment rule so a pad disappearing under the aircraft
   does not force an endless climb/descend loop.

5. **Search exhaustion / reserve:** use a known safe home or predeclared landing zone
   and bounded search time. A public coastal search corridor is a reasonable prior
   when the mission specifies one; arbitrary shoreline is not a verified landing
   site. A camera-only shoreline detector would be a separate perception task.
   Boat radio can remain fully absent while own GPS/attitude and a public map are
   available. The inspected observation schema does not contain usable battery SOC
   or an energy model, so genuine energy-reserve behavior requires adding and
   validating those inputs. A simulated time-budget fallback must be labelled as
   such, not presented as battery-aware control.

The new teacher should receive only RGB, own telemetry, camera encoders and declared
mission information through the same interface as the student. Simulator boat state
is allowed in labels and scoring, not in the action generator, camera aiming,
search-waypoint selection or descent decision. Setup before task start must also be
declared: no hidden pre-aiming in a scenario advertised as blind search. A teacher
using privileged masks or perfect visual detections is still an oracle teacher;
that must be disclosed separately rather than called strictly sensor-only.

## Interpreting “50% visible” and long range

Do not require a boat to occupy half the image. Even a useful distant boat occupies
far less than that, and near touchdown most of the hull may leave the frame while
the pad is still usable. If the intent is half of the boat being unoccluded, that
fraction requires a defined amodal-visibility estimate and is only a candidate
approach heuristic. Use stage-specific evidence: boat track for acquisition,
pad geometry for precision descent, physical support for touchdown.

Inspect target size in original camera pixels and the network's representation.
Consider a coarse boat detector plus high-resolution candidate crops or a feature
pyramid if evidence justifies it. Enlarging a crop cannot recover details that were
never captured. If nothing is visually resolvable, bounded mission-area coverage
is required; a camera-only system cannot know which direction contains an unseen
boat without an external prior or eventual visual contact.

## Proposed preview cases before any bulk collection

Use 6–8 short review-only flights, not another 160-episode batch. A teacher should
sometimes safely decline a landing; forcing every demonstration to land incentivizes
hidden shortcuts. Proposed cases:

| Situation | Behavior the preview must demonstrate |
|---|---|
| Boat visible, 5–15 m, moving | Centre, track, approach, align and initiate justified descent. |
| Boat behind camera, initially unseen | Stop the scan on a persistent sighting; no target-directed blind flight. |
| Boat 40–60 m away / near resolution limit | Coarse boat acquisition or documented coverage; do not fabricate fine pad pose. |
| Temporary loss during approach | Brake/hold, bounded track memory, local reacquisition, resume only after verification. |
| Loss near touchdown / pad occluded by aircraft | Correct distinction between recoverable loss and final supported contact. |
| In-air start above land near coast | Use declared search area and own-state constraints; no hidden boat waypoint. |
| No boat / visually similar distractor | Reject false acquisition, finish bounded search, demonstrate the planned fallback. |
| Wind/waves, partial hull visibility, changed water/sky | Maintain readiness long enough to descend, without relaxing touchdown requirements. |

Select seeds without trial-and-error cherry-picking. Publish the declared teacher
inputs and outcomes for all previews, including refusals. Let the user inspect them
before authorizing the eventual bulk demonstration set. Review clips alone do not
prove there are no hidden inputs; a code/interface audit is also required.

After review, collect targeted recovery states from learner rollouts, not just
perfect starts. A DAgger-style intervention process is useful, but only observation-
consistent recovery should become a positive action example if action learning is
introduced. For the present pose-supervised system, add the missing visual states,
boat/pad distinction and consistent labels; fix the explicit search/descent logic
as well. Preserve the original data, and flag or weight its limitations rather
than deleting it or relabelling unsupported control as visual-only behavior.

The amount of extra data should follow missing coverage, not a fixed episode quota.
Roughly 50–200 targeted episodes is a planning range, not a promise that more
demonstrations alone will fix the controller. Use a small pilot first. Keep useful
original approach/landing examples; add searches that detect, losses that recover,
negative observations that do not trigger pursuit, and readiness-to-descent transitions.
Broader appearance noise should not hide missing behavioral coverage.

The five inspected failures are now development evidence. Final reliability must be
measured on new untouched worlds/seeds, including target-absent cases with separately
reported safe-abort outcomes. Report landing completion, collisions, target loss,
false acquisition and time-to-descend separately. Never count expert landings as
learner success or claim near-perfect reliability from a handful of previews.

