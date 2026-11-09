# Flight record — E06_v60 (E06)   **SILVER**

Scenario `windows_review_E06_search_near` kind=beach seed=3200000001 distance=8.0m height=6.0m boat_speed=0.3m/s

- frames **2203** over **88.08s**; outcome **landed**
- physical events: touchdown@102.56s, stable_contact@103.8s, unstable_contact@104.43s, stable_contact@106.53s, landed@108.21s
- first lock on the truth target at t=**17.48s**; selection on target afterwards **100.00%**
- hard failures: **none**; soft: physical.no_press_after_contact; criteria hard: E01.4_no_false_boat_claim_drives_selection, E01.10_no_spurious_recovery; criteria soft: E01.9_descent_permission_stable, E01.10b_parent_recovery_share_below_limit

Acceptance criteria that did not pass, with their own numbers:

- `E01.4_no_false_boat_claim_drives_selection` — {"frames": 3, "examples": [{"t": 20.679999999993864, "name": "none", "prob": 0.0032846692483872175, "wrong": 0.9529138207435608, "size": 86.79108428955078}, {"t": 20.71999999999377, "name": "none", "prob": 0.0032846692483872175, "wrong": 0.9529138207435608, "size": 86.79108428955078}, {"t": 20.759999999993678, "name": "none", "prob": 0.0032846692483872175, "wrong": 0.9529138207435608, "size": 86.79108428955078}]}
- `E01.10_no_spurious_recovery` — {"recovery_executed_frames": 179, "first_t": 57.32000000000424, "parent_recovery_frames": 373}
- `E01.9_descent_permission_stable` — {"reversals": 10, "limit": 3}
- `E01.10b_parent_recovery_share_below_limit` — {"share": 0.1693, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}

## Check table (recomputed from files, not from the episode's claims)

| check | ok | severity | numbers |
|---|---|---|---|
| `record.trace_present` | yes | hard | `{"step_rows": 2203, "frame_rows": 2203}` |
| `record.frame_indices_contiguous` | yes | hard | `{"first": 0, "last": 2202}` |
| `record.video_join_consistent` | yes | hard | `{"frames": 2203, "probes": 5, "max_mean_abs_diff": 2.387025462962963}` |
| `record.closed_cleanly` | yes | hard | `{"failure": null, "cleanup": []}` |
| `record.actor_inputs_observer_free` | yes | hard | `{"observation_keys": ["beacon", "decision_dt_s", "gimbal_rad", "gimbal_source", "image_age_s", "image_capture_time_s", "image_delivery_time_s", "image_valid", "mission", "previous_executed_action", "px4"], "forbidden": []}` |
| `physical.landed_on_target` | yes | hard | `{"outcome": "landed", "stop_reason": null, "strict": true, "final_height": 0.694, "final_clearance": -0.0}` |
| `physical.disarmed_after_landing` | yes | hard | `{"armed": false, "landed": true, "outcome": "landed"}` |
| `physical.no_commands_after_contact` | yes | hard | `{"contact_t": 88.08, "commanded": 0, "examples": []}` |
| `physical.disarms_promptly_at_contact` | yes | hard | `{"contact_t": 82.24, "disarm_t": 86.08, "delay_s": 3.84, "limit_s": 5.0}` |
| `physical.no_press_after_contact` | NO | soft | `{"frames": 96, "span_s": 3.8}` |
| `physical.no_collision` | yes | hard | `{"events": [["touchdown", 102.56], ["stable_contact", 103.8], ["unstable_contact", 104.43], ["stable_contact", 106.53], ["landed", 108.21]]}` |
| `authority.descent_only_on_confirmed_target` | yes | hard | `{"frames": 0, "examples": [], "note": "positive down = descend; only checked below 3 m clearance, with two frames of transition tolerance"}` |
| `authority.confirmed_object_is_truth_target` | yes | hard | `{"confirmed_frames": 1755, "wrong_frames": 0, "wrong_fraction": 0.0, "first_wrong": null, "names": [], "allowed_label_flicker": 0.1}` |
| `authority.selection_is_the_target_object` | yes | hard | `{"frames": 0, "names": [], "examples": []}` |
| `authority.selection_label_consistent` | yes | soft | `{"frames": 3, "longest_s": 0.08, "note": "truth label refresh, not a different physical object"}` |
| `authority.locked_on_target` | yes | hard | `{"lock_t": 17.48, "target_fraction": 1.0, "aliases": ["21", "24", "25", "28", "30", "32", "41", "44", "48", "49", "50", "51", "52", "56", "58", "62", "73", "75"]}` |
| `authority.selection_continuity` | yes | hard | `{"fraction": 1.0, "limit": 0.98, "frames_after": 1766, "frames_on_target": 1766}` |
| `authority.guards_engaged_with_enforcement` | yes | soft | `{"events": 15, "kinds": ["descent_without_fresh_geometry"], "note": "a guard event is legitimate only if the descent command was actually blocked; the frame-level check above verifies the block"}` |
| `opportunity.initial_survey_is_justified` | yes | hard | `{"initial_scan_s": 17.44, "situation": "E06", "scenario_requires_survey": true, "limit_s": 1.0}` |
| `opportunity.no_survey_after_target_visible` | yes | hard | `{"frames": 0, "span_s": 0.0}` |
| `opportunity.framing_kept_in_descent` | yes | hard | `{"descent_frames": 1198, "lost_frames": 0, "lost_fraction": 0.0, "limit": 0.15}` |
| `recovery.bounded` | yes | hard | `{"interruptions": 1, "visibility_management": 4, "longest_s": 7.2, "limit_s": 8.0, "detail": [{"frames": 180, "t0": 57.28, "t1": 64.44, "duration_s": 7.2, "height_m": [1.01, 3.42, 1.01, 3.42], "horiz_dist_m": [0.01, 0.06, 0.01, 0.06], "clearance_m": [0.32, 2.74, 0.32, 2.74], "speed_m_s": [0.29, 0...` |
| `purpose.target_outside_initial_view` | yes | hard | `{"first_frame_target_px": 0.0, "lock_t": 17.48}` |
| `purpose.contract_present` | yes | hard | `{"initial_target": "outside_camera", "distance_band": [5.0, 20.0], "fault": null, "mode": "expert"}` |
| `digest.matches_recording` | yes | soft | `{"digest_frames": 2203, "frames": 2203, "present": true}` |

