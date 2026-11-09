# Flight record — E05_v60 (E05)   **SILVER**

Scenario `windows_review_E05_visible_start` kind=beach seed=3200000050 distance=8.0m height=6.0m boat_speed=0.3m/s

- frames **1151** over **46.00s**; outcome **landed**
- physical events: touchdown@60.44s, stable_contact@61.69s, unstable_contact@62.19s, stable_contact@64.27s, landed@65.94s
- first lock on the truth target at t=**0.12s**; selection on target afterwards **100.00%**
- hard failures: **none**; soft: physical.no_press_after_contact; criteria hard: none; criteria soft: E01.9_descent_permission_stable

Acceptance criteria that did not pass, with their own numbers:

- `E01.9_descent_permission_stable` — {"reversals": 6, "limit": 3}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1151, "frame_rows": 1151}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1150}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1151, "probes": 5, "max_mean_abs_diff": 3.497009548611111}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | yes | hard | `{"outcome": "landed", "stop_reason": null, "strict": true, "final_height": 0.688, "final_clearance": -0.0}` |
| `physical.disarmed_after_landing` | yes | hard | `{"armed": false, "landed": true, "outcome": "landed"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": 46.0, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | yes | hard | `{"contact_t": 40.32, "disarm_t": 44.0, "delay_s": 3.68, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 92, "span_s": 3.64}` |
| `physical.no_collision` | yes | hard | `{"events": [["touchdown", 60.44], ["stable_contact", 61.69], ["unstable_contact", 62.19], ["stable_contact", 64.27], ["landed", 65.94]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 1027, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 0, "longest_s": 0.0, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 0.12, "target_fraction": 1.0, "aliases": ["1", "13", "15", "2", "22", "4", "5", "7", "8", "9"]}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 1.0, "limit": 0.98, "frames_after": 1148, "frames_on_target": 1148}` |
| `authority.guards_engaged_with_enforcement` | yes | soft | `{"events": 15, "kinds": ["descent_without_fresh_geometry"], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 0.08, "situation": "E05", "scenario_requires_survey": false, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 876, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 2, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "visible", "distance_band": [5.0, 20.0], "fault": null, "mode": "expert"}` |
| `digest.matches_recording` | yes | soft | `{"digest_frames": 1151, "frames": 1151, "present": true}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.08 | 0.12 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.53→6.54 | 8.10→8.10 | 5.66→5.66 | -0.00,+0.00,-0.07,-0.03 | 6035 | 0.00 |
| 0.12–3.68 | 3.60 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1,2/target | 6.55→6.50 | 8.10→4.01 | 5.67→5.70 | +1.57,-0.00,-0.00,-0.00 | 14961 | 1.00 |
| 3.72–3.96 | 0.28 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2/target | 6.50→6.50 | 3.94→3.55 | 5.70→5.71 | +1.54,-0.01,-0.00,-0.00 | 16407 | 1.00 |
| 4.00–4.00 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2/target | 6.50→6.50 | 3.48→3.48 | 5.71→5.71 | +1.52,-0.03,+0.00,-0.01 | 16582 | 1.00 |
| 4.04–4.92 | 0.92 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1,2/target | 6.50→6.49 | 3.42→2.30 | 5.71→5.76 | +1.12,-0.01,-0.00,-0.01 | 19584 | 1.00 |
| 4.96–6.92 | 2.00 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.49→6.46 | 2.26→0.58 | 5.76→5.75 | +1.12,-0.04,+0.01,+0.01 | 22654 | 1.00 |
| 6.96–6.96 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 2/target | 6.46→6.46 | 0.55→0.55 | 5.75→5.75 | +0.58,-0.01,+0.00,+0.00 | 22680 | 1.00 |
| 7.00–7.36 | 0.40 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.46→6.46 | 0.53→0.37 | 5.75→5.75 | +0.57,-0.03,+0.01,-0.00 | 22802 | 1.00 |
| 7.40–7.40 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.46→6.46 | 0.36→0.36 | 5.75→5.75 | +0.50,-0.01,+0.07,+0.00 | 22833 | 1.00 |
| 7.44–7.44 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.46→6.46 | 0.34→0.34 | 5.75→5.75 | +0.56,-0.03,+0.04,+0.00 | 22786 | 1.00 |
| 7.48–9.08 | 1.64 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.46→6.13 | 0.33→0.08 | 5.75→5.45 | +0.48,-0.01,+0.23,+0.00 | 25345 | 1.00 |
| 9.12–9.64 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 2/target | 6.12→6.04 | 0.07→0.03 | 5.43→5.36 | +0.43,-0.01,+0.00,+0.00 | 26251 | 1.00 |
| 9.68–11.00 | 1.36 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 1,2/target | 6.04→6.05 | 0.03→0.23 | 5.36→5.35 | +0.03,+0.00,+0.00,+0.02 | 26716 | 1.00 |
| 11.04–11.56 | 0.56 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.05→6.04 | 0.24→0.41 | 5.35→5.35 | +0.43,+0.01,+0.04,+0.00 | 26363 | 1.00 |
| 11.60–12.32 | 0.76 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.04→6.00 | 0.41→0.33 | 5.35→5.31 | +0.74,-0.02,+0.06,-0.01 | 26802 | 1.00 |
| 12.36–13.60 | 1.28 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 5.99→5.79 | 0.32→0.07 | 5.30→5.10 | +0.41,-0.02,+0.18,-0.01 | 28987 | 1.00 |
| 13.64–38.56 | 24.96 | descend / target_align | `identity_and_fresh_geometry_associated` | 1,2,4,5+.../target | 5.78→0.85 | 0.07→0.00 | 5.09→0.16 | +0.31,-0.00,+0.19,-0.00 | 226882 | 1.00 |
| 38.60–38.80 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.84→0.83 | 0.00→0.00 | 0.16→0.14 | +0.29,-0.01,-0.01,-0.00 | 209331 | 1.00 |
| 38.84–40.24 | 1.44 | descend / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.83→0.71 | 0.00→0.00 | 0.14→0.03 | +0.29,-0.00,+0.10,+0.00 | 208479 | 1.00 |
| 40.28–40.28 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.71→0.71 | 0.01→0.01 | 0.02→0.02 | +0.30,+0.00,+0.15,+0.00 | 172793 | 1.00 |
| 40.32–43.92 | 3.64 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.70→0.68 | 0.01→0.01 | 0.02→-0.00 | +0.29,-0.02,+0.31,+0.00 | 170275 | 1.00 |
| 43.96–43.96 | 0.04 | confirm / ground_hold | `own_estimator_not_airborne` | 22/target | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | +0.24,+0.00,+0.32,+0.00 | 149321 | 1.00 |
| 44.00–46.00 | 2.04 | disarmed / ground_hold | `own_estimator_not_airborne` | 22/target | 0.68→0.69 | 0.01→0.02 | -0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 149495 | 1.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 0.1 | `scan` | 6.53→6.54 | 8.10→8.10 | 5.66→5.66 | 0% |
| 0.1 | 3.9 | `target_inspect` | 6.55→6.50 | 8.10→3.48 | 5.67→5.71 | 100% |
| 4.0 | 0.9 | `target_inspect` | 6.50→6.49 | 3.42→2.30 | 5.71→5.76 | 100% |
| 5.0 | 2.5 | `target_align` | 6.49→6.46 | 2.26→0.34 | 5.76→5.75 | 100% |
| 7.5 | 2.2 | `target_align` | 6.46→6.04 | 0.33→0.03 | 5.75→5.36 | 100% |
| 9.7 | 1.4 | `target_inspect` | 6.04→6.05 | 0.03→0.23 | 5.36→5.35 | 100% |
| 11.0 | 0.6 | `target_align` | 6.05→6.04 | 0.24→0.41 | 5.35→5.35 | 100% |
| 11.6 | 0.8 | `target_align` | 6.04→6.00 | 0.41→0.33 | 5.35→5.31 | 100% |
| 12.4 | 1.3 | `target_align` | 5.99→5.79 | 0.32→0.07 | 5.30→5.10 | 100% |
| 13.6 | 25.2 | `target_align` | 5.78→0.83 | 0.07→0.00 | 5.09→0.14 | 100% |
| 38.8 | 1.5 | `target_align` | 0.83→0.71 | 0.00→0.01 | 0.14→0.02 | 100% |
| 40.3 | 3.6 | `target_align` | 0.70→0.68 | 0.01→0.01 | 0.02→-0.00 | 100% |
| 44.0 | 0.0 | `ground_hold` | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | 100% |
| 44.0 | 2.0 | `ground_hold` | 0.68→0.69 | 0.01→0.02 | -0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.53, tgt 6035px)
- **t=0.12s** `target_inspect` — target_likely_evidence_requires_inspection (sel 1/target, alt 6.55, tgt 6069px)
- **t=4.96s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.49, tgt 19697px)
- **t=6.96s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 2/target, alt 6.46, tgt 22680px)
- **t=7.00s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.46, tgt 22660px)
- **t=9.12s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 2/target, alt 6.12, tgt 25509px)
- **t=9.68s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 2/target, alt 6.04, tgt 26134px)
- **t=11.04s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.05, tgt 26361px)
- **t=43.96s** `ground_hold` — own_estimator_not_airborne (sel 22/target, alt 0.68, tgt 149321px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–46.00s coverage 0.00 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- survey_interrupted track=None 
- preempt_candidate track=None 
- target_confirmed track=2 identity_evidence_acquired

## Recovery ledger

- visibility management (no altitude gain) t=0.12–3.68s (3.6s) alt [6.55, 6.5, 6.5, 6.56] range [8.1, 4.01, 4.01, 8.1]
- visibility management (no altitude gain) t=9.12–11.0s (1.92s) alt [6.12, 6.05, 6.04, 6.12] range [0.07, 0.23, 0.02, 0.23]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 5.0 | 6.49 | 2.22 | 5.76 | 1.29 | 0.3 | 19809 | True | 0.045 |
| 7.0 | 6.46 | 0.53 | 5.75 | 0.93 | -1.0 | 22660 | True | -0.023 |
| 9.0 | 6.16 | 0.08 | 5.47 | 0.43 | -8.5 | 25144 | True | 0.301 |
| 11.0 | 6.05 | 0.23 | 5.35 | 0.04 | 6.3 | 26389 | False | 0.000 |
| 13.0 | 5.92 | 0.15 | 5.22 | 0.51 | -2.1 | 27710 | True | 0.188 |
| 15.1 | 5.50 | 0.05 | 4.81 | 0.29 | 36.6 | 32586 | True | 0.275 |
| 17.1 | 5.05 | 0.03 | 4.35 | 0.32 | -50.9 | 39680 | True | 0.162 |
| 19.2 | 4.60 | 0.01 | 3.92 | 0.31 | -78.9 | 48758 | True | 0.237 |
| 21.2 | 4.18 | 0.00 | 3.49 | 0.30 | -40.7 | 60161 | True | 0.223 |
| 23.2 | 3.70 | 0.01 | 3.01 | 0.29 | -16.9 | 71653 | True | 0.187 |
| 25.3 | 3.29 | 0.03 | 2.61 | 0.29 | -7.3 | 82635 | True | 0.283 |
| 27.3 | 2.83 | 0.02 | 2.14 | 0.29 | 1.1 | 100632 | True | 0.223 |
| 29.4 | 2.36 | 0.02 | 1.67 | 0.30 | -34.2 | 127509 | True | 0.184 |
| 31.4 | 1.93 | 0.01 | 1.25 | 0.30 | -14.7 | 167750 | True | 0.224 |
| 33.4 | 1.48 | 0.00 | 0.79 | 0.29 | -31.8 | 226036 | True | 0.210 |
| 35.5 | 1.16 | 0.00 | 0.47 | 0.30 | -179.8 | 219168 | True | 0.080 |
| 37.5 | 0.95 | 0.00 | 0.27 | 0.30 | 113.0 | 212725 | True | 0.104 |
| 39.6 | 0.79 | 0.01 | 0.09 | 0.29 | -14.9 | 198086 | True | 0.092 |
| 41.6 | 0.69 | 0.02 | -0.00 | 0.30 | -54.3 | 149391 | True | 0.300 |
| 43.6 | 0.67 | 0.02 | -0.00 | 0.30 | -48.2 | 149463 | True | 0.324 |
| 45.6 | 0.69 | 0.01 | -0.00 | 0.29 | -60.3 | 149447 | True | 0.000 |

## Contradictions between belief and observed truth

- minor `identity_head_flips_near_deck` frames 372 t=23.32–23.32s {"flips": 30, "rate_per_s": 2.02, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- minor `recovery_while_pad_visible` frames 82 t=0.12–11.0s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E05_v60\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E05_v60\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E05_v60\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `8a0febedfd911b7bb452071a4caf431e139f624aeadd9e0c253023acd8eaa482`
- `frames.csv` sha256 `3ef40f7bde109aac9f7987db6bad97b4e4124bb1611652341175fc5f25f059b5`
- `verdict.json` sha256 `d803af0b5b8cd95e38cd7e550e7e86ab2f674f93331240a62dd935046bc9f5b9`
- `video_join.json` sha256 `ece6d18bb7cbdd06819f9d0dc5190c85d564280c66a5979e3f1ea287e2e7e831`
- `review.mp4` sha256 `44fe161c104bb8355fa46fc1675152ba815b49aeba8e0dad50400ab030e95e90`
