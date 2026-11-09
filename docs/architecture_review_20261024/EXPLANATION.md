# Boat search and policy architecture — code review, 24 October 2026

The difficult skill is obtaining a trustworthy target and pad estimate from an initially unhelpful camera view. Once that estimate exists, explicit landing control can align with the deck, match its motion and descend. A successful scripted search demonstration does not measure that acquisition skill.

Diagrams: [architecture](policy_architecture.svg) · [no-radio search](no_radio_search.svg). PNG previews accompany both. These are dependency diagrams; the runtime computes its proposal before the teacher applies its protocol override, so the drawings are not literal function-call order. Only explanatory files were added; no flight or training implementation was changed.

**Three implementations must be kept separate.**

| Implementation | What it actually does |
|---|---|
| `landing_training/policy.py` | Original baseline: MobileNet + telemetry MLP + GRU predicts six actions and ten auxiliary values. The project README identifies this as historical. |
| R15 learner, wrapped by the v60 teacher with v61 recognition | Learned visual state estimation, marker localization, geometric registration, explicit flight control and optional learned radio fusion. The teacher adds boat recognition, object tracking and search/identity rules. `run_windows_review_v61.py` selects the expert in expert mode; DAgger mode constructs the frozen R15 learner separately. |
| city80 review video | `SearchDirector` flies predetermined legs and uses the simulator's actual target pad for its geometry, turn-in and lock check. The stock `Expert(env)` takes over after lock and uses true pad position, velocity and orientation. It does not run the v61 recognizer. |

**How the observable teacher finds the boat without radio.**

1. **Look for objects and maintain tracks.** A neural detector proposes image boxes. A second CNN examines 96×96 RGB crops and produces target/wrong-design/unknown probabilities plus marker confidence. The v61 verifier uses its `rgb_only` mode. Several distinct camera captures establish that an object persists. Tracking uses camera calibration, gimbal angles and the aircraft's own estimated pose to turn pixels into world bearings. Intersecting those rays with an uncertain declared boat-height plane gives a rough range interval. This is an estimate, not a range sensor or the simulator's true target distance.
2. **Survey if there is nothing useful to inspect.** The aircraft rotates at −0.35 rad/s, about 20°/s. It records 36 heading sectors at the selected camera tilt; a sector counts only within 3° of that tilt. One uninterrupted revolution takes approximately 18 seconds. Empty completed surveys try 18°, 6° and 35° camera tilt bands. During the sweep, the adapter brakes horizontal motion and holds current height. This is a largely stationary angular survey, not the city80 two-leg flight pattern.
3. **Interrupt for a usable opportunity.** Recognition runs throughout the sweep. A likely target has at least 24 pixels of extent, identity support and peak target probability ≥0.85. Confirmed target identity needs three distinct strong captures at the recognizer threshold, 0.98 here. Importantly, current code also interrupts an active survey for an ordinary plausible boat: the extent gate for that class is 18 pixels, with a plausible implied hull size. The selected v61 detection-presence operating point is 0.3; the protocol's constructor default of 0.7 is overridden by the checkpoint.
4. **Approach to obtain better evidence.** Point the aircraft/camera at the selected bearing and close at bounded speed, only with a declared clear approach corridor, a track no older than 0.25 s and heading error below 20°. The speed calculation slows as the estimated stopping room shrinks. The teacher maintains height while the object is still unconfirmed. Strong repeated wrong-design evidence rejects the view; an uncertain classification alone does not prove it is a decoy. A stale selected candidate gets up to three seconds of reorientation. Inspection also has progress/time limits to prevent endless pursuit.
5. **Confirm this object, then obtain landing geometry.** A confirmed identity anchor associates subsequent track IDs with the same physical boat. Appearance helps this association. The pad localizer is restricted to the recognized object's box, and RGB registration fits the known pad pattern to estimate precise relative position. Target identity and valid pad geometry are separate requirements. A recognizable boat alone is insufficient for descent.
6. **Align, match, descend, recover if needed.** The controller uses estimated deck pose and relative motion to brake and align. Tight lateral, speed, heading, tilt and geometry-freshness gates permit descent. Brief visual loss can use bounded tracking memory; near deck level, local downward views and guarded recovery preserve the target instead of immediately starting a global survey. PX4 and the harness handle touchdown/disarm and physical outcome checks separately.

