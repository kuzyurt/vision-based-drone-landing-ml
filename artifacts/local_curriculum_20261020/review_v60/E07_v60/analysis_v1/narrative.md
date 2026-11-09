# Flight narrative — E07_v60

Scenario `windows_review_E07_search_mid` kind=beach seed=3200000002 distance=28.0m height=6.0m boat_speed=0.3m/s initial_target=outside_camera fault=None mode=expert
Frames 1931, task duration 77.20s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–17.56 | 0–439 | scan | complete_observed_360_before_inspection_pass | none | 0 | -140° | 6.5 | 28.1 | no | — |
| 17.60–18.04 | 440–451 | scan | complete_observed_360_before_inspection_pass | none | 377 | +29° | 6.5 | 33.5 | no | 306px |
| 18.08–18.08 | 452–452 | target_inspect | target_likely_evidence_requires_inspection | track18(target) | 303 | +19° | 6.5 | 33.7 | no | 204px |
| 18.12–21.00 | 453–525 | target_inspect | target_likely_evidence_requires_inspection | track18(target) | 298 | +18° | 6.5 | 33.7 | no | 191px |
| 21.04–21.08 | 526–527 | target_inspect | target_likely_evidence_requires_inspection | track18(target) | 304 | +0° | 6.5 | 31.1 | no | 7px |
| 21.12–24.48 | 528–612 | target_inspect | target_likely_evidence_requires_inspection | track18(target) | 302 | +0° | 6.5 | 30.9 | no | 5px |
| 24.52–36.16 | 613–904 | target_inspect | target_likely_evidence_requires_inspection | track18(target) | 529 | +0° | 6.5 | 24.7 | no | 3px |
| 36.20–36.64 | 905–916 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 13045 | -1° | 6.4 | 4.6 | no | 11px |
| 36.68–36.68 | 917–917 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 14887 | -1° | 6.4 | 3.9 | no | 4px |
| 36.72–36.72 | 918–918 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track18(target) | 15058 | -1° | 6.4 | 3.9 | no | 4px |
| 36.76–37.76 | 919–944 | target_align | identity_and_fresh_geometry_associated | track18(target) | 15177 | -1° | 6.4 | 3.8 | yes | 5px |
| 37.80–38.04 | 945–951 | target_align | identity_and_fresh_geometry_associated | track18(none) | 18542 | -1° | 6.4 | 2.8 | yes | 5px |
| 38.08–41.16 | 952–1029 | target_align | identity_and_fresh_geometry_associated | track18(target) | 19337 | -1° | 6.4 | 2.5 | yes | 20px |
| 41.20–41.20 | 1030–1030 | target_align | identity_and_fresh_geometry_associated | track22(target) | 23781 | -1° | 6.3 | 0.3 | yes | 8px |
| 41.24–42.20 | 1031–1055 | target_align | identity_and_fresh_geometry_associated | track18(target) | 23816 | +1° | 6.3 | 0.3 | yes | 5px |
| 42.24–42.64 | 1056–1066 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 25342 | +6° | 6.1 | 0.2 | no | 3px |
| 42.68–47.20 | 1067–1180 | target_align | identity_and_fresh_geometry_associated | track18(target) | 25575 | -6° | 6.1 | 0.2 | yes | 10px |
| 47.24–47.24 | 1181–1181 | target_align | identity_and_fresh_geometry_associated | track23(target) | 37302 | -2° | 5.2 | 0.1 | yes | 3px |
| 47.28–47.28 | 1182–1182 | target_align | identity_and_fresh_geometry_associated | track22(target) | 37497 | -3° | 5.2 | 0.1 | yes | 4px |
| 47.32–47.56 | 1183–1189 | target_align | identity_and_fresh_geometry_associated | track18(target) | 37516 | -5° | 5.2 | 0.1 | yes | 4px |
| 47.60–48.60 | 1190–1215 | target_align | identity_and_fresh_geometry_associated | track22(target) | 38109 | +11° | 5.1 | 0.1 | yes | 1px |
| 48.64–49.88 | 1216–1247 | target_align | identity_and_fresh_geometry_associated | track18(target) | 42870 | +7° | 4.9 | 0.0 | yes | 4px |
| 49.92–49.96 | 1248–1249 | target_align | identity_and_fresh_geometry_associated | track23(target) | 49146 | -10° | 4.6 | 0.0 | yes | 3px |
| 50.00–52.12 | 1250–1303 | target_align | identity_and_fresh_geometry_associated | track18(target) | 49468 | -0° | 4.6 | 0.0 | yes | 3px |
| 52.16–52.20 | 1304–1305 | target_align | identity_and_fresh_geometry_associated | track22(target) | 60862 | +43° | 4.1 | 0.0 | yes | 2px |
| 52.24–52.60 | 1306–1315 | target_align | identity_and_fresh_geometry_associated | track18(target) | 61197 | +22° | 4.1 | 0.0 | yes | 1px |
| 52.64–53.32 | 1316–1333 | target_align | identity_and_fresh_geometry_associated | track22(target) | 64191 | -36° | 4.0 | 0.0 | yes | 2px |
| 53.36–53.60 | 1334–1340 | target_align | identity_and_fresh_geometry_associated | track18(target) | 68717 | -40° | 3.8 | 0.0 | yes | 0px |
| 53.64–53.72 | 1341–1343 | target_align | identity_and_fresh_geometry_associated | track22(target) | 69733 | -99° | 3.8 | 0.0 | yes | 2px |
| 53.76–53.84 | 1344–1346 | target_align | identity_and_fresh_geometry_associated | track23(target) | 70186 | -100° | 3.8 | 0.0 | yes | 2px |
| 53.88–53.88 | 1347–1347 | target_align | identity_and_fresh_geometry_associated | track22(target) | 70508 | -117° | 3.7 | 0.0 | yes | 2px |
| 53.92–54.60 | 1348–1365 | target_align | identity_and_fresh_geometry_associated | track18(target) | 70886 | -124° | 3.7 | 0.0 | yes | 2px |
| 54.64–54.68 | 1366–1367 | target_align | identity_and_fresh_geometry_associated | track22(target) | 74606 | +124° | 3.6 | 0.0 | yes | 1px |
| 54.72–55.20 | 1368–1380 | target_align | identity_and_fresh_geometry_associated | track18(target) | 75137 | +133° | 3.6 | 0.0 | yes | 2px |
| 55.24–56.28 | 1381–1407 | target_align | identity_and_fresh_geometry_associated | track23(target) | 78695 | +44° | 3.4 | 0.0 | yes | 2px |
| 56.32–56.84 | 1408–1421 | target_align | identity_and_fresh_geometry_associated | track27(target) | 85807 | -160° | 3.2 | 0.0 | yes | 4px |
| 56.88–57.00 | 1422–1425 | target_align | identity_and_fresh_geometry_associated | track25(target) | 89689 | +42° | 3.1 | 0.0 | yes | 0px |
| 57.04–57.28 | 1426–1432 | target_align | identity_and_fresh_geometry_associated | track23(target) | 90589 | -18° | 3.1 | 0.0 | yes | 1px |
| 57.32–57.56 | 1433–1439 | target_align | identity_and_fresh_geometry_associated | track25(target) | 92664 | -57° | 3.0 | 0.0 | yes | 2px |
| 57.60–58.28 | 1440–1457 | target_align | identity_and_fresh_geometry_associated | track23(target) | 95197 | -68° | 2.9 | 0.0 | yes | 2px |
| 58.32–58.44 | 1458–1461 | target_align | identity_and_fresh_geometry_associated | track25(target) | 103132 | -91° | 2.8 | 0.0 | yes | 2px |
| 58.48–58.48 | 1462–1462 | target_align | identity_and_fresh_geometry_associated | track27(target) | 104955 | -71° | 2.7 | 0.0 | yes | 2px |
| 58.52–59.44 | 1463–1486 | target_align | identity_and_fresh_geometry_associated | track23(target) | 105445 | -71° | 2.7 | 0.0 | yes | 2px |
| 59.48–59.52 | 1487–1488 | target_align | identity_and_fresh_geometry_associated | track27(target) | 118883 | +69° | 2.5 | 0.0 | yes | 2px |
| 59.56–60.00 | 1489–1500 | target_align | identity_and_fresh_geometry_associated | track25(target) | 120058 | +57° | 2.5 | 0.0 | yes | 2px |
| 60.04–60.28 | 1501–1507 | target_align | identity_and_fresh_geometry_associated | track23(target) | 125730 | -141° | 2.4 | 0.0 | yes | 4px |
| 60.32–60.44 | 1508–1511 | target_align | identity_and_fresh_geometry_associated | track25(target) | 128955 | -133° | 2.3 | 0.0 | yes | 4px |
| 60.48–60.48 | 1512–1512 | target_align | identity_and_fresh_geometry_associated | track27(target) | 131076 | -111° | 2.3 | 0.0 | yes | 2px |
| 60.52–60.64 | 1513–1516 | target_align | identity_and_fresh_geometry_associated | track25(target) | 131406 | -112° | 2.3 | 0.0 | yes | 2px |
| 60.68–60.96 | 1517–1524 | target_align | identity_and_fresh_geometry_associated | track23(target) | 134097 | -117° | 2.3 | 0.0 | yes | 0px |
| 61.00–61.04 | 1525–1526 | target_align | identity_and_fresh_geometry_associated | track25(target) | 139899 | +99° | 2.2 | 0.0 | yes | 4px |
| 61.08–61.76 | 1527–1544 | target_align | identity_and_fresh_geometry_associated | track23(target) | 141536 | +100° | 2.2 | 0.0 | yes | 5px |
| 61.80–61.96 | 1545–1549 | target_align | identity_and_fresh_geometry_associated | track25(target) | 159959 | +11° | 2.0 | 0.0 | yes | 1px |
| 62.00–62.32 | 1550–1558 | target_align | identity_and_fresh_geometry_associated | track23(target) | 166070 | -7° | 1.9 | 0.0 | yes | 0px |
| 62.36–62.40 | 1559–1560 | target_align | identity_and_fresh_geometry_associated | track27(target) | 177701 | -6° | 1.9 | 0.0 | yes | 1px |
| 62.44–62.88 | 1561–1572 | target_align | identity_and_fresh_geometry_associated | track23(target) | 180218 | +7° | 1.9 | 0.0 | yes | 0px |
| 62.92–63.48 | 1573–1587 | target_align | identity_and_fresh_geometry_associated | track30(target) | 195336 | -73° | 1.8 | 0.0 | yes | 1px |
| 63.52–68.76 | 1588–1719 | target_align | identity_and_fresh_geometry_associated | track35(target) | 217538 | +72° | 1.6 | 0.0 | yes | 4px |
| 68.80–75.12 | 1720–1878 | target_align | identity_and_fresh_geometry_associated | track38(target) | 207192 | +180° | 0.9 | 0.0 | yes | 0px |
| 75.16–77.16 | 1879–1929 | ground_hold | own_estimator_not_airborne | track38(target) | 159647 | -16° | 0.7 | 0.0 | no | 0px |
| 77.20–77.20 | 1930–1930 | ground_hold | own_estimator_not_airborne | track38(target) | 162016 | -13° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