## Phase ledger

One row per constant (phase, intent, reason, selection, recovery) run. Columns: duration, altitude start→end, range, clearance, mean command, target pixels, pad visibility.

| t0–t1 | s | phase / intent | why | sel | alt | range | clr | cmd (fwd,right,down,yaw) | tgt px | pad |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–17.44 | 17.48 | scan / scan | `complete_observed_360_before_inspection_pass` | -/ | 6.55→6.52 | 8.12→13.60 | 5.66→5.49 | -0.00,+0.00,-0.00,-0.34 | 2238 | 0.00 |
| 17.48–17.88 | 0.44 | target_inspect / target_inspect | `target_likely_evidence_requires_inspection` | 21/target | 6.52→6.52 | 13.61→13.73 | 5.49→5.46 | +0.05,-0.06,+0.00,-0.29 | 3177 | 0.99 |
| 17.92–20.64 | 2.76 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 21/target | 6.52→6.53 | 13.74→11.16 | 5.46→5.57 | +1.59,-0.20,-0.00,-0.09 | 3297 | 1.00 |
| 20.68–20.76 | 0.12 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 21/none | 6.53→6.53 | 11.09→10.94 | 5.57→5.57 | +1.72,+0.02,-0.00,-0.01 | 3465 | 0.00 |
| 20.80–24.64 | 3.88 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 21/target | 6.53→6.52 | 10.87→3.95 | 5.57→5.71 | +1.95,-0.03,-0.00,-0.01 | 14974 | 0.99 |
| 24.68–24.92 | 0.28 | target_inspect / target_inspect | `confirmed_boat_needs_fresh_pad_geometry` | 21/target | 6.52→6.52 | 3.89→3.51 | 5.72→5.73 | +1.52,-0.03,-0.00,-0.01 | 16300 | 1.00 |
| 24.96–26.44 | 1.52 | align / target_align | `identity_and_fresh_geometry_associated` | 21/target | 6.52→6.63 | 3.45→1.92 | 5.74→5.91 | +1.22,-0.08,-0.07,+0.01 | 19307 | 1.00 |
| 26.48–26.56 | 0.12 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 21/target | 6.64→6.64 | 1.88→1.79 | 5.91→5.91 | +1.62,-0.04,+0.00,+0.01 | 19571 | 1.00 |
| 26.60–28.12 | 1.56 | align / target_align | `identity_and_fresh_geometry_associated` | 21,24/target | 6.64→6.68 | 1.75→0.44 | 5.92→5.97 | +0.81,-0.04,-0.05,+0.01 | 21698 | 1.00 |
| 28.16–28.40 | 0.28 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 24,25/target | 6.68→6.72 | 0.43→0.36 | 5.97→6.02 | +0.28,-0.01,-0.12,+0.00 | 21196 | 1.00 |
| 28.44–29.20 | 0.80 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 21/target | 6.73→6.67 | 0.36→0.27 | 6.02→5.98 | +0.50,-0.00,+0.16,+0.00 | 21176 | 1.00 |
| 29.24–29.36 | 0.16 | align / target_align | `identity_and_fresh_geometry_associated` | 21/target | 6.66→6.63 | 0.27→0.25 | 5.97→5.94 | +0.41,-0.03,+0.16,+0.00 | 21426 | 1.00 |
| 29.40–29.60 | 0.24 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 21,24/target | 6.62→6.58 | 0.25→0.23 | 5.93→5.89 | +0.47,-0.02,+0.21,-0.00 | 21812 | 1.00 |
| 29.64–29.72 | 0.12 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 21,24/target | 6.57→6.55 | 0.23→0.22 | 5.88→5.87 | +0.36,-0.01,+0.00,+0.00 | 21972 | 1.00 |
| 29.76–30.64 | 0.92 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 21/target | 6.55→6.43 | 0.21→0.15 | 5.86→5.74 | +0.43,-0.00,+0.16,-0.00 | 22941 | 1.00 |
| 30.68–30.76 | 0.12 | match / target_align | `identity_and_fresh_geometry_associated` | 21/target | 6.42→6.40 | 0.14→0.14 | 5.73→5.71 | +0.39,-0.04,+0.19,+0.00 | 23240 | 1.00 |
| 30.80–31.76 | 1.00 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 21/target | 6.39→6.14 | 0.14→0.10 | 5.70→5.44 | +0.39,+0.01,+0.25,-0.00 | 25500 | 1.00 |
| 31.80–56.24 | 24.48 | descend / target_align | `identity_and_fresh_geometry_associated` | 21,25,28,30+.../target | 6.13→1.07 | 0.09→0.00 | 5.43→0.37 | +0.31,-0.01,+0.20,-0.00 | 226973 | 1.00 |
| 56.28–56.48 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 44/target | 1.06→1.05 | 0.00→0.00 | 0.37→0.35 | +0.28,-0.00,-0.02,-0.00 | 213554 | 1.00 |
| 56.52–57.00 | 0.52 | descend / target_align | `identity_and_fresh_geometry_associated` | 44,48/target | 1.05→1.04 | 0.00→0.00 | 0.35→0.34 | +0.29,-0.00,+0.09,-0.00 | 214473 | 1.00 |
| 57.04–57.24 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 48,49/target | 1.03→1.02 | 0.00→0.01 | 0.34→0.33 | +0.30,-0.00,+0.01,+0.00 | 213123 | 1.00 |
| 57.28–57.28 | 0.04 | local_recovery / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 49/target | 1.01→1.01 | 0.01→0.01 | 0.32→0.32 | +0.30,+0.00,+0.00,+0.00 | 212699 | 1.00 |
| 57.32–57.32 | 0.04 | recovery_climb / target_align | `identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geomet` | 49/target | 1.01→1.01 | 0.01→0.01 | 0.32→0.32 | +0.30,+0.00,-0.02,+0.00 | 212812 | 1.00 |
| 57.36–64.44 | 7.12 | recovery_climb / target_align | `identity_and_fresh_geometry_associated` | 49,50,51,56/target | 1.01→3.42 | 0.01→0.06 | 0.32→2.74 | +0.30,-0.00,-0.33,+0.00 | 226757 | 1.00 |
| 64.48–64.64 | 0.20 | visual_approach / target_align | `identity_and_fresh_geometry_associated` | 56/target | 3.42→3.43 | 0.06→0.06 | 2.74→2.75 | +0.25,-0.08,-0.01,-0.00 | 78735 | 1.00 |
| 64.68–76.68 | 12.04 | descend / target_align | `identity_and_fresh_geometry_associated` | 51,52,56,58+.../target | 3.43→1.05 | 0.06→0.01 | 2.75→0.37 | +0.29,-0.01,+0.19,-0.00 | 226914 | 1.00 |
| 76.72–76.92 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 62/target | 1.05→1.03 | 0.01→0.01 | 0.37→0.35 | +0.29,-0.01,+0.01,+0.00 | 213121 | 1.00 |
| 76.96–77.04 | 0.12 | descend / target_align | `identity_and_fresh_geometry_associated` | 62/target | 1.03→1.03 | 0.01→0.01 | 0.35→0.34 | +0.29,+0.00,+0.05,-0.00 | 213776 | 1.00 |
| 77.08–77.60 | 0.56 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 62,73/target | 1.03→1.02 | 0.01→0.01 | 0.34→0.34 | +0.30,+0.01,+0.00,+0.00 | 214289 | 1.00 |
| 77.64–78.36 | 0.76 | descend / target_align | `identity_and_fresh_geometry_associated` | 73/target | 1.02→0.99 | 0.01→0.01 | 0.34→0.29 | +0.28,-0.02,+0.07,-0.00 | 214297 | 1.00 |
| 78.40–78.84 | 0.48 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 73/target | 0.99→0.97 | 0.01→0.01 | 0.28→0.27 | +0.29,+0.01,-0.01,+0.00 | 211971 | 1.00 |
| 78.88–80.24 | 1.40 | descend / target_align | `identity_and_fresh_geometry_associated` | 73,75/target | 0.97→0.83 | 0.01→0.00 | 0.27→0.16 | +0.30,-0.01,+0.11,-0.00 | 212871 | 1.00 |
| 80.28–80.48 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 75/target | 0.83→0.81 | 0.00→0.00 | 0.15→0.13 | +0.29,+0.00,-0.01,-0.00 | 209530 | 1.00 |
| 80.52–81.16 | 0.68 | descend / target_align | `identity_and_fresh_geometry_associated` | 75/target | 0.81→0.78 | 0.00→0.00 | 0.13→0.09 | +0.29,-0.00,+0.07,+0.00 | 207611 | 1.00 |
| 81.20–81.40 | 0.24 | visibility_align / target_align | `identity_and_fresh_geometry_associated` | 75/target | 0.78→0.77 | 0.00→0.00 | 0.08→0.07 | +0.29,-0.01,-0.01,+0.00 | 195531 | 1.00 |
| 81.44–82.16 | 0.76 | descend / target_align | `identity_and_fresh_geometry_associated` | 75/target | 0.77→0.72 | 0.00→0.00 | 0.07→0.03 | +0.30,-0.00,+0.10,+0.00 | 190782 | 1.00 |
| 82.20–82.20 | 0.04 | touchdown / target_align | `identity_and_fresh_geometry_associated` | 75/target | 0.72→0.72 | 0.00→0.00 | 0.02→0.02 | +0.30,-0.01,+0.14,+0.00 | 172498 | 1.00 |
| 82.24–86.00 | 3.80 | touchdown_commit / target_align | `identity_and_fresh_geometry_associated` | 75/target | 0.71→0.68 | 0.00→0.01 | 0.02→-0.00 | +0.29,-0.01,+0.31,+0.00 | 169896 | 1.00 |
| 86.04–86.04 | 0.04 | confirm / ground_hold | `own_estimator_not_airborne` | 75/target | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | +0.24,+0.00,+0.32,+0.00 | 149585 | 1.00 |
| 86.08–88.08 | 2.04 | disarmed / ground_hold | `own_estimator_not_airborne` | 75/target | 0.68→0.69 | 0.01→0.01 | -0.00→-0.00 | +0.00,+0.00,+0.00,+0.00 | 149661 | 1.00 |

