# Flight record — E03_v60 (E03)   **REJECT**

Scenario `windows_review_E03_yaw` kind=beach seed=3200000005 distance=8.0m height=6.0m boat_speed=0.3m/s

- frames **1138** over **45.48s**; outcome **collision_failure**
- physical events: touchdown@62.08s, collision_failure@65.5s
- first lock on the truth target at t=**0.12s**; selection on target afterwards **100.00%**
- hard failures: **physical.landed_on_target, physical.disarmed_after_landing, physical.disarms_promptly_at_contact, physical.no_collision, authority.descent_only_on_confirmed_target**; soft: physical.no_press_after_contact, authority.guards_engaged_with_enforcement, digest.matches_recording; criteria hard: E01.4_no_false_boat_claim_drives_selection, E01.10_no_spurious_recovery, E01.11_physical_termination; criteria soft: E01.9_descent_permission_stable

Acceptance criteria that did not pass, with their own numbers:

- `E01.4_no_false_boat_claim_drives_selection` — {"frames": 2, "examples": [{"t": 5.600000000006844, "name": "none", "prob": 0.018654903396964073, "wrong": 0.8997204899787903, "size": 114.00318145751953}, {"t": 5.640000000006893, "name": "none", "prob": 0.018654903396964073, "wrong": 0.8997204899787903, "size": 114.00318145751953}]}
- `E01.10_no_spurious_recovery` — {"recovery_executed_frames": 63, "first_t": 42.999999999942276, "parent_recovery_frames": 159}
- `E01.11_physical_termination` — {"outcome": "collision_failure", "landed": false, "armed": true, "final_clearance": 0.0072210378765921734, "final_t": 45.47999999994728, "touchdown_s": 62.07999999994602}
- `E01.9_descent_permission_stable` — {"reversals": 20, "limit": 3}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 1138, "frame_rows": 1138}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 1137}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 1138, "probes": 5, "max_mean_abs_diff": 3.662877604166667}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | NO | hard | `{"outcome": "collision_failure", "stop_reason": null, "strict": false, "final_height": 0.694, "final_clearance": -0.001}` |
| `physical.disarmed_after_landing` | NO | hard | `{"armed": true, "landed": false, "outcome": "collision_failure"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": null, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | NO | hard | `{"contact_t": 41.92, "disarm_t": null, "delay_s": null, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 27, "span_s": 1.04}` |
| `physical.no_collision` | NO | hard | `{"events": [["touchdown", 62.08], ["collision_failure", 65.5]]}` |
| `authority.descent_only_on_confirmed_target` | NO | hard | `{"frames": 4, "examples": [{"t": 42.84, "down": 0.3, "clearance": -0.0, "metric": false, "name": "target"}, {"t": 42.88, "down": 0.3, "clearance": -0.0, "metric": false, "name": "target"}, {"t": 42.92, "down": 0.3, "clearance": -0.0, "metric": false, "name": "target"}, {"t": 42.96, "down": 0.3, "...` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 1045, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 2, "longest_s": 0.04, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 0.12, "target_fraction": 1.0, "aliases": ["1", "14", "17", "21", "22", "3", "6", "8"]}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 1.0, "limit": 0.98, "frames_after": 1135, "frames_on_target": 1135}` |
| `authority.guards_engaged_with_enforcement` | NO | soft | `{"events": 39, "kinds": ["descent_without_fresh_geometry"], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 0.08, "situation": "E03", "scenario_requires_survey": false, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 828, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 5, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.fault_actually_injected` | yes | hard | `{"fault_rows": 30}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "visible", "distance_band": [5.0, 20.0], "fault": "gimbal_pan", "mode": "expert"}` |
| `digest.matches_recording` | NO | soft | `{"digest_frames": null, "frames": 1138, "present": false}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.08 | 0.12 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.54→6.55 | 8.12→8.12 | 5.68→5.69 | -0.00,-0.00,-0.07,-0.03 | 6051 | 0.00 |
| 0.12–0.28 | 0.20 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1/target | 6.55→6.56 | 8.13→8.13 | 5.70→5.71 | +0.17,+0.02,-0.00,-0.01 | 6066 | 0.76 |
| 0.32–3.68 | 3.40 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 1/target | 6.56→6.51 | 8.13→4.04 | 5.71→5.73 | +1.65,-0.00,+0.00,-0.00 | 14619 | 1.00 |
| 3.72–3.72 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 1/target | 6.51→6.51 | 3.97→3.97 | 5.73→5.73 | +1.61,+0.01,-0.00,+0.01 | 14783 | 1.00 |
| 3.76–3.80 | 0.08 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 1/target | 6.51→6.51 | 3.91→3.84 | 5.73→5.73 | +1.63,-0.01,-0.00,-0.00 | 15270 | 1.00 |
| 3.84–4.04 | 0.24 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.51→6.51 | 3.78→3.47 | 5.73→5.73 | +1.46,-0.09,+0.06,+0.00 | 16410 | 1.00 |
| 4.08–4.12 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.51→6.50 | 3.41→3.35 | 5.72→5.72 | +1.24,-0.08,+0.00,+0.00 | 16845 | 1.00 |
| 4.16–4.88 | 0.76 | align / target_align | `identity_and_fresh_geometry_associated` | 1,3/target | 6.50→6.49 | 3.29→2.47 | 5.72→5.74 | +1.04,-0.02,-0.00,+0.00 | 18910 | 1.00 |
| 4.92–4.92 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.49→6.49 | 2.44→2.44 | 5.74→5.74 | +1.32,-0.00,-0.01,+0.00 | 19002 | 1.00 |
| 4.96–5.56 | 0.64 | align / target_align | `identity_and_fresh_geometry_associated` | 1,3/target | 6.49→6.47 | 2.40→1.82 | 5.74→5.74 | +1.68,-0.04,+0.02,+0.01 | 20663 | 1.00 |
| 5.60–5.64 | 0.08 | align / target_align | `identity_and_fresh_geometry_associated` | 1/none | 6.47→6.47 | 1.77→1.73 | 5.74→5.74 | +1.57,-0.03,-0.05,+0.01 | 20952 | 1.00 |
| 5.68–6.24 | 0.60 | align / target_align | `identity_and_fresh_geometry_associated` | 1,3/target | 6.47→6.51 | 1.68→1.03 | 5.74→5.79 | +1.10,-0.01,-0.12,+0.00 | 21888 | 1.00 |
| 6.28–6.28 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 3/target | 6.51→6.51 | 0.99→0.99 | 5.80→5.80 | +0.71,-0.00,-0.18,+0.00 | 21921 | 1.00 |
| 6.32–6.44 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 3/target | 6.52→6.54 | 0.95→0.84 | 5.81→5.83 | +0.74,-0.02,-0.13,+0.00 | 21996 | 1.00 |
| 6.48–6.84 | 0.40 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1,3/target | 6.55→6.58 | 0.81→0.57 | 5.84→5.88 | +0.53,-0.00,-0.01,+0.00 | 21910 | 1.00 |
| 6.88–7.08 | 0.24 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.58→6.58 | 0.55→0.47 | 5.89→5.89 | +0.56,-0.02,+0.04,-0.00 | 21708 | 1.00 |
| 7.12–7.20 | 0.12 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.58→6.58 | 0.45→0.43 | 5.89→5.89 | +0.57,-0.00,+0.00,+0.00 | 21733 | 1.00 |
| 7.24–7.32 | 0.12 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.58→6.57 | 0.42→0.39 | 5.89→5.88 | +0.47,+0.05,+0.02,-0.00 | 21758 | 1.00 |
| 7.36–7.36 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.57→6.57 | 0.38→0.38 | 5.88→5.88 | +0.51,+0.02,+0.05,+0.00 | 21769 | 1.00 |
| 7.40–7.68 | 0.32 | align / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.57→6.56 | 0.37→0.31 | 5.88→5.87 | +0.53,+0.00,+0.07,+0.00 | 21836 | 1.00 |
| 7.72–7.96 | 0.28 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.56→6.54 | 0.30→0.26 | 5.86→5.84 | +0.62,-0.05,+0.13,+0.00 | 22045 | 1.00 |
| 8.00–8.08 | 0.12 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1,3/target | 6.54→6.53 | 0.26→0.24 | 5.84→5.83 | +0.56,-0.01,+0.00,+0.00 | 22185 | 1.00 |
| 8.12–8.12 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 3/target | 6.52→6.52 | 0.24→0.24 | 5.82→5.82 | +0.54,-0.02,+0.02,+0.01 | 22275 | 1.00 |
| 8.16–8.32 | 0.20 | align / target_align | `identity_and_fresh_geometry_associated` | 3/target | 6.52→6.51 | 0.23→0.20 | 5.82→5.80 | +0.49,-0.02,+0.01,+0.00 | 22530 | 1.00 |
| 8.36–9.00 | 0.68 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1,3/target | 6.50→6.47 | 0.20→0.12 | 5.80→5.77 | +0.45,-0.01,+0.07,-0.00 | 22797 | 1.00 |
| 9.04–9.08 | 0.08 | match / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.47→6.46 | 0.12→0.12 | 5.76→5.76 | +0.40,+0.01,-0.01,+0.00 | 22896 | 1.00 |
| 9.12–9.28 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.46→6.45 | 0.11→0.11 | 5.76→5.75 | +0.41,+0.01,+0.05,-0.00 | 22860 | 1.00 |
| 9.32–9.36 | 0.08 | descend / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.45→6.45 | 0.10→0.10 | 5.75→5.75 | +0.40,+0.02,+0.13,-0.00 | 22851 | 1.00 |
| 9.40–9.44 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.45→6.44 | 0.10→0.10 | 5.75→5.75 | +0.35,+0.01,+0.00,+0.00 | 22871 | 1.00 |
| 9.48–9.64 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.44→6.43 | 0.10→0.09 | 5.75→5.75 | +0.46,+0.01,+0.05,-0.00 | 22921 | 1.00 |
| 9.68–10.40 | 0.76 | descend / target_align | `identity_and_fresh_geometry_associated` | 1,3/target | 6.43→6.32 | 0.09→0.07 | 5.75→5.64 | +0.43,-0.02,+0.20,-0.00 | 23777 | 1.00 |
| 10.44–10.44 | 0.04 | match / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.31→6.31 | 0.06→0.06 | 5.63→5.63 | +0.37,-0.01,+0.28,+0.00 | 23906 | 1.00 |
| 10.48–10.64 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.30→6.26 | 0.06→0.06 | 5.62→5.57 | +0.35,-0.01,+0.35,-0.00 | 24342 | 1.00 |
| 10.68–10.68 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 6.24→6.24 | 0.06→0.06 | 5.55→5.55 | +0.34,-0.01,+0.00,+0.00 | 24522 | 1.00 |
| 10.72–10.88 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 6.23→6.18 | 0.05→0.05 | 5.54→5.49 | +0.38,-0.01,+0.07,+0.00 | 25024 | 1.00 |
| 10.92–12.12 | 1.24 | descend / target_align | `identity_and_fresh_geometry_associated` | 1,3/target | 6.18→6.00 | 0.05→0.04 | 5.49→5.30 | +0.37,+0.00,+0.17,+0.00 | 26780 | 1.00 |
| 12.16–12.16 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 1/target | 5.99→5.99 | 0.04→0.04 | 5.30→5.30 | +0.34,-0.01,+0.00,+0.00 | 26965 | 1.00 |
| 12.20–12.36 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 5.98→5.95 | 0.04→0.04 | 5.29→5.26 | +0.38,-0.01,+0.07,+0.00 | 27173 | 1.00 |
| 12.40–13.16 | 0.80 | descend / target_align | `identity_and_fresh_geometry_associated` | 1,3/target | 5.95→5.79 | 0.04→0.03 | 5.26→5.10 | +0.33,-0.01,+0.26,+0.00 | 28929 | 1.00 |
| 13.20–13.32 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 1/target | 5.77→5.73 | 0.03→0.04 | 5.08→5.04 | +0.35,-0.03,+0.25,+0.00 | 29554 | 1.00 |
| 13.36–13.52 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 1/target | 5.72→5.67 | 0.04→0.04 | 5.03→4.98 | +0.34,-0.01,+0.23,-0.00 | 30282 | 1.00 |
| 13.56–33.72 | 20.20 | descend / target_align | `identity_and_fresh_geometry_associated` | 1,3,6,8+.../target | 5.66→1.31 | 0.04→0.00 | 4.97→0.61 | +0.31,-0.00,+0.21,+0.00 | 226910 | 1.00 |
| 33.76–35.92 | 2.20 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 17/target | 1.30→1.27 | 0.00→0.00 | 0.60→0.59 | +0.30,-0.00,+0.01,+0.00 | 223152 | 1.00 |
| 35.96–36.12 | 0.20 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 17/target | 1.27→1.27 | 0.00→0.00 | 0.59→0.59 | +0.30,-0.00,-0.01,-0.00 | 222851 | 1.00 |
| 36.16–41.80 | 5.68 | descend / target_align | `identity_and_fresh_geometry_associated` | 17,21,22/target | 1.27→0.71 | 0.00→0.01 | 0.59→0.03 | +0.29,-0.00,+0.10,-0.00 | 222840 | 1.00 |
| 41.84–41.84 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.71→0.71 | 0.01→0.01 | 0.03→0.03 | +0.30,+0.00,+0.11,+0.00 | 173306 | 1.00 |
| 41.88–42.36 | 0.52 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 22/target | 0.70→0.69 | 0.01→0.02 | 0.02→-0.00 | +0.29,-0.01,+0.25,+0.00 | 170647 | 1.00 |
| 42.40–42.96 | 0.60 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 22/target | 0.69→0.70 | 0.02→0.02 | -0.00→-0.00 | +0.29,-0.02,+0.30,+0.00 | 172543 | 1.00 |
| 43.00–43.00 | 0.04 | local_downlook / local_downlook | `arrest_descent_and_inspect_below` | 22/target | 0.70→0.70 | 0.02→0.02 | -0.00→-0.00 | +0.24,+0.00,+0.00,+0.00 | 170804 | 0.00 |
| 43.04–43.52 | 0.52 | local_downlook / local_downlook | `bounded_fresh_downward_observation` | 22/target | 0.69→0.70 | 0.02→0.02 | -0.00→0.00 | +0.03,+0.00,+0.00,+0.00 | 189302 | 0.00 |
| 43.56–44.00 | 0.48 | local_recovery / local_downlook | `bounded_fresh_downward_observation` | 22/target | 0.70→0.69 | 0.03→0.08 | 0.00→0.00 | +0.07,-0.01,+0.00,+0.00 | 181219 | 0.00 |
| 44.04–45.48 | 1.48 | local_recovery / local_downlook | `upward_clearance_unverified` | 22/target | 0.69→0.69 | 0.08→0.27 | 0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 230400 | 0.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 0.1 | `scan` | 6.54→6.55 | 8.12→8.12 | 5.68→5.69 | 0% |
| 0.1 | 0.2 | `target_inspect` | 6.55→6.56 | 8.13→8.13 | 5.70→5.71 | 100% |
| 0.3 | 3.5 | `target_inspect` | 6.56→6.51 | 8.13→3.84 | 5.71→5.73 | 100% |
| 3.8 | 0.3 | `target_align` | 6.51→6.50 | 3.78→3.35 | 5.73→5.72 | 100% |
| 4.2 | 5.5 | `target_align` | 6.50→6.43 | 3.29→0.09 | 5.72→5.75 | 99% |
| 9.7 | 1.2 | `target_align` | 6.43→6.18 | 0.09→0.05 | 5.75→5.49 | 100% |
| 10.9 | 1.5 | `target_align` | 6.18→5.95 | 0.05→0.04 | 5.49→5.26 | 100% |
| 12.4 | 1.2 | `target_align` | 5.95→5.67 | 0.04→0.04 | 5.26→4.98 | 100% |
| 13.6 | 20.2 | `target_align` | 5.66→1.31 | 0.04→0.00 | 4.97→0.61 | 100% |
| 33.8 | 2.4 | `target_align` | 1.30→1.27 | 0.00→0.00 | 0.60→0.59 | 100% |
| 36.2 | 6.8 | `target_align` | 1.27→0.70 | 0.00→0.02 | 0.59→-0.00 | 100% |
| 43.0 | 1.0 | `local_downlook` | 0.70→0.69 | 0.02→0.08 | -0.00→0.00 | 100% |
| 44.0 | 1.5 | `local_downlook` | 0.69→0.69 | 0.08→0.27 | 0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.54, tgt 6045px)
- **t=0.12s** `target_inspect` — target_likely_evidence_requires_inspection (sel 1/target, alt 6.55, tgt 6061px)
- **t=3.72s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 1/target, alt 6.51, tgt 14783px)
- **t=3.84s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.51, tgt 15447px)
- **t=4.08s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.51, tgt 16642px)
- **t=4.16s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.50, tgt 17007px)
- **t=4.92s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.49, tgt 19002px)
- **t=4.96s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.49, tgt 19082px)
- **t=6.28s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 3/target, alt 6.51, tgt 21921px)
- **t=6.32s** `target_align` — identity_and_fresh_geometry_associated (sel 3/target, alt 6.52, tgt 21901px)
- **t=6.48s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 3/target, alt 6.55, tgt 21910px)
- **t=6.88s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.58, tgt 21689px)
- **t=7.12s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.58, tgt 21615px)
- **t=7.24s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.58, tgt 21681px)
- **t=8.00s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.54, tgt 22147px)
- **t=8.12s** `target_align` — identity_and_fresh_geometry_associated (sel 3/target, alt 6.52, tgt 22275px)
- **t=9.40s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.45, tgt 22871px)
- **t=9.48s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.44, tgt 22853px)
- **t=10.68s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 6.24, tgt 24522px)
- **t=10.72s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 6.23, tgt 24555px)
- **t=12.16s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 1/target, alt 5.99, tgt 26965px)
- **t=12.20s** `target_align` — identity_and_fresh_geometry_associated (sel 1/target, alt 5.98, tgt 26950px)
- **t=42.40s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 22/target, alt 0.69, tgt 170726px)
- **t=43.00s** `local_downlook` — arrest_descent_and_inspect_below (sel 22/target, alt 0.70, tgt 170804px)
- **t=43.04s** `local_downlook` — bounded_fresh_downward_observation (sel 22/target, alt 0.69, tgt 171746px)
- **t=44.04s** `local_downlook` — upward_clearance_unverified (sel 22/target, alt 0.69, tgt 176898px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–45.48s coverage 0.00 rad, inspected views 0, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- survey_interrupted track=None 
- target_confirmed track=1 identity_evidence_acquired
- recovery_start track=None 

## Recovery ledger

- visibility management (no altitude gain) t=0.32–3.72s (3.44s) alt [6.56, 6.51, 6.51, 6.56] range [8.13, 3.97, 3.97, 8.13]
- visibility management (no altitude gain) t=6.48–6.84s (0.4s) alt [6.55, 6.58, 6.55, 6.58] range [0.81, 0.57, 0.57, 0.81]
- visibility management (no altitude gain) t=7.12–7.2s (0.12s) alt [6.58, 6.58, 6.58, 6.58] range [0.45, 0.43, 0.43, 0.45]
- visibility management (no altitude gain) t=8.0–8.08s (0.12s) alt [6.54, 6.53, 6.53, 6.54] range [0.26, 0.24, 0.24, 0.26]
- visibility management (no altitude gain) t=43.56–45.48s (1.96s) alt [0.7, 0.69, 0.69, 0.7] range [0.03, 0.27, 0.03, 0.27]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 3.9 | 6.51 | 3.65 | 5.73 | 1.95 | 0.3 | 15761 | True | 0.047 |
| 5.9 | 6.48 | 1.39 | 5.75 | 1.61 | -0.7 | 21557 | True | -0.091 |
| 7.9 | 6.54 | 0.27 | 5.85 | 0.53 | 11.9 | 22015 | True | 0.175 |
| 9.9 | 6.41 | 0.08 | 5.73 | 0.38 | -0.3 | 22942 | True | 0.213 |
| 11.9 | 6.03 | 0.04 | 5.33 | 0.33 | -18.8 | 26555 | True | 0.185 |
| 14.0 | 5.58 | 0.04 | 4.89 | 0.31 | -66.4 | 31417 | True | 0.109 |
| 16.0 | 5.19 | 0.03 | 4.51 | 0.31 | -63.0 | 36990 | True | 0.242 |
| 18.0 | 4.74 | 0.02 | 4.04 | 0.30 | -41.5 | 45823 | True | 0.198 |
| 20.1 | 4.32 | 0.01 | 3.63 | 0.30 | -77.0 | 56139 | True | 0.192 |
| 22.1 | 3.87 | 0.01 | 3.18 | 0.29 | 172.4 | 67462 | True | 0.242 |
| 24.2 | 3.39 | 0.00 | 2.69 | 0.29 | -153.2 | 80326 | True | 0.215 |
| 26.2 | 2.96 | 0.02 | 2.28 | 0.30 | 44.5 | 94574 | True | 0.216 |
| 28.2 | 2.52 | 0.01 | 1.84 | 0.29 | 26.8 | 116545 | True | 0.231 |
| 30.3 | 2.07 | 0.01 | 1.37 | 0.30 | -9.9 | 153092 | True | 0.206 |
| 32.3 | 1.62 | 0.01 | 0.95 | 0.29 | 126.1 | 216822 | True | 0.237 |
| 34.4 | 1.27 | 0.01 | 0.58 | 0.29 | 157.9 | 222730 | True | 0.021 |
| 36.4 | 1.27 | 0.01 | 0.58 | 0.30 | -141.7 | 222736 | True | 0.093 |
| 38.4 | 1.07 | 0.01 | 0.38 | 0.30 | 29.2 | 214314 | True | 0.112 |
| 40.5 | 0.87 | 0.01 | 0.17 | 0.29 | 148.3 | 202260 | True | 0.114 |
| 42.5 | 0.69 | 0.02 | -0.00 | 0.30 | -43.5 | 170885 | True | 0.300 |
| 44.6 | 0.69 | 0.14 | 0.00 | 0.15 | -7.2 | 221933 | False | 0.000 |

## Contradictions between belief and observed truth

- **SEVERE** `descent_without_metric` frames 4 t=42.84–42.96s {"note": "down command while metric_confirmed false"}
- minor `identity_head_flips_near_deck` frames 431 t=22.96–22.96s {"flips": 38, "rate_per_s": 2.2, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- **SEVERE** `collision_after_contact` frames 1 t=45.48–45.48s {"event_time": 65.50399999994872}
- minor `recovery_while_pad_visible` frames 69 t=0.32–12.16s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E03_v60\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `33cfba470711c0351519f6db3105ae9382882c4109a6fd9a9da9bfb211497819`
- `frames.csv` sha256 `468fe9555622de35493d72a6d27e88483f17417cda75dd901e0028b24776d473`
- `verdict.json` sha256 `0eda98d14c900e622d0947cb001d824d437df802661f4687458eb1557a281ad1`
- `video_join.json` sha256 `f338e19613870f054326b2472220d853a3f0ec0eccf78cc16f450766f41e5d71`
- `review.mp4` sha256 `0ef07bf62bb106332d02dcdbb0efeec6620dca0cfaa1613edd2bf2f27a36e78f`
