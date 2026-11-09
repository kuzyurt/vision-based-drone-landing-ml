# Flight record — E08_v61c (E08)   **REJECT**

Scenario `windows_review_E08_search_far` kind=beach seed=3200000003 distance=52.0m height=8.0m boat_speed=0.3m/s

- frames **4323** over **172.88s**; outcome **landed**
- physical events: touchdown@189.08s, stable_contact@190.34s, unstable_contact@190.62s, stable_contact@193.08s, landed@194.73s
- first lock on the truth target at t=**20.76s**; selection on target afterwards **93.69%**
- hard failures: **authority.selection_continuity**; soft: physical.no_press_after_contact, digest.matches_recording; criteria hard: E01.4_selection_continuity_after_lock, E01.4_no_false_boat_claim_drives_selection; criteria soft: E01.9_descent_permission_stable, E01.10b_parent_recovery_share_below_limit

Acceptance criteria that did not pass, with their own numbers:

- `E01.4_selection_continuity_after_lock` — {"frames_after": 3804, "frames_on_target": 3558, "fraction": 0.9353, "limit": 0.95}
- `E01.4_no_false_boat_claim_drives_selection` — {"frames": 249, "examples": [{"t": 20.639999999987847, "name": "none", "prob": 0.03608939051628113, "wrong": 0.2896750271320343, "size": 7.375710487365723}, {"t": 20.679999999987754, "name": "none", "prob": 0.03608939051628113, "wrong": 0.2896750271320343, "size": 7.375710487365723}, {"t": 20.71999999998766, "name": "none", "prob": 0.03608939051628113, "wrong": 0.2896750271320343, "size": 7.375710487365723}, {"t": 27.599999999971626, "name": "decoy_debris", "prob": 1.5354113429566496e-06, "wrong": 0.5199069976806641, "size": 11.795333862304688}, {"t": 27.639999999971533, "name": "none", "prob": 1.5354113429566496e-06, "wrong": 0.5199069976806641, "size": 11.795333862304688}]}
- `E01.9_descent_permission_stable` — {"reversals": 164, "limit": 3}
- `E01.10b_parent_recovery_share_below_limit` — {"share": 0.2811, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 4323, "frame_rows": 4323}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 4322}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 4323, "probes": 5, "max_mean_abs_diff": 2.1021875}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | yes | hard | `{"outcome": "landed", "stop_reason": null, "strict": true, "final_height": 0.675, "final_clearance": -0.0}` |
| `physical.disarmed_after_landing` | yes | hard | `{"armed": false, "landed": true, "outcome": "landed"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": 172.88, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | yes | hard | `{"contact_t": 167.04, "disarm_t": 170.88, "delay_s": 3.84, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 96, "span_s": 3.8}` |
| `physical.no_collision` | yes | hard | `{"events": [["touchdown", 189.08], ["stable_contact", 190.34], ["unstable_contact", 190.62], ["stable_contact", 193.08], ["landed", 194.73]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 3146, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 32, "longest_s": 0.24, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 20.76, "target_fraction": 0.9369, "aliases": ["18", "23", "25", "26", "27", "29", "33", "37", "40", "43", "47", "48"]}` |
| `authority.selection_continuity` | NO | hard | `{"fraction": 0.9369, "limit": 0.98, "frames_after": 3804, "frames_on_target": 3564}` |
| `authority.guards_engaged_with_enforcement` | yes | soft | `{"events": 698, "kinds": ["descent_without_fresh_geometry"], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 20.6, "situation": "E08", "scenario_requires_survey": true, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 1370, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 0, "visibility_management": 58, "longest_s": 0.0, "limit_s": 8.0, "detail": []}` |
| `purpose.target_outside_initial_view` | yes | hard | `{"first_frame_target_px": 0.0, "lock_t": 20.76}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "outside_camera", "distance_band": [40.0, 60.0], "fault": null, "mode": "expert"}` |
| `digest.matches_recording` | NO | soft | `{"digest_frames": null, "frames": 4323, "present": false}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–20.60 | 20.64 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 8.53→8.46 | 52.19→58.59 | 6.70→6.30 | -0.00,+0.00,-0.00,-0.34 | 121 | 0.00 |
| 20.64–20.72 | 0.12 | inspect_candidate / inspect_candidate | `weak_extent_candidate_inspect_from_safe_standoff` | 13/none | 8.46→8.46 | 58.60→58.63 | 6.30→6.31 | -0.00,+0.00,+0.00,-0.32 | 6 | 0.00 |
| 20.76–27.56 | 6.84 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/target | 8.47→8.48 | 58.64→54.54 | 6.31→6.62 | +1.02,+0.10,+0.00,+0.11 | 112 | 0.00 |
| 27.60–27.60 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.48→8.48 | 54.47→54.47 | 6.62→6.62 | +1.97,+0.08,+0.00,+0.02 | 88 | 0.00 |
| 27.64–27.68 | 0.08 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/none | 8.48→8.48 | 54.39→54.32 | 6.62→6.62 | +1.97,+0.18,+0.00,+0.05 | 93 | 0.00 |
| 27.72–27.72 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.48→8.48 | 54.24→54.24 | 6.61→6.61 | +1.97,+0.28,+0.00,+0.07 | 93 | 0.00 |
| 27.76–27.84 | 0.12 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/none | 8.48→8.48 | 54.17→54.02 | 6.61→6.60 | +1.97,+0.34,+0.00,+0.11 | 94 | 0.00 |
| 27.88–27.88 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.48→8.48 | 53.95→53.95 | 6.60→6.60 | +1.97,+0.33,+0.00,+0.13 | 94 | 0.00 |
| 27.92–28.08 | 0.20 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/none | 8.48→8.48 | 53.87→53.58 | 6.60→6.59 | +1.98,+0.30,+0.00,+0.12 | 96 | 0.00 |
| 28.12–28.24 | 0.16 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.48→8.48 | 53.50→53.28 | 6.59→6.58 | +1.98,+0.26,+0.00,+0.10 | 100 | 0.00 |
| 28.28–28.28 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/none | 8.48→8.48 | 53.21→53.21 | 6.58→6.58 | +1.99,+0.24,+0.00,+0.10 | 102 | 0.00 |
| 28.32–28.60 | 0.32 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.47→8.47 | 53.14→52.63 | 6.57→6.55 | +1.99,+0.21,+0.00,+0.08 | 104 | 0.00 |
| 28.64–28.64 | 0.04 | reorient_candidate / reorient_candidate | `remembered_candidate_needs_fresh_visual_confirmation` | 13/none | 8.47→8.47 | 52.56→52.56 | 6.55→6.55 | +1.94,+0.12,+0.00,+0.07 | 100 | 0.00 |
| 28.68–28.68 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.47→8.47 | 52.48→52.48 | 6.54→6.54 | +1.99,+0.16,+0.00,+0.07 | 98 | 0.00 |
| 28.72–28.72 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/none | 8.47→8.47 | 52.41→52.41 | 6.53→6.53 | +1.99,+0.16,+0.00,+0.06 | 104 | 0.00 |
| 28.76–28.88 | 0.16 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.47→8.47 | 52.34→52.12 | 6.53→6.51 | +1.99,+0.15,+0.00,+0.06 | 110 | 0.00 |
| 28.92–29.04 | 0.16 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/none | 8.47→8.47 | 52.05→51.84 | 6.50→6.48 | +2.00,+0.13,+0.00,+0.05 | 105 | 0.00 |
| 29.08–29.16 | 0.12 | reorient_candidate / reorient_candidate | `remembered_candidate_needs_fresh_visual_confirmation` | 13/none | 8.47→8.47 | 51.76→51.62 | 6.47→6.45 | +1.89,-0.00,+0.00,+0.05 | 112 | 0.00 |
| 29.20–29.24 | 0.08 | reorient_candidate / reorient_candidate | `remembered_candidate_needs_fresh_visual_confirmation` | 13/decoy_debris | 8.47→8.47 | 51.55→51.48 | 6.44→6.43 | +1.75,-0.05,+0.00,+0.04 | 109 | 0.00 |
| 29.28–29.28 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.47→8.47 | 51.41→51.41 | 6.42→6.42 | +1.77,+0.02,+0.00,+0.04 | 106 | 0.00 |
| 29.32–29.36 | 0.08 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/none | 8.47→8.47 | 51.34→51.27 | 6.42→6.41 | +1.86,+0.08,+0.00,+0.03 | 105 | 0.00 |
| 29.40–29.40 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.47→8.47 | 51.20→51.20 | 6.40→6.40 | +1.94,+0.07,+0.00,+0.03 | 106 | 0.00 |
| 29.44–29.44 | 0.04 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/none | 8.47→8.47 | 51.13→51.13 | 6.40→6.40 | +2.00,+0.07,+0.00,+0.03 | 99 | 0.00 |
| 29.48–30.68 | 1.24 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.47→8.46 | 51.06→48.98 | 6.39→6.78 | +2.00,+0.05,+0.00,+0.02 | 126 | 0.00 |
| 30.72–30.72 | 0.04 | reorient_candidate / reorient_candidate | `remembered_candidate_needs_fresh_visual_confirmation` | 13/decoy_debris | 8.46→8.46 | 48.91→48.91 | 6.79→6.79 | +1.95,-0.02,+0.00,+0.01 | 122 | 0.00 |
| 30.76–37.16 | 6.44 | inspect_candidate / inspect_candidate | `plausible_boat_inspect_unknown_design` | 13/decoy_debris | 8.46→8.44 | 48.84→38.03 | 6.81→6.90 | +2.00,+0.00,+0.00,+0.00 | 254 | 0.00 |
| 37.20–42.36 | 5.20 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 18/target | 8.44→8.44 | 37.96→29.16 | 6.91→7.06 | +1.99,-0.13,+0.00,-0.05 | 408 | 0.79 |
| 42.40–47.04 | 4.68 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 18/target | 8.44→8.43 | 29.09→21.13 | 7.07→7.35 | +2.00,+0.00,+0.00,+0.00 | 869 | 0.98 |
| 47.08–56.28 | 9.24 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.43→8.38 | 21.06→5.34 | 7.35→7.59 | +2.00,+0.00,-0.00,+0.00 | 8271 | 1.00 |
| 56.32–57.60 | 1.32 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.38→8.38 | 5.27→3.27 | 7.59→7.60 | +1.78,-0.03,+0.01,+0.03 | 10960 | 1.00 |
| 57.64–57.64 | 0.04 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.38→8.38 | 3.21→3.21 | 7.60→7.60 | +1.76,-0.04,-0.00,+0.08 | 11033 | 1.00 |
| 57.68–57.72 | 0.08 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.37→8.37 | 3.15→3.09 | 7.60→7.59 | +1.68,-0.01,-0.04,+0.07 | 11201 | 1.00 |
| 57.76–57.76 | 0.04 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.37→8.37 | 3.03→3.03 | 7.59→7.59 | +1.71,-0.04,-0.07,+0.07 | 11305 | 1.00 |
| 57.80–57.84 | 0.08 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.37→8.36 | 2.97→2.91 | 7.59→7.59 | +1.63,-0.03,-0.10,+0.07 | 11452 | 1.00 |
| 57.88–57.92 | 0.08 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.36→8.36 | 2.85→2.79 | 7.60→7.60 | +1.67,-0.05,-0.14,+0.07 | 11575 | 1.00 |
| 57.96–60.36 | 2.44 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.37→8.41 | 2.73→0.41 | 7.60→7.71 | +1.01,-0.07,+0.00,+0.02 | 12718 | 1.00 |
| 60.40–60.52 | 0.16 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.40→8.39 | 0.40→0.36 | 7.71→7.70 | +0.47,-0.04,+0.01,-0.00 | 12771 | 1.00 |
| 60.56–60.56 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.35→0.35 | 7.70→7.70 | +0.50,-0.04,-0.04,-0.01 | 12751 | 1.00 |
| 60.60–61.00 | 0.44 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.39→8.39 | 0.34→0.28 | 7.69→7.69 | +0.29,-0.00,-0.00,+0.00 | 12827 | 1.00 |
| 61.04–61.08 | 0.08 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.28→0.28 | 7.69→7.69 | +0.20,+0.01,-0.04,-0.01 | 12808 | 1.00 |
| 61.12–61.28 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.28→0.28 | 7.69→7.69 | +0.34,-0.05,+0.02,-0.01 | 12825 | 1.00 |
| 61.32–61.32 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.29→0.29 | 7.69→7.69 | +0.40,+0.01,+0.05,-0.01 | 12779 | 1.00 |
| 61.36–61.44 | 0.12 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.29→0.29 | 7.69→7.69 | +0.51,-0.05,+0.01,-0.01 | 12863 | 1.00 |
| 61.48–62.00 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.39→8.39 | 0.29→0.31 | 7.69→7.68 | +0.33,-0.01,+0.00,+0.00 | 12942 | 1.00 |
| 62.04–62.16 | 0.16 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.39→8.39 | 0.31→0.32 | 7.68→7.68 | +0.13,-0.00,-0.00,-0.03 | 12925 | 1.00 |
| 62.20–62.20 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.32→0.32 | 7.68→7.68 | +0.11,-0.00,-0.02,-0.02 | 12877 | 1.00 |
| 62.24–62.32 | 0.12 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.33→0.34 | 7.68→7.68 | +0.22,-0.06,-0.07,-0.00 | 12874 | 1.00 |
| 62.36–62.36 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.34→0.34 | 7.69→7.69 | +0.22,-0.00,-0.12,+0.00 | 12848 | 1.00 |
| 62.40–62.48 | 0.12 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.39→8.39 | 0.35→0.36 | 7.69→7.69 | +0.33,-0.06,-0.07,+0.00 | 12850 | 1.00 |
| 62.52–62.52 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.40→8.40 | 0.37→0.37 | 7.70→7.70 | +0.44,-0.06,-0.02,+0.00 | 12798 | 1.00 |
| 62.56–62.80 | 0.28 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.40→8.41 | 0.37→0.41 | 7.70→7.72 | +0.65,+0.00,+0.00,-0.00 | 12796 | 1.00 |
| 62.84–62.96 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.41→8.41 | 0.41→0.41 | 7.72→7.72 | +0.74,-0.01,-0.04,+0.00 | 12742 | 1.00 |
| 63.00–63.52 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.42→8.43 | 0.41→0.36 | 7.73→7.73 | +0.39,+0.01,-0.01,+0.00 | 12738 | 1.00 |
| 63.56–63.80 | 0.28 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.43→8.43 | 0.36→0.35 | 7.73→7.72 | +0.09,-0.00,-0.00,-0.04 | 12767 | 1.00 |
| 63.84–63.92 | 0.12 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.43→8.43 | 0.35→0.36 | 7.72→7.72 | +0.11,-0.09,+0.04,-0.05 | 12761 | 1.00 |
| 63.96–64.40 | 0.48 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.43→8.42 | 0.36→0.43 | 7.72→7.71 | +0.10,+0.12,+0.02,-0.00 | 12829 | 1.00 |
| 64.44–64.96 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,23/target | 8.41→8.41 | 0.44→0.55 | 7.70→7.71 | +0.26,+0.02,-0.00,+0.00 | 12825 | 1.00 |
| 65.00–65.04 | 0.08 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.41→8.41 | 0.56→0.56 | 7.71→7.71 | +0.22,-0.00,+0.00,-0.02 | 12766 | 1.00 |
| 65.08–65.20 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.41→8.42 | 0.57→0.59 | 7.71→7.71 | +0.33,-0.05,-0.01,-0.00 | 12767 | 1.00 |
| 65.24–65.76 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,23/target | 8.42→8.42 | 0.60→0.66 | 7.71→7.73 | +0.30,+0.01,-0.00,+0.00 | 12756 | 1.00 |
| 65.80–66.00 | 0.24 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.42→8.42 | 0.66→0.68 | 7.73→7.72 | +0.11,+0.00,+0.00,-0.06 | 12627 | 1.00 |
| 66.04–66.12 | 0.12 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.42→8.42 | 0.69→0.70 | 7.72→7.72 | +0.11,-0.07,+0.04,-0.07 | 12648 | 1.00 |
| 66.16–67.40 | 1.28 | align / target_align | `identity_and_fresh_geometry_associated` | 18,23/target | 8.42→8.33 | 0.70→0.88 | 7.72→7.62 | +0.49,+0.01,+0.07,+0.01 | 12888 | 1.00 |
| 67.44–67.44 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.33→8.33 | 0.87→0.87 | 7.61→7.61 | +1.06,+0.04,-0.02,+0.03 | 12921 | 1.00 |
| 67.48–67.68 | 0.24 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.33→8.33 | 0.86→0.78 | 7.61→7.61 | +0.93,+0.01,-0.04,+0.03 | 13016 | 1.00 |
| 67.72–68.08 | 0.40 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.33→8.35 | 0.76→0.59 | 7.61→7.63 | +0.51,+0.01,-0.01,+0.00 | 13178 | 1.00 |
| 68.12–68.64 | 0.56 | align / target_align | `identity_and_fresh_geometry_associated` | 18,23/target | 8.35→8.36 | 0.57→0.45 | 7.63→7.66 | +0.09,-0.03,-0.03,+0.00 | 13139 | 1.00 |
| 68.68–69.20 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,23/target | 8.37→8.37 | 0.45→0.45 | 7.66→7.68 | +0.31,-0.00,+0.00,-0.00 | 12955 | 1.00 |
| 69.24–69.88 | 0.68 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18,23/target | 8.37→8.37 | 0.46→0.50 | 7.68→7.67 | +0.12,-0.00,-0.00,-0.01 | 12949 | 1.00 |
| 69.92–70.24 | 0.36 | align / target_align | `identity_and_fresh_geometry_associated` | 18,23/target | 8.37→8.38 | 0.51→0.56 | 7.67→7.67 | +0.17,+0.04,-0.07,+0.00 | 12895 | 1.00 |
| 70.28–70.28 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.38→8.38 | 0.57→0.57 | 7.67→7.67 | +0.27,+0.01,-0.06,+0.00 | 12822 | 1.00 |
| 70.32–70.52 | 0.24 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.38→8.39 | 0.58→0.61 | 7.67→7.68 | +0.35,-0.05,-0.00,+0.01 | 12825 | 1.00 |
| 70.56–71.08 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,25/target | 8.40→8.40 | 0.61→0.65 | 7.68→7.68 | +0.32,+0.00,+0.00,+0.00 | 12874 | 1.00 |
| 71.12–71.32 | 0.24 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 25/target | 8.39→8.39 | 0.65→0.66 | 7.68→7.68 | +0.10,+0.00,-0.00,-0.02 | 12882 | 1.00 |
| 71.36–71.80 | 0.48 | align / target_align | `identity_and_fresh_geometry_associated` | 18,25/target | 8.39→8.38 | 0.66→0.71 | 7.68→7.68 | +0.09,+0.06,+0.02,-0.00 | 12875 | 1.00 |
| 71.84–72.28 | 0.48 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.38→8.38 | 0.71→0.79 | 7.68→7.68 | +0.29,+0.01,-0.00,+0.00 | 12780 | 1.00 |
| 72.32–72.60 | 0.32 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.38→8.37 | 0.79→0.82 | 7.68→7.67 | +0.56,-0.11,+0.07,+0.01 | 12800 | 1.00 |
| 72.64–73.16 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.37→8.35 | 0.82→0.77 | 7.67→7.64 | +0.42,-0.01,+0.00,+0.00 | 12930 | 1.00 |
| 73.20–73.20 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.35→8.35 | 0.77→0.77 | 7.64→7.64 | +0.35,+0.00,-0.00,+0.00 | 12845 | 1.00 |
| 73.24–73.36 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.35→8.35 | 0.76→0.75 | 7.64→7.64 | +0.21,+0.09,+0.02,+0.00 | 12922 | 1.00 |
| 73.40–73.92 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,25/target | 8.35→8.35 | 0.75→0.73 | 7.64→7.64 | +0.32,+0.01,+0.00,+0.00 | 12954 | 1.00 |
| 73.96–74.36 | 0.44 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18,25/target | 8.35→8.35 | 0.73→0.73 | 7.64→7.63 | +0.20,+0.00,-0.00,-0.02 | 12941 | 1.00 |
| 74.40–75.16 | 0.80 | align / target_align | `identity_and_fresh_geometry_associated` | 18,25/target | 8.34→8.33 | 0.73→0.81 | 7.63→7.62 | +0.24,-0.00,+0.06,-0.00 | 12984 | 1.00 |
| 75.20–75.68 | 0.52 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,25/target | 8.32→8.29 | 0.81→0.81 | 7.61→7.58 | +0.32,-0.01,+0.00,+0.00 | 13125 | 1.00 |
| 75.72–75.84 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 25/target | 8.29→8.29 | 0.81→0.81 | 7.58→7.58 | +0.35,-0.03,-0.01,+0.01 | 13056 | 1.00 |
| 75.88–76.40 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,25/target | 8.29→8.29 | 0.81→0.80 | 7.58→7.59 | +0.33,+0.01,-0.00,+0.00 | 13072 | 1.00 |
| 76.44–76.52 | 0.12 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.29→8.29 | 0.80→0.80 | 7.59→7.59 | +0.35,+0.01,+0.00,+0.02 | 13027 | 1.00 |
| 76.56–76.68 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.29→8.29 | 0.80→0.80 | 7.59→7.59 | +0.41,+0.01,-0.01,+0.01 | 12996 | 1.00 |
| 76.72–77.24 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,26/target | 8.29→8.30 | 0.79→0.77 | 7.58→7.58 | +0.31,-0.00,-0.00,+0.00 | 13150 | 1.00 |
| 77.28–77.64 | 0.40 | align / target_align | `identity_and_fresh_geometry_associated` | 18,26/target | 8.30→8.29 | 0.77→0.76 | 7.58→7.57 | +0.37,-0.03,+0.03,+0.01 | 13163 | 1.00 |
| 77.68–78.08 | 0.44 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,26/target | 8.29→8.29 | 0.76→0.73 | 7.57→7.58 | +0.35,+0.02,-0.00,+0.00 | 13149 | 1.00 |
| 78.12–78.40 | 0.32 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.29→8.29 | 0.73→0.71 | 7.58→7.59 | +0.54,-0.08,+0.01,+0.00 | 13127 | 1.00 |
| 78.44–78.48 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 8.29→8.29 | 0.71→0.70 | 7.59→7.59 | +0.65,-0.03,+0.00,+0.00 | 13114 | 1.00 |
| 78.52–78.64 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18,25,26/target | 8.29→8.29 | 0.70→0.68 | 7.59→7.59 | +0.76,-0.04,+0.02,+0.00 | 13076 | 1.00 |
| 78.68–78.76 | 0.12 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.29→8.28 | 0.67→0.65 | 7.59→7.59 | +0.73,-0.00,+0.00,+0.00 | 13087 | 1.00 |
| 78.80–79.36 | 0.60 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.28→8.27 | 0.64→0.46 | 7.59→7.57 | +0.67,-0.04,+0.04,+0.00 | 13220 | 1.00 |
| 79.40–79.48 | 0.12 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.27→8.26 | 0.44→0.41 | 7.57→7.56 | +0.40,+0.01,+0.00,+0.00 | 13277 | 1.00 |
| 79.52–79.60 | 0.12 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.26→8.26 | 0.40→0.37 | 7.56→7.55 | +0.32,-0.02,+0.00,-0.01 | 13328 | 1.00 |
| 79.64–79.64 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.26→8.26 | 0.36→0.36 | 7.55→7.55 | +0.27,-0.01,+0.00,-0.01 | 13372 | 1.00 |
| 79.68–79.68 | 0.04 | visual_acquire / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.26→8.26 | 0.34→0.34 | 7.55→7.55 | +0.21,+0.00,+0.00,+0.00 | 13318 | 1.00 |
| 79.72–79.84 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.26→8.26 | 0.33→0.30 | 7.55→7.55 | +0.10,+0.03,+0.06,+0.00 | 13382 | 1.00 |
| 79.88–80.08 | 0.24 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.26→8.25 | 0.29→0.26 | 7.55→7.54 | +0.24,-0.02,+0.17,+0.01 | 13411 | 1.00 |
| 80.12–80.12 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.24→8.24 | 0.26→0.26 | 7.53→7.53 | +0.33,+0.07,+0.19,+0.01 | 13367 | 1.00 |
| 80.16–80.24 | 0.12 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.24→8.22 | 0.25→0.25 | 7.53→7.51 | +0.43,+0.02,+0.23,+0.00 | 13464 | 1.00 |
| 80.28–80.28 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.22→8.22 | 0.25→0.25 | 7.51→7.51 | +0.43,+0.08,+0.23,-0.01 | 13469 | 1.00 |
| 80.32–80.40 | 0.12 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.21→8.19 | 0.24→0.24 | 7.50→7.48 | +0.43,+0.03,+0.28,-0.03 | 13591 | 1.00 |
| 80.44–80.56 | 0.16 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.18→8.15 | 0.23→0.23 | 7.47→7.45 | +0.33,+0.02,+0.00,-0.00 | 13724 | 1.00 |
| 80.60–80.80 | 0.24 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.14→8.12 | 0.22→0.21 | 7.44→7.42 | +0.41,+0.00,+0.07,+0.00 | 13790 | 1.00 |
| 80.84–80.96 | 0.16 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.12→8.11 | 0.20→0.20 | 7.42→7.41 | +0.36,-0.02,+0.04,+0.01 | 13798 | 1.00 |
| 81.00–81.00 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.11→8.11 | 0.19→0.19 | 7.41→7.41 | +0.34,+0.00,+0.00,+0.00 | 13792 | 1.00 |
| 81.04–81.04 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.10→8.10 | 0.19→0.19 | 7.41→7.41 | +0.31,-0.00,-0.02,+0.01 | 13789 | 1.00 |
| 81.08–81.08 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.10→8.10 | 0.19→0.19 | 7.41→7.41 | +0.36,-0.04,-0.05,+0.01 | 13829 | 1.00 |
| 81.12–81.12 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.10→8.10 | 0.18→0.18 | 7.41→7.41 | +0.30,+0.00,-0.07,+0.01 | 13794 | 1.00 |
| 81.16–81.24 | 0.12 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18,26/target | 8.10→8.10 | 0.18→0.17 | 7.41→7.41 | +0.35,-0.01,-0.02,+0.02 | 13808 | 1.00 |
| 81.28–81.80 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,26/target | 8.10→8.11 | 0.17→0.15 | 7.41→7.42 | +0.28,+0.01,+0.00,+0.00 | 13774 | 1.00 |
| 81.84–82.04 | 0.24 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.11→8.11 | 0.15→0.15 | 7.42→7.42 | +0.09,+0.00,+0.00,+0.06 | 13835 | 1.00 |
| 82.08–82.20 | 0.16 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18,26/target | 8.11→8.11 | 0.15→0.16 | 7.42→7.42 | +0.14,-0.10,+0.00,+0.06 | 13902 | 1.00 |
| 82.24–82.56 | 0.36 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.11→8.11 | 0.16→0.18 | 7.42→7.42 | +0.45,-0.04,-0.04,+0.00 | 13860 | 1.00 |
| 82.60–82.60 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.12→8.12 | 0.19→0.19 | 7.42→7.42 | +0.49,+0.00,-0.00,+0.00 | 13766 | 1.00 |
| 82.64–82.64 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.12→8.12 | 0.19→0.19 | 7.43→7.43 | +0.50,+0.00,+0.02,+0.00 | 13740 | 1.00 |
| 82.68–82.76 | 0.12 | match / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.12→8.12 | 0.19→0.19 | 7.43→7.43 | +0.40,+0.02,+0.07,+0.00 | 13751 | 1.00 |
| 82.80–82.80 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.12→8.12 | 0.18→0.18 | 7.43→7.43 | +0.42,-0.00,+0.12,+0.00 | 13727 | 1.00 |
| 82.84–83.36 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.12→8.11 | 0.18→0.16 | 7.43→7.41 | +0.28,+0.01,+0.00,+0.00 | 13862 | 1.00 |
| 83.40–84.32 | 0.96 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18,25/target | 8.11→8.12 | 0.16→0.26 | 7.41→7.42 | +0.01,-0.00,-0.00,+0.02 | 13987 | 1.00 |
| 84.36–85.32 | 1.00 | align / target_align | `identity_and_fresh_geometry_associated` | 18,25/target | 8.12→8.03 | 0.27→0.49 | 7.42→7.34 | +0.34,-0.01,+0.15,+0.00 | 14062 | 1.00 |
| 85.36–85.88 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.02→7.96 | 0.49→0.42 | 7.33→7.26 | +0.51,-0.01,+0.00,+0.00 | 14414 | 1.00 |
| 85.92–86.36 | 0.48 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 7.96→7.97 | 0.41→0.36 | 7.26→7.25 | +0.08,+0.00,+0.00,-0.01 | 14732 | 1.00 |
| 86.40–86.60 | 0.24 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.97→7.97 | 0.36→0.37 | 7.25→7.25 | +0.12,+0.17,-0.00,+0.00 | 14701 | 1.00 |
| 86.64–86.68 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.97→7.97 | 0.37→0.38 | 7.25→7.25 | +0.16,+0.03,-0.01,+0.00 | 14510 | 1.00 |
| 86.72–86.84 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.97→7.97 | 0.38→0.39 | 7.25→7.26 | +0.15,-0.03,-0.01,-0.00 | 14465 | 1.00 |
| 86.88–87.40 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.97→7.98 | 0.40→0.46 | 7.26→7.28 | +0.31,-0.01,-0.00,+0.00 | 14420 | 1.00 |
| 87.44–87.52 | 0.12 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 7.98→7.98 | 0.46→0.46 | 7.28→7.28 | +0.21,+0.00,+0.00,-0.03 | 14279 | 1.00 |
| 87.56–88.08 | 0.56 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.98→7.95 | 0.47→0.49 | 7.28→7.26 | +0.27,+0.02,+0.10,-0.01 | 14420 | 1.00 |
| 88.12–88.12 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.95→7.95 | 0.49→0.49 | 7.25→7.25 | +0.28,-0.01,+0.00,+0.00 | 14309 | 1.00 |
| 88.16–88.32 | 0.20 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.94→7.93 | 0.49→0.50 | 7.25→7.23 | +0.36,-0.14,-0.02,+0.00 | 14508 | 1.00 |
| 88.36–88.84 | 0.52 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.93→7.94 | 0.50→0.50 | 7.23→7.23 | +0.29,-0.02,-0.01,+0.00 | 14577 | 1.00 |
| 88.88–89.00 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.94→7.94 | 0.50→0.49 | 7.23→7.23 | +0.40,+0.01,+0.01,-0.01 | 14447 | 1.00 |
| 89.04–89.56 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.94→7.94 | 0.49→0.47 | 7.23→7.23 | +0.35,-0.01,+0.00,-0.00 | 14506 | 1.00 |
| 89.60–89.68 | 0.12 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 7.94→7.94 | 0.47→0.47 | 7.23→7.23 | +0.18,+0.00,+0.00,-0.03 | 14552 | 1.00 |
| 89.72–90.48 | 0.80 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.94→8.01 | 0.47→0.48 | 7.23→7.31 | +0.25,-0.03,-0.11,-0.00 | 14485 | 1.00 |
| 90.52–90.56 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 8.02→8.02 | 0.49→0.49 | 7.32→7.32 | +0.43,-0.07,+0.00,+0.00 | 14155 | 1.00 |
| 90.60–90.72 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 18,26/target | 8.02→8.03 | 0.49→0.49 | 7.32→7.33 | +0.54,-0.11,+0.06,+0.00 | 14124 | 1.00 |
| 90.76–91.28 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,26/target | 8.03→8.02 | 0.49→0.45 | 7.33→7.32 | +0.40,-0.01,+0.00,+0.00 | 14172 | 1.00 |
| 91.32–91.40 | 0.12 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 8.02→8.02 | 0.44→0.44 | 7.32→7.32 | +0.25,+0.02,-0.00,+0.03 | 14169 | 1.00 |
| 91.44–91.48 | 0.08 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.02→8.02 | 0.43→0.43 | 7.32→7.32 | +0.28,-0.02,+0.03,+0.03 | 14146 | 1.00 |
| 91.52–91.60 | 0.12 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18,26/target | 8.01→8.01 | 0.43→0.42 | 7.32→7.32 | +0.42,-0.08,+0.09,+0.00 | 14161 | 1.00 |
| 91.64–92.44 | 0.84 | align / target_align | `identity_and_fresh_geometry_associated` | 18,26/target | 8.01→7.90 | 0.42→0.35 | 7.32→7.20 | +0.46,-0.02,+0.10,+0.00 | 14591 | 1.00 |
| 92.48–92.76 | 0.32 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.90→7.91 | 0.35→0.29 | 7.20→7.20 | +0.56,-0.04,+0.01,-0.00 | 14654 | 1.00 |
| 92.80–93.08 | 0.32 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.91→7.91 | 0.29→0.22 | 7.20→7.20 | +0.41,-0.01,+0.00,+0.00 | 14711 | 1.00 |
| 93.12–93.12 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.90→7.90 | 0.21→0.21 | 7.20→7.20 | +0.24,-0.04,-0.02,-0.01 | 14686 | 1.00 |
| 93.16–93.24 | 0.12 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.90→7.90 | 0.20→0.19 | 7.20→7.20 | +0.30,-0.04,-0.01,-0.01 | 14738 | 1.00 |
| 93.28–93.28 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.90→7.90 | 0.18→0.18 | 7.20→7.20 | +0.26,-0.01,+0.00,+0.00 | 14694 | 1.00 |
| 93.32–93.32 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.90→7.90 | 0.17→0.17 | 7.20→7.20 | +0.26,+0.00,-0.02,-0.01 | 14661 | 1.00 |
| 93.36–93.40 | 0.08 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.90→7.91 | 0.17→0.16 | 7.20→7.20 | +0.33,-0.05,-0.06,-0.01 | 14682 | 1.00 |
| 93.44–93.44 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.91→7.91 | 0.15→0.15 | 7.20→7.20 | +0.39,-0.02,-0.07,-0.01 | 14659 | 1.00 |
| 93.48–93.48 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.91→7.91 | 0.15→0.15 | 7.21→7.21 | +0.35,-0.05,-0.04,-0.01 | 14628 | 1.00 |
| 93.52–93.60 | 0.12 | match / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.91→7.91 | 0.14→0.14 | 7.21→7.21 | +0.38,-0.04,-0.04,-0.01 | 14616 | 1.00 |
| 93.64–93.64 | 0.04 | align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.91→7.91 | 0.13→0.13 | 7.22→7.22 | +0.45,-0.02,+0.01,-0.00 | 14583 | 1.00 |
| 93.68–93.68 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.91→7.91 | 0.13→0.13 | 7.22→7.22 | +0.40,-0.01,+0.00,+0.00 | 14572 | 1.00 |
| 93.72–94.12 | 0.44 | match / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.92→7.93 | 0.12→0.09 | 7.22→7.25 | +0.36,-0.01,-0.04,-0.00 | 14530 | 1.00 |
| 94.16–94.28 | 0.16 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,26/target | 7.94→7.94 | 0.08→0.08 | 7.25→7.26 | +0.36,-0.01,+0.00,+0.00 | 14401 | 1.00 |
| 94.32–94.44 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.94→7.94 | 0.07→0.06 | 7.26→7.26 | +0.17,-0.03,-0.03,-0.00 | 14371 | 1.00 |
| 94.48–95.00 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,26/target | 7.94→7.95 | 0.06→0.05 | 7.26→7.26 | +0.24,-0.01,-0.00,+0.00 | 14382 | 1.00 |
| 95.04–95.12 | 0.12 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 18/target | 7.95→7.95 | 0.05→0.06 | 7.26→7.26 | +0.23,+0.01,-0.00,+0.03 | 14370 | 1.00 |
| 95.16–95.16 | 0.04 | match / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.95→7.95 | 0.06→0.06 | 7.26→7.26 | +0.23,-0.01,-0.02,+0.03 | 14359 | 1.00 |
| 95.20–95.32 | 0.16 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.95→7.95 | 0.06→0.06 | 7.26→7.25 | +0.35,-0.02,-0.06,+0.00 | 14405 | 1.00 |
| 95.36–95.88 | 0.56 | match / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.95→7.97 | 0.06→0.06 | 7.26→7.26 | +0.33,-0.03,+0.04,+0.00 | 14433 | 1.00 |
| 95.92–95.96 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18/target | 7.96→7.96 | 0.06→0.06 | 7.26→7.26 | +0.30,-0.01,+0.00,+0.00 | 14423 | 1.00 |
| 96.00–96.04 | 0.08 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.96→7.95 | 0.06→0.06 | 7.25→7.25 | +0.33,-0.00,+0.04,-0.01 | 14444 | 1.00 |
| 96.08–96.12 | 0.08 | match / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.95→7.95 | 0.06→0.06 | 7.25→7.24 | +0.32,+0.02,+0.01,+0.00 | 14495 | 1.00 |
| 96.16–96.32 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.94→7.94 | 0.06→0.05 | 7.24→7.24 | +0.30,+0.03,+0.01,+0.00 | 14506 | 1.00 |
| 96.36–96.36 | 0.04 | descend / target_align | `identity_and_fresh_geometry_associated` | 18/target | 7.94→7.94 | 0.05→0.05 | 7.23→7.23 | +0.31,+0.04,-0.05,+0.00 | 14484 | 1.00 |
| 96.40–96.92 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,26/target | 7.93→7.94 | 0.05→0.05 | 7.24→7.25 | +0.30,-0.00,-0.00,+0.00 | 14528 | 1.00 |
| 96.96–97.16 | 0.24 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 7.94→7.94 | 0.05→0.05 | 7.25→7.25 | +0.11,+0.00,-0.00,+0.05 | 14479 | 1.00 |
| 97.20–97.32 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.94→7.94 | 0.05→0.05 | 7.25→7.25 | +0.14,-0.07,+0.01,+0.01 | 14574 | 1.00 |
| 97.36–97.44 | 0.12 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.94→7.94 | 0.06→0.06 | 7.25→7.25 | +0.29,-0.02,+0.00,+0.00 | 14534 | 1.00 |
| 97.48–97.68 | 0.24 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.94→7.94 | 0.07→0.08 | 7.25→7.26 | +0.42,-0.03,-0.08,-0.01 | 14426 | 1.00 |
| 97.72–97.84 | 0.16 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.94→7.95 | 0.08→0.09 | 7.26→7.27 | +0.33,-0.01,-0.08,+0.00 | 14415 | 1.00 |
| 97.88–97.92 | 0.08 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.95→7.96 | 0.09→0.09 | 7.27→7.27 | +0.36,-0.01,-0.08,-0.02 | 14350 | 1.00 |
| 97.96–98.08 | 0.16 | visual_acquire / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.96→7.97 | 0.09→0.09 | 7.28→7.29 | +0.22,-0.02,-0.04,-0.00 | 14328 | 1.00 |
| 98.12–98.16 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.98→7.98 | 0.09→0.09 | 7.29→7.29 | +0.22,-0.00,+0.00,+0.00 | 14265 | 1.00 |
| 98.20–98.32 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.98→7.99 | 0.09→0.09 | 7.29→7.30 | +0.34,-0.03,+0.01,-0.03 | 14263 | 1.00 |
| 98.36–98.60 | 0.28 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.99→7.99 | 0.09→0.09 | 7.30→7.30 | +0.29,-0.01,+0.00,-0.01 | 14256 | 1.00 |
| 98.64–98.76 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.99→7.99 | 0.09→0.09 | 7.30→7.29 | +0.36,-0.04,+0.01,-0.04 | 14228 | 1.00 |
| 98.80–98.88 | 0.12 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.99→7.99 | 0.09→0.09 | 7.29→7.29 | +0.31,-0.02,+0.00,-0.02 | 14304 | 1.00 |
| 98.92–99.04 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.99→7.98 | 0.09→0.09 | 7.29→7.29 | +0.44,-0.02,+0.01,-0.03 | 14275 | 1.00 |
| 99.08–99.20 | 0.16 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.98→7.98 | 0.09→0.09 | 7.29→7.29 | +0.39,-0.01,+0.00,-0.00 | 14325 | 1.00 |
| 99.24–99.72 | 0.52 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.98→7.97 | 0.08→0.06 | 7.29→7.28 | +0.27,-0.00,+0.01,-0.00 | 14437 | 1.00 |
| 99.76–100.28 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.97→7.98 | 0.06→0.05 | 7.28→7.29 | +0.28,-0.00,-0.01,+0.00 | 14387 | 1.00 |
| 100.32–100.44 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.98→7.98 | 0.05→0.05 | 7.29→7.29 | +0.38,-0.01,-0.06,+0.00 | 14336 | 1.00 |
| 100.48–100.48 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.98→7.98 | 0.05→0.05 | 7.29→7.29 | +0.36,-0.00,-0.07,+0.00 | 14246 | 1.00 |
| 100.52–100.84 | 0.36 | match / target_align | `identity_and_fresh_geometry_associated` | 18,26/target | 7.98→8.01 | 0.05→0.04 | 7.29→7.32 | +0.31,-0.00,-0.13,+0.00 | 14303 | 1.00 |
| 100.88–101.40 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 18,26/target | 8.01→8.05 | 0.04→0.03 | 7.33→7.36 | +0.33,+0.00,-0.01,+0.00 | 14124 | 1.00 |
| 101.44–101.60 | 0.20 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 8.05→8.05 | 0.03→0.03 | 7.36→7.36 | +0.14,+0.00,-0.00,+0.04 | 14039 | 1.00 |
| 101.64–101.76 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 8.04→8.04 | 0.03→0.03 | 7.35→7.35 | +0.17,-0.03,-0.06,+0.01 | 14168 | 1.00 |
| 101.80–102.32 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 8.05→8.06 | 0.03→0.05 | 7.35→7.36 | +0.26,-0.01,-0.01,+0.00 | 14160 | 1.00 |
| 102.36–102.40 | 0.08 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 8.06→8.06 | 0.05→0.06 | 7.36→7.36 | +0.17,+0.00,+0.00,+0.03 | 14025 | 1.00 |
| 102.44–102.52 | 0.12 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 8.06→8.06 | 0.06→0.06 | 7.36→7.36 | +0.25,+0.01,-0.05,+0.00 | 14038 | 1.00 |
| 102.56–102.72 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 8.06→8.06 | 0.07→0.07 | 7.36→7.37 | +0.43,+0.01,-0.00,-0.02 | 14031 | 1.00 |
| 102.76–102.80 | 0.08 | descend / target_align | `identity_and_fresh_geometry_associated` | 27/target | 8.06→8.07 | 0.08→0.08 | 7.37→7.37 | +0.44,-0.01,+0.08,-0.01 | 14024 | 1.00 |
| 102.84–102.96 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 8.07→8.06 | 0.08→0.08 | 7.37→7.37 | +0.42,-0.00,+0.08,+0.00 | 13991 | 1.00 |
| 103.00–103.00 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 8.06→8.06 | 0.08→0.08 | 7.37→7.37 | +0.39,-0.00,+0.00,+0.00 | 13992 | 1.00 |
| 103.04–103.16 | 0.16 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 8.06→8.05 | 0.08→0.07 | 7.37→7.36 | +0.37,-0.02,+0.06,-0.01 | 14040 | 1.00 |
| 103.20–103.72 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 8.05→8.03 | 0.07→0.05 | 7.36→7.35 | +0.28,-0.00,+0.00,+0.00 | 14074 | 1.00 |
| 103.76–104.04 | 0.32 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 8.03→8.03 | 0.05→0.05 | 7.35→7.34 | +0.06,+0.00,-0.00,+0.05 | 14160 | 1.00 |
| 104.08–104.24 | 0.20 | match / target_align | `identity_and_fresh_geometry_associated` | 18/target | 8.03→8.03 | 0.06→0.07 | 7.34→7.34 | +0.17,-0.08,-0.04,+0.01 | 14187 | 1.00 |
| 104.28–104.36 | 0.12 | match / target_align | `identity_and_fresh_geometry_associated` | 18/none | 8.03→8.03 | 0.08→0.09 | 7.34→7.34 | +0.39,-0.07,-0.06,+0.00 | 14083 | 1.00 |
| 104.40–104.44 | 0.08 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 8.04→8.04 | 0.09→0.10 | 7.35→7.35 | +0.45,-0.04,-0.00,+0.00 | 14039 | 1.00 |
| 104.48–104.52 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 8.04→8.04 | 0.10→0.11 | 7.35→7.35 | +0.36,-0.01,+0.00,+0.00 | 14053 | 1.00 |
| 104.56–105.00 | 0.48 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 8.04→8.04 | 0.11→0.12 | 7.35→7.34 | +0.43,-0.01,+0.07,+0.00 | 14091 | 1.00 |
| 105.04–105.04 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 8.04→8.04 | 0.12→0.12 | 7.34→7.34 | +0.40,-0.01,+0.00,+0.00 | 14139 | 1.00 |
| 105.08–105.36 | 0.32 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 8.04→8.01 | 0.12→0.10 | 7.34→7.31 | +0.35,-0.02,+0.05,-0.02 | 14240 | 1.00 |
| 105.40–105.68 | 0.32 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 8.00→7.99 | 0.10→0.08 | 7.31→7.30 | +0.28,+0.00,+0.00,-0.00 | 14298 | 1.00 |
| 105.72–105.88 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.99→7.99 | 0.08→0.08 | 7.30→7.30 | +0.31,-0.01,-0.01,-0.02 | 14235 | 1.00 |
| 105.92–106.00 | 0.12 | descend / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.99→7.99 | 0.08→0.08 | 7.30→7.30 | +0.28,-0.03,+0.02,-0.01 | 14216 | 1.00 |
| 106.04–106.04 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.99→7.99 | 0.07→0.07 | 7.30→7.30 | +0.29,-0.01,+0.00,+0.00 | 14222 | 1.00 |
| 106.08–106.12 | 0.08 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.99→7.99 | 0.07→0.07 | 7.30→7.30 | +0.30,-0.02,-0.04,-0.01 | 14159 | 1.00 |
| 106.16–106.28 | 0.16 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.99→7.99 | 0.07→0.07 | 7.30→7.30 | +0.32,-0.05,+0.01,-0.01 | 14214 | 1.00 |
| 106.32–106.36 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.99→8.00 | 0.07→0.07 | 7.31→7.31 | +0.30,-0.01,+0.00,+0.00 | 14198 | 1.00 |
| 106.40–106.52 | 0.16 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.99→7.99 | 0.07→0.07 | 7.31→7.30 | +0.42,-0.04,+0.06,-0.01 | 14271 | 1.00 |
| 106.56–106.72 | 0.20 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.99→7.99 | 0.07→0.07 | 7.30→7.30 | +0.35,-0.01,+0.00,+0.00 | 14238 | 1.00 |
| 106.76–106.92 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.99→7.98 | 0.07→0.06 | 7.30→7.30 | +0.33,-0.03,+0.04,-0.01 | 14266 | 1.00 |
| 106.96–107.12 | 0.20 | descend / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.98→7.97 | 0.06→0.05 | 7.29→7.29 | +0.32,-0.01,+0.12,-0.01 | 14327 | 1.00 |
| 107.16–107.68 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.97→7.94 | 0.05→0.04 | 7.29→7.26 | +0.31,-0.01,+0.00,+0.00 | 14388 | 1.00 |
| 107.72–107.92 | 0.24 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 7.94→7.94 | 0.04→0.04 | 7.26→7.25 | +0.12,+0.01,+0.00,+0.04 | 14412 | 1.00 |
| 107.96–108.24 | 0.32 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.94→7.94 | 0.04→0.05 | 7.25→7.24 | +0.23,-0.03,+0.01,+0.00 | 14491 | 1.00 |
| 108.28–108.72 | 0.48 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.94→7.92 | 0.06→0.07 | 7.24→7.22 | +0.34,+0.01,+0.09,+0.00 | 14535 | 1.00 |
| 108.76–108.92 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.92→7.90 | 0.07→0.07 | 7.21→7.20 | +0.31,+0.01,+0.16,-0.00 | 14661 | 1.00 |
| 108.96–109.20 | 0.28 | descend / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.89→7.86 | 0.07→0.07 | 7.19→7.16 | +0.32,-0.00,+0.11,-0.00 | 14820 | 1.00 |
| 109.24–109.72 | 0.52 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.85→7.82 | 0.07→0.07 | 7.15→7.14 | +0.30,+0.00,+0.00,+0.00 | 14930 | 1.00 |
| 109.76–109.92 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.82→7.82 | 0.07→0.07 | 7.14→7.14 | +0.31,-0.06,+0.07,-0.02 | 14884 | 1.00 |
| 109.96–109.96 | 0.04 | descend / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.82→7.82 | 0.07→0.07 | 7.14→7.14 | +0.36,-0.05,+0.14,-0.02 | 14834 | 1.00 |
| 110.00–110.52 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.82→7.80 | 0.07→0.07 | 7.14→7.13 | +0.33,-0.00,+0.00,+0.00 | 14911 | 1.00 |
| 110.56–110.68 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.80→7.80 | 0.07→0.06 | 7.12→7.12 | +0.34,+0.02,+0.06,-0.01 | 14960 | 1.00 |
| 110.72–110.84 | 0.16 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.80→7.80 | 0.06→0.06 | 7.12→7.11 | +0.33,+0.01,+0.00,+0.00 | 15013 | 1.00 |
| 110.88–111.00 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.80→7.80 | 0.06→0.05 | 7.11→7.10 | +0.21,-0.02,-0.01,-0.01 | 15042 | 1.00 |
| 111.04–111.56 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.80→7.80 | 0.05→0.05 | 7.10→7.10 | +0.25,-0.01,-0.00,-0.00 | 15143 | 1.00 |
| 111.60–111.76 | 0.20 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 7.80→7.80 | 0.05→0.06 | 7.10→7.10 | +0.17,+0.01,+0.00,-0.00 | 15130 | 1.00 |
| 111.80–111.92 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.80→7.80 | 0.06→0.06 | 7.10→7.10 | +0.20,-0.00,-0.01,+0.00 | 15137 | 1.00 |
| 111.96–112.48 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.80→7.80 | 0.06→0.09 | 7.10→7.11 | +0.30,-0.01,-0.00,+0.00 | 15153 | 1.00 |
| 112.52–112.68 | 0.20 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 7.80→7.80 | 0.09→0.10 | 7.11→7.11 | +0.14,+0.00,+0.00,-0.03 | 14975 | 1.00 |
| 112.72–113.00 | 0.32 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.80→7.80 | 0.10→0.12 | 7.11→7.11 | +0.28,-0.03,+0.10,-0.01 | 15014 | 1.00 |
| 113.04–113.32 | 0.32 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.79→7.75 | 0.12→0.13 | 7.11→7.06 | +0.46,-0.00,+0.26,+0.00 | 15212 | 1.00 |
| 113.36–113.88 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26/target | 7.74→7.68 | 0.13→0.11 | 7.05→6.99 | +0.31,-0.00,+0.00,+0.00 | 15569 | 1.00 |
| 113.92–113.96 | 0.08 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26,27/target | 7.68→7.68 | 0.11→0.11 | 6.99→6.99 | +0.18,+0.00,+0.00,+0.03 | 15539 | 1.00 |
| 114.00–114.16 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.68→7.68 | 0.11→0.11 | 6.99→6.99 | +0.31,-0.06,+0.01,+0.00 | 15538 | 1.00 |
| 114.20–114.20 | 0.04 | descend / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.68→7.68 | 0.11→0.11 | 6.99→6.99 | +0.40,-0.08,+0.05,-0.01 | 15479 | 1.00 |
| 114.24–114.28 | 0.08 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.68→7.68 | 0.11→0.11 | 6.99→6.99 | +0.40,-0.06,+0.08,-0.01 | 15525 | 1.00 |
| 114.32–114.84 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 27,29/target | 7.68→7.67 | 0.11→0.09 | 6.99→6.98 | +0.31,-0.01,+0.00,+0.00 | 15570 | 1.00 |
| 114.88–115.48 | 0.64 | match / target_align | `identity_and_fresh_geometry_associated` | 27,29/target | 7.67→7.66 | 0.09→0.08 | 6.98→6.97 | +0.33,-0.03,-0.01,-0.01 | 15665 | 1.00 |
| 115.52–115.52 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 27/target | 7.66→7.66 | 0.08→0.08 | 6.97→6.97 | +0.30,-0.00,-0.08,+0.00 | 15620 | 1.00 |
| 115.56–115.68 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.67→7.67 | 0.08→0.07 | 6.97→6.98 | +0.40,-0.03,-0.08,+0.00 | 15636 | 1.00 |
| 115.72–115.88 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.67→7.69 | 0.07→0.06 | 6.98→6.99 | +0.29,-0.03,-0.07,+0.00 | 15633 | 1.00 |
| 115.92–116.20 | 0.32 | descend / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.69→7.71 | 0.06→0.05 | 7.00→7.02 | +0.26,-0.02,-0.06,+0.00 | 15526 | 1.00 |
| 116.24–116.76 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26,27/target | 7.72→7.73 | 0.05→0.05 | 7.03→7.05 | +0.32,+0.01,+0.00,+0.00 | 15443 | 1.00 |
| 116.80–116.92 | 0.16 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 27/target | 7.73→7.73 | 0.05→0.05 | 7.05→7.05 | +0.21,+0.00,-0.00,+0.03 | 15243 | 1.00 |
| 116.96–117.32 | 0.40 | match / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.73→7.72 | 0.05→0.05 | 7.04→7.03 | +0.28,-0.02,+0.04,-0.00 | 15339 | 1.00 |
| 117.36–117.88 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 27/target | 7.72→7.71 | 0.05→0.06 | 7.03→7.01 | +0.28,-0.01,+0.00,+0.00 | 15507 | 1.00 |
| 117.92–118.00 | 0.12 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 27/target | 7.71→7.71 | 0.06→0.06 | 7.01→7.01 | +0.19,+0.01,+0.00,+0.00 | 15480 | 1.00 |
| 118.04–118.44 | 0.44 | match / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 7.71→7.72 | 0.06→0.07 | 7.01→7.02 | +0.36,+0.02,-0.04,+0.00 | 15583 | 1.00 |
| 118.48–119.00 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26,27,29/target | 7.72→7.74 | 0.07→0.05 | 7.02→7.05 | +0.34,-0.00,-0.01,+0.00 | 15415 | 1.00 |
| 119.04–119.32 | 0.32 | match / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 7.74→7.74 | 0.05→0.04 | 7.05→7.05 | +0.31,-0.04,+0.02,-0.00 | 15261 | 1.00 |
| 119.36–119.88 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26,27/target | 7.74→7.73 | 0.04→0.02 | 7.06→7.05 | +0.33,-0.01,+0.00,+0.00 | 15275 | 1.00 |
| 119.92–119.92 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 7.73→7.73 | 0.02→0.02 | 7.05→7.05 | +0.20,+0.01,-0.00,+0.02 | 15239 | 1.00 |
| 119.96–120.08 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 7.73→7.73 | 0.02→0.02 | 7.05→7.04 | +0.31,-0.03,+0.04,-0.00 | 15302 | 1.00 |
| 120.12–120.64 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26,27/target | 7.73→7.72 | 0.01→0.01 | 7.04→7.03 | +0.31,-0.00,+0.00,+0.00 | 15348 | 1.00 |
| 120.68–120.80 | 0.16 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26/target | 7.72→7.72 | 0.01→0.01 | 7.03→7.03 | +0.16,+0.00,-0.00,+0.04 | 15373 | 1.00 |
| 120.84–120.88 | 0.08 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 7.72→7.72 | 0.01→0.01 | 7.02→7.02 | +0.16,+0.01,+0.00,+0.04 | 15439 | 1.00 |
| 120.92–121.00 | 0.12 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 27/none | 7.72→7.72 | 0.01→0.01 | 7.02→7.02 | +0.29,-0.02,+0.01,+0.00 | 15484 | 1.00 |
| 121.04–121.12 | 0.12 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 29/target | 7.72→7.72 | 0.01→0.01 | 7.02→7.03 | +0.35,-0.01,+0.06,-0.01 | 15416 | 1.00 |
| 121.16–121.28 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 27,29/target | 7.72→7.72 | 0.02→0.02 | 7.03→7.02 | +0.28,+0.02,+0.13,+0.00 | 15371 | 1.00 |
| 121.32–121.48 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.72→7.70 | 0.02→0.02 | 7.02→7.00 | +0.28,+0.01,+0.23,-0.01 | 15436 | 1.00 |
| 121.52–121.64 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 7.69→7.67 | 0.02→0.03 | 7.00→6.97 | +0.31,-0.01,+0.29,-0.00 | 15624 | 1.00 |
| 121.68–122.20 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26,27,29/target | 7.65→7.59 | 0.03→0.03 | 6.96→6.90 | +0.32,-0.02,+0.00,+0.00 | 15984 | 1.00 |
| 122.24–122.28 | 0.08 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26,29/target | 7.59→7.59 | 0.03→0.03 | 6.90→6.90 | +0.24,+0.01,+0.00,-0.03 | 15936 | 1.00 |
| 122.32–123.24 | 0.96 | match / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.59→7.48 | 0.03→0.04 | 6.90→6.80 | +0.30,-0.00,+0.14,-0.00 | 16380 | 1.00 |
| 123.28–123.44 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.47→7.45 | 0.04→0.04 | 6.79→6.77 | +0.31,-0.01,+0.16,-0.00 | 16504 | 1.00 |
| 123.48–123.68 | 0.24 | descend / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 7.44→7.41 | 0.04→0.04 | 6.76→6.72 | +0.30,-0.03,+0.24,-0.01 | 16761 | 1.00 |
| 123.72–124.24 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26,27,29/target | 7.40→7.35 | 0.04→0.03 | 6.71→6.65 | +0.31,-0.01,+0.00,+0.00 | 17201 | 1.00 |
| 124.28–124.40 | 0.16 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 26,27,29/target | 7.35→7.35 | 0.03→0.03 | 6.65→6.65 | +0.17,+0.01,+0.00,+0.04 | 17212 | 1.00 |
| 124.44–124.72 | 0.32 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 7.35→7.34 | 0.03→0.03 | 6.65→6.64 | +0.32,-0.01,+0.10,+0.01 | 17243 | 1.00 |
| 124.76–125.28 | 0.56 | match / target_align | `identity_and_fresh_geometry_associated` | 26,27,29/target | 7.34→7.28 | 0.04→0.04 | 6.64→6.59 | +0.28,+0.00,+0.06,+0.00 | 17463 | 1.00 |
| 125.32–125.44 | 0.16 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.28→7.28 | 0.04→0.04 | 6.59→6.59 | +0.23,-0.02,-0.07,-0.01 | 17487 | 1.00 |
| 125.48–126.00 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 27,29/target | 7.28→7.30 | 0.04→0.06 | 6.59→6.63 | +0.30,-0.00,-0.01,+0.00 | 17452 | 1.00 |
| 126.04–126.20 | 0.20 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 27/target | 7.30→7.31 | 0.06→0.07 | 6.63→6.62 | +0.14,+0.00,+0.00,+0.05 | 17241 | 1.00 |
| 126.24–126.36 | 0.16 | camera_axis_align / target_align | `identity_and_fresh_geometry_associated` | 27,29/target | 7.31→7.31 | 0.07→0.07 | 6.62→6.62 | +0.17,-0.05,+0.05,+0.04 | 17389 | 1.00 |
| 126.40–126.48 | 0.12 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.31→7.30 | 0.07→0.08 | 6.62→6.62 | +0.37,-0.09,+0.11,-0.02 | 17368 | 1.00 |
| 126.52–126.64 | 0.16 | match / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.30→7.29 | 0.08→0.09 | 6.62→6.60 | +0.49,-0.06,+0.08,-0.00 | 17379 | 1.00 |
| 126.68–126.84 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.29→7.28 | 0.09→0.09 | 6.60→6.58 | +0.40,-0.02,+0.07,-0.01 | 17468 | 1.00 |
| 126.88–126.92 | 0.08 | descend / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.27→7.27 | 0.09→0.09 | 6.58→6.57 | +0.33,-0.01,+0.13,-0.03 | 17531 | 1.00 |
| 126.96–127.16 | 0.24 | match / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.27→7.25 | 0.09→0.08 | 6.57→6.55 | +0.30,+0.01,+0.06,-0.00 | 17673 | 1.00 |
| 127.20–127.36 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 7.24→7.23 | 0.08→0.08 | 6.55→6.54 | +0.32,+0.02,+0.02,-0.01 | 17784 | 1.00 |
| 127.40–127.84 | 0.48 | descend / target_align | `identity_and_fresh_geometry_associated` | 26/target | 7.23→7.21 | 0.08→0.06 | 6.53→6.52 | +0.31,-0.00,+0.09,-0.01 | 17817 | 1.00 |
| 127.88–128.40 | 0.56 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 26,27/target | 7.21→7.18 | 0.06→0.05 | 6.51→6.50 | +0.31,-0.01,+0.00,+0.00 | 17937 | 1.00 |
| 128.44–128.44 | 0.04 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 27/target | 7.18→7.18 | 0.05→0.05 | 6.50→6.50 | +0.26,+0.00,+0.00,+0.02 | 17916 | 1.00 |
| 128.48–128.52 | 0.08 | match / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.19→7.19 | 0.05→0.05 | 6.50→6.50 | +0.29,-0.04,+0.00,-0.01 | 17913 | 1.00 |
| 128.56–128.56 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.19→7.19 | 0.05→0.05 | 6.50→6.50 | +0.24,-0.07,+0.03,-0.01 | 17915 | 1.00 |
| 128.60–128.60 | 0.04 | match / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.19→7.19 | 0.05→0.05 | 6.50→6.50 | +0.29,-0.04,+0.00,-0.01 | 17892 | 1.00 |
| 128.64–128.64 | 0.04 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.19→7.19 | 0.05→0.05 | 6.50→6.50 | +0.24,-0.04,+0.03,-0.01 | 17891 | 1.00 |
| 128.68–128.84 | 0.20 | match / target_align | `identity_and_fresh_geometry_associated` | 27,29/target | 7.19→7.19 | 0.05→0.04 | 6.50→6.50 | +0.30,-0.04,+0.03,-0.02 | 17923 | 1.00 |
| 128.88–129.04 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.19→7.18 | 0.04→0.04 | 6.50→6.50 | +0.32,-0.00,+0.08,-0.02 | 17912 | 1.00 |
| 129.08–129.36 | 0.32 | descend / target_align | `identity_and_fresh_geometry_associated` | 27/target | 7.18→7.16 | 0.04→0.04 | 6.49→6.47 | +0.40,-0.00,+0.04,-0.01 | 18040 | 1.00 |
| 129.40–129.44 | 0.08 | match / target_align | `identity_and_fresh_geometry_associated` | 29/target | 7.16→7.16 | 0.04→0.04 | 6.47→6.47 | +0.26,-0.01,+0.04,+0.00 | 18056 | 1.00 |
| 129.48–129.64 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 29/target | 7.16→7.15 | 0.03→0.03 | 6.47→6.46 | +0.23,-0.00,+0.12,-0.00 | 18193 | 1.00 |
| 129.68–131.08 | 1.44 | descend / target_align | `identity_and_fresh_geometry_associated` | 26,27,29/target | 7.15→6.86 | 0.03→0.03 | 6.45→6.17 | +0.28,-0.00,+0.21,-0.00 | 19864 | 1.00 |
| 131.12–131.12 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 27/target | 6.86→6.86 | 0.03→0.03 | 6.16→6.16 | +0.32,+0.00,+0.00,+0.00 | 19952 | 1.00 |
| 131.16–131.32 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 6.85→6.82 | 0.03→0.03 | 6.15→6.13 | +0.26,-0.01,+0.07,-0.01 | 20199 | 1.00 |
| 131.36–131.80 | 0.48 | descend / target_align | `identity_and_fresh_geometry_associated` | 27/target | 6.82→6.75 | 0.03→0.04 | 6.12→6.06 | +0.29,-0.03,+0.24,-0.01 | 20630 | 1.00 |
| 131.84–131.88 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 27/target | 6.73→6.72 | 0.04→0.04 | 6.05→6.04 | +0.28,+0.00,+0.00,+0.00 | 20807 | 1.00 |
| 131.92–132.08 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 26/target | 6.71→6.68 | 0.04→0.04 | 6.03→6.00 | +0.26,+0.01,+0.05,-0.00 | 20944 | 1.00 |
| 132.12–132.56 | 0.48 | descend / target_align | `identity_and_fresh_geometry_associated` | 26,27/target | 6.68→6.67 | 0.04→0.05 | 5.99→5.99 | +0.29,+0.01,-0.02,+0.00 | 21151 | 1.00 |
| 132.60–132.64 | 0.08 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 27/target | 6.67→6.67 | 0.05→0.05 | 5.99→5.99 | +0.32,-0.01,+0.00,+0.00 | 21104 | 1.00 |
| 132.68–132.84 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 6.67→6.67 | 0.05→0.05 | 5.99→5.99 | +0.36,-0.02,+0.07,+0.00 | 21073 | 1.00 |
| 132.88–132.88 | 0.04 | descend / target_align | `identity_and_fresh_geometry_associated` | 27/target | 6.67→6.67 | 0.05→0.05 | 5.99→5.99 | +0.38,-0.03,+0.14,-0.00 | 21158 | 1.00 |
| 132.92–132.92 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 27/target | 6.67→6.67 | 0.05→0.05 | 5.98→5.98 | +0.33,-0.01,+0.00,+0.00 | 21181 | 1.00 |
| 132.96–133.12 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 27/target | 6.67→6.66 | 0.05→0.05 | 5.98→5.97 | +0.33,-0.02,+0.07,+0.00 | 21200 | 1.00 |
| 133.16–159.64 | 26.52 | descend / target_align | `identity_and_fresh_geometry_associated` | 26,27,29,33+.../target | 6.66→1.10 | 0.05→0.01 | 5.96→0.42 | +0.30,-0.01,+0.21,-0.00 | 226848 | 1.00 |
| 159.68–160.44 | 0.80 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 43/target | 1.10→1.07 | 0.01→0.01 | 0.41→0.39 | +0.28,-0.02,+0.01,-0.00 | 216451 | 1.00 |
| 160.48–160.52 | 0.08 | descend / target_align | `identity_and_fresh_geometry_associated` | 43/target | 1.07→1.07 | 0.01→0.01 | 0.39→0.39 | +0.28,-0.00,+0.03,-0.00 | 215657 | 1.00 |
| 160.56–161.16 | 0.64 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 43/target | 1.07→1.08 | 0.01→0.01 | 0.39→0.39 | +0.29,+0.02,-0.00,-0.00 | 216534 | 1.00 |
| 161.20–161.64 | 0.48 | descend / target_align | `identity_and_fresh_geometry_associated` | 43/target | 1.08→1.06 | 0.01→0.00 | 0.39→0.38 | +0.30,-0.01,+0.08,-0.00 | 215145 | 1.00 |
| 161.68–161.88 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 43,47/target | 1.06→1.04 | 0.00→0.00 | 0.37→0.35 | +0.30,-0.02,-0.01,-0.00 | 213519 | 1.00 |
| 161.92–162.04 | 0.16 | descend / target_align | `identity_and_fresh_geometry_associated` | 47/target | 1.04→1.04 | 0.00→0.00 | 0.35→0.35 | +0.30,-0.02,+0.04,+0.00 | 213737 | 1.00 |
| 162.08–162.52 | 0.48 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 47/target | 1.04→1.04 | 0.00→0.00 | 0.35→0.34 | +0.30,+0.00,-0.01,-0.00 | 214313 | 1.00 |
| 162.56–162.92 | 0.40 | descend / target_align | `identity_and_fresh_geometry_associated` | 47/target | 1.04→1.04 | 0.00→0.00 | 0.34→0.34 | +0.30,+0.01,+0.09,+0.00 | 213059 | 1.00 |
| 162.96–163.28 | 0.36 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 47/target | 1.03→1.01 | 0.00→0.00 | 0.34→0.32 | +0.31,-0.01,+0.02,+0.00 | 213241 | 1.00 |
| 163.32–163.32 | 0.04 | descend / target_align | `identity_and_fresh_geometry_associated` | 47/target | 1.01→1.01 | 0.00→0.00 | 0.32→0.32 | +0.31,-0.02,+0.05,+0.00 | 212743 | 1.00 |
| 163.36–163.56 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 47/target | 1.01→1.00 | 0.01→0.01 | 0.32→0.32 | +0.30,-0.02,+0.02,-0.00 | 212800 | 1.00 |
| 163.60–165.36 | 1.80 | descend / target_align | `identity_and_fresh_geometry_associated` | 47,48/target | 1.00→0.86 | 0.01→0.01 | 0.32→0.16 | +0.30,-0.01,+0.08,-0.00 | 215042 | 1.00 |
| 165.40–165.60 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 48/target | 0.86→0.84 | 0.01→0.01 | 0.16→0.14 | +0.30,+0.01,-0.00,+0.00 | 206467 | 1.00 |
| 165.64–166.96 | 1.36 | descend / target_align | `identity_and_fresh_geometry_associated` | 48/target | 0.84→0.71 | 0.01→0.01 | 0.14→0.03 | +0.30,-0.02,+0.11,-0.00 | 206568 | 1.00 |
| 167.00–167.00 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 48/target | 0.71→0.71 | 0.01→0.01 | 0.02→0.02 | +0.30,-0.00,+0.11,+0.00 | 172168 | 1.00 |
| 167.04–170.80 | 3.80 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 48/target | 0.70→0.68 | 0.01→0.01 | 0.02→-0.00 | +0.30,-0.00,+0.31,+0.00 | 169372 | 1.00 |
| 170.84–170.84 | 0.04 | confirm / ground_hold | `own_estimator_not_airborne` | 48/target | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | +0.25,+0.00,+0.32,+0.00 | 149992 | 1.00 |
| 170.88–172.88 | 2.04 | disarmed / ground_hold | `own_estimator_not_airborne` | 48/target | 0.68→0.67 | 0.01→0.01 | -0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 150028 | 1.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 20.6 | `scan` | 8.53→8.46 | 52.19→58.59 | 6.70→6.30 | 0% |
| 20.6 | 0.1 | `inspect_candidate` | 8.46→8.46 | 58.60→58.63 | 6.30→6.31 | 0% |
| 20.8 | 8.7 | `inspect_candidate` | 8.47→8.47 | 58.64→51.13 | 6.31→6.40 | 78% |
| 29.5 | 7.7 | `inspect_candidate` | 8.47→8.44 | 51.06→38.03 | 6.39→6.90 | 0% |
| 37.2 | 5.2 | `target_inspect` | 8.44→8.44 | 37.96→29.16 | 6.91→7.06 | 100% |
| 42.4 | 4.7 | `target_inspect` | 8.44→8.43 | 29.09→21.13 | 7.07→7.35 | 100% |
| 47.1 | 9.2 | `target_inspect` | 8.43→8.38 | 21.06→5.34 | 7.35→7.59 | 100% |
| 56.3 | 1.6 | `target_align` | 8.38→8.36 | 5.27→2.79 | 7.59→7.60 | 100% |
| 58.0 | 8.2 | `target_align` | 8.37→8.42 | 2.73→0.70 | 7.60→7.72 | 100% |
| 66.2 | 17.2 | `target_align` | 8.42→8.11 | 0.70→0.16 | 7.72→7.41 | 100% |
| 83.4 | 1.0 | `target_inspect` | 8.11→8.12 | 0.16→0.26 | 7.41→7.42 | 100% |
| 84.4 | 7.3 | `target_align` | 8.12→8.01 | 0.27→0.42 | 7.42→7.32 | 100% |
| 91.6 | 38.0 | `target_align` | 8.01→7.15 | 0.42→0.03 | 7.32→6.46 | 99% |
| 129.7 | 3.5 | `target_align` | 7.15→6.66 | 0.03→0.05 | 6.45→5.97 | 100% |
| 133.2 | 26.5 | `target_align` | 6.66→1.10 | 0.05→0.01 | 5.96→0.42 | 100% |
| 159.7 | 3.9 | `target_align` | 1.10→1.00 | 0.01→0.01 | 0.41→0.32 | 100% |
| 163.6 | 2.0 | `target_align` | 1.00→0.84 | 0.01→0.01 | 0.32→0.14 | 100% |
| 165.6 | 1.4 | `target_align` | 0.84→0.71 | 0.01→0.01 | 0.14→0.02 | 100% |
| 167.0 | 3.8 | `target_align` | 0.70→0.68 | 0.01→0.01 | 0.02→-0.00 | 100% |
| 170.8 | 0.0 | `ground_hold` | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | 100% |
| 170.9 | 2.0 | `ground_hold` | 0.68→0.67 | 0.01→0.01 | -0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 8.53, tgt 0px)
- **t=20.64s** `inspect_candidate` — weak_extent_candidate_inspect_from_safe_standoff (sel 13/none, alt 8.46, tgt 0px)
- **t=20.76s** `inspect_candidate` — plausible_boat_inspect_unknown_design (sel 13/target, alt 8.47, tgt 112px)
- **t=28.64s** `reorient_candidate` — remembered_candidate_needs_fresh_visual_confirmation (sel 13/none, alt 8.47, tgt 100px)
- **t=28.68s** `inspect_candidate` — plausible_boat_inspect_unknown_design (sel 13/decoy_debris, alt 8.47, tgt 98px)
- **t=29.08s** `reorient_candidate` — remembered_candidate_needs_fresh_visual_confirmation (sel 13/none, alt 8.47, tgt 107px)
- **t=29.28s** `inspect_candidate` — plausible_boat_inspect_unknown_design (sel 13/decoy_debris, alt 8.47, tgt 106px)
- **t=30.72s** `reorient_candidate` — remembered_candidate_needs_fresh_visual_confirmation (sel 13/decoy_debris, alt 8.46, tgt 122px)
- **t=30.76s** `inspect_candidate` — plausible_boat_inspect_unknown_design (sel 13/decoy_debris, alt 8.46, tgt 125px)
- **t=37.20s** `target_inspect` — target_likely_evidence_requires_inspection (sel 18/target, alt 8.44, tgt 254px)
- **t=47.08s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.43, tgt 878px)
- **t=56.32s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.38, tgt 8365px)
- **t=60.60s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.39, tgt 12800px)
- **t=61.04s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.39, tgt 12808px)
- **t=61.48s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.39, tgt 12814px)
- **t=62.04s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.39, tgt 12925px)
- **t=62.20s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.39, tgt 12877px)
- **t=63.00s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.42, tgt 12686px)
- **t=63.56s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.43, tgt 12767px)
- **t=63.84s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.43, tgt 12761px)
- **t=64.44s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.41, tgt 12758px)
- **t=65.00s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.41, tgt 12766px)
- **t=65.08s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.41, tgt 12755px)
- **t=65.24s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 23/target, alt 8.42, tgt 12756px)
- **t=65.80s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.42, tgt 12627px)
- **t=66.04s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.42, tgt 12631px)
- **t=67.44s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.33, tgt 12921px)
- **t=67.48s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.33, tgt 12851px)
- **t=67.72s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.33, tgt 13068px)
- **t=68.12s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.35, tgt 13139px)
- **t=68.68s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.37, tgt 12910px)
- **t=69.24s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.37, tgt 12851px)
- **t=69.92s** `target_align` — identity_and_fresh_geometry_associated (sel 23/target, alt 8.37, tgt 12895px)
- **t=70.28s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.38, tgt 12822px)
- **t=70.32s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.38, tgt 12780px)
- **t=70.56s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.40, tgt 12818px)
- **t=71.12s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 25/target, alt 8.39, tgt 12855px)
- **t=71.36s** `target_align` — identity_and_fresh_geometry_associated (sel 25/target, alt 8.39, tgt 12875px)
- **t=71.84s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.38, tgt 12780px)
- **t=72.32s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.38, tgt 12713px)
- **t=72.64s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.37, tgt 12781px)
- **t=73.20s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.35, tgt 12845px)
- **t=73.24s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.35, tgt 12841px)
- **t=73.40s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 25/target, alt 8.35, tgt 12879px)
- **t=73.96s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 25/target, alt 8.35, tgt 12873px)
- **t=74.40s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.34, tgt 12951px)
- **t=75.20s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.32, tgt 12963px)
- **t=75.72s** `target_align` — identity_and_fresh_geometry_associated (sel 25/target, alt 8.29, tgt 13053px)
- **t=75.88s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 25/target, alt 8.29, tgt 13039px)
- **t=76.44s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.29, tgt 12961px)
- **t=76.56s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.29, tgt 12991px)
- **t=76.72s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.29, tgt 13020px)
- **t=77.28s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 8.30, tgt 13060px)
- **t=77.68s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.29, tgt 13149px)
- **t=78.12s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.29, tgt 13064px)
- **t=78.44s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.29, tgt 13114px)
- **t=78.52s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 8.29, tgt 13054px)
- **t=78.68s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.29, tgt 13071px)
- **t=78.80s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.28, tgt 13056px)
- **t=79.40s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.27, tgt 13214px)
- **t=79.52s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.26, tgt 13275px)
- **t=79.68s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.26, tgt 13318px)
- **t=79.72s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.26, tgt 13337px)
- **t=80.44s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.18, tgt 13618px)
- **t=80.60s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.14, tgt 13716px)
- **t=81.00s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.11, tgt 13792px)
- **t=81.04s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.10, tgt 13789px)
- **t=81.28s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.10, tgt 13770px)
- **t=81.84s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.11, tgt 13771px)
- **t=82.08s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 8.11, tgt 13847px)
- **t=82.60s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.12, tgt 13766px)
- **t=82.64s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.12, tgt 13740px)
- **t=82.84s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.12, tgt 13725px)
- **t=83.40s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.11, tgt 13734px)
- **t=84.36s** `target_align` — identity_and_fresh_geometry_associated (sel 25/target, alt 8.12, tgt 13970px)
- **t=85.36s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.02, tgt 14082px)
- **t=85.92s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 7.96, tgt 14419px)
- **t=86.40s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.97, tgt 14701px)
- **t=86.64s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.97, tgt 14495px)
- **t=86.72s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.97, tgt 14443px)
- **t=86.88s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.97, tgt 14420px)
- **t=87.44s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 7.98, tgt 14279px)
- **t=87.56s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.98, tgt 14249px)
- **t=88.12s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.95, tgt 14309px)
- **t=88.16s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.94, tgt 14344px)
- **t=88.36s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.93, tgt 14447px)
- **t=88.88s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.94, tgt 14432px)
- **t=89.04s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.94, tgt 14393px)
- **t=89.60s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 7.94, tgt 14484px)
- **t=89.72s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.94, tgt 14471px)
- **t=90.52s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.02, tgt 14131px)
- **t=90.60s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.02, tgt 14124px)
- **t=90.76s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.03, tgt 14076px)
- **t=91.32s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 8.02, tgt 14169px)
- **t=91.44s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.02, tgt 14146px)
- **t=92.80s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.91, tgt 14618px)
- **t=93.12s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.90, tgt 14686px)
- **t=93.28s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.90, tgt 14694px)
- **t=93.32s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.90, tgt 14661px)
- **t=93.68s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.91, tgt 14572px)
- **t=93.72s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.92, tgt 14517px)
- **t=94.16s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.94, tgt 14401px)
- **t=94.32s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.94, tgt 14366px)
- **t=94.48s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.94, tgt 14381px)
- **t=95.04s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 18/target, alt 7.95, tgt 14318px)
- **t=95.16s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.95, tgt 14359px)
- **t=95.92s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.96, tgt 14408px)
- **t=96.00s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 7.96, tgt 14444px)
- **t=96.40s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 7.93, tgt 14528px)
- **t=96.96s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 7.94, tgt 14401px)
- **t=97.20s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.94, tgt 14517px)
- **t=97.36s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.94, tgt 14534px)
- **t=97.48s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.94, tgt 14426px)
- **t=97.72s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.94, tgt 14415px)
- **t=97.88s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.95, tgt 14326px)
- **t=97.96s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.96, tgt 14320px)
- **t=98.20s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.98, tgt 14255px)
- **t=98.36s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.99, tgt 14197px)
- **t=98.64s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.99, tgt 14209px)
- **t=98.80s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.99, tgt 14227px)
- **t=98.92s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.99, tgt 14275px)
- **t=99.08s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.98, tgt 14308px)
- **t=99.24s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.98, tgt 14291px)
- **t=99.76s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.97, tgt 14387px)
- **t=100.32s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.98, tgt 14222px)
- **t=100.48s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.98, tgt 14246px)
- **t=100.52s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.98, tgt 14303px)
- **t=100.88s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 18/target, alt 8.01, tgt 14124px)
- **t=101.44s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 8.05, tgt 13903px)
- **t=101.64s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 8.04, tgt 14092px)
- **t=101.80s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.05, tgt 14160px)
- **t=102.36s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 8.06, tgt 14016px)
- **t=102.44s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 8.06, tgt 14034px)
- **t=103.00s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.06, tgt 13992px)
- **t=103.04s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 8.06, tgt 13934px)
- **t=103.20s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.05, tgt 14016px)
- **t=103.76s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 8.03, tgt 14033px)
- **t=104.08s** `target_align` — identity_and_fresh_geometry_associated (sel 18/target, alt 8.03, tgt 14181px)
- **t=104.48s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.04, tgt 14053px)
- **t=104.56s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 8.04, tgt 14052px)
- **t=105.04s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.04, tgt 14139px)
- **t=105.08s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 8.04, tgt 14107px)
- **t=105.40s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 8.00, tgt 14184px)
- **t=105.72s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.99, tgt 14235px)
- **t=106.04s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.99, tgt 14222px)
- **t=106.08s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.99, tgt 14141px)
- **t=106.32s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.99, tgt 14162px)
- **t=106.40s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.99, tgt 14209px)
- **t=106.56s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.99, tgt 14213px)
- **t=106.76s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.99, tgt 14244px)
- **t=107.16s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.97, tgt 14277px)
- **t=107.72s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 7.94, tgt 14374px)
- **t=107.96s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.94, tgt 14448px)
- **t=109.24s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.85, tgt 14840px)
- **t=109.76s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.82, tgt 14879px)
- **t=110.00s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.82, tgt 14843px)
- **t=110.56s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.80, tgt 14885px)
- **t=110.72s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.80, tgt 14897px)
- **t=110.88s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.80, tgt 14965px)
- **t=111.04s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.80, tgt 15009px)
- **t=111.60s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 7.80, tgt 15072px)
- **t=111.80s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.80, tgt 15103px)
- **t=111.96s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.80, tgt 15021px)
- **t=112.52s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 7.80, tgt 14964px)
- **t=112.72s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.80, tgt 14991px)
- **t=113.36s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.74, tgt 15245px)
- **t=113.92s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 7.68, tgt 15539px)
- **t=114.00s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 7.68, tgt 15538px)
- **t=114.32s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 7.68, tgt 15508px)
- **t=114.88s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 7.67, tgt 15510px)
- **t=115.52s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 7.66, tgt 15620px)
- **t=115.56s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 7.67, tgt 15563px)
- **t=116.24s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 7.72, tgt 15394px)
- **t=116.80s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 27/target, alt 7.73, tgt 15166px)
- **t=116.96s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 7.73, tgt 15266px)
- **t=117.36s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 7.72, tgt 15335px)
- **t=117.92s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 27/target, alt 7.71, tgt 15440px)
- **t=118.04s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 7.71, tgt 15583px)
- **t=118.48s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.72, tgt 15415px)
- **t=119.04s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 7.74, tgt 15192px)
- **t=119.36s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 7.74, tgt 15238px)
- **t=119.92s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 7.73, tgt 15239px)
- **t=119.96s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.73, tgt 15250px)
- **t=120.12s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 7.73, tgt 15287px)
- **t=120.68s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 26/target, alt 7.72, tgt 15335px)
- **t=120.84s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.72, tgt 15397px)
- **t=121.68s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.65, tgt 15626px)
- **t=122.24s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 29/target, alt 7.59, tgt 15936px)
- **t=122.32s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.59, tgt 15888px)
- **t=123.72s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 7.40, tgt 16880px)
- **t=124.28s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 29/target, alt 7.35, tgt 17212px)
- **t=124.44s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 7.35, tgt 17161px)
- **t=125.48s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 7.28, tgt 17452px)
- **t=126.04s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 27/target, alt 7.30, tgt 17189px)
- **t=126.24s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 7.31, tgt 17283px)
- **t=127.88s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 26/target, alt 7.21, tgt 17838px)
- **t=128.44s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 27/target, alt 7.18, tgt 17916px)
- **t=128.48s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 7.19, tgt 17899px)
- **t=131.12s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 6.86, tgt 19952px)
- **t=131.16s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 6.85, tgt 20000px)
- **t=131.84s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 6.73, tgt 20705px)
- **t=131.92s** `target_align` — identity_and_fresh_geometry_associated (sel 26/target, alt 6.71, tgt 20793px)
- **t=132.60s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 6.67, tgt 21104px)
- **t=132.68s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 6.67, tgt 20999px)
- **t=132.92s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 27/target, alt 6.67, tgt 21181px)
- **t=132.96s** `target_align` — identity_and_fresh_geometry_associated (sel 27/target, alt 6.67, tgt 21067px)
- **t=170.84s** `ground_hold` — own_estimator_not_airborne (sel 48/target, alt 0.68, tgt 149992px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–172.88s coverage 6.28 rad, inspected views 12, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- reject_candidate track=15 visually_observed_wrong_design
- survey_complete track=None 
- reject_candidate track=12 visually_observed_wrong_design
- preempt_candidate track=None 
- target_confirmed track=18 identity_evidence_acquired

## Recovery ledger

- visibility management (no altitude gain) t=42.4–56.28s (13.92s) alt [8.44, 8.38, 8.38, 8.44] range [29.09, 5.34, 5.34, 29.09]
- visibility management (no altitude gain) t=60.6–61.0s (0.44s) alt [8.39, 8.39, 8.39, 8.39] range [0.34, 0.28, 0.28, 0.34]
- visibility management (no altitude gain) t=61.48–62.16s (0.72s) alt [8.39, 8.39, 8.39, 8.39] range [0.29, 0.32, 0.29, 0.32]
- visibility management (no altitude gain) t=63.0–63.8s (0.84s) alt [8.42, 8.43, 8.42, 8.43] range [0.41, 0.35, 0.35, 0.41]
- visibility management (no altitude gain) t=64.44–65.04s (0.64s) alt [8.41, 8.41, 8.41, 8.41] range [0.44, 0.56, 0.44, 0.56]
- visibility management (no altitude gain) t=65.24–66.0s (0.8s) alt [8.42, 8.42, 8.42, 8.42] range [0.6, 0.68, 0.6, 0.68]
- visibility management (no altitude gain) t=67.72–68.08s (0.4s) alt [8.33, 8.35, 8.33, 8.35] range [0.76, 0.59, 0.59, 0.76]
- visibility management (no altitude gain) t=68.68–69.88s (1.24s) alt [8.37, 8.37, 8.37, 8.37] range [0.45, 0.5, 0.45, 0.5]
- visibility management (no altitude gain) t=70.56–71.32s (0.8s) alt [8.4, 8.39, 8.39, 8.4] range [0.61, 0.66, 0.61, 0.66]
- visibility management (no altitude gain) t=71.84–72.28s (0.48s) alt [8.38, 8.38, 8.38, 8.38] range [0.71, 0.79, 0.71, 0.79]
- visibility management (no altitude gain) t=72.64–73.2s (0.6s) alt [8.37, 8.35, 8.35, 8.37] range [0.82, 0.77, 0.77, 0.82]
- visibility management (no altitude gain) t=73.4–74.36s (1.0s) alt [8.35, 8.35, 8.35, 8.35] range [0.75, 0.73, 0.73, 0.75]
- visibility management (no altitude gain) t=75.2–75.68s (0.52s) alt [8.32, 8.29, 8.29, 8.32] range [0.81, 0.81, 0.81, 0.82]
- visibility management (no altitude gain) t=75.88–76.52s (0.68s) alt [8.29, 8.29, 8.29, 8.29] range [0.81, 0.8, 0.8, 0.81]
- visibility management (no altitude gain) t=76.72–77.24s (0.56s) alt [8.29, 8.3, 8.29, 8.3] range [0.79, 0.77, 0.77, 0.79]
- visibility management (no altitude gain) t=77.68–78.08s (0.44s) alt [8.29, 8.29, 8.29, 8.29] range [0.76, 0.73, 0.73, 0.76]
- visibility management (no altitude gain) t=78.68–78.76s (0.12s) alt [8.29, 8.28, 8.28, 8.29] range [0.67, 0.65, 0.65, 0.67]
- visibility management (no altitude gain) t=79.4–79.48s (0.12s) alt [8.27, 8.26, 8.26, 8.27] range [0.44, 0.41, 0.41, 0.44]
- visibility management (no altitude gain) t=80.44–80.56s (0.16s) alt [8.18, 8.15, 8.15, 8.18] range [0.23, 0.23, 0.23, 0.23]
- visibility management (no altitude gain) t=81.28–82.04s (0.8s) alt [8.1, 8.11, 8.1, 8.11] range [0.17, 0.15, 0.15, 0.17]
- visibility management (no altitude gain) t=82.84–84.32s (1.52s) alt [8.12, 8.12, 8.11, 8.12] range [0.18, 0.26, 0.16, 0.26]
- visibility management (no altitude gain) t=85.36–86.36s (1.04s) alt [8.02, 7.97, 7.96, 8.02] range [0.49, 0.36, 0.36, 0.49]
- visibility management (no altitude gain) t=86.88–87.52s (0.68s) alt [7.97, 7.98, 7.97, 7.98] range [0.4, 0.46, 0.4, 0.46]
- visibility management (no altitude gain) t=88.36–88.84s (0.52s) alt [7.93, 7.94, 7.93, 7.94] range [0.5, 0.5, 0.5, 0.5]
- visibility management (no altitude gain) t=89.04–89.68s (0.68s) alt [7.94, 7.94, 7.94, 7.94] range [0.49, 0.47, 0.47, 0.49]
- visibility management (no altitude gain) t=90.76–91.4s (0.68s) alt [8.03, 8.02, 8.02, 8.03] range [0.49, 0.44, 0.44, 0.49]
- visibility management (no altitude gain) t=92.8–93.08s (0.32s) alt [7.91, 7.91, 7.91, 7.91] range [0.29, 0.22, 0.22, 0.29]
- visibility management (no altitude gain) t=94.16–94.28s (0.16s) alt [7.94, 7.94, 7.94, 7.94] range [0.08, 0.08, 0.08, 0.08]
- visibility management (no altitude gain) t=94.48–95.12s (0.68s) alt [7.94, 7.95, 7.94, 7.95] range [0.06, 0.06, 0.05, 0.06]
- visibility management (no altitude gain) t=96.4–97.16s (0.8s) alt [7.93, 7.94, 7.93, 7.94] range [0.05, 0.05, 0.05, 0.05]
- visibility management (no altitude gain) t=97.36–97.44s (0.12s) alt [7.94, 7.94, 7.94, 7.94] range [0.06, 0.06, 0.06, 0.06]
- visibility management (no altitude gain) t=97.72–97.84s (0.16s) alt [7.94, 7.95, 7.94, 7.95] range [0.08, 0.09, 0.08, 0.09]
- visibility management (no altitude gain) t=98.36–98.6s (0.28s) alt [7.99, 7.99, 7.99, 7.99] range [0.09, 0.09, 0.09, 0.09]
- visibility management (no altitude gain) t=98.8–98.88s (0.12s) alt [7.99, 7.99, 7.99, 7.99] range [0.09, 0.09, 0.09, 0.09]
- visibility management (no altitude gain) t=99.08–99.2s (0.16s) alt [7.98, 7.98, 7.98, 7.98] range [0.09, 0.09, 0.09, 0.09]
- visibility management (no altitude gain) t=99.76–100.28s (0.56s) alt [7.97, 7.98, 7.97, 7.98] range [0.06, 0.05, 0.05, 0.06]
- visibility management (no altitude gain) t=100.88–101.6s (0.76s) alt [8.01, 8.05, 8.01, 8.05] range [0.04, 0.03, 0.03, 0.04]
- visibility management (no altitude gain) t=101.8–102.4s (0.64s) alt [8.05, 8.06, 8.05, 8.06] range [0.03, 0.06, 0.03, 0.06]
- visibility management (no altitude gain) t=103.2–104.04s (0.88s) alt [8.05, 8.03, 8.03, 8.05] range [0.07, 0.05, 0.05, 0.07]
- visibility management (no altitude gain) t=105.4–105.68s (0.32s) alt [8.0, 7.99, 7.99, 8.0] range [0.1, 0.08, 0.08, 0.1]
- visibility management (no altitude gain) t=106.56–106.72s (0.2s) alt [7.99, 7.99, 7.99, 7.99] range [0.07, 0.07, 0.07, 0.07]
- visibility management (no altitude gain) t=107.16–107.92s (0.8s) alt [7.97, 7.94, 7.94, 7.97] range [0.05, 0.04, 0.04, 0.05]
- visibility management (no altitude gain) t=109.24–109.72s (0.52s) alt [7.85, 7.82, 7.82, 7.85] range [0.07, 0.07, 0.07, 0.07]
- visibility management (no altitude gain) t=110.0–110.52s (0.56s) alt [7.82, 7.8, 7.8, 7.82] range [0.07, 0.07, 0.07, 0.07]
- visibility management (no altitude gain) t=110.72–110.84s (0.16s) alt [7.8, 7.8, 7.8, 7.8] range [0.06, 0.06, 0.06, 0.06]
- visibility management (no altitude gain) t=111.04–111.76s (0.76s) alt [7.8, 7.8, 7.8, 7.8] range [0.05, 0.06, 0.05, 0.06]
- visibility management (no altitude gain) t=111.96–112.68s (0.76s) alt [7.8, 7.8, 7.8, 7.8] range [0.06, 0.1, 0.06, 0.1]
- visibility management (no altitude gain) t=113.36–113.96s (0.64s) alt [7.74, 7.68, 7.68, 7.74] range [0.13, 0.11, 0.11, 0.13]
- visibility management (no altitude gain) t=114.32–114.84s (0.56s) alt [7.68, 7.67, 7.67, 7.68] range [0.11, 0.09, 0.09, 0.11]
- visibility management (no altitude gain) t=116.24–116.92s (0.72s) alt [7.72, 7.73, 7.72, 7.73] range [0.05, 0.05, 0.05, 0.05]
- visibility management (no altitude gain) t=117.36–118.0s (0.68s) alt [7.72, 7.71, 7.71, 7.72] range [0.05, 0.06, 0.05, 0.06]
- visibility management (no altitude gain) t=118.48–119.0s (0.56s) alt [7.72, 7.74, 7.72, 7.74] range [0.07, 0.05, 0.05, 0.07]
- visibility management (no altitude gain) t=119.36–119.92s (0.6s) alt [7.74, 7.73, 7.73, 7.74] range [0.04, 0.02, 0.02, 0.04]
- visibility management (no altitude gain) t=120.12–120.8s (0.72s) alt [7.73, 7.72, 7.72, 7.73] range [0.01, 0.01, 0.01, 0.01]
- visibility management (no altitude gain) t=121.68–122.28s (0.64s) alt [7.65, 7.59, 7.59, 7.65] range [0.03, 0.03, 0.03, 0.03]
- visibility management (no altitude gain) t=123.72–124.4s (0.72s) alt [7.4, 7.35, 7.35, 7.4] range [0.04, 0.03, 0.03, 0.04]
- visibility management (no altitude gain) t=125.48–126.2s (0.76s) alt [7.28, 7.31, 7.28, 7.31] range [0.04, 0.07, 0.04, 0.07]
- visibility management (no altitude gain) t=127.88–128.44s (0.6s) alt [7.21, 7.18, 7.18, 7.21] range [0.06, 0.05, 0.05, 0.06]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 57.0 | 8.42 | 4.18 | 7.62 | 1.78 | 0.7 | 9700 | True | 0.044 |
| 59.0 | 8.53 | 1.31 | 7.81 | 1.48 | 2.2 | 12286 | True | 0.032 |
| 61.0 | 8.39 | 0.28 | 7.69 | 0.34 | -1.0 | 12798 | False | 0.000 |
| 63.0 | 8.42 | 0.41 | 7.73 | 0.32 | -5.3 | 12686 | True | -0.048 |
| 65.0 | 8.41 | 0.56 | 7.71 | 0.13 | 16.3 | 12766 | False | 0.000 |
| 67.0 | 8.38 | 0.88 | 7.67 | 0.14 | 15.5 | 12767 | True | 0.140 |
| 69.0 | 8.37 | 0.45 | 7.68 | 0.29 | 3.7 | 12824 | False | 0.000 |
| 71.0 | 8.40 | 0.64 | 7.68 | 0.25 | 3.3 | 12807 | False | 0.000 |
| 73.0 | 8.35 | 0.79 | 7.65 | 0.43 | 3.5 | 12873 | False | 0.000 |
| 75.0 | 8.34 | 0.79 | 7.63 | 0.15 | 10.5 | 12897 | True | 0.124 |
| 77.0 | 8.30 | 0.78 | 7.58 | 0.34 | 4.4 | 13084 | False | 0.000 |
| 79.0 | 8.28 | 0.59 | 7.59 | 0.61 | 2.6 | 13168 | True | 0.063 |
| 81.0 | 8.11 | 0.19 | 7.41 | 0.38 | 13.7 | 13792 | True | 0.000 |
| 83.0 | 8.12 | 0.17 | 7.42 | 0.35 | 0.3 | 13761 | True | 0.000 |
| 85.0 | 8.08 | 0.44 | 7.39 | 0.11 | 35.5 | 13837 | True | 0.163 |
| 87.0 | 7.97 | 0.42 | 7.26 | 0.17 | 27.9 | 14402 | False | 0.000 |
| 89.0 | 7.94 | 0.49 | 7.23 | 0.30 | 8.5 | 14412 | True | 0.047 |
| 91.0 | 8.02 | 0.48 | 7.32 | 0.39 | 2.8 | 14130 | True | 0.000 |
| 93.0 | 7.91 | 0.24 | 7.20 | 0.54 | 1.3 | 14660 | False | 0.000 |
| 95.0 | 7.95 | 0.05 | 7.26 | 0.27 | 3.8 | 14326 | False | 0.000 |
| 97.0 | 7.94 | 0.05 | 7.25 | 0.30 | 22.1 | 14415 | False | 0.000 |
| 99.0 | 7.98 | 0.09 | 7.29 | 0.31 | -0.0 | 14218 | True | 0.023 |
| 101.0 | 8.03 | 0.04 | 7.35 | 0.32 | 12.2 | 14020 | True | 0.000 |
| 103.0 | 8.06 | 0.08 | 7.37 | 0.32 | -4.3 | 13992 | True | 0.000 |
| 105.0 | 8.04 | 0.12 | 7.34 | 0.33 | -4.5 | 14091 | True | 0.187 |
| 107.0 | 7.98 | 0.06 | 7.29 | 0.34 | 11.3 | 14219 | True | 0.101 |
| 109.0 | 7.89 | 0.07 | 7.18 | 0.30 | -13.5 | 14701 | True | 0.102 |
| 111.0 | 7.80 | 0.05 | 7.10 | 0.33 | 8.4 | 15018 | True | -0.047 |
| 113.0 | 7.80 | 0.12 | 7.11 | 0.21 | 106.0 | 15000 | True | 0.187 |
| 115.0 | 7.67 | 0.09 | 6.97 | 0.32 | 7.1 | 15563 | True | 0.047 |
| 117.0 | 7.73 | 0.05 | 7.04 | 0.31 | -10.2 | 15283 | True | 0.001 |
| 119.0 | 7.74 | 0.05 | 7.05 | 0.35 | -1.8 | 15270 | False | 0.000 |
| 121.0 | 7.72 | 0.01 | 7.02 | 0.26 | -65.2 | 15461 | True | 0.025 |
| 123.0 | 7.53 | 0.04 | 6.85 | 0.29 | 155.7 | 16105 | True | 0.177 |
| 125.0 | 7.31 | 0.04 | 6.61 | 0.30 | -27.8 | 17352 | True | 0.061 |
| 127.0 | 7.26 | 0.09 | 6.57 | 0.33 | -3.9 | 17570 | True | 0.097 |
| 129.0 | 7.18 | 0.04 | 6.50 | 0.30 | 23.1 | 17910 | True | 0.076 |
| 131.0 | 6.88 | 0.03 | 6.18 | 0.28 | -24.0 | 19821 | True | 0.228 |
| 133.0 | 6.67 | 0.05 | 5.98 | 0.31 | 56.3 | 21113 | True | 0.047 |
| 135.0 | 6.19 | 0.03 | 5.51 | 0.30 | 8.7 | 24801 | True | 0.270 |
| 137.0 | 5.76 | 0.01 | 5.06 | 0.29 | -123.5 | 29385 | True | 0.182 |
| 139.0 | 5.32 | 0.01 | 4.64 | 0.31 | 91.3 | 34868 | True | 0.197 |
| 141.0 | 4.95 | 0.02 | 4.25 | 0.30 | -131.8 | 41478 | True | 0.190 |
| 143.0 | 4.50 | 0.03 | 3.81 | 0.29 | 166.7 | 51595 | True | 0.188 |
| 145.0 | 4.05 | 0.02 | 3.36 | 0.30 | 149.0 | 62564 | True | 0.232 |
| 147.0 | 3.62 | 0.01 | 2.92 | 0.29 | -117.4 | 73943 | True | 0.187 |
| 149.0 | 3.17 | 0.00 | 2.48 | 0.29 | -29.8 | 87000 | True | 0.185 |
| 151.0 | 2.76 | 0.02 | 2.08 | 0.30 | 96.3 | 103527 | True | 0.246 |
| 153.0 | 2.31 | 0.02 | 1.61 | 0.30 | 51.3 | 131458 | True | 0.205 |
| 155.0 | 1.87 | 0.01 | 1.19 | 0.30 | 21.5 | 175412 | True | 0.225 |
| 157.0 | 1.44 | 0.00 | 0.76 | 0.30 | -30.5 | 225671 | True | 0.229 |
| 159.0 | 1.17 | 0.00 | 0.47 | 0.31 | -160.5 | 219220 | True | 0.101 |
| 161.0 | 1.08 | 0.01 | 0.39 | 0.29 | 134.2 | 214997 | True | 0.000 |
| 163.0 | 1.03 | 0.00 | 0.34 | 0.29 | -73.8 | 213115 | True | 0.000 |
| 165.0 | 0.89 | 0.01 | 0.19 | 0.29 | 37.9 | 203841 | True | 0.069 |
| 167.0 | 0.71 | 0.01 | 0.02 | 0.30 | -9.0 | 172168 | True | 0.112 |
| 169.0 | 0.69 | 0.01 | -0.00 | 0.30 | -66.7 | 150022 | True | 0.325 |
| 171.0 | 0.68 | 0.00 | -0.00 | 0.30 | -79.4 | 149973 | True | 0.000 |

## Contradictions between belief and observed truth

- minor `identity_head_flips_near_deck` frames 458 t=146.6–146.6s {"flips": 30, "rate_per_s": 1.64, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- minor `recovery_while_pad_visible` frames 956 t=42.4–132.92s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v61\E08_v61c\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v61\E08_v61c\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v61\E08_v61c\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `91584c99c2823deb9a9e469d227747f5c9f5637ce0fbac4cf0fab730ceb4ed51`
- `frames.csv` sha256 `f9a3d3847fc099ff3de1e0e7dafdedfdbe79d49f03de0eed4f2f6546cb1ceb01`
- `verdict.json` sha256 `b19ca783dbe03b5b2ddfd37b7a931ac1a85698efbe190323290c9b024dd8c346`
- `video_join.json` sha256 `886463fcec3a99b984d72447cd4209a5562d0b3c15c92bfbf47cfc905a7a3863`
- `review.mp4` sha256 `dbb661391346ee1961b943196efc5f44bd0882ef94bd592e729e289862a2f0f8`