## Macro timeline (runs shorter than 0.75 s folded into their neighbour)

This is the story a reviewer would tell: how long the aircraft spent in each behaviour, how the altitude and range moved, and where the object was.

| t | s | behaviour | alt start→end | range start→end | clearance | on target |
|---|---|---|---|---|---|---|
| 0.0 | 17.5 | `scan` | 6.55→6.52 | 8.12→13.60 | 5.66→5.49 | 0% |
| 17.5 | 0.4 | `target_inspect` | 6.52→6.52 | 13.61→13.73 | 5.49→5.46 | 100% |
| 17.9 | 2.9 | `target_inspect` | 6.52→6.53 | 13.74→10.94 | 5.46→5.57 | 96% |
| 20.8 | 4.2 | `target_inspect` | 6.53→6.52 | 10.87→3.51 | 5.57→5.73 | 100% |
| 25.0 | 1.6 | `target_align` | 6.52→6.64 | 3.45→1.79 | 5.74→5.91 | 100% |
| 26.6 | 1.8 | `target_align` | 6.64→6.72 | 1.75→0.36 | 5.92→6.02 | 100% |
| 28.4 | 1.3 | `target_align` | 6.73→6.55 | 0.36→0.22 | 6.02→5.87 | 100% |
| 29.8 | 1.0 | `target_align` | 6.55→6.40 | 0.21→0.14 | 5.86→5.71 | 100% |
| 30.8 | 1.0 | `target_align` | 6.39→6.14 | 0.14→0.10 | 5.70→5.44 | 100% |
| 31.8 | 25.6 | `target_align` | 6.13→1.01 | 0.09→0.01 | 5.43→0.32 | 100% |
| 57.4 | 7.3 | `target_align` | 1.01→3.43 | 0.01→0.06 | 0.32→2.75 | 100% |
| 64.7 | 13.0 | `target_align` | 3.43→1.02 | 0.06→0.01 | 2.75→0.34 | 100% |
| 77.6 | 1.2 | `target_align` | 1.02→0.97 | 0.01→0.01 | 0.34→0.27 | 100% |
| 78.9 | 2.6 | `target_align` | 0.97→0.77 | 0.01→0.00 | 0.27→0.07 | 100% |
| 81.4 | 0.8 | `target_align` | 0.77→0.72 | 0.00→0.00 | 0.07→0.02 | 100% |
| 82.2 | 3.8 | `target_align` | 0.71→0.68 | 0.00→0.01 | 0.02→-0.00 | 100% |
| 86.0 | 0.0 | `ground_hold` | 0.68→0.68 | 0.01→0.01 | -0.00→-0.00 | 100% |
| 86.1 | 2.0 | `ground_hold` | 0.68→0.69 | 0.01→0.01 | -0.00→-0.00 | 100% |

