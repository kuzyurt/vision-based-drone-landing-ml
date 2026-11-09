# Flight narrative — E01_nominal_cpu_v3

Scenario `windows_review_E01_nominal` kind=beach seed=3200000000 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=visible fault=None mode=expert
Frames 1882, task duration 75.24s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.20 | 0–5 | scan | complete_observed_360_without_chasing_selected_memory | none | 5929 | +0° | 6.5 | 8.2 | no | 20px |
| 0.24–1.92 | 6–48 | scan | complete_observed_360_without_chasing_selected_memory | none | 5982 | -0° | 6.5 | 8.2 | no | 43px |
| 1.96–3.20 | 49–80 | scan | complete_observed_360_without_chasing_selected_memory | none | 1143 | -22° | 6.5 | 8.3 | no | 250px |
| 3.24–17.36 | 81–434 | scan | complete_observed_360_without_chasing_selected_memory | none | 0 | -47° | 6.5 | 8.7 | no | — |
| 17.40–18.32 | 435–458 | scan | complete_observed_360_without_chasing_selected_memory | none | 1565 | +33° | 6.4 | 13.6 | no | 322px |
| 18.36–18.56 | 459–464 | scan | complete_observed_360_without_chasing_selected_memory | none | 2265 | +14° | 6.4 | 13.9 | no | 140px |
| 18.60–18.60 | 465–465 | reorient_candidate | full_survey_complete_investigate_retained_visual_candidate | track1(decoy_buoy) | 2129 | +9° | 6.4 | 14.0 | no | 99px |
| 18.64–24.64 | 466–616 | inspect_candidate | plausible_unknown_inspect_without_identity_gate | track1(decoy_buoy) | 2127 | +9° | 6.4 | 14.0 | no | 97px |
| 24.68–26.16 | 617–654 | target_inspect | recognizable_boat_needs_fresh_pad_geometry | track14(target) | 6527 | +29° | 6.4 | 9.4 | no | 254px |
| 26.20–26.72 | 655–668 | reorient_candidate | remembered_candidate_needs_fresh_visual_confirmation | track1(none) | 7443 | +6° | 6.4 | 7.7 | no | 82px |
| 26.76–26.84 | 669–671 | target_inspect | recognizable_boat_needs_fresh_pad_geometry | track1(decoy_buoy) | 8702 | +23° | 6.4 | 7.5 | no | 186px |
| 26.88–27.88 | 672–697 | target_inspect | recognizable_boat_needs_fresh_pad_geometry | track14(target) | 9249 | +27° | 6.4 | 7.5 | no | 220px |
| 27.92–29.20 | 698–730 | target_inspect | recognizable_boat_needs_fresh_pad_geometry | track2(target) | 7472 | +1° | 6.4 | 7.6 | no | 80px |
| 29.24–29.84 | 731–746 | reorient_candidate | remembered_candidate_needs_fresh_visual_confirmation | track1(none) | 9550 | -3° | 6.4 | 6.2 | no | 29px |
| 29.88–30.12 | 747–753 | target_inspect | recognizable_boat_needs_fresh_pad_geometry | track1(decoy_buoy) | 13213 | +22° | 6.4 | 5.1 | no | 150px |
| 30.16–31.36 | 754–784 | target_align | identity_and_geometry_confirmed | track1(decoy_buoy) | 15762 | +34° | 6.4 | 4.8 | yes | 207px |
| 31.40–39.72 | 785–993 | target_align | identity_and_geometry_confirmed | track1(none) | 19401 | +46° | 6.5 | 3.7 | yes | 224px |
| 39.76–39.76 | 994–994 | inspect_candidate | nearest_estimated_plausible_unrejected_candidate | track16(target) | 25920 | +18° | 6.1 | 0.0 | no | 0px |
| 39.80–41.28 | 995–1032 | target_align | identity_and_geometry_confirmed | track16(target) | 26004 | +13° | 6.1 | 0.0 | yes | 1px |
| 41.32–41.32 | 1033–1033 | inspect_candidate | nearest_estimated_plausible_unrejected_candidate | track14(target) | 29025 | +10° | 5.8 | 0.0 | no | 3px |
| 41.36–41.84 | 1034–1046 | target_align | identity_and_geometry_confirmed | track14(target) | 29069 | +2° | 5.8 | 0.0 | yes | 5px |
| 41.88–41.88 | 1047–1047 | inspect_candidate | nearest_estimated_plausible_unrejected_candidate | track16(target) | 29955 | -21° | 5.7 | 0.1 | no | 4px |
| 41.92–65.08 | 1048–1627 | target_align | identity_and_geometry_confirmed | track16(target) | 30017 | -24° | 5.7 | 0.1 | yes | 3px |
| 65.12–65.12 | 1628–1628 | clearance_hold | search_climb_not_authorized | track16(target) | 213042 | +82° | 1.0 | 0.0 | no | 0px |
| 65.16–65.72 | 1629–1643 | target_align | identity_and_geometry_confirmed | track16(target) | 213429 | +77° | 1.0 | 0.0 | yes | 0px |
| 65.76–65.76 | 1644–1644 | clearance_hold | search_climb_not_authorized | track16(target) | 213141 | +71° | 1.0 | 0.0 | no | 0px |
| 65.80–68.04 | 1645–1701 | target_align | identity_and_geometry_confirmed | track16(target) | 212835 | +67° | 1.0 | 0.0 | yes | 0px |
| 68.08–68.08 | 1702–1702 | clearance_hold | search_climb_not_authorized | track16(target) | 198326 | +48° | 0.8 | 0.0 | no | 0px |
| 68.12–68.12 | 1703–1703 | target_align | identity_and_geometry_confirmed | track16(target) | 197423 | +71° | 0.8 | 0.0 | yes | 0px |
| 68.16–68.16 | 1704–1704 | clearance_hold | search_climb_not_authorized | track16(target) | 196488 | +77° | 0.8 | 0.0 | no | 0px |
| 68.20–69.16 | 1705–1729 | target_align | identity_and_geometry_confirmed | track16(target) | 195836 | +75° | 0.8 | 0.0 | yes | 0px |
| 69.20–73.16 | 1730–1829 | target_contact_confirmation | preserve_existing_bounded_visual_touchdown_commit | track16(target) | 168930 | +39° | 0.7 | 0.0 | yes | 0px |
| 73.20–75.20 | 1830–1880 | ground_hold | own_estimator_not_airborne | track16(target) | 149999 | -101° | 0.7 | 0.0 | no | 0px |
| 75.24–75.24 | 1881–1881 | ground_hold | own_estimator_not_airborne | track16(target) | 149953 | -65° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

