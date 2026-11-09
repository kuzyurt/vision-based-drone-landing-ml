# Flight record — E01_nominal_v60c (E01)   **SILVER**

Scenario `windows_review_E01_nominal` kind=beach seed=3200000000 distance=8.0m height=6.0m boat_speed=0.3m/s

- frames **1162** over **46.44s**; outcome **landed**
- physical events: touchdown@60.67s, stable_contact@61.91s, unstable_contact@62.22s, stable_contact@64.68s, landed@66.37s
- first lock on the truth target at t=**0.12s**; selection on target afterwards **100.00%**
- hard failures: **none**; soft: physical.no_press_after_contact; criteria hard: none; criteria soft: E01.9_descent_permission_stable

Acceptance criteria that did not pass, with their own numbers:

- `E01.9_descent_permission_stable` — {"reversals": 10, "limit": 3}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1162, "frame_rows": 1162}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1161}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1162, "probes": 5, "max_mean_abs_diff": 3.4255946180555554}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | yes | hard | `{"outcome": "landed", "stop_reason": null, "strict": true, "final_height": 0.68, "final_clearance": -0.0}` |
| `physical.disarmed_after_landing` | yes | hard | `{"armed": false, "landed": true, "outcome": "landed"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": 46.44, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | yes | hard | `{"contact_t": 40.56, "disarm_t": 44.44, "delay_s": 3.88, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 97, "span_s": 3.84}` |
| `physical.no_collision` | yes | hard | `{"events": [["touchdown", 60.67], ["stable_contact", 61.91], ["unstable_contact", 62.22], ["stable_contact", 64.68], ["landed", 66.37]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 1045, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 0, "longest_s": 0.0, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 0.12, "target_fraction": 1.0, "aliases": ["11", "13", "16", "19", "2", "4", "5", "7"]}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 1.0, "limit": 0.98, "frames_after": 1159, "frames_on_target": 1159}` |
| `authority.guards_engaged_with_enforcement` | yes | hard | `{"events": 0, "kinds": [], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 0.08, "situation": "E01", "scenario_requires_survey": false, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 873, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 2, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "visible", "distance_band": [5.0, 20.0], "fault": null, "mode": "expert"}` |
| `digest.matches_recording` | yes | soft | `{"digest_frames": 1162, "frames": 1162, "present": true}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.08 | 0.12 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.53→6.54 | 8.17→8.17 | 5.64→5.64 | +0.00,+0.00,-0.07,-0.03 | 5930 | 0.00 |
| 0.12–3.48 | 3.40 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2,3/target | 6.54→6.49 | 8.17→4.43 | 5.65→5.69 | +1.56,+0.00,-0.00,-0.00 | 13533 | 0.98 |
| 3.52–4.64 | 1.16 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2,3/target | 6.48→6.48 | 4.36→2.68 | 5.69→5.71 | +1.41,-0.01,-0.00,-0.00 | 18773 | 1.00 |
| 4.68–4.80 | 0.16 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 2/target | 6.48→6.48 | 2.63→2.50 | 5.71→5.72 | +0.98,-0.00,-0.00,-0.00 | 19317 | 1.00 |
| 4.84–5.16 | 0.36 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.48→6.48 | 2.46→2.17 | 5.72→5.73 | +0.64,+0.07,-0.05,+0.00 | 20184 | 1.00 |
| 5.20–5.20 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 2/target | 6.48→6.48 | 2.14→2.14 | 5.73→5.73 | +0.47,-0.01,-0.11,-0.02 | 20275 | 1.00 |
| 5.24–6.52 | 1.32 | align / target_align | `identity_and_fresh_geometry_associated` | 2,4/target | 6.48→6.50 | 2.11→1.38 | 5.74→5.78 | +1.19,-0.07,-0.01,+0.01 | 21290 | 1.00 |
| 6.56–6.60 | 0.08 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 4/target | 6.50→6.50 | 1.34→1.30 | 5.78→5.78 | +1.25,-0.01,+0.00,-0.01 | 21539 | 1.00 |
| 6.64–7.60 | 1.00 | align / target_align | `identity_and_fresh_geometry_associated` | 2,4/target | 6.50→6.53 | 1.27→0.52 | 5.78→5.81 | +0.82,-0.02,-0.03,+0.00 | 22401 | 1.00 |
| 7.64–8.12 | 0.52 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 2,4/target | 6.53→6.52 | 0.49→0.29 | 5.81→5.82 | +0.42,+0.00,-0.00,+0.02 | 22557 | 1.00 |
| 8.16–8.24 | 0.12 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.52→6.52 | 0.28→0.26 | 5.82→5.82 | +0.13,-0.08,+0.02,+0.05 | 22538 | 1.00 |
| 8.28–8.64 | 0.40 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.52→6.51 | 0.25→0.23 | 5.82→5.81 | +0.40,-0.04,+0.14,-0.01 | 22477 | 1.00 |
| 8.68–8.76 | 0.12 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.50→6.49 | 0.23→0.23 | 5.81→5.80 | +0.61,-0.00,+0.15,+0.00 | 22481 | 1.00 |
| 8.80–8.96 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.48→6.45 | 0.23→0.23 | 5.79→5.76 | +0.56,-0.00,+0.17,-0.00 | 22749 | 1.00 |
| 9.00–9.08 | 0.12 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.44→6.43 | 0.23→0.22 | 5.76→5.74 | +0.49,+0.01,+0.12,+0.00 | 22866 | 1.00 |
| 9.12–10.56 | 1.48 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.42→6.06 | 0.22→0.11 | 5.74→5.36 | +0.46,-0.01,+0.24,-0.00 | 26232 | 1.00 |
| 10.60–10.88 | 0.32 | descend / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.05→6.02 | 0.10→0.09 | 5.36→5.32 | +0.42,+0.02,+0.08,-0.01 | 26635 | 1.00 |
| 10.92–10.92 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 2/target | 6.01→6.01 | 0.09→0.09 | 5.32→5.32 | +0.39,-0.00,+0.00,+0.01 | 26657 | 1.00 |
| 10.96–11.12 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.01→6.00 | 0.08→0.08 | 5.32→5.30 | +0.38,+0.01,+0.07,-0.00 | 26742 | 1.00 |
| 11.16–32.44 | 21.32 | descend / target_align | `identity_and_fresh_geometry_associated` | 2,4,5,7+.../target | 6.00→1.35 | 0.07→0.00 | 5.30→0.66 | +0.31,-0.00,+0.22,+0.00 | 226824 | 1.00 |
| 32.48–32.68 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 13,19/target | 1.34→1.31 | 0.00→0.00 | 0.65→0.61 | +0.29,+0.02,-0.01,+0.00 | 224033 | 1.00 |
| 32.72–35.56 | 2.88 | descend / target_align | `identity_and_fresh_geometry_associated` | 13/target | 1.31→1.04 | 0.00→0.01 | 0.61→0.36 | +0.30,-0.00,+0.10,+0.00 | 223420 | 1.00 |
| 35.60–35.80 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 13/target | 1.04→1.03 | 0.01→0.01 | 0.35→0.34 | +0.29,-0.01,-0.02,+0.00 | 212312 | 1.00 |
| 35.84–36.20 | 0.40 | descend / target_align | `identity_and_fresh_geometry_associated` | 13/target | 1.03→1.02 | 0.01→0.01 | 0.33→0.32 | +0.30,-0.01,+0.06,-0.00 | 213036 | 1.00 |
| 36.24–36.52 | 0.32 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 13/target | 1.02→1.01 | 0.01→0.01 | 0.32→0.31 | +0.31,+0.01,-0.02,+0.00 | 215547 | 1.00 |
| 36.56–37.72 | 1.20 | descend / target_align | `identity_and_fresh_geometry_associated` | 13/target | 1.01→0.90 | 0.01→0.01 | 0.31→0.22 | +0.30,-0.01,+0.11,+0.00 | 215448 | 1.00 |
| 37.76–37.96 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 13/target | 0.89→0.87 | 0.01→0.01 | 0.22→0.19 | +0.30,-0.01,+0.00,+0.00 | 207223 | 1.00 |
| 38.00–38.52 | 0.56 | descend / target_align | `identity_and_fresh_geometry_associated` | 13/target | 0.87→0.85 | 0.01→0.01 | 0.19→0.16 | +0.30,+0.01,+0.07,-0.00 | 203874 | 1.00 |
| 38.56–38.76 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 13/target | 0.84→0.83 | 0.01→0.01 | 0.15→0.14 | +0.30,+0.01,-0.02,-0.00 | 209709 | 1.00 |
| 38.80–39.60 | 0.84 | descend / target_align | `identity_and_fresh_geometry_associated` | 13/target | 0.83→0.78 | 0.01→0.01 | 0.14→0.09 | +0.29,-0.00,+0.09,+0.00 | 208748 | 1.00 |
| 39.64–39.84 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 13/target | 0.78→0.76 | 0.01→0.01 | 0.09→0.07 | +0.30,-0.00,+0.03,+0.00 | 196208 | 1.00 |
| 39.88–40.48 | 0.64 | descend / target_align | `identity_and_fresh_geometry_associated` | 13/target | 0.76→0.71 | 0.01→0.01 | 0.07→0.03 | +0.30,-0.02,+0.10,+0.00 | 191101 | 1.00 |
| 40.52–40.52 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 13/target | 0.71→0.71 | 0.01→0.01 | 0.02→0.02 | +0.30,-0.01,+0.12,+0.00 | 172134 | 1.00 |
| 40.56–44.36 | 3.84 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 13/target | 0.70→0.68 | 0.01→0.01 | 0.02→-0.00 | +0.30,-0.00,+0.31,+0.00 | 169174 | 1.00 |
| 44.40–44.40 | 0.04 | confirm / ground_hold | `own_estimator_not_airborne` | 13/target | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | +0.24,+0.00,+0.32,+0.00 | 149759 | 1.00 |
| 44.44–46.44 | 2.04 | disarmed / ground_hold | `own_estimator_not_airborne` | 13/target | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 149801 | 1.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 0.1 | `scan` | 6.53→6.54 | 8.17→8.17 | 5.64→5.64 | 0% |
| 0.1 | 3.4 | `target_inspect` | 6.54→6.49 | 8.17→4.43 | 5.65→5.69 | 100% |
| 3.5 | 1.7 | `target_inspect` | 6.48→6.48 | 4.36→2.14 | 5.69→5.73 | 100% |
| 5.2 | 3.9 | `target_align` | 6.48→6.43 | 2.11→0.22 | 5.74→5.74 | 100% |
| 9.1 | 2.0 | `target_align` | 6.42→6.00 | 0.22→0.08 | 5.74→5.30 | 100% |
| 11.2 | 21.6 | `target_align` | 6.00→1.31 | 0.07→0.00 | 5.30→0.61 | 100% |
| 32.7 | 3.8 | `target_align` | 1.31→1.01 | 0.00→0.01 | 0.61→0.31 | 100% |
| 36.6 | 2.2 | `target_align` | 1.01→0.83 | 0.01→0.01 | 0.31→0.14 | 100% |
| 38.8 | 1.8 | `target_align` | 0.83→0.71 | 0.01→0.01 | 0.14→0.02 | 100% |
| 40.6 | 3.8 | `target_align` | 0.70→0.68 | 0.01→0.01 | 0.02→-0.00 | 100% |
| 44.4 | 0.0 | `ground_hold` | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | 100% |
| 44.4 | 2.0 | `ground_hold` | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.53, tgt 5930px)
- **t=0.12s** `target_inspect` — target_likely_evidence_requires_inspection (sel 2/target, alt 6.54, tgt 5921px)
- **t=4.68s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 2/target, alt 6.48, tgt 18940px)
- **t=4.84s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.48, tgt 19442px)
- **t=5.20s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 2/target, alt 6.48, tgt 20275px)
- **t=5.24s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.48, tgt 20325px)
- **t=6.56s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 4/target, alt 6.50, tgt 21419px)
- **t=6.64s** `target_align` — identity_and_fresh_geometry_associated (sel 4/target, alt 6.50, tgt 21568px)
- **t=7.64s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 4/target, alt 6.53, tgt 22254px)
- **t=8.16s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.52, tgt 22522px)
- **t=10.92s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 2/target, alt 6.01, tgt 26657px)
- **t=10.96s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.01, tgt 26726px)
- **t=44.40s** `ground_hold` — own_estimator_not_airborne (sel 13/target, alt 0.68, tgt 149759px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–46.44s coverage 0.00 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- survey_interrupted track=None 
- preempt_candidate track=None 
- target_confirmed track=2 identity_evidence_acquired

## Recovery ledger

- visibility management (no altitude gain) t=0.12–3.48s (3.4s) alt [6.54, 6.49, 6.49, 6.55] range [8.17, 4.43, 4.43, 8.17]
- visibility management (no altitude gain) t=7.64–8.12s (0.52s) alt [6.53, 6.52, 6.52, 6.53] range [0.49, 0.29, 0.29, 0.49]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 5.5 | 6.50 | 1.96 | 5.77 | 0.84 | 5.0 | 20152 | True | 0.031 |
| 7.5 | 6.53 | 0.56 | 5.81 | 0.94 | -1.9 | 22259 | True | 0.036 |
| 9.5 | 6.35 | 0.18 | 5.67 | 0.44 | -4.4 | 23385 | True | 0.269 |
| 11.5 | 5.96 | 0.06 | 5.26 | 0.35 | 15.8 | 27149 | True | 0.232 |
| 13.6 | 5.46 | 0.03 | 4.77 | 0.33 | -20.2 | 32932 | True | 0.264 |
| 15.6 | 5.07 | 0.02 | 4.39 | 0.30 | 9.6 | 38970 | True | 0.275 |
| 17.6 | 4.60 | 0.01 | 3.91 | 0.30 | -60.6 | 48952 | True | 0.192 |
| 19.7 | 4.14 | 0.01 | 3.46 | 0.31 | -60.5 | 60818 | True | 0.232 |
| 21.7 | 3.71 | 0.01 | 3.03 | 0.28 | -94.6 | 70850 | True | 0.253 |
| 23.8 | 3.27 | 0.02 | 2.57 | 0.29 | -174.9 | 83985 | True | 0.197 |
| 25.8 | 2.80 | 0.01 | 2.11 | 0.29 | -111.8 | 101926 | True | 0.211 |
| 27.8 | 2.36 | 0.00 | 1.68 | 0.29 | -149.8 | 126745 | True | 0.205 |
| 29.9 | 1.92 | 0.00 | 1.22 | 0.30 | -177.3 | 170652 | True | 0.206 |
| 31.9 | 1.47 | 0.01 | 0.78 | 0.30 | 164.9 | 225956 | True | 0.223 |
| 34.0 | 1.21 | 0.01 | 0.53 | 0.29 | 75.2 | 221211 | True | 0.115 |
| 36.0 | 1.02 | 0.01 | 0.33 | 0.29 | -164.8 | 210994 | True | 0.074 |
| 38.0 | 0.87 | 0.01 | 0.19 | 0.30 | 34.0 | 203646 | True | 0.044 |
| 40.1 | 0.75 | 0.01 | 0.06 | 0.29 | -138.2 | 189227 | True | 0.115 |
| 42.1 | 0.69 | 0.01 | -0.00 | 0.30 | -49.2 | 149809 | True | 0.314 |
| 44.2 | 0.67 | 0.01 | -0.00 | 0.30 | -46.1 | 149774 | True | 0.323 |
| 46.2 | 0.69 | 0.01 | -0.00 | 0.29 | -16.1 | 149761 | True | 0.000 |

## Contradictions between belief and observed truth

- minor `identity_head_flips_near_deck` frames 401 t=21.88–21.88s {"flips": 22, "rate_per_s": 1.37, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- minor `recovery_while_pad_visible` frames 52 t=0.12–10.92s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E01_nominal_v60c\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E01_nominal_v60c\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E01_nominal_v60c\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `cfbce459c1ad855cb956abd8fe575cc9de0da27192e2dc988d97e1727ca033ac`
- `frames.csv` sha256 `14508805f790a8ebce22bc2c1a05a7ecbe0a009566ead6b9c497e6f1e369cd68`
- `verdict.json` sha256 `e47d6c29d3491863922a24e10a1c38f0aa1890ad1aa9ad093d37604f769a29cf`
- `video_join.json` sha256 `9a3838c22aff7cb4fc504c712d40f23e67a5ba84e448a8b8113a916d319765ce`
- `review.mp4` sha256 `0c179b9ec6caa8aaaa26dbbeca5b0ba767625806fb834754e5e2f219e4f14e30`
