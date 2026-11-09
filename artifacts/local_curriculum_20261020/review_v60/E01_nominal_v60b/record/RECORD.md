# Flight record — E01_nominal_v60b (E01)   **REJECT**

Scenario `windows_review_E01_nominal` kind=beach seed=3200000000 distance=8.0m height=6.0m boat_speed=0.3m/s

- frames **1085** over **43.36s**; outcome **collision_failure**
- physical events: touchdown@58.7s, stable_contact@59.95s, unstable_contact@60.24s, collision_failure@63.26s
- first lock on the truth target at t=**0.12s**; selection on target afterwards **92.79%**
- hard failures: **physical.landed_on_target, physical.disarmed_after_landing, physical.disarms_promptly_at_contact, physical.no_collision, authority.selection_continuity, opportunity.no_survey_after_target_visible**; soft: physical.no_press_after_contact, digest.matches_recording; criteria hard: E01.3_no_pointless_survey_while_opportunity_visible, E01.4_selection_continuity_after_lock, E01.10_no_spurious_recovery, E01.11_physical_termination; criteria soft: E01.9_no_chatter, E01.9_descent_permission_stable

Acceptance criteria that did not pass, with their own numbers:

- `E01.3_no_pointless_survey_while_opportunity_visible` — {"scan_frames": 81, "scan_span_s": 43.35999999994186, "limit_s": 1.0, "window": [0.0, 43.35999999994186]}
- `E01.4_selection_continuity_after_lock` — {"frames_after": 1082, "frames_on_target": 1004, "fraction": 0.9279, "limit": 0.95}
- `E01.10_no_spurious_recovery` — {"recovery_frames": 137, "first_t": 0.12000000000014666, "metric_loss_frames": 127}
- `E01.11_physical_termination` — {"outcome": "collision_failure", "landed": false, "armed": true, "final_clearance": 0.005680211823346604, "final_t": 43.35999999994186, "touchdown_s": 58.699999999953896}
- `E01.9_no_chatter` — {"intent_changes": 33, "span_s": 43.36, "per_10s": 7.611, "limit": 6.0}
- `E01.9_descent_permission_stable` — {"reversals": 6, "limit": 3}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1085, "frame_rows": 1085}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1084}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1085, "probes": 5, "max_mean_abs_diff": 3.736837384259259}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | NO | hard | `{"outcome": "collision_failure", "stop_reason": null, "strict": false, "final_height": 0.697, "final_clearance": -0.002}` |
| `physical.disarmed_after_landing` | NO | hard | `{"armed": true, "landed": false, "outcome": "collision_failure"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": null, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | NO | hard | `{"contact_t": 38.64, "disarm_t": null, "delay_s": null, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 41, "span_s": 1.6}` |
| `physical.no_collision` | NO | hard | `{"events": [["touchdown", 58.7], ["stable_contact", 59.95], ["unstable_contact", 60.24], ["collision_failure", 63.26]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 895, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 0, "longest_s": 0.0, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 0.12, "target_fraction": 0.9279, "aliases": ["14", "3"]}` |
| `authority.selection_continuity` | NO | hard | `{"fraction": 0.9279, "limit": 0.98, "frames_after": 1082, "frames_on_target": 1004}` |
| `authority.guards_engaged_with_enforcement` | yes | hard | `{"events": 0, "kinds": [], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 0.08, "situation": "E01", "scenario_requires_survey": false, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | NO | hard | `{"frames": 78, "span_s": 3.08}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 830, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 4, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "visible", "distance_band": [5.0, 20.0], "fault": null, "mode": "expert"}` |
| `digest.matches_recording` | NO | soft | `{"digest_frames": null, "frames": 1085, "present": false}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.08 | 0.12 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.53→6.54 | 8.17→8.17 | 5.64→5.65 | +0.00,+0.00,-0.07,-0.03 | 5902 | 0.00 |
| 0.12–0.12 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2/target | 6.54→6.54 | 8.17→8.17 | 5.65→5.65 | +0.06,-0.01,-0.03,-0.03 | 5911 | 0.85 |
| 0.16–0.16 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 2/target | 6.54→6.54 | 8.17→8.17 | 5.65→5.65 | +0.11,+0.01,-0.00,-0.02 | 5976 | 0.00 |
| 0.20–2.16 | 2.00 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 2,3/target | 6.54→6.50 | 8.17→6.77 | 5.65→5.67 | +1.38,+0.00,+0.00,+0.00 | 8060 | 1.00 |
| 2.20–2.20 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.50→6.50 | 6.70→6.70 | 5.67→5.67 | +2.00,+0.01,+0.00,+0.01 | 8197 | 0.00 |
| 2.24–2.28 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.50→6.50 | 6.64→6.57 | 5.67→5.67 | +2.00,+0.02,+0.00,+0.01 | 8458 | 0.64 |
| 2.32–2.32 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.50→6.50 | 6.50→6.50 | 5.67→5.67 | +2.00,+0.05,+0.00,+0.02 | 8576 | 0.00 |
| 2.36–2.36 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.50→6.50 | 6.43→6.43 | 5.67→5.67 | +2.00,+0.02,+0.00,+0.01 | 8713 | 0.80 |
| 2.40–2.40 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.50→6.50 | 6.36→6.36 | 5.67→5.67 | +2.00,-0.03,+0.00,-0.01 | 8858 | 0.00 |
| 2.44–2.52 | 0.12 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.50→6.49 | 6.29→6.15 | 5.67→5.67 | +2.00,-0.01,+0.00,-0.01 | 9253 | 0.59 |
| 2.56–2.56 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.49→6.49 | 6.08→6.08 | 5.67→5.67 | +2.00,+0.01,+0.00,+0.01 | 9444 | 0.00 |
| 2.60–2.64 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.49→6.49 | 6.01→5.94 | 5.67→5.68 | +2.00,-0.02,+0.00,-0.01 | 9714 | 0.85 |
| 2.68–2.68 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.49→6.49 | 5.87→5.87 | 5.68→5.68 | +2.00,+0.02,+0.00,+0.01 | 9880 | 0.00 |
| 2.72–2.76 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.49→6.49 | 5.79→5.72 | 5.68→5.68 | +2.00,-0.01,+0.00,-0.00 | 10211 | 0.86 |
| 2.80–2.84 | 0.08 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.49→6.49 | 5.65→5.58 | 5.68→5.68 | +2.00,+0.01,+0.00,+0.00 | 10541 | 0.00 |
| 2.88–3.16 | 0.32 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.49→6.48 | 5.50→5.00 | 5.68→5.68 | +1.94,-0.01,+0.00,-0.01 | 11968 | 1.00 |
| 3.20–3.20 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.48→6.48 | 4.92→4.92 | 5.68→5.68 | +1.86,-0.01,+0.00,-0.01 | 12144 | 1.00 |
| 3.24–3.24 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.48→6.48 | 4.85→4.85 | 5.68→5.68 | +1.85,-0.01,+0.00,-0.01 | 12407 | 1.00 |
| 3.28–3.28 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.48→6.48 | 4.78→4.78 | 5.68→5.68 | +1.80,-0.03,+0.00,-0.01 | 12525 | 1.00 |
| 3.32–3.32 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.48→6.48 | 4.71→4.71 | 5.69→5.69 | +1.83,-0.02,+0.00,-0.01 | 12755 | 1.00 |
| 3.36–3.36 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.48→6.48 | 4.64→4.64 | 5.69→5.69 | +1.79,+0.00,+0.00,+0.00 | 12968 | 1.00 |
| 3.40–3.64 | 0.28 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.48→6.48 | 4.56→4.15 | 5.69→5.69 | +1.78,-0.01,+0.00,-0.00 | 14389 | 1.00 |
| 3.68–3.84 | 0.20 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.48→6.48 | 4.08→3.81 | 5.69→5.69 | +1.61,+0.00,-0.00,+0.00 | 15517 | 1.00 |
| 3.88–3.88 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.48→6.48 | 3.75→3.75 | 5.69→5.69 | +1.57,-0.01,-0.00,-0.01 | 15742 | 1.00 |
| 3.92–3.92 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.48→6.48 | 3.68→3.68 | 5.69→5.69 | +1.53,-0.03,-0.00,-0.01 | 15939 | 1.00 |
| 3.96–4.00 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.48→6.48 | 3.62→3.55 | 5.69→5.69 | +1.49,-0.02,-0.00,-0.01 | 16344 | 1.00 |
| 4.04–4.04 | 0.04 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.48→6.48 | 3.49→3.49 | 5.69→5.69 | +1.50,-0.02,-0.00,-0.01 | 16534 | 1.00 |
| 4.08–4.12 | 0.08 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.47→6.47 | 3.43→3.37 | 5.69→5.69 | +1.45,-0.02,-0.00,-0.01 | 16923 | 1.00 |
| 4.16–4.32 | 0.20 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.47→6.47 | 3.31→3.08 | 5.69→5.69 | +1.32,-0.01,-0.00,-0.01 | 17746 | 1.00 |
| 4.36–4.40 | 0.08 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 3/target | 6.47→6.47 | 3.02→2.97 | 5.69→5.69 | +1.17,+0.01,-0.00,+0.01 | 18076 | 1.00 |
| 4.44–4.44 | 0.04 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 3/target | 6.47→6.47 | 2.91→2.91 | 5.70→5.70 | +1.15,-0.02,-0.00,-0.01 | 18225 | 1.00 |
| 4.48–4.56 | 0.12 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 3/target | 6.47→6.47 | 2.86→2.76 | 5.70→5.70 | +1.15,-0.01,-0.00,-0.01 | 18669 | 1.00 |
| 4.60–5.00 | 0.44 | align / target_align | `identity_and_fresh_geometry_associated` | 3/target | 6.47→6.46 | 2.71→2.28 | 5.70→5.71 | +1.05,-0.04,+0.06,+0.02 | 19858 | 1.00 |
| 5.04–5.32 | 0.32 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 3/target | 6.46→6.44 | 2.24→2.00 | 5.71→5.71 | +0.95,-0.01,-0.01,-0.01 | 20669 | 1.00 |
| 5.36–7.52 | 2.20 | align / target_align | `identity_and_fresh_geometry_associated` | 3/target | 6.44→6.35 | 1.96→0.36 | 5.71→5.64 | +1.00,-0.03,+0.04,+0.00 | 23750 | 1.00 |
| 7.56–8.68 | 1.16 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 3/target | 6.35→6.19 | 0.34→0.11 | 5.64→5.50 | +0.47,+0.00,+0.19,+0.00 | 24924 | 1.00 |
| 8.72–8.72 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 3/target | 6.18→6.18 | 0.11→0.11 | 5.49→5.49 | +0.33,-0.00,+0.00,-0.01 | 25051 | 1.00 |
| 8.76–9.08 | 0.36 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 3/target | 6.17→6.10 | 0.10→0.09 | 5.48→5.42 | +0.40,-0.03,+0.08,-0.00 | 25648 | 1.00 |
| 9.12–34.48 | 25.40 | descend / target_align | `identity_and_fresh_geometry_associated` | 3,14/target | 6.10→1.02 | 0.09→0.01 | 5.41→0.34 | +0.32,-0.00,+0.20,+0.00 | 226890 | 1.00 |
| 34.52–34.84 | 0.36 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 14/target | 1.02→0.99 | 0.01→0.01 | 0.34→0.31 | +0.30,-0.00,+0.00,-0.00 | 213354 | 1.00 |
| 34.88–36.68 | 1.84 | descend / target_align | `identity_and_fresh_geometry_associated` | 14/target | 0.99→0.86 | 0.01→0.00 | 0.31→0.16 | +0.30,+0.00,+0.08,+0.00 | 214255 | 1.00 |
| 36.72–36.96 | 0.28 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 14/target | 0.86→0.84 | 0.00→0.00 | 0.16→0.14 | +0.30,+0.01,+0.01,+0.00 | 209495 | 1.00 |
| 37.00–37.76 | 0.80 | descend / target_align | `identity_and_fresh_geometry_associated` | 14/target | 0.84→0.77 | 0.00→0.01 | 0.14→0.09 | +0.30,-0.02,+0.11,-0.00 | 209681 | 1.00 |
| 37.80–38.00 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 14/target | 0.76→0.74 | 0.01→0.01 | 0.08→0.06 | +0.30,-0.01,+0.01,+0.00 | 196287 | 1.00 |
| 38.04–38.52 | 0.52 | descend / target_align | `identity_and_fresh_geometry_associated` | 14/target | 0.74→0.72 | 0.01→0.00 | 0.06→0.03 | +0.30,+0.01,+0.07,-0.00 | 188169 | 1.00 |
| 38.56–38.56 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 14/target | 0.71→0.71 | 0.00→0.00 | 0.02→0.02 | +0.30,+0.01,+0.10,+0.00 | 172753 | 1.00 |
| 38.60–40.24 | 1.68 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 14/target | 0.71→0.68 | 0.00→0.00 | 0.02→-0.00 | +0.30,-0.00,+0.30,+0.00 | 170338 | 1.00 |
| 40.28–42.36 | 2.12 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 0.68→0.70 | 0.00→0.15 | -0.00→0.00 | -0.08,-0.01,-0.00,-0.28 | 220774 | 1.00 |
| 42.40–43.36 | 1.00 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 0.70→0.70 | 0.15→0.24 | 0.00→-0.00 | -0.07,-0.00,-0.02,-0.34 | 184189 | 0.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 0.1 | `scan` | 6.53→6.54 | 8.17→8.17 | 5.64→5.65 | 0% |
| 0.1 | 5.2 | `target_inspect` | 6.54→6.44 | 8.17→2.00 | 5.65→5.71 | 100% |
| 5.4 | 2.2 | `target_align` | 6.44→6.35 | 1.96→0.36 | 5.71→5.64 | 100% |
| 7.6 | 1.6 | `target_align` | 6.35→6.10 | 0.34→0.09 | 5.64→5.42 | 100% |
| 9.1 | 25.8 | `target_align` | 6.10→0.99 | 0.09→0.01 | 5.41→0.31 | 100% |
| 34.9 | 2.1 | `target_align` | 0.99→0.84 | 0.01→0.00 | 0.31→0.14 | 100% |
| 37.0 | 1.6 | `target_align` | 0.84→0.71 | 0.00→0.00 | 0.14→0.02 | 100% |
| 38.6 | 1.7 | `target_align` | 0.71→0.68 | 0.00→0.00 | 0.02→-0.00 | 100% |
| 40.3 | 2.1 | `scan` | 0.68→0.70 | 0.00→0.15 | -0.00→0.00 | 0% |
| 42.4 | 1.0 | `scan` | 0.70→0.70 | 0.15→0.24 | 0.00→-0.00 | 0% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.53, tgt 5884px)
- **t=0.12s** `target_inspect` — target_likely_evidence_requires_inspection (sel 2/target, alt 6.54, tgt 5911px)
- **t=0.16s** `inspect_candidate` — plausible_boat_inspect_unknown_design (sel 2/target, alt 6.54, tgt 5976px)
- **t=0.20s** `target_inspect` — target_likely_evidence_requires_inspection (sel 2/target, alt 6.54, tgt 5989px)
- **t=2.20s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.50, tgt 8197px)
- **t=2.24s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.50, tgt 8304px)
- **t=2.32s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.50, tgt 8576px)
- **t=2.36s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.50, tgt 8713px)
- **t=2.40s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.50, tgt 8858px)
- **t=2.44s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.50, tgt 8999px)
- **t=2.56s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.49, tgt 9444px)
- **t=2.60s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.49, tgt 9562px)
- **t=2.68s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.49, tgt 9880px)
- **t=2.72s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.49, tgt 10028px)
- **t=2.80s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.49, tgt 10346px)
- **t=2.88s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.49, tgt 10685px)
- **t=3.20s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.48, tgt 12144px)
- **t=3.24s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.48, tgt 12407px)
- **t=3.28s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.48, tgt 12525px)
- **t=3.32s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.48, tgt 12755px)
- **t=3.36s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.48, tgt 12968px)
- **t=3.40s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.48, tgt 13177px)
- **t=3.92s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.48, tgt 15939px)
- **t=3.96s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.48, tgt 16169px)
- **t=4.04s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.48, tgt 16534px)
- **t=4.16s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.47, tgt 17133px)
- **t=4.36s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 3/target, alt 6.47, tgt 17883px)
- **t=4.44s** `target_inspect` — target_likely_evidence_requires_inspection (sel 3/target, alt 6.47, tgt 18225px)
- **t=4.48s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 3/target, alt 6.47, tgt 18324px)
- **t=4.60s** `target_align` — identity_and_fresh_geometry_associated (sel 3/target, alt 6.47, tgt 18770px)
- **t=5.04s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 3/target, alt 6.46, tgt 19896px)
- **t=5.36s** `target_align` — identity_and_fresh_geometry_associated (sel 3/target, alt 6.44, tgt 20766px)
- **t=8.72s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 3/target, alt 6.18, tgt 25051px)
- **t=8.76s** `target_align` — identity_and_fresh_geometry_associated (sel 3/target, alt 6.17, tgt 25104px)
- **t=40.28s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 0.68, tgt 149933px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–40.24s coverage 0.00 rad, inspected views 0, exhausted=False
- survey epoch 2 t=40.28–43.36s coverage 0.35 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- survey_interrupted track=None 
- preempt_candidate track=None 
- target_confirmed track=3 identity_evidence_acquired
- identity_memory_expired track=None 

## Recovery ledger

- visibility management (no altitude gain) t=0.12–3.64s (3.56s) alt [6.54, 6.48, 6.48, 6.55] range [8.17, 4.15, 4.15, 8.17]
- visibility management (no altitude gain) t=4.08–4.56s (0.52s) alt [6.47, 6.47, 6.47, 6.47] range [3.43, 2.76, 2.76, 3.43]
- visibility management (no altitude gain) t=5.04–5.32s (0.32s) alt [6.46, 6.44, 6.44, 6.46] range [2.24, 2.0, 2.0, 2.24]
- visibility management (no altitude gain) t=42.4–43.36s (1.0s) alt [0.7, 0.7, 0.7, 0.71] range [0.15, 0.24, 0.15, 0.24]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 4.6 | 6.47 | 2.66 | 5.70 | 1.59 | 0.4 | 18885 | True | 0.046 |
| 6.6 | 6.45 | 0.93 | 5.74 | 1.29 | -1.0 | 22322 | True | 0.039 |
| 8.6 | 6.20 | 0.11 | 5.51 | 0.46 | 6.2 | 24810 | True | 0.307 |
| 10.6 | 5.86 | 0.07 | 5.17 | 0.36 | -12.8 | 28198 | True | 0.195 |
| 12.6 | 5.47 | 0.04 | 4.79 | 0.33 | -55.2 | 32765 | True | 0.250 |
| 14.7 | 5.02 | 0.02 | 4.32 | 0.31 | -40.7 | 40075 | True | 0.191 |
| 16.7 | 4.57 | 0.01 | 3.88 | 0.31 | -12.2 | 49833 | True | 0.141 |
| 18.8 | 4.16 | 0.01 | 3.48 | 0.30 | -123.5 | 60008 | True | 0.231 |
| 20.8 | 3.70 | 0.01 | 3.00 | 0.30 | -60.4 | 71812 | True | 0.217 |
| 22.8 | 3.24 | 0.02 | 2.55 | 0.31 | 13.4 | 84591 | True | 0.211 |
| 24.9 | 2.81 | 0.01 | 2.12 | 0.30 | 24.5 | 101313 | True | 0.213 |
| 26.9 | 2.35 | 0.01 | 1.66 | 0.29 | 16.1 | 127885 | True | 0.219 |
| 29.0 | 1.91 | 0.01 | 1.22 | 0.30 | 106.2 | 170857 | True | 0.226 |
| 31.0 | 1.47 | 0.00 | 0.80 | 0.29 | 131.8 | 226075 | True | 0.235 |
| 33.0 | 1.17 | 0.01 | 0.48 | 0.29 | 176.7 | 219451 | True | 0.097 |
| 35.1 | 0.99 | 0.00 | 0.31 | 0.30 | -13.1 | 212258 | True | 0.097 |
| 37.1 | 0.83 | 0.00 | 0.14 | 0.30 | -48.5 | 209670 | True | 0.116 |
| 39.2 | 0.69 | 0.01 | -0.00 | 0.30 | 12.8 | 149939 | True | 0.300 |
| 41.2 | 0.70 | 0.08 | 0.01 | 0.15 | -29.4 | 179418 | True | -0.013 |
| 43.2 | 0.70 | 0.22 | -0.00 | 0.11 | -12.7 | 164817 | False | -0.035 |

## Contradictions between belief and observed truth

- minor `survey_after_target_visible` frames 78 t=40.28–43.36s {"span_s": 3.08, "known_target_px": true}
- minor `identity_head_flips_near_deck` frames 384 t=20.84–20.84s {"flips": 35, "rate_per_s": 2.28, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- **SEVERE** `collision_after_contact` frames 1 t=43.36–43.36s {"event_time": 63.25999999994327}
- minor `yaw_below_1_5_m` frames 69 t=40.6–43.32s {}
- minor `recovery_while_pad_visible` frames 76 t=0.12–8.72s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E01_nominal_v60b\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E01_nominal_v60b\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E01_nominal_v60b\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `2a81b6e3c8bf198cbb2cf0e3f683afe5d2a542112ee061994dd2047aaf6858d1`
- `frames.csv` sha256 `777e0aa255e81aa68c96dd466033545e6c8798b5ae75f0972a4485ddddd540ef`
- `verdict.json` sha256 `0aa75e89e7b1d3a7c6e632e9955dcb699523022a3c5d3e1de1782fc9482b638b`
- `video_join.json` sha256 `9cabfaf607d7e266f3c4ea5d83207448b37d45433b425efb46e51762b11da4c2`
- `review.mp4` sha256 `f4c4f8a51e1048ecda0d425e400eb6b04e00a31ff0a152157aec43d09dcadd31`