A usable target was visible while a different object was being pursued:
- 18.60–24.64s: selected track1(decoy_buoy) while target had 2129 px of visible structure; selected object 17 px, target_probability 0.0000, wrong_object_probability 0.435.
- 26.20–26.84s: selected track1(none) while target had 7443 px of visible structure; selected object 30 px, target_probability 0.0004, wrong_object_probability 0.138.
- 29.24–39.72s: selected track1(none) while target had 9550 px of visible structure; selected object 33 px, target_probability 0.0017, wrong_object_probability 0.845.

Camera survey continued although a usable target was in view:
- 0.00–1.92s scanning with 5929 px of target structure visible.
- 17.40–18.56s scanning with 1565 px of target structure visible.

## Observer-truth visibility arcs

- target visible 0.00–2.64s (2.6s), peak 6321 px, identity support 1.00
- target visible 17.28–75.24s (58.0s), peak 226889 px, identity support 1.00

## Verdict

- FAIL **E01.2_initial_opportunity_used** — {"first_usable_t": 0.0, "first_usable_px": 5929, "first_target_select_t": 24.679999999985252, "first_target_approach_t": 24.679999999985252, "delay_s": 24.679999999985252, "limit_s": 1.0}
- FAIL **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 79, "scan_span_s": 18.559999999999516, "limit_s": 1.0, "window": [0.0, 18.559999999999516]}
- FAIL **E01.4_no_non_target_outranks_visible_target** — {"frames": 432, "worst_span_s": 10.479999999975579, "limit_s": 0.5, "spans": [{"t0": 18.599999999999422, "t1": 24.639999999985346, "selected": "decoy_buoy", "selected_boat": true, "target_prob": 2.1223795556579717e-06, "target_px": 2129, "selected_size_px": 16.509830474853516}, {"t0": 26.19999999998171, "t1": 26.83999999998022, "selected": "none", "selected_boat": true, "target_prob": 0.0004317515704315156, "target_px": 7443, "selected_size_px": 30.360881805419922}, {"t0": 29.239999999974625, "t1": 39.719999999950204, "selected": "none", "selected_boat": true, "target_prob": 0.001727998605929315, "target_px": 9550, "selected_size_px": 33.08401107788086}]}
- FAIL **E01.4_selection_continuity_after_lock** — {"frames_after": 1265, "frames_on_target": 985, "fraction": 0.7787, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 432, "examples": [{"t": 18.599999999999422, "name": "decoy_buoy", "prob": 2.1223795556579717e-06, "wrong": 0.43496525287628174, "size": 16.509830474853516}, {"t": 18.63999999999933, "name": "decoy_buoy", "prob": 9.266288998333039e-07, "wrong": 0.2798871397972107, "size": 15.423388481140137}, {"t": 18.679999999999236, "name": "decoy_buoy", "prob": 5.066002017883875e-07, "wrong": 0.1590837836265564, "size": 12.683736801147461}, {"t": 18.719999999999143, "name": "decoy_buoy", "prob": 4.127552983845817e-06, "wrong": 0.6368761658668518, "size": 18.720417022705078}, {"t": 18.75999999999905, "name": "decoy_buoy", "prob": 4.098456429346697e-06, "wrong": 0.6896466612815857, "size": 18.86870002746582}]}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 1069, "lost_frames": 87, "good_frames": 969, "lost_fraction": 0.0814, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 30.15999999997248, "metric_confirmed_at_start": true, "descent_span_s": 43.00000000010668}
- PASS **E01.9_no_chatter** — {"intent_changes": 24, "span_s": 75.24, "per_10s": 3.19, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 16, "limit": 3}
- FAIL **E01.9_no_unnecessary_hold** — {"worst_hold_s": 18.519999999999325, "limit_s": 6.0, "holds": [{"t0": 0.08000000000009777, "t1": 18.599999999999422, "phase": "scan"}]}
- FAIL **E01.10_no_spurious_recovery** — {"recovery_frames": 370, "first_t": 0.2400000000002933, "metric_loss_frames": 370}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.002657240405682826, "final_t": 75.2400000000891, "touchdown_s": 89.30500000006236}
- PASS **integrity.observer_join** — {"frames": 1882, "joined_frames": 1882}

Behavioural acceptance: **False** (8 failing checks).