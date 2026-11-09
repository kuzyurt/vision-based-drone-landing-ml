# Flight record — E08_v60 (E08)   **REJECT**

Scenario `windows_review_E08_search_far` kind=beach seed=3200000003 distance=52.0m height=8.0m boat_speed=0.3m/s

- frames **1338** over **53.48s**; outcome **development_diagnostic_stop** (`boat_task_failed_before_any_home_action`)
- physical events: none
- first lock on the truth target at t=**20.76s**; selection on target afterwards **99.88%**
- hard failures: **physical.landed_on_target, physical.disarmed_after_landing, physical.disarms_promptly_at_contact**; soft: digest.matches_recording; criteria hard: E01.4_no_false_boat_claim_drives_selection, E01.8_descent_started_after_identity_and_geometry, E01.11_physical_termination; criteria soft: E01.7_descent_keeps_useful_framing, E01.10b_parent_recovery_share_below_limit

Acceptance criteria that did not pass, with their own numbers:

- `E01.4_no_false_boat_claim_drives_selection` — {"frames": 3, "examples": [{"t": 20.639999999987563, "name": "none", "prob": 0.021078314632177353, "wrong": 0.2933513820171356, "size": 9.741961479187012}, {"t": 20.67999999998747, "name": "none", "prob": 0.021078314632177353, "wrong": 0.2933513820171356, "size": 9.741961479187012}, {"t": 20.719999999987376, "name": "none", "prob": 0.021078314632177353, "wrong": 0.2933513820171356, "size": 9.741961479187012}]}
- `E01.8_descent_started_after_identity_and_geometry` — {"reason": "never descended"}
- `E01.11_physical_termination` — {"outcome": "flying", "landed": false, "armed": true, "final_clearance": 7.726496575332459, "final_t": 53.4799999999923, "touchdown_s": null}
- `E01.7_descent_keeps_useful_framing` — {"reason": "no descent permission frames"}
- `E01.10b_parent_recovery_share_below_limit` — {"share": 0.2324, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1338, "frame_rows": 1338}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1337}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1338, "probes": 5, "max_mean_abs_diff": 2.1158000578703704}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | NO | hard | `{"outcome": "development_diagnostic_stop", "stop_reason": "boat_task_failed_before_any_home_action", "strict": false, "final_height": 8.402, "final_clearance": 7.515}` |
| `physical.disarmed_after_landing` | NO | hard | `{"armed": true, "landed": false, "outcome": "flying"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": null, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | NO | hard | `{"contact_t": null, "disarm_t": null, "delay_s": null, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | yes | soft | `{"frames": 0, "span_s": 0.0}` |
| `physical.no_collision` | yes | hard | `{"events": []}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 0, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 3, "longest_s": 0.08, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 20.76, "target_fraction": 0.9988, "aliases": []}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 0.9988, "limit": 0.98, "frames_after": 819, "frames_on_target": 818}` |
| `authority.guards_engaged_with_enforcement` | yes | hard | `{"events": 0, "kinds": [], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 20.6, "situation": "E08", "scenario_requires_survey": true, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 0, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 2, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.target_outside_initial_view` | yes | hard | `{"first_frame_target_px": 0.0, "lock_t": 20.76}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "outside_camera", "distance_band": [40.0, 60.0], "fault": null, "mode": "expert"}` |
| `digest.matches_recording` | NO | soft | `{"digest_frames": null, "frames": 1338, "present": false}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–20.60 | 20.64 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 8.53→8.47 | 52.19→58.59 | 6.66→6.31 | -0.00,+0.00,-0.00,-0.34 | 123 | 0.00 |
| 20.64–20.72 | 0.12 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 19/none | 8.47→8.47 | 58.60→58.62 | 6.32→6.33 | -0.00,-0.00,+0.00,-0.32 | 15 | 0.00 |
| 20.76–40.52 | 19.80 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 19/target | 8.47→8.45 | 58.64→31.75 | 6.34→7.12 | +1.66,+0.03,+0.00,+0.04 | 322 | 0.00 |
| 40.56–49.48 | 8.96 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 19,23/target | 8.45→8.42 | 31.69→16.45 | 7.11→7.39 | +2.00,-0.00,+0.00,-0.00 | 1481 | 0.99 |
| 49.52–49.96 | 0.48 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 23/target | 8.42→8.42 | 16.38→15.63 | 7.39→7.38 | +2.00,-0.00,+0.00,-0.00 | 1657 | 0.75 |
| 50.00–53.44 | 3.48 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 19,23/target | 8.42→8.40 | 15.56→9.68 | 7.38→7.51 | +2.00,-0.01,+0.00,-0.00 | 4058 | 0.98 |
| 53.48–53.48 | 0.04 | return_home /  | `` | -/ | 8.40→8.40 | 9.62→9.62 | 7.51→7.51 | +0.00,+0.00,+0.00,+0.00 | 4093 | 0.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 20.6 | `scan` | 8.53→8.47 | 52.19→58.59 | 6.66→6.31 | 0% |
| 20.6 | 0.1 | `inspect_candidate` | 8.47→8.47 | 58.60→58.62 | 6.32→6.33 | 0% |
| 20.8 | 19.8 | `inspect_candidate` | 8.47→8.45 | 58.64→31.75 | 6.34→7.12 | 100% |
| 40.6 | 9.4 | `target_inspect` | 8.45→8.42 | 31.69→15.63 | 7.11→7.38 | 100% |
| 50.0 | 3.5 | `target_inspect` | 8.42→8.40 | 15.56→9.68 | 7.38→7.51 | 100% |
| 53.5 | 0.0 | `` | 8.40→8.40 | 9.62→9.62 | 7.51→7.51 | 0% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 8.53, tgt 0px)
- **t=20.64s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 19/none, alt 8.47, tgt 0px)
- **t=20.76s** `inspect_candidate` — plausible_boat_inspect_unknown_design (sel 19/target, alt 8.47, tgt 118px)
- **t=40.56s** `target_inspect` — target_likely_evidence_requires_inspection (sel 19/target, alt 8.45, tgt 322px)
- **t=53.48s** `` —  (sel /, alt 8.40, tgt 4093px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–53.44s coverage 6.28 rad, inspected views 7, exhausted=False
- survey epoch 0 t=53.48–53.48s coverage 0.00 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- reject_candidate track=18 visually_observed_wrong_design
- survey_complete track=None 
- preempt_candidate track=None 

## Recovery ledger

- visibility management (no altitude gain) t=40.56–49.48s (8.96s) alt [8.45, 8.42, 8.42, 8.45] range [31.69, 16.45, 16.45, 31.69]
- visibility management (no altitude gain) t=50.0–53.44s (3.48s) alt [8.42, 8.4, 8.4, 8.42] range [15.56, 9.68, 9.68, 15.56]
- triggers seen: ['far_existing_visibility_aware_acquisition']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|

## Contradictions between belief and observed truth

- minor `recovery_while_pad_visible` frames 90 t=40.56–53.36s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E08_v60\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E08_v60\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E08_v60\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `83a967b6b907b4b2ba5acf4ebbac15cb38facc4e7314fbec1ea9e0981f837c0b`
- `frames.csv` sha256 `5750db9b7f14516856d41c4157875ff3f6935f6168d543a19d5208625b57fe31`
- `verdict.json` sha256 `c00784bbad0dcadf93fc1e283476dcf2d91d454db85ea8c0c1cbf49fa83c441f`
- `video_join.json` sha256 `1ef112b5218eb3bb89f15ad77b76d153c1a435a883ca641ea758b3b36607960a`
- `review.mp4` sha256 `3891ba8417f524bf93544094be132140af3b8006f7c579ca040eeed961607dcb`