A usable target was visible while a different object was being pursued:
- 37.80–38.04s: selected track18(none) while target had 18542 px of visible structure; selected object 40 px, target_probability 0.0007, wrong_object_probability 0.740.

Camera survey continued although a usable target was in view:
- 17.60–18.04s scanning with 377 px of target structure visible.

## Observer-truth visibility arcs

- target visible 17.48–77.20s (59.7s), peak 226819 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 17.60000000000161, "first_usable_px": 377, "first_target_select_t": 18.080000000000492, "first_target_approach_t": 18.080000000000492, "delay_s": 0.4799999999988813, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 12, "scan_span_s": 0.43999999999897454, "limit_s": 1.0, "window": [17.60000000000161, 18.040000000000585]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 7, "worst_span_s": 0.23999999999944066, "limit_s": 0.5, "spans": [{"t0": 37.79999999995454, "t1": 38.03999999995398, "selected": "none", "selected_boat": true, "target_prob": 0.0007085602264851332, "target_px": 18542, "selected_size_px": 40.14657974243164}]}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 1479, "frames_on_target": 1472, "fraction": 0.9953, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 7, "examples": [{"t": 37.79999999995454, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}, {"t": 37.83999999995444, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}, {"t": 37.87999999995435, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}, {"t": 37.91999999995426, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}, {"t": 37.959999999954164, "name": "none", "prob": 0.0007085602264851332, "wrong": 0.7399354577064514, "size": 40.14657974243164}]}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 949, "lost_frames": 32, "good_frames": 887, "lost_fraction": 0.0337, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 36.75999999995696, "metric_confirmed_at_start": true, "descent_span_s": 38.360000000131706}
- FAIL **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 1.24, "limit_s": 1.0, "windows": [{"t0": 38.319999999953325, "t1": 39.559999999950435, "pad_err": 45.002777692049186}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 3, "span_s": 77.2, "per_10s": 0.389, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 4, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.0, "limit_s": 6.0, "holds": []}
- PASS **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 0, "first_t": null, "parent_recovery_frames": 380}
- FAIL **E01.10b_parent_recovery_share_below_limit** — {"share": 0.1968, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.002433063969740301, "final_t": 77.2000000000986, "touchdown_s": 91.45400000007263}
- PASS **integrity.observer_join** — {"frames": 1931, "joined_frames": 1931}

Behavioural acceptance: **False** (4 failing checks).