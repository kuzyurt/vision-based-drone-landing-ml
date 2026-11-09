# Flight record — E07_v60 (E07)   **SILVER**

Scenario `windows_review_E07_search_mid` kind=beach seed=3200000002 distance=28.0m height=6.0m boat_speed=0.3m/s

- frames **1931** over **77.20s**; outcome **landed**
- physical events: touchdown@91.45s, stable_contact@92.72s, unstable_contact@92.94s, stable_contact@95.51s, landed@97.17s
- first lock on the truth target at t=**18.08s**; selection on target afterwards **100.00%**
- hard failures: **none**; soft: physical.no_press_after_contact; criteria hard: E01.4_no_false_boat_claim_drives_selection; criteria soft: E01.7_descent_framing_no_long_loss, E01.9_descent_permission_stable, E01.10b_parent_recovery_share_below_limit

Acceptance criteria that did not pass, with their own numbers:

- `E01.4_no_false_boat_claim_drives_selection` — {"frames": 7, "examples": [{"t": 37.79999999995454, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}, {"t": 37.83999999995444, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}, {"t": 37.87999999995435, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}, {"t": 37.91999999995426, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}, {"t": 37.959999999954164, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}]}
- `E01.7_descent_framing_no_long_loss` — {"longest_lost_descent_s": 1.24, "limit_s": 1.0, "windows": [{"t0": 38.319999999953325, "t1": 39.559999999950435, "pad_err": 45.002777692049186}]}
- `E01.9_descent_permission_stable` — {"reversals": 4, "limit": 3}
- `E01.10b_parent_recovery_share_below_limit` — {"share": 0.1968, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1931, "frame_rows": 1931}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1930}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1931, "probes": 5, "max_mean_abs_diff": 2.2441160300925924}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | yes | hard | `{"outcome": "landed", "stop_reason": null, "strict": true, "final_height": 0.675, "final_clearance": -0.0}` |
| `physical.disarmed_after_landing` | yes | hard | `{"armed": false, "landed": true, "outcome": "landed"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": 77.2, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | yes | hard | `{"contact_t": 71.32, "disarm_t": 75.2, "delay_s": 3.88, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 97, "span_s": 3.84}` |
| `physical.no_collision` | yes | hard | `{"events": [["touchdown", 91.45], ["stable_contact", 92.72], ["unstable_contact", 92.94], ["stable_contact", 95.51], ["landed", 97.17]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 1282, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 7, "longest_s": 0.24, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 18.08, "target_fraction": 1.0, "aliases": ["18", "22", "23", "25", "27", "30", "35", "38"]}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 1.0, "limit": 0.98, "frames_after": 1479, "frames_on_target": 1479}` |
| `authority.guards_engaged_with_enforcement` | yes | soft | `{"events": 11, "kinds": ["descent_without_fresh_geometry"], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 18.04, "situation": "E07", "scenario_requires_survey": true, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 872, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 3, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.target_outside_initial_view` | yes | hard | `{"first_frame_target_px": 0.0, "lock_t": 18.08}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "outside_camera", "distance_band": [20.0, 40.0], "fault": null, "mode": "expert"}` |
| `digest.matches_recording` | yes | soft | `{"digest_frames": 1931, "frames": 1931, "present": true}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–18.04 | 18.08 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.54→6.51 | 28.09→33.66 | 5.25→4.94 | -0.00,-0.00,-0.00,-0.34 | 379 | 0.00 |
| 18.08–21.08 | 3.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 18/target | 6.51→6.50 | 33.67→31.00 | 4.94→4.93 | +1.53,-0.08,+0.00,-0.06 | 305 | 0.90 |
| 21.12–24.48 | 3.40 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 18/target | 6.50→6.49 | 30.93→24.76 | 4.93→5.19 | +2.00,-0.01,+0.00,-0.00 | 528 | 0.48 |
| 24.52–25.92 | 1.44 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 18/target | 6.49→6.48 | 24.68→22.18 | 5.19→5.29 | +2.00,-0.01,+0.00,-0.00 | 688 | 0.97 |
| 25.96–36.16 | 10.24 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 6.48→6.44 | 22.11→4.65 | 5.30→5.65 | +1.96,-0.01,-0.00,-0.00 | 12866 | 0.99 |
| 36.20–36.64 | 0.48 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 6.44→6.43 | 4.59→4.00 | 5.65→5.64 | +1.43,-0.00,-0.00,-0.01 | 14745 | 0.07 |
| 36.68–36.68 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 6.43→6.43 | 3.94→3.94 | 5.64→5.64 | +1.39,+0.01,+0.00,+0.01 | 14887 | 0.87 |
| 36.72–36.72 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 6.43→6.43 | 3.89→3.89 | 5.64→5.64 | +1.44,+0.01,+0.00,+0.01 | 15058 | 1.00 |
| 36.76–37.76 | 1.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 6.43→6.41 | 3.84→2.82 | 5.64→5.64 | +1.24,-0.01,+0.02,+0.00 | 18468 | 1.00 |
| 37.80–38.04 | 0.28 | align / target_align | `identity_and_fresh_geometry_associated` | 18/none | 6.40→6.41 | 2.78→2.55 | 5.65→5.66 | +1.76,+0.01,-0.02,+0.04 | 19185 | 1.00 |
| 38.08–40.48 | 2.44 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 6.41→6.35 | 2.51→0.39 | 5.66→5.65 | +0.99,-0.02,+0.02,+0.01 | 23671 | 1.00 |
| 40.52–42.20 | 1.72 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18,22/target | 6.35→6.15 | 0.38→0.18 | 5.65→5.46 | +0.46,-0.01,+0.13,+0.00 | 25240 | 1.00 |
| 42.24–42.64 | 0.44 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 6.14→6.11 | 0.18→0.16 | 5.46→5.42 | +0.32,-0.01,+0.00,+0.00 | 25697 | 1.00 |
| 42.68–43.28 | 0.64 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 6.11→6.06 | 0.16→0.15 | 5.42→5.37 | +0.44,-0.01,+0.19,-0.00 | 26129 | 1.00 |
| 43.32–43.44 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 18/target | 6.05→6.02 | 0.15→0.15 | 5.36→5.32 | +0.44,+0.02,+0.27,+0.00 | 26604 | 1.00 |
| 43.48–44.64 | 1.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 6.01→5.73 | 0.15→0.10 | 5.31→5.04 | +0.39,-0.00,+0.22,-0.00 | 29803 | 1.00 |
| 44.68–69.48 | 24.84 | descend / target_align | `identity_and_fresh_geometry_associated` | 18,22,23,25+.../target | 5.72→0.85 | 0.10→0.00 | 5.03→0.16 | +0.31,-0.00,+0.19,-0.00 | 226819 | 1.00 |
| 69.52–69.72 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 38/target | 0.85→0.83 | 0.00→0.00 | 0.15→0.14 | +0.30,-0.02,+0.02,-0.00 | 208209 | 1.00 |
| 69.76–70.40 | 0.68 | descend / target_align | `identity_and_fresh_geometry_associated` | 38/target | 0.82→0.77 | 0.00→0.01 | 0.14→0.09 | +0.30,-0.02,+0.10,+0.00 | 208194 | 1.00 |
| 70.44–70.64 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 38/target | 0.76→0.74 | 0.01→0.00 | 0.09→0.07 | +0.29,+0.00,+0.01,+0.00 | 195799 | 1.00 |
| 70.68–71.20 | 0.56 | descend / target_align | `identity_and_fresh_geometry_associated` | 38/target | 0.74→0.72 | 0.00→0.01 | 0.06→0.03 | +0.29,-0.00,+0.07,-0.00 | 189274 | 1.00 |
| 71.24–71.24 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 38/target | 0.71→0.71 | 0.01→0.01 | 0.03→0.03 | +0.30,-0.00,+0.10,+0.00 | 172808 | 1.00 |
| 71.28–75.12 | 3.88 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 38/target | 0.71→0.69 | 0.01→0.02 | 0.02→-0.00 | +0.29,-0.00,+0.31,+0.00 | 170222 | 1.00 |
| 75.16–75.16 | 0.04 | confirm / ground_hold | `own_estimator_not_airborne` | 38/target | 0.69→0.69 | 0.02→0.02 | -0.00→-0.00 | +0.23,+0.00,+0.32,+0.00 | 159647 | 1.00 |
| 75.20–77.20 | 2.04 | disarmed / ground_hold | `own_estimator_not_airborne` | 38/target | 0.69→0.68 | 0.02→0.02 | -0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 162016 | 1.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 18.1 | `scan` | 6.54→6.51 | 28.09→33.66 | 5.25→4.94 | 0% |
| 18.1 | 3.0 | `target_inspect` | 6.51→6.50 | 33.67→31.00 | 4.94→4.93 | 100% |
| 21.1 | 3.4 | `target_inspect` | 6.50→6.49 | 30.93→24.76 | 4.93→5.19 | 100% |
| 24.5 | 1.4 | `target_inspect` | 6.49→6.48 | 24.68→22.18 | 5.19→5.29 | 100% |
| 26.0 | 10.8 | `target_inspect` | 6.48→6.43 | 22.11→3.89 | 5.30→5.64 | 100% |
| 36.8 | 1.3 | `target_align` | 6.43→6.41 | 3.84→2.55 | 5.64→5.66 | 79% |
| 38.1 | 2.4 | `target_align` | 6.41→6.35 | 2.51→0.39 | 5.66→5.65 | 100% |
| 40.5 | 3.0 | `target_align` | 6.35→6.02 | 0.38→0.15 | 5.65→5.32 | 100% |
| 43.5 | 1.2 | `target_align` | 6.01→5.73 | 0.15→0.10 | 5.31→5.04 | 100% |
| 44.7 | 26.6 | `target_align` | 5.72→0.71 | 0.10→0.01 | 5.03→0.03 | 100% |
| 71.3 | 3.9 | `target_align` | 0.71→0.69 | 0.01→0.02 | 0.02→-0.00 | 100% |
| 75.2 | 0.0 | `ground_hold` | 0.69→0.69 | 0.02→0.02 | -0.00→-0.00 | 100% |
| 75.2 | 2.0 | `ground_hold` | 0.69→0.68 | 0.02→0.02 | -0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.54, tgt 0px)
- **t=18.08s** `target_inspect` — target_likely_evidence_requires_inspection (sel 18/target, alt 6.51, tgt 303px)
- **t=25.96s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 6.48, tgt 701px)
- **t=36.76s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 6.43, tgt 15177px)
- **t=42.24s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 6.14, tgt 25342px)
- **t=42.68s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 6.11, tgt 25575px)
- **t=75.16s** `ground_hold` — own_estimator_not_airborne (sel 38/target, alt 0.69, tgt 159647px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–77.20s coverage 5.24 rad, inspected views 11, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- reject_candidate track=13 visually_observed_wrong_design
- survey_interrupted track=None 
- reject_candidate track=14 visually_observed_wrong_design
- target_confirmed track=18 identity_evidence_acquired

## Recovery ledger

- visibility management (no altitude gain) t=18.08–21.08s (3.04s) alt [6.51, 6.5, 6.5, 6.51] range [33.67, 31.0, 31.0, 33.8]
- visibility management (no altitude gain) t=24.52–36.16s (11.68s) alt [6.49, 6.44, 6.44, 6.49] range [24.68, 4.65, 4.65, 24.68]
- visibility management (no altitude gain) t=42.24–42.64s (0.44s) alt [6.14, 6.11, 6.11, 6.14] range [0.18, 0.16, 0.16, 0.18]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 37.0 | 6.43 | 3.52 | 5.64 | 1.42 | -0.7 | 16285 | True | 0.047 |
| 39.1 | 6.39 | 1.28 | 5.67 | 1.46 | 1.4 | 22310 | True | 0.145 |
| 41.1 | 6.33 | 0.27 | 5.63 | 0.40 | -0.3 | 23811 | True | 0.113 |
| 43.2 | 6.09 | 0.16 | 5.40 | 0.30 | -9.1 | 25876 | True | 0.303 |
| 45.2 | 5.59 | 0.09 | 4.91 | 0.31 | 17.3 | 31195 | True | 0.207 |
| 47.2 | 5.20 | 0.06 | 4.50 | 0.31 | 2.6 | 37101 | True | 0.157 |
| 49.2 | 4.76 | 0.04 | 4.07 | 0.30 | -34.9 | 45153 | True | 0.223 |
| 51.2 | 4.34 | 0.03 | 3.65 | 0.30 | -91.5 | 56044 | True | 0.197 |
| 53.2 | 3.87 | 0.00 | 3.17 | 0.29 | -80.4 | 67667 | True | 0.185 |
| 55.2 | 3.45 | 0.00 | 2.76 | 0.29 | 55.1 | 78195 | True | 0.184 |
| 57.2 | 3.05 | 0.01 | 2.36 | 0.29 | -45.8 | 91478 | True | 0.218 |
| 59.2 | 2.57 | 0.01 | 1.87 | 0.29 | 80.8 | 114221 | True | 0.213 |
| 61.2 | 2.15 | 0.01 | 1.47 | 0.30 | 94.8 | 143324 | True | 0.241 |
| 63.2 | 1.71 | 0.00 | 1.01 | 0.29 | -62.7 | 203171 | True | 0.209 |
| 65.2 | 1.26 | 0.00 | 0.58 | 0.30 | 2.0 | 222506 | True | 0.089 |
| 67.2 | 1.07 | 0.00 | 0.39 | 0.29 | 154.7 | 214670 | True | 0.115 |
| 69.2 | 0.89 | 0.01 | 0.19 | 0.29 | 174.6 | 203576 | True | 0.110 |
| 71.2 | 0.72 | 0.01 | 0.03 | 0.30 | 147.1 | 177236 | True | 0.078 |
| 73.2 | 0.69 | 0.01 | -0.00 | 0.30 | -18.5 | 159322 | True | 0.327 |
| 75.2 | 0.69 | 0.02 | -0.00 | 0.30 | -16.1 | 159647 | True | 0.320 |
| 77.2 | 0.67 | 0.02 | -0.00 | 0.31 | -11.1 | 160473 | True | 0.000 |

## Contradictions between belief and observed truth

- minor `identity_head_flips_near_deck` frames 370 t=54.2–54.2s {"flips": 29, "rate_per_s": 1.96, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- minor `recovery_while_pad_visible` frames 123 t=18.08–42.64s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E07_v60\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E07_v60\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E07_v60\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `bec88308aca3921d5c5c5353a1417a1df1e1a6876c22182f82707e6e9d16efb3`
- `frames.csv` sha256 `5c7db52fbd6c1dad1ce9c1e63a299e6b3c2dacbc1689e6d6ecc0eff1fe150259`
- `verdict.json` sha256 `6b8e38f5cb757a67fb3f0b6a25747734ca4226413882efe882b05d61ef192f87`
- `video_join.json` sha256 `9feede6946fcb6458bde43db9daae19b6d8f61840ac1ab0955ba5ce7afe4f5ef`
- `review.mp4` sha256 `c011d0b8a2d7b49701b111a408cd7a887bd979eabfea1e76d83c8418d560c8dd`