## Intent changes (what the actor decided, and the reason it wrote down)

- **t=0.00s** `scan` — complete_observed_360_before_inspection_pass (sel /, alt 6.55, tgt 0px)
- **t=17.48s** `target_inspect` — target_likely_evidence_requires_inspection (sel 21/target, alt 6.52, tgt 2749px)
- **t=17.92s** `target_inspect` — confirmed_boat_needs_fresh_pad_geometry (sel 21/target, alt 6.52, tgt 2174px)
- **t=24.96s** `target_align` — identity_and_fresh_geometry_associated (sel 21/target, alt 6.52, tgt 16488px)
- **t=26.48s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 21/target, alt 6.64, tgt 19376px)
- **t=26.60s** `target_align` — identity_and_fresh_geometry_associated (sel 21/target, alt 6.64, tgt 19683px)
- **t=28.16s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 24/target, alt 6.68, tgt 21120px)
- **t=28.44s** `target_align` — identity_and_fresh_geometry_associated (sel 21/target, alt 6.73, tgt 20743px)
- **t=29.64s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 24/target, alt 6.57, tgt 21842px)
- **t=29.76s** `target_align` — identity_and_fresh_geometry_associated (sel 21/target, alt 6.55, tgt 21950px)
- **t=57.28s** `target_align` — identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry (sel 49/target, alt 1.01, tgt 212699px)
- **t=57.36s** `target_align` — identity_and_fresh_geometry_associated (sel 49/target, alt 1.01, tgt 212863px)
- **t=86.04s** `ground_hold` — own_estimator_not_airborne (sel 75/target, alt 0.68, tgt 149585px)

