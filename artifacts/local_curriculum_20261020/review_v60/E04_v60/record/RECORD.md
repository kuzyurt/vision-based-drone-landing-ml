# Flight record — E04_v60 (E04)   **SILVER**

Scenario `windows_review_E04_close_loss` kind=beach seed=3200000006 distance=8.0m height=6.0m boat_speed=0.3m/s

- frames **1647** over **65.84s**; outcome **landed**
- physical events: touchdown@80.2s, stable_contact@81.42s, unstable_contact@81.87s, stable_contact@84.28s, landed@85.93s
- first lock on the truth target at t=**0.08s**; selection on target afterwards **100.00%**
- hard failures: **none**; soft: physical.no_press_after_contact; criteria hard: E01.4_no_false_boat_claim_drives_selection, E01.10_no_spurious_recovery; criteria soft: E01.9_descent_permission_stable, E01.10b_parent_recovery_share_below_limit

Acceptance criteria that did not pass, with their own numbers:

- `E01.4_no_false_boat_claim_drives_selection` — {"frames": 4, "examples": [{"t": 8.760000000010706, "name": "none", "prob": 0.04977346584200859, "wrong": 0.7786045670509338, "size": 79.52037048339844}, {"t": 8.800000000010755, "name": "none", "prob": 0.04977346584200859, "wrong": 0.7786045670509338, "size": 79.52037048339844}, {"t": 8.840000000010804, "name": "none", "prob": 0.04977346584200859, "wrong": 0.7786045670509338, "size": 79.52037048339844}, {"t": 8.880000000010853, "name": "none", "prob": 0.04977346584200859, "wrong": 0.7786045670509338, "size": 79.52037048339844}]}
- `E01.10_no_spurious_recovery` — {"recovery_executed_frames": 177, "first_t": 33.91999999996315, "parent_recovery_frames": 282}
- `E01.9_descent_permission_stable` — {"reversals": 16, "limit": 3}
- `E01.10b_parent_recovery_share_below_limit` — {"share": 0.1712, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1647, "frame_rows": 1647}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1646}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1647, "probes": 5, "max_mean_abs_diff": 2.981714409722222}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | yes | hard | `{"outcome": "landed", "stop_reason": null, "strict": true, "final_height": 0.695, "final_clearance": -0.0}` |
| `physical.disarmed_after_landing` | yes | hard | `{"armed": false, "landed": true, "outcome": "landed"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": 65.84, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | yes | hard | `{"contact_t": 59.92, "disarm_t": 63.84, "delay_s": 3.92, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 98, "span_s": 3.88}` |
| `physical.no_collision` | yes | hard | `{"events": [["touchdown", 80.2], ["stable_contact", 81.42], ["unstable_contact", 81.87], ["stable_contact", 84.28], ["landed", 85.93]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 1533, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 4, "longest_s": 0.12, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 0.08, "target_fraction": 1.0, "aliases": ["1", "10", "11", "12", "14", "16", "18", "2", "23", "24", "3", "32", "35", "36", "38", "5", "50", "51", "6"]}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 1.0, "limit": 0.98, "frames_after": 1645, "frames_on_target": 1645}` |
| `authority.guards_engaged_with_enforcement` | yes | soft | `{"events": 37, "kinds": ["descent_without_fresh_geometry"], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 0.04, "situation": "E04", "scenario_requires_survey": false, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 1152, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 1, "visibility_management": 3, "longest_s": 7.16, "limit_s": 12.0, "detail": [{"frames": 179, "t0": 33.84, "t1": 40.96, "duration_s": 7.16, "height_m": [1.23, 3.63, 1.23, 3.63], "horiz_dist_m": [0.01, 0.64, 0.0, 0.67], "clearance_m": [0.53, 2.92, 0.53, 2.92], "speed_m_s": [0.3, ...` |
| `purpose.fault_actually_injected` | yes | hard | `{"fault_rows": 40}` |
| `purpose.metric_loss_occurred` | yes | hard | `{"near_metric_missing_frames": 78}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "visible", "distance_band": [5.0, 20.0], "fault": "gimbal_tilt", "mode": "expert"}` |
| `digest.matches_recording` | yes | soft | `{"digest_frames": 1647, "frames": 1647, "present": true}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.04 | 0.08 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.55→6.55 | 8.09→8.09 | 5.66→5.67 | -0.00,+0.00,-0.08,-0.03 | 6091 | 0.00 |
| 0.08–0.12 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1/target | 6.56→6.56 | 8.09→8.09 | 5.68→5.68 | +0.08,+0.01,-0.04,-0.01 | 6106 | 0.69 |
| 0.16–3.44 | 3.32 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1,2/target | 6.56→6.52 | 8.09→4.33 | 5.69→5.74 | +1.58,-0.00,+0.00,-0.00 | 13677 | 1.00 |
| 3.48–3.76 | 0.32 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1,2/target | 6.52→6.52 | 4.26→3.80 | 5.74→5.75 | +1.61,-0.01,-0.00,-0.01 | 15295 | 1.00 |
| 3.80–3.84 | 0.08 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1,2/target | 6.52→6.52 | 3.73→3.67 | 5.75→5.75 | +1.53,-0.02,-0.00,-0.01 | 15667 | 1.00 |
| 3.88–4.52 | 0.68 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1/target | 6.52→6.51 | 3.61→2.72 | 5.75→5.75 | +1.28,-0.01,-0.00,-0.01 | 18524 | 1.00 |
| 4.56–5.52 | 1.00 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.51→6.53 | 2.67→1.89 | 5.75→5.79 | +0.98,-0.02,-0.03,+0.00 | 20057 | 1.00 |
| 5.56–5.56 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.53→6.53 | 1.87→1.87 | 5.79→5.79 | +1.46,+0.01,+0.00,+0.00 | 20099 | 1.00 |
| 5.60–6.48 | 0.92 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.53→6.55 | 1.84→1.02 | 5.80→5.83 | +1.34,-0.04,-0.00,+0.01 | 21688 | 1.00 |
| 6.52–6.52 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.55→6.55 | 0.98→0.98 | 5.83→5.83 | +0.84,-0.00,+0.00,+0.00 | 21748 | 1.00 |
| 6.56–7.04 | 0.52 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.55→6.53 | 0.95→0.59 | 5.83→5.83 | +0.72,+0.00,+0.03,+0.01 | 22090 | 1.00 |
| 7.08–7.44 | 0.40 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.53→6.52 | 0.56→0.39 | 5.83→5.82 | +0.44,-0.00,+0.00,+0.00 | 22276 | 1.00 |
| 7.48–7.52 | 0.08 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.38→0.36 | 5.82→5.82 | +0.43,-0.01,-0.03,+0.00 | 22258 | 1.00 |
| 7.56–7.60 | 0.08 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.35→0.34 | 5.82→5.83 | +0.53,-0.05,-0.00,+0.00 | 22261 | 1.00 |
| 7.64–7.64 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.33→0.33 | 5.83→5.83 | +0.59,-0.03,-0.01,+0.00 | 22191 | 1.00 |
| 7.68–7.80 | 0.16 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.52→6.52 | 0.32→0.30 | 5.83→5.83 | +0.46,-0.01,+0.00,+0.00 | 22186 | 1.00 |
| 7.84–7.84 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.29→0.29 | 5.83→5.83 | +0.32,+0.06,-0.02,+0.00 | 22170 | 1.00 |
| 7.88–7.88 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.28→0.28 | 5.83→5.83 | +0.37,-0.00,+0.00,+0.00 | 22113 | 1.00 |
| 7.92–8.04 | 0.16 | visual_acquire / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.52→6.52 | 0.28→0.26 | 5.83→5.83 | +0.29,-0.01,+0.00,+0.00 | 22210 | 1.00 |
| 8.08–8.08 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.26→0.26 | 5.83→5.83 | +0.37,-0.02,-0.02,+0.00 | 22213 | 1.00 |
| 8.12–8.12 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.25→0.25 | 5.83→5.83 | +0.42,-0.04,+0.00,+0.00 | 22219 | 1.00 |
| 8.16–8.36 | 0.24 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.25→0.24 | 5.83→5.83 | +0.51,-0.03,-0.02,+0.00 | 22278 | 1.00 |
| 8.40–8.68 | 0.32 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.24→0.22 | 5.82→5.82 | +0.65,-0.01,+0.08,-0.00 | 22295 | 1.00 |
| 8.72–8.72 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.52→6.52 | 0.22→0.22 | 5.82→5.82 | +0.59,+0.04,+0.14,+0.00 | 22306 | 1.00 |
| 8.76–8.80 | 0.08 | align / target_align | `identity_and_fresh_geometry_associated` | 1/none | 6.52→6.51 | 0.22→0.21 | 5.81→5.81 | +0.51,+0.02,+0.10,+0.00 | 22459 | 1.00 |
| 8.84–8.88 | 0.08 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/none | 6.51→6.50 | 0.21→0.20 | 5.80→5.80 | +0.51,+0.01,+0.13,-0.00 | 22463 | 1.00 |
| 8.92–9.80 | 0.92 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1,2/target | 6.50→6.30 | 0.20→0.11 | 5.79→5.60 | +0.45,-0.01,+0.25,+0.00 | 24055 | 1.00 |
| 9.84–9.88 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.29→6.27 | 0.10→0.10 | 5.59→5.58 | +0.38,+0.00,+0.00,+0.00 | 24275 | 1.00 |
| 9.92–10.08 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.26→6.23 | 0.10→0.09 | 5.57→5.55 | +0.39,+0.00,+0.06,-0.00 | 24544 | 1.00 |
| 10.12–10.84 | 0.76 | descend / target_align | `identity_and_fresh_geometry_associated` | 1,2/target | 6.22→6.17 | 0.08→0.06 | 5.54→5.48 | +0.38,-0.01,+0.11,+0.00 | 25082 | 1.00 |
| 10.88–10.96 | 0.12 | match / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.16→6.15 | 0.06→0.06 | 5.48→5.46 | +0.42,-0.01,+0.12,+0.00 | 25309 | 1.00 |
| 11.00–11.16 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 2/target | 6.14→6.11 | 0.06→0.06 | 5.46→5.43 | +0.38,+0.00,+0.15,+0.00 | 25564 | 1.00 |
| 11.20–33.64 | 22.48 | descend / target_align | `identity_and_fresh_geometry_associated` | 1,2,3,5+.../target | 6.11→1.24 | 0.06→0.01 | 5.42→0.55 | +0.31,-0.00,+0.21,+0.00 | 226893 | 1.00 |
| 33.68–33.80 | 0.16 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 14,18/target | 1.24→1.23 | 0.01→0.01 | 0.54→0.53 | +0.29,-0.00,-0.03,-0.00 | 227742 | 1.00 |
| 33.84–33.88 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 1.23→1.23 | 0.01→0.01 | 0.53→0.53 | +0.30,-0.00,-0.00,+0.00 | 228386 | 1.00 |
| 33.92–34.40 | 0.52 | recovery_climb / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 1.23→1.26 | 0.01→0.00 | 0.53→0.57 | +0.30,-0.00,-0.16,+0.00 | 230400 | 1.00 |
| 34.44–34.44 | 0.04 | recovery_climb / local_downlook | `arrest_descent_and_inspect_below` | 18/target | 1.27→1.27 | 0.00→0.00 | 0.57→0.57 | +0.30,-0.00,-0.33,+0.00 | 174076 | 0.00 |
| 34.48–35.44 | 1.00 | recovery_climb / local_downlook | `bounded_fresh_downward_observation` | 18/target | 1.28→1.67 | 0.00→0.01 | 0.58→0.99 | +0.23,-0.00,-0.40,+0.00 | 161165 | 0.00 |
| 35.48–37.36 | 1.92 | recovery_climb / recovery_climb | `bounded_clearance_gated_climb` | 18,23,32/target | 1.68→2.47 | 0.01→0.46 | 1.00→1.77 | +0.00,+0.00,-0.40,+0.00 | 123361 | 1.00 |
| 37.40–40.96 | 3.60 | recovery_climb / target_align | `identity_and_fresh_geometry_associated` | 23,32/target | 2.49→3.63 | 0.47→0.64 | 1.78→2.92 | +0.30,+0.00,-0.30,+0.00 | 116975 | 1.00 |
| 41.00–42.24 | 1.28 | align / target_align | `identity_and_fresh_geometry_associated` | 23,32/target | 3.64→3.64 | 0.63→0.35 | 2.93→2.95 | +0.63,-0.03,-0.00,-0.00 | 72079 | 1.00 |
| 42.28–43.48 | 1.24 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 32/target | 3.64→3.42 | 0.34→0.07 | 2.95→2.72 | +0.38,-0.01,+0.19,-0.00 | 79457 | 1.00 |
| 43.52–55.76 | 12.28 | descend / target_align | `identity_and_fresh_geometry_associated` | 24,32,35,36+.../target | 3.41→1.02 | 0.07→0.01 | 2.71→0.33 | +0.30,-0.00,+0.19,+0.00 | 226848 | 1.00 |
| 55.80–56.04 | 0.28 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 50/target | 1.01→1.00 | 0.01→0.01 | 0.32→0.31 | +0.30,+0.01,-0.02,-0.00 | 214737 | 1.00 |
| 56.08–57.88 | 1.84 | descend / target_align | `identity_and_fresh_geometry_associated` | 50,51/target | 1.00→0.84 | 0.01→0.01 | 0.31→0.16 | +0.30,-0.01,+0.10,+0.00 | 215398 | 1.00 |
| 57.92–58.12 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 51/target | 0.83→0.81 | 0.01→0.01 | 0.15→0.13 | +0.31,-0.02,-0.01,-0.00 | 204514 | 1.00 |
| 58.16–58.80 | 0.68 | descend / target_align | `identity_and_fresh_geometry_associated` | 51/target | 0.81→0.79 | 0.01→0.01 | 0.13→0.09 | +0.29,+0.00,+0.07,+0.00 | 206652 | 1.00 |
| 58.84–59.04 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 51/target | 0.78→0.77 | 0.01→0.01 | 0.09→0.07 | +0.29,+0.02,-0.00,+0.00 | 195938 | 1.00 |
| 59.08–59.84 | 0.80 | descend / target_align | `identity_and_fresh_geometry_associated` | 51/target | 0.77→0.71 | 0.01→0.01 | 0.07→0.03 | +0.29,-0.01,+0.10,-0.00 | 191892 | 1.00 |
| 59.88–59.88 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 51/target | 0.71→0.71 | 0.01→0.01 | 0.02→0.02 | +0.30,-0.01,+0.13,+0.00 | 171607 | 1.00 |
| 59.92–63.76 | 3.88 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 51/target | 0.71→0.68 | 0.01→0.02 | 0.02→-0.00 | +0.29,-0.01,+0.32,+0.00 | 168895 | 1.00 |
| 63.80–63.80 | 0.04 | confirm / ground_hold | `own_estimator_not_airborne` | 51/target | 0.68→0.68 | 0.02→0.02 | -0.00→-0.00 | +0.24,+0.00,+0.32,+0.00 | 149644 | 1.00 |
| 63.84–65.84 | 2.04 | disarmed / ground_hold | `own_estimator_not_airborne` | 51/target | 0.68→0.69 | 0.02→0.01 | -0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 149644 | 1.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 0.1 | `scan` | 6.55→6.55 | 8.09→8.09 | 5.66→5.67 | 0% |
| 0.1 | 0.1 | `target_inspect` | 6.56→6.56 | 8.09→8.09 | 5.68→5.68 | 100% |
| 0.2 | 4.4 | `target_inspect` | 6.56→6.51 | 8.09→2.72 | 5.69→5.75 | 100% |
| 4.6 | 1.0 | `target_align` | 6.51→6.53 | 2.67→1.87 | 5.75→5.79 | 100% |
| 5.6 | 3.3 | `target_align` | 6.53→6.50 | 1.84→0.20 | 5.80→5.80 | 95% |
| 8.9 | 1.2 | `target_align` | 6.50→6.23 | 0.20→0.09 | 5.79→5.55 | 100% |
| 10.1 | 1.1 | `target_align` | 6.22→6.11 | 0.08→0.06 | 5.54→5.43 | 100% |
| 11.2 | 23.2 | `target_align` | 6.11→1.26 | 0.06→0.00 | 5.42→0.57 | 100% |
| 34.4 | 0.0 | `local_downlook` | 1.27→1.27 | 0.00→0.00 | 0.57→0.57 | 100% |
| 34.5 | 1.0 | `local_downlook` | 1.28→1.67 | 0.00→0.01 | 0.58→0.99 | 100% |
| 35.5 | 1.9 | `recovery_climb` | 1.68→2.47 | 0.01→0.46 | 1.00→1.77 | 100% |
| 37.4 | 3.6 | `target_align` | 2.49→3.63 | 0.47→0.64 | 1.78→2.92 | 100% |
| 41.0 | 1.3 | `target_align` | 3.64→3.64 | 0.63→0.35 | 2.93→2.95 | 100% |
| 42.3 | 1.2 | `target_align` | 3.64→3.42 | 0.34→0.07 | 2.95→2.72 | 100% |
| 43.5 | 12.6 | `target_align` | 3.41→1.00 | 0.07→0.01 | 2.71→0.31 | 100% |
| 56.1 | 3.0 | `target_align` | 1.00→0.77 | 0.01→0.01 | 0.31→0.07 | 100% |
| 59.1 | 0.8 | `target_align` | 0.77→0.71 | 0.01→0.01 | 0.07→0.02 | 100% |
| 59.9 | 3.9 | `target_align` | 0.71→0.68 | 0.01→0.02 | 0.02→-0.00 | 100% |
| 63.8 | 0.0 | `ground_hold` | 0.68→0.68 | 0.02→0.02 | -0.00→-0.00 | 100% |
| 63.8 | 2.0 | `ground_hold` | 0.68→0.69 | 0.02→0.01 | -0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.55, tgt 6089px)
- **t=0.08s** `target_inspect` — target_likely_evidence_requires_inspection (sel 1/target, alt 6.56, tgt 6087px)
- **t=4.56s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.51, tgt 18617px)
- **t=5.56s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.53, tgt 20099px)
- **t=5.60s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.53, tgt 20132px)
- **t=6.52s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.55, tgt 21748px)
- **t=6.56s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.55, tgt 21759px)
- **t=7.08s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.53, tgt 22089px)
- **t=7.48s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.52, tgt 22227px)
- **t=7.68s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.52, tgt 22186px)
- **t=7.84s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.52, tgt 22170px)
- **t=7.92s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.52, tgt 22210px)
- **t=8.08s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.52, tgt 22213px)
- **t=9.84s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.29, tgt 24072px)
- **t=9.92s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.26, tgt 24250px)
- **t=33.84s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 1.23, tgt 228106px)
- **t=34.44s** `local_downlook` — arrest_descent_and_inspect_below (sel 18/target, alt 1.27, tgt 174076px)
- **t=34.48s** `local_downlook` — bounded_fresh_downward_observation (sel 18/target, alt 1.28, tgt 161165px)
- **t=35.48s** `recovery_climb` — bounded_clearance_gated_climb (sel 18/target, alt 1.68, tgt 1014px)
- **t=37.40s** `target_align` — identity_and_fresh_geometry_associated (sel 32/target, alt 2.49, tgt 116975px)
- **t=63.80s** `ground_hold` — own_estimator_not_airborne (sel 51/target, alt 0.68, tgt 149644px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–65.84s coverage 0.00 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- survey_interrupted track=None 
- preempt_candidate track=None 
- target_confirmed track=1 identity_evidence_acquired
- recovery_start track=None 
- recovery_climb track=None 

## Recovery ledger

- **climb recovery** t=33.84–40.96s (7.16s, climb 2.4m) alt [1.23, 3.63, 1.23, 3.63] range [0.01, 0.64, 0.0, 0.67] phases ['local_recovery', 'recovery_climb']
- visibility management (no altitude gain) t=0.16–3.44s (3.32s) alt [6.56, 6.52, 6.52, 6.57] range [8.09, 4.33, 4.33, 8.09]
- visibility management (no altitude gain) t=7.08–7.44s (0.4s) alt [6.53, 6.52, 6.52, 6.53] range [0.56, 0.39, 0.39, 0.56]
- visibility management (no altitude gain) t=7.68–7.8s (0.16s) alt [6.52, 6.52, 6.52, 6.52] range [0.32, 0.3, 0.3, 0.32]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap', 'visibility_margin_expiring']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 4.7 | 6.51 | 2.54 | 5.75 | 1.49 | 0.1 | 18971 | True | 0.040 |
| 6.7 | 6.54 | 0.84 | 5.83 | 1.24 | -0.8 | 21972 | True | 0.011 |
| 8.7 | 6.52 | 0.22 | 5.82 | 0.45 | -7.6 | 22242 | True | 0.164 |
| 10.7 | 6.18 | 0.06 | 5.51 | 0.34 | -9.8 | 24924 | True | 0.201 |
| 12.7 | 5.77 | 0.04 | 5.08 | 0.32 | 37.4 | 29199 | True | 0.247 |
| 14.8 | 5.31 | 0.03 | 4.62 | 0.31 | -40.4 | 35157 | True | 0.222 |
| 16.8 | 4.89 | 0.01 | 4.21 | 0.30 | -18.0 | 42307 | True | 0.187 |
| 18.8 | 4.44 | 0.02 | 3.75 | 0.30 | -163.4 | 53242 | True | 0.206 |
| 20.9 | 4.00 | 0.02 | 3.31 | 0.31 | 167.6 | 63932 | True | 0.209 |
| 22.9 | 3.56 | 0.00 | 2.88 | 0.29 | 173.4 | 74974 | True | 0.203 |
| 25.0 | 3.12 | 0.02 | 2.42 | 0.29 | -26.2 | 89294 | True | 0.200 |
| 27.0 | 2.67 | 0.02 | 1.98 | 0.30 | -20.0 | 108211 | True | 0.229 |
| 29.0 | 2.23 | 0.01 | 1.55 | 0.30 | 24.2 | 136793 | True | 0.220 |
| 31.1 | 1.78 | 0.01 | 1.09 | 0.30 | 34.7 | 190349 | True | 0.215 |
| 33.1 | 1.33 | 0.01 | 0.65 | 0.30 | 50.6 | 224184 | True | 0.211 |
| 35.2 | 1.55 | 0.01 | 0.87 | 0.30 | 91.6 | 2859 | False | -0.400 |
| 37.2 | 2.41 | 0.41 | 1.70 | 0.02 | 2.6 | 120486 | False | -0.400 |
| 39.2 | 3.24 | 0.67 | 2.55 | 0.29 | 1.9 | 81309 | True | -0.391 |
| 41.3 | 3.65 | 0.62 | 2.95 | 0.36 | 5.8 | 71990 | True | -0.004 |
| 43.3 | 3.46 | 0.09 | 2.76 | 0.44 | -6.3 | 77996 | True | 0.217 |
| 45.3 | 3.00 | 0.02 | 2.32 | 0.30 | -27.8 | 93069 | True | 0.236 |
| 47.3 | 2.56 | 0.01 | 1.86 | 0.29 | -39.6 | 114936 | True | 0.201 |
| 49.3 | 2.11 | 0.01 | 1.41 | 0.29 | 125.6 | 148801 | True | 0.208 |
| 51.3 | 1.69 | 0.02 | 1.01 | 0.30 | 104.2 | 204572 | True | 0.239 |
| 53.3 | 1.26 | 0.01 | 0.56 | 0.30 | 106.3 | 222336 | True | 0.100 |
| 55.3 | 1.06 | 0.02 | 0.38 | 0.30 | 168.8 | 213905 | True | 0.088 |
| 57.3 | 0.91 | 0.01 | 0.22 | 0.30 | -139.3 | 208224 | True | 0.122 |
| 59.3 | 0.76 | 0.01 | 0.07 | 0.29 | 54.3 | 191168 | True | 0.108 |
| 61.3 | 0.68 | 0.01 | -0.00 | 0.29 | -42.1 | 149606 | True | 0.313 |
| 63.3 | 0.69 | 0.01 | -0.00 | 0.29 | -39.7 | 149640 | True | 0.339 |
| 65.3 | 0.69 | 0.01 | -0.00 | 0.29 | -40.7 | 149551 | True | 0.000 |

## Contradictions between belief and observed truth

- minor `identity_head_flips_near_deck` frames 879 t=22.4–22.4s {"flips": 107, "rate_per_s": 3.04, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- minor `recovery_while_pad_visible` frames 168 t=0.16–40.96s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E04_v60\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E04_v60\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E04_v60\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `c0c429407f9ea06b3443291d6dd801a1f471b273785aca6c9860377936060834`
- `frames.csv` sha256 `60b0d7ed71fda7c238db699501aadbf97e3c372850a9c9286aac2c741ed1cb5a`
- `verdict.json` sha256 `c803724cdb891bb7d72a58239735a9c312588e18c1447775b342adafd55336a6`
- `video_join.json` sha256 `e6aeba245f811cf7876a332a060a31cc59a98d5952882eeffb37380ed5756a50`
- `review.mp4` sha256 `454e51de7c1fa580676838ad1128d6b2133349652149a9dd4e7e398ad687b8bd`
