# Flight record — E03_v60_forced (E03)   **SILVER**

Scenario `windows_review_E03_yaw` kind=beach seed=3200000005 distance=8.0m height=6.0m boat_speed=0.3m/s

- frames **1117** over **44.64s**; outcome **landed**
- physical events: touchdown@61.65s, stable_contact@62.89s, landed@64.62s
- first lock on the truth target at t=**0.24s**; selection on target afterwards **100.00%**
- hard failures: **none**; soft: physical.no_press_after_contact; criteria hard: none; criteria soft: E01.9_descent_permission_stable

Acceptance criteria that did not pass, with their own numbers:

- `E01.9_descent_permission_stable` — {"reversals": 6, "limit": 3}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1117, "frame_rows": 1117}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1116}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1117, "probes": 5, "max_mean_abs_diff": 3.992119502314815}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | yes | hard | `{"outcome": "landed", "stop_reason": null, "strict": true, "final_height": 0.678, "final_clearance": -0.0}` |
| `physical.disarmed_after_landing` | yes | hard | `{"armed": false, "landed": true, "outcome": "landed"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": 44.64, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | yes | hard | `{"contact_t": 41.52, "disarm_t": 42.64, "delay_s": 1.12, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 28, "span_s": 1.08}` |
| `physical.no_collision` | yes | hard | `{"events": [["touchdown", 61.65], ["stable_contact", 62.89], ["landed", 64.62]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 993, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 0, "longest_s": 0.0, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 0.24, "target_fraction": 1.0, "aliases": ["10", "18", "19", "2", "22", "4", "6", "7"]}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 1.0, "limit": 0.98, "frames_after": 1111, "frames_on_target": 1111}` |
| `authority.guards_engaged_with_enforcement` | yes | soft | `{"events": 3, "kinds": ["descent_without_fresh_geometry"], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 0.2, "situation": "E03", "scenario_requires_survey": false, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 827, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 2, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.fault_actually_injected` | yes | hard | `{"fault_rows": 30}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "visible", "distance_band": [5.0, 20.0], "fault": "gimbal_pan", "mode": "expert"}` |
| `digest.matches_recording` | yes | soft | `{"digest_frames": 1117, "frames": 1117, "present": true}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.20 | 0.24 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.54→6.56 | 8.12→8.12 | 5.68→5.70 | -0.00,-0.00,-0.04,-0.06 | 6066 | 0.00 |
| 0.24–3.88 | 3.68 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2,3/target | 6.56→6.51 | 8.12→3.96 | 5.70→5.72 | +1.57,+0.01,+0.00,+0.00 | 14956 | 1.00 |
| 3.92–4.28 | 0.40 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2/target | 6.51→6.50 | 3.90→3.34 | 5.72→5.72 | +1.50,-0.01,-0.00,-0.00 | 16845 | 1.00 |
| 4.32–4.60 | 0.32 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2/target | 6.50→6.50 | 3.29→2.90 | 5.72→5.73 | +1.26,-0.01,-0.00,-0.01 | 18094 | 1.00 |
| 4.64–4.92 | 0.32 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2/target | 6.50→6.50 | 2.85→2.53 | 5.73→5.74 | +1.00,-0.01,-0.00,-0.01 | 19057 | 1.00 |
| 4.96–7.56 | 2.64 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.50→6.48 | 2.49→0.35 | 5.74→5.78 | +1.02,-0.02,+0.01,+0.01 | 22584 | 1.00 |
| 7.60–9.00 | 1.44 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.48→6.28 | 0.34→0.11 | 5.78→5.57 | +0.47,-0.01,+0.17,+0.00 | 24290 | 1.00 |
| 9.04–9.08 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 2/target | 6.27→6.26 | 0.11→0.11 | 5.56→5.55 | +0.35,+0.02,+0.00,+0.00 | 24469 | 1.00 |
| 9.12–9.28 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.25→6.22 | 0.11→0.10 | 5.55→5.52 | +0.41,+0.00,+0.04,+0.01 | 24811 | 1.00 |
| 9.32–11.24 | 1.96 | descend / target_align | `identity_and_fresh_geometry_associated` | 2,4/target | 6.21→5.87 | 0.10→0.03 | 5.52→5.18 | +0.40,-0.01,+0.18,+0.00 | 28027 | 1.00 |
| 11.28–11.28 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 2/target | 5.86→5.86 | 0.03→0.03 | 5.17→5.17 | +0.30,+0.01,+0.00,+0.00 | 28306 | 1.00 |
| 11.32–11.48 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2,4/target | 5.86→5.83 | 0.03→0.02 | 5.16→5.13 | +0.36,-0.01,+0.06,-0.00 | 28606 | 1.00 |
| 11.52–32.52 | 21.04 | descend / target_align | `identity_and_fresh_geometry_associated` | 2,4,6,7+.../target | 5.83→1.27 | 0.02→0.01 | 5.13→0.59 | +0.31,-0.00,+0.21,+0.00 | 226901 | 1.00 |
| 32.56–34.72 | 2.20 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18,19/target | 1.26→1.26 | 0.01→0.01 | 0.58→0.58 | +0.30,-0.00,+0.00,+0.00 | 222816 | 1.00 |
| 34.76–34.92 | 0.20 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 19/target | 1.26→1.25 | 0.01→0.01 | 0.58→0.57 | +0.30,-0.02,+0.02,+0.00 | 222567 | 1.00 |
| 34.96–37.28 | 2.36 | descend / target_align | `identity_and_fresh_geometry_associated` | 19/target | 1.25→1.05 | 0.01→0.01 | 0.57→0.36 | +0.29,+0.00,+0.09,-0.00 | 222519 | 1.00 |
| 37.32–37.52 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 19/target | 1.05→1.03 | 0.01→0.01 | 0.36→0.34 | +0.29,-0.01,+0.00,+0.00 | 215254 | 1.00 |
| 37.56–38.68 | 1.16 | descend / target_align | `identity_and_fresh_geometry_associated` | 19/target | 1.03→0.93 | 0.01→0.01 | 0.34→0.25 | +0.29,+0.00,+0.10,+0.00 | 214123 | 1.00 |
| 38.72–38.92 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 19/target | 0.93→0.91 | 0.01→0.01 | 0.24→0.23 | +0.29,-0.01,+0.01,-0.00 | 210593 | 1.00 |
| 38.96–39.76 | 0.84 | descend / target_align | `identity_and_fresh_geometry_associated` | 19,22/target | 0.90→0.85 | 0.01→0.01 | 0.22→0.16 | +0.29,-0.01,+0.08,+0.00 | 208488 | 1.00 |
| 39.80–40.00 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.85→0.84 | 0.01→0.01 | 0.15→0.14 | +0.29,+0.01,-0.02,+0.00 | 209405 | 1.00 |
| 40.04–41.40 | 1.40 | descend / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.83→0.71 | 0.01→0.01 | 0.14→0.03 | +0.29,-0.00,+0.11,-0.00 | 208829 | 1.00 |
| 41.44–41.44 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.70→0.70 | 0.01→0.01 | 0.03→0.03 | +0.30,-0.00,+0.13,+0.00 | 173359 | 1.00 |
| 41.48–42.60 | 1.16 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.70→0.69 | 0.01→0.02 | 0.02→-0.00 | +0.29,-0.01,+0.28,+0.00 | 170524 | 1.00 |
| 42.64–44.64 | 2.04 | disarmed / ground_hold | `own_estimator_not_airborne` | 22/target | 0.69→0.68 | 0.02→0.02 | -0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 154861 | 1.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 0.2 | `scan` | 6.54→6.56 | 8.12→8.12 | 5.68→5.70 | 0% |
| 0.2 | 4.7 | `target_inspect` | 6.56→6.50 | 8.12→2.53 | 5.70→5.74 | 100% |
| 5.0 | 2.6 | `target_align` | 6.50→6.48 | 2.49→0.35 | 5.74→5.78 | 100% |
| 7.6 | 1.7 | `target_align` | 6.48→6.22 | 0.34→0.10 | 5.78→5.52 | 100% |
| 9.3 | 2.2 | `target_align` | 6.21→5.83 | 0.10→0.02 | 5.52→5.13 | 100% |
| 11.5 | 21.0 | `target_align` | 5.83→1.27 | 0.02→0.01 | 5.13→0.59 | 100% |
| 32.6 | 2.4 | `target_align` | 1.26→1.25 | 0.01→0.01 | 0.58→0.57 | 100% |
| 35.0 | 2.6 | `target_align` | 1.25→1.03 | 0.01→0.01 | 0.57→0.34 | 100% |
| 37.6 | 1.4 | `target_align` | 1.03→0.91 | 0.01→0.01 | 0.34→0.23 | 100% |
| 39.0 | 1.1 | `target_align` | 0.90→0.84 | 0.01→0.01 | 0.22→0.14 | 100% |
| 40.0 | 1.4 | `target_align` | 0.83→0.70 | 0.01→0.01 | 0.14→0.03 | 100% |
| 41.5 | 1.2 | `target_align` | 0.70→0.69 | 0.01→0.02 | 0.02→-0.00 | 100% |
| 42.6 | 2.0 | `ground_hold` | 0.69→0.68 | 0.02→0.02 | -0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.54, tgt 6064px)
- **t=0.24s** `target_inspect` — target_likely_evidence_requires_inspection (sel 2/target, alt 6.56, tgt 6058px)
- **t=4.96s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.50, tgt 19226px)
- **t=9.04s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 2/target, alt 6.27, tgt 24462px)
- **t=9.12s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.25, tgt 24623px)
- **t=11.28s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 2/target, alt 5.86, tgt 28306px)
- **t=11.32s** `target_align` — identity_and_fresh_geometry_associated (sel 4/target, alt 5.86, tgt 28358px)
- **t=42.64s** `ground_hold` — own_estimator_not_airborne (sel 22/target, alt 0.69, tgt 152333px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–44.64s coverage 0.00 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- survey_interrupted track=None 
- preempt_candidate track=None 
- target_confirmed track=2 identity_evidence_acquired

## Recovery ledger

- visibility management (no altitude gain) t=0.24–3.88s (3.68s) alt [6.56, 6.51, 6.51, 6.56] range [8.12, 3.96, 3.96, 8.13]
- visibility management (no altitude gain) t=4.32–4.6s (0.32s) alt [6.5, 6.5, 6.5, 6.5] range [3.29, 2.9, 2.9, 3.29]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 5.0 | 6.50 | 2.44 | 5.74 | 1.41 | 0.1 | 19282 | True | 0.045 |
| 7.0 | 6.50 | 0.61 | 5.80 | 0.98 | -2.4 | 22242 | True | 0.042 |
| 9.0 | 6.28 | 0.11 | 5.57 | 0.42 | -21.0 | 24290 | True | 0.295 |
| 11.0 | 5.94 | 0.03 | 5.25 | 0.35 | -47.1 | 27343 | True | 0.242 |
| 13.0 | 5.51 | 0.03 | 4.83 | 0.31 | 25.8 | 32254 | True | 0.237 |
| 15.1 | 5.07 | 0.01 | 4.37 | 0.31 | -25.1 | 39170 | True | 0.165 |
| 17.1 | 4.64 | 0.01 | 3.95 | 0.31 | -58.6 | 47827 | True | 0.202 |
| 19.2 | 4.22 | 0.01 | 3.54 | 0.30 | 41.6 | 58780 | True | 0.212 |
| 21.2 | 3.77 | 0.02 | 3.07 | 0.29 | -133.4 | 69894 | True | 0.189 |
| 23.2 | 3.31 | 0.01 | 2.63 | 0.29 | -93.0 | 82299 | True | 0.227 |
| 25.3 | 2.87 | 0.01 | 2.19 | 0.29 | -83.0 | 98449 | True | 0.226 |
| 27.3 | 2.41 | 0.01 | 1.71 | 0.29 | -31.7 | 124479 | True | 0.198 |
| 29.4 | 1.97 | 0.01 | 1.28 | 0.30 | -9.7 | 163488 | True | 0.216 |
| 31.4 | 1.52 | 0.01 | 0.83 | 0.30 | -35.6 | 226524 | True | 0.217 |
| 33.4 | 1.25 | 0.01 | 0.55 | 0.29 | -43.6 | 221862 | True | -0.031 |
| 35.5 | 1.22 | 0.00 | 0.54 | 0.30 | 4.1 | 221744 | True | 0.097 |
| 37.5 | 1.03 | 0.01 | 0.34 | 0.29 | -165.5 | 214323 | True | 0.003 |
| 39.6 | 0.87 | 0.01 | 0.18 | 0.30 | -166.6 | 202748 | True | 0.076 |
| 41.6 | 0.69 | 0.01 | 0.01 | 0.30 | 100.4 | 159506 | True | 0.221 |
| 43.6 | 0.68 | 0.02 | -0.00 | 0.30 | -10.7 | 152994 | True | 0.000 |

## Contradictions between belief and observed truth

- minor `identity_head_flips_near_deck` frames 444 t=21.6–21.6s {"flips": 34, "rate_per_s": 1.91, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- minor `recovery_while_pad_visible` frames 63 t=0.24–11.28s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60_forced\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60_forced\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60_forced\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `544844d66d02e0d46156c5c58ca62e929a7763365b52c1d317fdb0700a959d48`
- `frames.csv` sha256 `b83b67e7f6aa90df906615c11b2ef5f0b259373f288e70e62ce2cfe973ec6786`
- `verdict.json` sha256 `c03f82f6866445c2f0a67c05403bbe6d5fc6a1d3fcc90870f777d1331ccede85`
- `video_join.json` sha256 `dbb8947b22d13edd0ff1b84d1ceed345aae979d6341d83641f433057998dbf3a`
- `review.mp4` sha256 `84bc0b782b916b77a3b027de1c37c67d99e7e5ce8ae980751fef4ace6dbc6b68`