## Survey / inspection ledger

- survey epoch 1 t=0.00–88.08s coverage 5.06 rad, inspected views 2, exhausted=False

Candidate events recorded by the actor:
- new_survey track=None no_plausible_visible_candidate
- reject_candidate track=5 visually_observed_wrong_design
- reject_candidate track=18 visually_observed_wrong_design
- survey_interrupted track=None 
- target_confirmed track=21 identity_evidence_acquired

## Recovery ledger

- **climb recovery** t=57.28–64.44s (7.2s, climb 2.41m) alt [1.01, 3.42, 1.01, 3.42] range [0.01, 0.06, 0.01, 0.06] phases ['local_recovery', 'recovery_climb']
- visibility management (no altitude gain) t=17.48–24.64s (7.2s) alt [6.52, 6.52, 6.52, 6.53] range [13.61, 3.95, 3.95, 13.82]
- visibility management (no altitude gain) t=26.48–26.56s (0.12s) alt [6.64, 6.64, 6.64, 6.64] range [1.88, 1.79, 1.79, 1.88]
- visibility management (no altitude gain) t=28.16–28.4s (0.28s) alt [6.68, 6.72, 6.68, 6.72] range [0.43, 0.36, 0.36, 0.43]
- visibility management (no altitude gain) t=29.64–29.72s (0.12s) alt [6.57, 6.55, 6.55, 6.57] range [0.23, 0.22, 0.22, 0.23]
- triggers seen: ['far_existing_visibility_aware_acquisition', 'metric_gap', 'visibility_margin_expiring']

