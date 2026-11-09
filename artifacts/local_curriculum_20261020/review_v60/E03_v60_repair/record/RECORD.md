# Flight record — E03_v60_repair (E03)   **SILVER**

Scenario `windows_review_E03_yaw` kind=beach seed=3200000005 distance=8.0m height=6.0m boat_speed=0.3m/s

- frames **1215** over **48.56s**; outcome **landed**
- physical events: touchdown@62.99s, stable_contact@64.22s, unstable_contact@65.08s, stable_contact@66.87s, landed@68.53s
- first lock on the truth target at t=**0.2s**; selection on target afterwards **100.00%**
- hard failures: **none**; soft: physical.no_press_after_contact; criteria hard: E01.4_no_false_boat_claim_drives_selection; criteria soft: E01.9_descent_permission_stable

Acceptance criteria that did not pass, with their own numbers:

- `E01.4_no_false_boat_claim_drives_selection` — {"frames": 6, "examples": [{"t": 10.440000000012759, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}, {"t": 10.480000000012808, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}, {"t": 10.520000000012857, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}, {"t": 10.560000000012906, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}, {"t": 10.600000000012955, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}]}
- `E01.9_descent_permission_stable` — {"reversals": 20, "limit": 3}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1215, "frame_rows": 1215}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1214}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1215, "probes": 5, "max_mean_abs_diff": 3.102171585648148}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | yes | hard | `{"outcome": "landed", "stop_reason": null, "strict": true, "final_height": 0.677, "final_clearance": -0.0}` |
| `physical.disarmed_after_landing` | yes | hard | `{"armed": false, "landed": true, "outcome": "landed"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": 48.56, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | yes | hard | `{"contact_t": 42.8, "disarm_t": 46.56, "delay_s": 3.76, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 94, "span_s": 3.72}` |
| `physical.no_collision` | yes | hard | `{"events": [["touchdown", 62.99], ["stable_contact", 64.22], ["unstable_contact", 65.08], ["stable_contact", 66.87], ["landed", 68.53]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 1077, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 6, "longest_s": 0.2, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 0.2, "target_fraction": 1.0, "aliases": ["11", "12", "18", "2", "21", "23", "24", "25", "4", "5", "6", "7", "8", "9"]}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 1.0, "limit": 0.98, "frames_after": 1210, "frames_on_target": 1210}` |
| `authority.guards_engaged_with_enforcement` | yes | soft | `{"events": 20, "kinds": ["descent_without_fresh_geometry"], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 0.16, "situation": "E03", "scenario_requires_survey": false, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 865, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 3, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.fault_actually_injected` | yes | hard | `{"fault_rows": 30}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "visible", "distance_band": [5.0, 20.0], "fault": "gimbal_pan", "mode": "expert"}` |
| `digest.matches_recording` | yes | soft | `{"digest_frames": 1215, "frames": 1215, "present": true}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.16 | 0.20 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.54→6.55 | 8.12→8.12 | 5.68→5.70 | -0.00,-0.00,-0.05,-0.05 | 6064 | 0.00 |
| 0.20–3.80 | 3.64 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2/target | 6.56→6.51 | 8.13→4.02 | 5.70→5.72 | +1.57,+0.01,+0.00,+0.00 | 14730 | 1.00 |
| 3.84–5.48 | 1.68 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2,4/target | 6.51→6.50 | 3.95→2.00 | 5.72→5.75 | +1.09,-0.01,-0.00,-0.01 | 20472 | 1.00 |
| 5.52–6.40 | 0.92 | align / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.50→6.56 | 1.98→1.49 | 5.75→5.83 | +1.22,-0.03,-0.11,+0.02 | 20614 | 1.00 |
| 6.44–6.48 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 2,4/target | 6.56→6.57 | 1.46→1.43 | 5.84→5.85 | +1.41,+0.01,-0.18,+0.00 | 20614 | 1.00 |
| 6.52–6.96 | 0.48 | align / target_align | `identity_and_fresh_geometry_associated` | 4/target | 6.57→6.65 | 1.40→1.00 | 5.86→5.94 | +1.07,-0.00,-0.09,+0.01 | 21054 | 1.00 |
| 7.00–7.00 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 4/target | 6.65→6.65 | 0.96→0.96 | 5.94→5.94 | +0.92,-0.01,+0.00,+0.00 | 20930 | 1.00 |
| 7.04–7.16 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 2,4/target | 6.65→6.66 | 0.93→0.84 | 5.95→5.96 | +0.84,-0.04,-0.01,+0.01 | 21025 | 1.00 |
| 7.20–7.24 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 2/target | 6.66→6.66 | 0.80→0.77 | 5.96→5.96 | +0.71,-0.01,-0.01,+0.00 | 21068 | 1.00 |
| 7.28–7.56 | 0.32 | align / target_align | `identity_and_fresh_geometry_associated` | 2,4/target | 6.66→6.66 | 0.74→0.57 | 5.96→5.96 | +0.68,-0.03,+0.02,+0.01 | 21179 | 1.00 |
| 7.60–7.60 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 4/target | 6.65→6.65 | 0.54→0.54 | 5.95→5.95 | +0.69,-0.01,-0.02,+0.00 | 21165 | 1.00 |
| 7.64–7.76 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 4/target | 6.65→6.65 | 0.52→0.46 | 5.95→5.95 | +0.76,-0.02,-0.04,-0.00 | 21189 | 1.00 |
| 7.80–7.92 | 0.16 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 4/target | 6.65→6.66 | 0.44→0.39 | 5.95→5.96 | +0.70,+0.00,-0.00,+0.00 | 21221 | 1.00 |
| 7.96–8.68 | 0.76 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 4/target | 6.66→6.58 | 0.37→0.15 | 5.96→5.87 | +0.46,-0.01,+0.21,+0.00 | 22022 | 1.00 |
| 8.72–8.96 | 0.28 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 4/target | 6.56→6.50 | 0.14→0.11 | 5.86→5.79 | +0.37,-0.00,+0.00,+0.00 | 22558 | 1.00 |
| 9.00–9.16 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 4/target | 6.49→6.48 | 0.10→0.09 | 5.79→5.78 | +0.40,-0.02,+0.07,+0.00 | 22701 | 1.00 |
| 9.20–9.72 | 0.56 | descend / target_align | `identity_and_fresh_geometry_associated` | 4,5/target | 6.48→6.40 | 0.09→0.07 | 5.78→5.72 | +0.43,-0.00,+0.22,-0.00 | 23118 | 1.00 |
| 9.76–9.84 | 0.12 | match / target_align | `identity_and_fresh_geometry_associated` | 4/target | 6.39→6.37 | 0.07→0.07 | 5.71→5.69 | +0.42,-0.01,+0.22,+0.00 | 23291 | 1.00 |
| 9.88–10.04 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 4,5/target | 6.36→6.32 | 0.07→0.06 | 5.68→5.64 | +0.42,-0.02,+0.30,-0.00 | 23665 | 1.00 |
| 10.08–10.24 | 0.20 | descend / target_align | `identity_and_fresh_geometry_associated` | 2,4/target | 6.31→6.26 | 0.06→0.05 | 5.63→5.58 | +0.46,-0.05,+0.32,+0.01 | 24227 | 1.00 |
| 10.28–10.28 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 2/target | 6.24→6.24 | 0.05→0.05 | 5.56→5.56 | +0.40,-0.02,+0.00,+0.00 | 24479 | 1.00 |
| 10.32–10.40 | 0.12 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.23→6.21 | 0.05→0.05 | 5.55→5.52 | +0.38,-0.03,+0.05,+0.00 | 24735 | 1.00 |
| 10.44–10.48 | 0.08 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 4/none | 6.20→6.19 | 0.04→0.04 | 5.51→5.50 | +0.33,-0.00,+0.08,+0.00 | 24875 | 1.00 |
| 10.52–10.56 | 0.08 | descend / target_align | `identity_and_fresh_geometry_associated` | 4/none | 6.18→6.18 | 0.04→0.04 | 5.50→5.49 | +0.22,+0.00,+0.04,-0.00 | 25066 | 1.00 |
| 10.60–10.60 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 4/none | 6.17→6.17 | 0.04→0.04 | 5.48→5.48 | +0.24,+0.00,+0.00,+0.00 | 25119 | 1.00 |
| 10.64–10.64 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 4/none | 6.17→6.17 | 0.04→0.04 | 5.48→5.48 | +0.30,-0.01,+0.02,-0.00 | 25144 | 1.00 |
| 10.68–10.80 | 0.16 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.16→6.16 | 0.04→0.04 | 5.47→5.47 | +0.40,-0.01,+0.08,-0.00 | 25267 | 1.00 |
| 10.84–10.84 | 0.04 | descend / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.16→6.16 | 0.04→0.04 | 5.47→5.47 | +0.49,+0.02,+0.14,-0.00 | 25393 | 1.00 |
| 10.88–10.88 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 2/target | 6.16→6.16 | 0.04→0.04 | 5.47→5.47 | +0.43,+0.01,+0.00,+0.00 | 25170 | 1.00 |
| 10.92–11.08 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2,5/target | 6.15→6.14 | 0.04→0.04 | 5.46→5.45 | +0.39,+0.01,+0.07,-0.00 | 25382 | 1.00 |
| 11.12–33.40 | 22.32 | descend / target_align | `identity_and_fresh_geometry_associated` | 2,4,5,6+.../target | 6.14→1.30 | 0.04→0.01 | 5.45→0.60 | +0.31,-0.00,+0.21,+0.00 | 226905 | 1.00 |
| 33.44–35.56 | 2.16 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 21/target | 1.29→1.27 | 0.01→0.00 | 0.59→0.59 | +0.30,-0.00,+0.01,+0.00 | 223056 | 1.00 |
| 35.60–35.76 | 0.20 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 21/target | 1.27→1.27 | 0.00→0.00 | 0.59→0.59 | +0.30,+0.01,-0.01,-0.00 | 222942 | 1.00 |
| 35.80–38.16 | 2.40 | descend / target_align | `identity_and_fresh_geometry_associated` | 21,23/target | 1.27→1.07 | 0.00→0.01 | 0.59→0.38 | +0.29,-0.00,+0.09,+0.00 | 222952 | 1.00 |
| 38.20–38.40 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 23/target | 1.06→1.04 | 0.01→0.00 | 0.38→0.36 | +0.30,+0.01,+0.01,+0.00 | 213733 | 1.00 |
| 38.44–38.52 | 0.12 | descend / target_align | `identity_and_fresh_geometry_associated` | 23/target | 1.04→1.04 | 0.00→0.00 | 0.36→0.36 | +0.27,+0.01,+0.06,-0.00 | 214763 | 1.00 |
| 38.56–39.08 | 0.56 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 23,24/target | 1.04→1.03 | 0.01→0.01 | 0.35→0.35 | +0.29,-0.01,+0.01,-0.00 | 215448 | 1.00 |
| 39.12–41.84 | 2.76 | descend / target_align | `identity_and_fresh_geometry_associated` | 24,25/target | 1.03→0.77 | 0.01→0.01 | 0.35→0.09 | +0.29,-0.01,+0.10,+0.00 | 214812 | 1.00 |
| 41.88–42.08 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 25/target | 0.77→0.75 | 0.01→0.01 | 0.09→0.06 | +0.28,-0.01,-0.01,-0.00 | 196278 | 1.00 |
| 42.12–42.68 | 0.60 | descend / target_align | `identity_and_fresh_geometry_associated` | 25/target | 0.75→0.73 | 0.01→0.01 | 0.06→0.03 | +0.29,-0.00,+0.06,+0.00 | 188908 | 1.00 |
| 42.72–42.72 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 25/target | 0.72→0.72 | 0.01→0.01 | 0.03→0.03 | +0.30,+0.01,+0.10,+0.00 | 173545 | 1.00 |
| 42.76–46.48 | 3.76 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 25/target | 0.72→0.69 | 0.01→0.01 | 0.02→-0.00 | +0.29,-0.00,+0.31,+0.00 | 171558 | 1.00 |
| 46.52–46.52 | 0.04 | confirm / ground_hold | `own_estimator_not_airborne` | 25/target | 0.69→0.69 | 0.01→0.01 | -0.00→-0.00 | +0.23,+0.00,+0.32,+0.00 | 149726 | 1.00 |
| 46.56–48.56 | 2.04 | disarmed / ground_hold | `own_estimator_not_airborne` | 25/target | 0.69→0.68 | 0.01→0.01 | -0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 149751 | 1.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 0.2 | `scan` | 6.54→6.55 | 8.12→8.12 | 5.68→5.70 | 0% |
| 0.2 | 3.6 | `target_inspect` | 6.56→6.51 | 8.13→4.02 | 5.70→5.72 | 100% |
| 3.8 | 1.7 | `target_inspect` | 6.51→6.50 | 3.95→2.00 | 5.72→5.75 | 100% |
| 5.5 | 2.4 | `target_align` | 6.50→6.66 | 1.98→0.39 | 5.75→5.96 | 100% |
| 8.0 | 3.2 | `target_align` | 6.66→6.14 | 0.37→0.04 | 5.96→5.45 | 92% |
| 11.1 | 22.3 | `target_align` | 6.14→1.30 | 0.04→0.01 | 5.45→0.60 | 100% |
| 33.4 | 2.4 | `target_align` | 1.29→1.27 | 0.01→0.00 | 0.59→0.59 | 100% |
| 35.8 | 3.3 | `target_align` | 1.27→1.03 | 0.00→0.01 | 0.59→0.35 | 100% |
| 39.1 | 3.6 | `target_align` | 1.03→0.72 | 0.01→0.01 | 0.35→0.03 | 100% |
| 42.8 | 3.8 | `target_align` | 0.72→0.69 | 0.01→0.01 | 0.02→-0.00 | 100% |
| 46.5 | 0.0 | `ground_hold` | 0.69→0.69 | 0.01→0.01 | -0.00→-0.00 | 100% |
| 46.6 | 2.0 | `ground_hold` | 0.69→0.68 | 0.01→0.01 | -0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.54, tgt 6060px)
- **t=0.20s** `target_inspect` — target_likely_evidence_requires_inspection (sel 2/target, alt 6.56, tgt 6017px)
- **t=5.52s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.50, tgt 20451px)
- **t=6.44s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 2/target, alt 6.56, tgt 20605px)
- **t=6.52s** `target_align` — identity_and_fresh_geometry_associated (sel 4/target, alt 6.57, tgt 20714px)
- **t=7.00s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 4/target, alt 6.65, tgt 20930px)
- **t=7.04s** `target_align` — identity_and_fresh_geometry_associated (sel 4/target, alt 6.65, tgt 21014px)
- **t=7.20s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 2/target, alt 6.66, tgt 21068px)
- **t=7.28s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.66, tgt 21037px)
- **t=7.60s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 4/target, alt 6.65, tgt 21165px)
- **t=7.64s** `target_align` — identity_and_fresh_geometry_associated (sel 4/target, alt 6.65, tgt 21125px)
- **t=7.80s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 4/target, alt 6.65, tgt 21186px)
- **t=7.96s** `target_align` — identity_and_fresh_geometry_associated (sel 4/target, alt 6.66, tgt 21121px)
- **t=8.72s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 4/target, alt 6.56, tgt 22113px)
- **t=9.00s** `target_align` — identity_and_fresh_geometry_associated (sel 4/target, alt 6.49, tgt 22538px)
- **t=10.28s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 2/target, alt 6.24, tgt 24479px)
- **t=10.32s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.23, tgt 24419px)
- **t=10.60s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 4/none, alt 6.17, tgt 25119px)
- **t=10.64s** `target_align` — identity_and_fresh_geometry_associated (sel 4/none, alt 6.17, tgt 25144px)
- **t=10.88s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 2/target, alt 6.16, tgt 25170px)
- **t=10.92s** `target_align` — identity_and_fresh_geometry_associated (sel 2/target, alt 6.15, tgt 25284px)
- **t=46.52s** `ground_hold` — own_estimator_not_airborne (sel 25/target, alt 0.69, tgt 149726px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–48.56s coverage 0.00 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- survey_interrupted track=None 
- preempt_candidate track=None 
- target_confirmed track=2 identity_evidence_acquired

## Recovery ledger

- visibility management (no altitude gain) t=0.2–3.8s (3.64s) alt [6.56, 6.51, 6.51, 6.56] range [8.13, 4.02, 4.02, 8.13]
- visibility management (no altitude gain) t=7.8–7.92s (0.16s) alt [6.65, 6.66, 6.65, 6.66] range [0.44, 0.39, 0.39, 0.44]
- visibility management (no altitude gain) t=8.72–8.96s (0.28s) alt [6.56, 6.5, 6.5, 6.56] range [0.14, 0.11, 0.11, 0.14]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 7.3 | 6.66 | 0.72 | 5.96 | 1.09 | 0.7 | 21107 | True | 0.047 |
| 9.3 | 6.47 | 0.09 | 5.78 | 0.39 | 4.0 | 22737 | True | 0.210 |
| 11.3 | 6.13 | 0.04 | 5.43 | 0.33 | -17.3 | 25547 | True | 0.240 |
| 13.4 | 5.64 | 0.04 | 4.96 | 0.31 | 100.5 | 30657 | True | 0.205 |
| 15.4 | 5.22 | 0.03 | 4.53 | 0.31 | -15.1 | 36621 | True | 0.138 |
| 17.4 | 4.79 | 0.02 | 4.10 | 0.31 | -78.4 | 44550 | True | 0.217 |
| 19.5 | 4.36 | 0.01 | 3.69 | 0.30 | -12.9 | 54781 | True | 0.226 |
| 21.5 | 3.91 | 0.01 | 3.21 | 0.29 | -114.5 | 66264 | True | 0.187 |
| 23.6 | 3.46 | 0.01 | 2.78 | 0.29 | -150.2 | 77545 | True | 0.210 |
| 25.6 | 3.03 | 0.01 | 2.35 | 0.29 | 16.2 | 91943 | True | 0.231 |
| 27.6 | 2.58 | 0.01 | 1.89 | 0.29 | -134.6 | 113316 | True | 0.217 |
| 29.7 | 2.13 | 0.01 | 1.44 | 0.30 | -93.7 | 146449 | True | 0.210 |
| 31.7 | 1.69 | 0.01 | 1.00 | 0.30 | -51.6 | 205529 | True | 0.226 |
| 33.8 | 1.27 | 0.00 | 0.57 | 0.29 | -67.7 | 222462 | True | -0.007 |
| 35.8 | 1.27 | 0.00 | 0.59 | 0.30 | 161.9 | 222951 | True | 0.018 |
| 37.8 | 1.10 | 0.01 | 0.41 | 0.29 | 148.6 | 216217 | True | 0.100 |
| 39.9 | 0.99 | 0.01 | 0.29 | 0.29 | 61.9 | 210298 | True | 0.083 |
| 41.9 | 0.76 | 0.01 | 0.08 | 0.30 | 124.0 | 194866 | True | 0.002 |
| 44.0 | 0.68 | 0.01 | -0.00 | 0.30 | -31.8 | 149737 | True | 0.325 |
| 46.0 | 0.69 | 0.01 | -0.00 | 0.29 | -31.4 | 149716 | True | 0.311 |
| 48.0 | 0.67 | 0.01 | -0.00 | 0.30 | -9.8 | 149724 | True | 0.000 |

## Contradictions between belief and observed truth

- minor `identity_head_flips_near_deck` frames 455 t=22.68–22.68s {"flips": 32, "rate_per_s": 1.76, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- minor `recovery_while_pad_visible` frames 72 t=0.2–10.88s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60_repair\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60_repair\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60_repair\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `f39f5e1a4f73f010c7535398238fe54608e1d450fa97f2d4e015974ddbf17fb0`
- `frames.csv` sha256 `b2d399ff79c0f4e1abee24a048eb1af16bb822fe6799121dd4fdf4d58ce6bded`
- `verdict.json` sha256 `222cd1575d2e619eac6129110f6ba394e1d4d1da46155aee5b89597626a0bc36`
- `video_join.json` sha256 `f9fe224765f6b792fd3b71dc12f61a8ab8db53b8a010283b62b4ab98306ff77a`
- `review.mp4` sha256 `f72c89254c84b1f9341176cf76428419093acdfe1e971d0f1093ac84f0725baa`