**What the tree describes beyond today's implementation.**

`artifacts/teacher_tree/tree.json` is an editable explanation/intent document. Its server saves that document; the inspected actor does not execute it as a behavior-tree configuration. Editing it alone does not change the teacher or train a student.

- Its 35–27 m and 27–0 m bands are explanatory intent. Actual transitions use image size, evidence and estimated geometry, not those fixed distance thresholds.
- Its strict first scan, looser second scan and queue-until-finished description do not fully match current code. The current `P2.5` branch interrupts for a visible plausible boat. The queue is written, but the post-survey picker operates on currently visible candidates, ordered by class then first-seen time.
- The post-survey picker has no colour-similarity ranking. Appearance is used for identity/view association and rejection memory.
- There is no general explicit state that approaches a far candidate, flies directly over it and verifies it from above. Inspection, local downlook and recovery provide parts of that behavior.
- Survey epoch/coverage and rejection/identity memory are explicit teacher state, not added fields in the student's 32-number neural input. A GRU could infer some history, but it is not explicitly told “scan 2.” The tree's claim that the student cannot tell the scans apart is too absolute.

**Why the city80 sweep is easier than the required skill.**

It starts with the target outside the image and flies two planned legs while the gimbal pans ±30° on a nine-second cycle. However, the waypoints are built from `frame(env)`, which reads the actual pad position and the start-to-pad axis. After the legs, `error = self.pad[:2] - position[:2]` directs the turn-in and subsequent motion toward the true target. `_confirmed()` uses true range ≤55 m, central image coordinates and `pad_visibility()` raycasts, sustained for six calls. It never asks the RGB recognizer to distinguish the six decoys. After lock, the stock simulator expert uses true deck state to land.

The recording reports lock at 51.44 s and 54.72 m, followed by a landing in a 119 s video. These verify that this scripted geometry/control sequence completed. They do not verify visual identification at 55 m, rejection of the decoys or a learned no-radio search. `flown_search_m=55.7` is implemented as displacement from the start, not integrated path length. The files are explicitly review recordings with `training_eligible=False`.

**The neural architecture in plain English.**

The shared MobileNetV3-Small CNN converts RGB into visual features. It provides fine/context feature maps to spatial detection/localization heads and a spatial summary to a 256-feature visual projection. A small fully connected telemetry network converts the fixed 32-number contract into 64 features. Combining those gives 320 features per step, processed by a GRU with a 128-number hidden memory. A GRU carries a compact learned summary of previous observations into the next decision.

In the R15 pose runtime, the useful recurrent output is a 15-value state: visibility (1), relative position (3), relative velocity (3), deck heading representation (2), deck normal (3), marker image location (2), and contact confidence (1). The inherited six-action neural head is not what commands the aircraft in this path. The runtime turns state estimates into actions with explicit control and marker geometry.

The 32-number sensor contract includes own velocity/attitude/angular rates, two gimbal angles, radio position/velocity slots, freshness/validity/status fields, image timing, previous command slots and decision interval. In this model's `periodic_no_action_v1` representation, the six previous-command slots are replaced by sine/cosine pairs of yaw, pan and tilt. Radio coordinates, validity, age, quality and dock status are neutralized for the independent visual recurrence.

Optional radio enters a separate learned fusion MLP: 13 inputs → 48 hidden features → two blend weights for position and velocity. Each blend weight is at most 0.35 and becomes zero when radio is invalid/stale. The network cannot silently replace vision with full radio steering, and raw radio is disabled in the downstream controller interface. Own GNSS/odometry remains available when the boat radio is off; it tells the aircraft where it is, not where the unseen boat is.

The observable teacher adds another kind of memory: explicit object tracks, target votes, rejected views, scan progress and a confirmed identity anchor. This is different from the GRU's learned hidden memory. Those rules choose what object to inspect and gate the shared landing runtime's proposal.

The executed output has exactly six numbers at 25 Hz:

`[forward velocity, right velocity, down velocity, yaw rate, camera pan rate, camera tilt rate]`

The first four go through the PX4 offboard velocity/yaw interface. PX4's flight-control loops produce four motor commands; the simulated propulsion turns those into rotor speed, thrust and aircraft motion. The last two integrate camera-gimbal targets, whose servos move pan/tilt joints. The next image and own telemetry close the feedback loop. The policy does not output four motor voltages.

**Implication for the next training effort.**

The central gap is selecting a weak, uncertain candidate and actively obtaining enough visual evidence to identify it. A stationary sweep increases angular coverage; it does not improve range or pixel detail. If every distant hull is below the proposal/plausibility gate, the code can exhaust three tilt-band surveys without approaching anything.

The useful next evaluation would run the observable teacher and the learner separately on the decoy scene, allowing only declared search-area priors and sensor inputs. It should measure first candidate detection, selection, identity confirmation, wrong-object approaches, time to a usable pad pose and unaided landing. That would expose which acquisition stage needs training. The v61 recognizer's qualification file still marks it development-review-only; the inspected handoff does not show that it or the student flew this city80 scene.

Teacher improvements become student improvements only through an actual training/update path. The inspected DAgger wrapper evaluates learner and expert on the same frame, records the expert's separate action proposal, and can hand control to the expert. Its learner is frozen R15 in this review harness. An expert-assisted landing is not an unaided learner success, and the inspected review recordings are not automatically admitted as training data.

**Source map.**

- [Handoff](../../artifacts/city80_decoys_20261023/HANDOFF.md), [tree intent](../../artifacts/teacher_tree/tree.json), [tree editor server](../../artifacts/teacher_tree/server.py).
- [Current teacher protocol](../../artifacts/local_curriculum_20261020/sources/target_learning/protocol_priority_v60.py): `classify`, `_scan_step`, `step` P2/P2.5, `_pick_after_survey`, `_inspect_or_align`, `_target_branch`.
- [Teacher adapter](../../artifacts/local_curriculum_20261020/sources/target_learning/expert_adapter_v60.py): checkpoint-selected thresholds, recognizer proxy, `_decode`, `act`.
- [RGB verifier](../../artifacts/local_curriculum_20261020/sources/target_learning/object_verifier_v12.py), [v61 model report](../../artifacts/local_curriculum_20261020/models/perception_v61/result.json), [qualification](../../artifacts/local_curriculum_20261020/models/perception_v61/qualification.json), [visual tracking](../../artifacts/local_curriculum_20261020/sources/target_learning/tracks.py).
- [v61 harness](../../artifacts/local_curriculum_20261020/run_windows_review_v61.py), [DAgger wrapper](../../artifacts/local_curriculum_20261020/sources/target_learning/dagger_v48.py), [bundle resolution](../../artifacts/local_curriculum_20261020/local_paths.py).
- [Shared runtime](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v48_local_recovery/package/base_r15/code/landing_training/radio_robust_20261015/runtime.py), [fusion model](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v48_local_recovery/package/base_r15/code/landing_training/radio_robust_20261015/model.py), [parent model](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v48_local_recovery/package/base_r15/code/landing_training/radio_robust_20261015/parent_model.py), [backbone](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v48_local_recovery/package/base_r15/code/landing_training/policy.py), [pose model](../../artifacts/approved_curriculum_20261020/candidate_exports/experimental_v48_local_recovery/package/base_r15/code/landing_training/pose_model.py).
- [City80 director](../../artifacts/city80_decoys_20261023/run_search_land.py), [target-anchored frame](../../artifacts/city80_decoys_20261023/search_geometry.py), [stock truth-based expert](../../landing_training/expert.py), [episode result](../../artifacts/city80_decoys_20261023/episode_search_v2/summary.json).
- [PX4 interface](../../landing_training/px4.py), [Windows PX4 bridge](../../artifacts/local_curriculum_20261020/windows_px4_v2.py), [motor/gimbal physics](../../landing_training/environment.py), [historical-versus-current policy reference](../../landing_training/docs/CURRENT_POLICY.md).