## Descent profile (every 2 s while descending)

| t | alt | range | clearance | speed | bearing err | target px | metric | cmd down |
|---|---|---|---|---|---|---|---|---|
| 26.6 | 6.64 | 1.70 | 5.92 | 1.42 | 0.8 | 19841 | True | 0.047 |
| 28.7 | 6.75 | 0.33 | 6.05 | 0.37 | -8.0 | 20581 | True | 0.118 |
| 30.7 | 6.41 | 0.14 | 5.72 | 0.35 | -4.4 | 23150 | True | 0.187 |
| 32.8 | 5.93 | 0.09 | 5.25 | 0.29 | -24.3 | 27358 | True | 0.200 |
| 34.8 | 5.50 | 0.06 | 4.81 | 0.29 | -45.6 | 32521 | True | 0.248 |
| 36.8 | 5.02 | 0.03 | 4.33 | 0.31 | -56.7 | 39970 | True | 0.188 |
| 38.9 | 4.62 | 0.02 | 3.94 | 0.30 | -81.0 | 48209 | True | 0.232 |
| 40.9 | 4.17 | 0.02 | 3.47 | 0.29 | 174.4 | 60058 | True | 0.236 |
| 43.0 | 3.72 | 0.01 | 3.03 | 0.28 | -112.0 | 71005 | True | 0.217 |
| 45.0 | 3.29 | 0.00 | 2.60 | 0.29 | 129.6 | 82911 | True | 0.220 |
| 47.0 | 2.83 | 0.01 | 2.13 | 0.30 | -16.9 | 100878 | True | 0.212 |
| 49.0 | 2.39 | 0.02 | 1.71 | 0.29 | 91.8 | 124562 | True | 0.221 |
| 51.0 | 1.98 | 0.01 | 1.29 | 0.30 | 128.5 | 162343 | True | 0.229 |
| 53.0 | 1.52 | 0.00 | 0.83 | 0.30 | -100.3 | 226470 | True | 0.212 |
| 55.0 | 1.18 | 0.01 | 0.50 | 0.29 | 118.2 | 220408 | True | 0.114 |
| 57.0 | 1.04 | 0.00 | 0.34 | 0.29 | -102.3 | 212176 | True | 0.112 |
| 59.0 | 1.49 | 0.01 | 0.80 | 0.30 | 47.7 | 226317 | True | -0.400 |
| 61.0 | 2.33 | 0.03 | 1.64 | 0.30 | 130.2 | 129489 | True | -0.400 |
| 63.0 | 3.13 | 0.04 | 2.44 | 0.30 | -80.5 | 88775 | True | -0.303 |
| 65.0 | 3.42 | 0.05 | 2.73 | 0.29 | 173.2 | 78821 | True | 0.201 |
| 67.0 | 2.97 | 0.01 | 2.29 | 0.29 | -77.6 | 94164 | True | 0.256 |
| 69.0 | 2.50 | 0.00 | 1.80 | 0.29 | 53.7 | 118408 | True | 0.207 |
| 71.0 | 2.06 | 0.01 | 1.39 | 0.29 | 147.4 | 151823 | True | 0.234 |
| 73.0 | 1.62 | 0.01 | 0.93 | 0.29 | 165.2 | 219589 | True | 0.213 |
| 75.0 | 1.22 | 0.01 | 0.53 | 0.29 | -173.8 | 221556 | True | 0.096 |
| 77.0 | 1.03 | 0.01 | 0.35 | 0.30 | -6.4 | 212766 | True | 0.029 |
| 79.0 | 0.97 | 0.01 | 0.28 | 0.29 | 127.7 | 211345 | True | 0.078 |
| 81.0 | 0.80 | 0.00 | 0.11 | 0.29 | 86.8 | 202600 | True | 0.076 |
| 83.0 | 0.68 | 0.01 | -0.00 | 0.30 | -52.9 | 149871 | True | 0.311 |
| 85.0 | 0.69 | 0.01 | -0.00 | 0.29 | -42.2 | 149611 | True | 0.314 |
| 87.0 | 0.68 | 0.01 | -0.00 | 0.30 | -41.3 | 149551 | True | 0.000 |

