# Flight record — E02_v60 (E02)   **REJECT**

Scenario `windows_review_E02_distractors` kind=beach seed=3200000004 distance=20.0m height=6.0m boat_speed=0.3m/s

- frames **2501** over **100.00s**; outcome **development_diagnostic_stop** (`boat_task_failed_before_any_home_action`)
- physical events: none
- first lock on the truth target at t=**17.08s**; selection on target afterwards **1.01%**
- hard failures: **physical.landed_on_target, physical.disarmed_after_landing, physical.disarms_promptly_at_contact, authority.confirmed_object_is_truth_target, authority.selection_continuity**; soft: digest.matches_recording; criteria hard: E01.4_no_non_target_outranks_visible_target, E01.4_selection_continuity_after_lock, E01.4_no_false_boat_claim_drives_selection, E01.8_descent_started_after_identity_and_geometry, E01.11_physical_termination; criteria soft: E01.7_descent_keeps_useful_framing, E01.9_no_unnecessary_hold

Acceptance criteria that did not pass, with their own numbers:

- `E01.4_no_non_target_outranks_visible_target` — {"frames": 69, "worst_span_s": 0.7999999999981355, "limit_s": 0.5, "spans": [{"t0": 16.840000000002814, "t1": 17.040000000002347, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.9696034789085388, "target_px": 773, "selected_size_px": 81.17989349365234}, {"t0": 17.160000000002068, "t1": 17.600000000001042, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.40710318088531494, "target_px": 697, "selected_size_px": 110.49140930175781}, {"t0": 17.76000000000067, "t1": 17.800000000000576, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.9199885129928589, "target_px": 655, "selected_size_px": 100.2486801147461}, {"t0": 17.88000000000039, "t1": 17.920000000000297, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.26488634943962097, "target_px": 598, "selected_size_px": 96.58985900878906}, {"t0": 18.040000000000017, "t1": 18.11999999999983, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.8146162033081055, "target_px": 581, "selected_size_px": 80.10740661621094}, {"t0": 18.199999999999644, "t1": 18.199999999999644, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.5798972845077515, "target_px": 595, "selected_size_px": 85.62039184570312}, {"t0": 18.279999999999458, "t1": 18.279999999999458, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.45208460092544556, "target_px": 607, "selected_size_px": 55.96976852416992}, {"t0": 18.35999999999927, "t1": 18.35999999999927, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.860007107257843, "target_px": 615, "selected_size_px": 75.3434829711914}, {"t0": 18.439999999999085, "t1": 18.63999999999862, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.9585376977920532, "target_px": 632, "selected_size_px": 82.7237319946289}, {"t0": 18.719999999998432, "t1": 18.87999999999806, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.40029630064964294, "target_px": 715, "selected_size_px": 79.4938735961914}, {"t0": 18.99999999999778, "t1": 19.279999999997127, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.3458413779735565, "target_px": 750, "selected_size_px": 99.8934326171875}, {"t0": 19.519999999996568, "t1": 19.519999999996568, "selected": "decoy_blank_clone", "selected_boat": true, "target_prob": 0.5219186544418335, "target_px": 733, "selected_size_px": 97.9958267211914}]}
- `E01.4_selection_continuity_after_lock` — {"frames_after": 2074, "frames_on_target": 21, "fraction": 0.0101, "limit": 0.95}
- `E01.4_no_false_boat_claim_drives_selection` — {"frames": 1201, "examples": [{"t": 18.75999999999834, "name": "decoy_blank_clone", "prob": 0.00905012059956789, "wrong": 0.9548874497413635, "size": 96.35369110107422}, {"t": 18.799999999998246, "name": "decoy_blank_clone", "prob": 0.00905012059956789, "wrong": 0.9548874497413635, "size": 96.35369110107422}, {"t": 18.839999999998152, "name": "decoy_blank_clone", "prob": 0.00905012059956789, "wrong": 0.9548874497413635, "size": 96.35369110107422}, {"t": 18.87999999999806, "name": "decoy_blank_clone", "prob": 0.00905012059956789, "wrong": 0.9548874497413635, "size": 96.35369110107422}, {"t": 19.679999999996195, "name": "decoy_blank_clone", "prob": 0.03264717385172844, "wrong": 0.8581274151802063, "size": 30.177722930908203}]}
- `E01.8_descent_started_after_identity_and_geometry` — {"reason": "never descended"}
- `E01.11_physical_termination` — {"outcome": "flying", "landed": false, "armed": true, "final_clearance": 5.6921194482187065, "final_t": 100.00000000020803, "touchdown_s": null}
- `E01.7_descent_keeps_useful_framing` — {"reason": "no descent permission frames"}
- `E01.9_no_unnecessary_hold` — {"worst_hold_s": 61.1200000002563, "limit_s": 6.0, "holds": [{"t0": 25.31999999998305, "t1": 31.63999999996832, "phase": "target_inspect"}, {"t0": 32.879999999965435, "t1": 35.27999999995984, "phase": "target_inspect"}, {"t0": 35.359999999959655, "t1": 37.03999999995574, "phase": "target_inspect"}, {"t0": 38.839999999951544, "t1": 99.96000000020784, "phase": "target_inspect"}]}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 2501, "frame_rows": 2501}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 2500}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 2501, "probes": 5, "max_mean_abs_diff": 2.414603587962963}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | NO | hard | `{"outcome": "development_diagnostic_stop", "stop_reason": "boat_task_failed_before_any_home_action", "strict": false, "final_height": 6.382, "final_clearance": 4.565}` |
| `physical.disarmed_after_landing` | NO | hard | `{"armed": true, "landed": false, "outcome": "flying"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": null, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | NO | hard | `{"contact_t": null, "disarm_t": null, "delay_s": null, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | yes | soft | `{"frames": 0, "span_s": 0.0}` |
| `physical.no_collision` | yes | hard | `{"events": []}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | NO | hard | `{"confirmed_frames": 2010, "wrong_frames": 2010, "wrong_fraction": 1.0, "first_wrong": {"t": 19.6, "name": "decoy_blank_clone"}, "names": ["decoy_blank_clone"], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 0, "longest_s": 0.0, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 17.08, "target_fraction": 0.0101, "aliases": ["20", "24", "27"]}` |
| `authority.selection_continuity` | NO | hard | `{"fraction": 0.0101, "limit": 0.98, "frames_after": 2074, "frames_on_target": 21}` |
| `authority.guards_engaged_with_enforcement` | yes | hard | `{"events": 0, "kinds": [], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 16.12, "situation": "E02", "scenario_requires_survey": true, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 0, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 1, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.target_outside_initial_view` | yes | hard | `{"first_frame_target_px": 0.0, "lock_t": 17.08}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "outside_camera", "distance_band": [12.0, 30.0], "fault": null, "mode": "expert"}` |
| `digest.matches_recording` | NO | soft | `{"digest_frames": null, "frames": 2501, "present": false}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–16.12 | 16.16 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.55→6.48 | 20.12→25.17 | 5.40→5.29 | -0.00,-0.00,-0.00,-0.34 | 0 | 0.00 |
| 16.16–16.20 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 25.18→25.20 | 5.29→5.30 | -0.00,-0.00,+0.00,-0.34 | 0 | 0.56 |
| 16.24–17.04 | 0.84 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 25.21→25.42 | 5.30→5.17 | +0.24,-0.22,+0.00,-0.26 | 773 | 0.97 |
| 17.08–17.12 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 25.42→25.43 | 5.16→5.15 | +0.64,-0.33,+0.00,-0.20 | 743 | 0.87 |
| 17.16–17.60 | 0.48 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 25.43→25.34 | 5.14→5.10 | +0.97,-0.31,+0.00,-0.13 | 700 | 0.96 |
| 17.64–17.72 | 0.12 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.49→6.49 | 25.32→25.29 | 5.10→5.10 | +1.16,-0.11,+0.00,-0.13 | 701 | 0.90 |
| 17.76–17.80 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.49→6.49 | 25.27→25.25 | 5.10→5.11 | +1.19,-0.14,+0.00,-0.12 | 655 | 0.90 |
| 17.84–17.84 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.49→6.49 | 25.22→25.22 | 5.11→5.11 | +1.16,-0.09,+0.00,-0.13 | 614 | 0.00 |
| 17.88–17.92 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.49→6.49 | 25.20→25.18 | 5.12→5.12 | +1.24,-0.16,+0.00,-0.11 | 598 | 0.87 |
| 17.96–18.00 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.49→6.49 | 25.15→25.13 | 5.13→5.13 | +1.19,-0.06,+0.00,-0.12 | 593 | 0.88 |
| 18.04–18.12 | 0.12 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 25.10→25.04 | 5.14→5.16 | +1.27,-0.10,+0.00,-0.10 | 590 | 0.97 |
| 18.16–18.16 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 25.01→25.01 | 5.16→5.16 | +1.27,-0.02,+0.00,-0.10 | 583 | 0.66 |
| 18.20–18.20 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 24.99→24.99 | 5.17→5.17 | +1.33,-0.09,+0.00,-0.08 | 595 | 0.55 |
| 18.24–18.24 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 24.96→24.96 | 5.18→5.18 | +1.27,-0.02,+0.00,-0.10 | 602 | 0.41 |
| 18.28–18.28 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 24.93→24.93 | 5.19→5.19 | +1.33,-0.06,+0.00,-0.08 | 607 | 0.41 |
| 18.32–18.32 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 24.89→24.89 | 5.19→5.19 | +1.27,+0.00,+0.00,-0.10 | 620 | 0.41 |
| 18.36–18.36 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 24.86→24.86 | 5.20→5.20 | +1.33,-0.05,+0.00,-0.08 | 615 | 0.84 |
| 18.40–18.40 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 24.83→24.83 | 5.21→5.21 | +1.27,+0.01,+0.00,-0.10 | 623 | 0.86 |
| 18.44–18.64 | 0.24 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 24.80→24.63 | 5.22→5.25 | +1.47,-0.03,+0.00,-0.04 | 689 | 0.97 |
| 18.68–18.68 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 24.59→24.59 | 5.25→5.25 | +1.55,+0.03,+0.00,-0.02 | 712 | 0.89 |
| 18.72–18.88 | 0.20 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 24.56→24.40 | 5.26→5.27 | +1.71,-0.02,+0.00,-0.01 | 753 | 0.98 |
| 18.92–18.96 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 24.36→24.32 | 5.28→5.28 | +1.74,+0.02,+0.00,-0.04 | 770 | 0.25 |
| 19.00–19.28 | 0.32 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20,24/decoy_blank_clone | 6.48→6.48 | 24.28→23.96 | 5.28→5.28 | +1.93,+0.01,+0.00,-0.00 | 813 | 0.98 |
| 19.32–19.48 | 0.20 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 23.91→23.70 | 5.28→5.27 | +1.83,+0.00,+0.00,-0.05 | 832 | 0.98 |
| 19.52–19.52 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 20/decoy_blank_clone | 6.48→6.48 | 23.65→23.65 | 5.27→5.27 | +1.78,+0.02,+0.00,-0.07 | 733 | 0.48 |
| 19.56–19.56 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 26/target | 6.48→6.48 | 23.60→23.60 | 5.27→5.27 | +1.72,-0.00,+0.00,-0.09 | 720 | 0.97 |
| 19.60–22.80 | 3.24 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 20/decoy_blank_clone | 6.48→6.47 | 23.54→19.06 | 5.27→5.45 | +1.95,+0.06,-0.00,+0.02 | 1088 | 0.99 |
| 22.84–99.96 | 77.16 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 20,24,27/decoy_blank_clone | 6.47→6.38 | 19.01→39.64 | 5.45→4.57 | +0.03,-0.00,-0.00,-0.00 | 0 | 0.85 |
| 100.00–100.00 | 0.04 | return_home /  | `` | -/ | 6.38→6.38 | 39.66→39.66 | 4.56→4.56 | +0.00,+0.00,+0.00,+0.00 | 0 | 0.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 16.2 | `scan` | 6.55→6.48 | 20.12→25.17 | 5.40→5.29 | 0% |
| 16.2 | 0.1 | `target_inspect` | 6.48→6.48 | 25.18→25.20 | 5.29→5.30 | 0% |
| 16.2 | 3.4 | `target_inspect` | 6.48→6.48 | 25.21→23.60 | 5.30→5.27 | 25% |
| 19.6 | 3.2 | `target_inspect` | 6.48→6.47 | 23.54→19.06 | 5.27→5.45 | 0% |
| 22.8 | 77.2 | `target_inspect` | 6.47→6.38 | 19.01→39.64 | 5.45→4.57 | 0% |
| 100.0 | 0.0 | `` | 6.38→6.38 | 39.66→39.66 | 4.56→4.56 | 0% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.55, tgt 0px)
- **t=16.16s** `target_inspect` — target_likely_evidence_requires_inspection (sel 20/decoy_blank_clone, alt 6.48, tgt 0px)
- **t=19.60s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 20/decoy_blank_clone, alt 6.48, tgt 692px)
- **t=100.00s** `` —  (sel /, alt 6.38, tgt 0px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–99.96s coverage 4.71 rad, inspected views 2, exhausted=False
- survey epoch 0 t=100.00–100.00s coverage 0.00 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- survey_interrupted track=None 
- reject_candidate track=21 visually_observed_wrong_design
- preempt_candidate track=None 
- reject_candidate track=17 visually_observed_wrong_design
- target_confirmed track=20 identity_evidence_acquired

## Recovery ledger

- visibility management (no altitude gain) t=16.24–22.8s (6.6s) alt [6.48, 6.47, 6.47, 6.49] range [25.21, 19.06, 19.06, 25.43]
- triggers seen: ['far_existing_visibility_aware_acquisition']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|

## Contradictions between belief and observed truth

- minor `recovery_while_pad_visible` frames 72 t=16.24–21.96s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E02_v60\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E02_v60\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E02_v60\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `c85e83939b76e0c04e9b99c176580d21a3b6174b916155ad673165a1f0160e65`
- `frames.csv` sha256 `98b1bef35e79eb0dc0e1cfe78a4cb7f8f7a42f26dfd600e41150195293c52dc5`
- `verdict.json` sha256 `7862699a2db78242f77017a6f80e2672470d2a734c2ab8b879d80816e2f6e2a3`
- `video_join.json` sha256 `920c4d6825270284851461d33263b93bd9e5eab21c5bf668ff56759c5c243428`
- `review.mp4` sha256 `d267fe4f56780cabe30020578bcc91b7f25e696262847f04307700299c8e1d31`