## Contradictions between belief and observed truth

- minor `identity_head_flips_near_deck` frames 921 t=43.08–43.08s {"flips": 65, "rate_per_s": 1.76, "note": "3-class head instability, target-confidence only; identity_support stayed usable"}
- minor `recovery_while_pad_visible` frames 287 t=17.48–64.44s {}

## What this record cannot settle

- Whether two sighting episodes are the *same physical hull*: the record proves object class and pixel geometry per frame, not re-identification across occlusion. Use the alias set and `capture_annotations.jsonl` identity ids for that.
- Appearance-level confusion between similar grey hulls; the numeric side shows probability margins, but only the video shows the actual pixels. Spot-check the annotated clip at the timestamps of any contradiction above.
- Anything about the world outside the rendered frustum (a boat that was never in view).

Video: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E06_v60\review.mp4`  Annotated: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E06_v60\analysis_v1\review_annotated.mp4`  Sheets: `D:\Dokumente\CODE_PROJEKTE\SMARTSYSTEMS\schiebel-drone-landing\artifacts\local_curriculum_20261020\review_v60\E06_v60\analysis_v1\sheets`

## Provenance

- `steps.jsonl` sha256 `fc262bdee38fe4acf22cc4cc53cfbaab7ff72868fe880ddba860659c66685036`
- `frames.csv` sha256 `a2ed36b5311a479fb612994d89aa0491b84afe8bfbc81c94a97d9ba95ffa7611`
- `verdict.json` sha256 `848838e5446a68f53c56b15a995c4279ec3975506190f65905848b0bfbc8d8d4`
- `video_join.json` sha256 `079b5c61ba3767dc5a7074c870accb724b3c52d95ab65a6f93f853ff5ad03746`
- `review.mp4` sha256 `d86201c817552d2c093b9aaa9b0c1632a7a0c73e6e9380ef69cb9fb8fb53ae6a`
