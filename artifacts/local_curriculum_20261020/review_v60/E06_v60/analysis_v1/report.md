# Flight narrative — E06_v60

Scenario `windows_review_E06_search_near` kind=beach seed=3200000001 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=outside_camera fault=None mode=expert
Frames 2203, task duration 88.08s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–17.36 | 0–434 | scan | complete_observed_360_before_inspection_pass | none | 0 | -140° | 6.6 | 8.1 | no | — |
| 17.40–17.44 | 435–436 | scan | complete_observed_360_before_inspection_pass | none | 1646 | +33° | 6.5 | 13.6 | no | 322px |
| 17.48–20.64 | 437–516 | target_inspect | target_likely_evidence_requires_inspection | track21(target) | 2749 | +31° | 6.5 | 13.6 | no | 311px |
| 20.68–20.76 | 517–519 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track21(none) | 3354 | -0° | 6.5 | 11.1 | no | 25px |
| 20.80–24.64 | 520–616 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track21(target) | 3531 | -0° | 6.5 | 10.9 | no | 43px |
| 24.68–24.92 | 617–623 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track21(target) | 15194 | +1° | 6.5 | 3.9 | no | 61px |
| 24.96–26.44 | 624–661 | target_align | identity_and_fresh_geometry_associated | track21(target) | 16488 | +1° | 6.5 | 3.4 | yes | 64px |
| 26.48–26.56 | 662–664 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track21(target) | 19376 | +3° | 6.6 | 1.9 | no | 17px |
| 26.60–27.64 | 665–691 | target_align | identity_and_fresh_geometry_associated | track21(target) | 19683 | +2° | 6.6 | 1.7 | yes | 36px |
| 27.68–27.72 | 692–693 | target_align | identity_and_fresh_geometry_associated | track24(target) | 21513 | -0° | 6.6 | 0.6 | yes | 41px |
| 27.76–28.00 | 694–700 | target_align | identity_and_fresh_geometry_associated | track21(target) | 21414 | -1° | 6.6 | 0.6 | yes | 31px |
| 28.04–28.12 | 701–703 | target_align | identity_and_fresh_geometry_associated | track24(target) | 21232 | -3° | 6.7 | 0.5 | yes | 8px |
| 28.16–28.36 | 704–709 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track24(target) | 21120 | -5° | 6.7 | 0.4 | no | 18px |
| 28.40–28.40 | 710–710 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track25(target) | 20824 | -5° | 6.7 | 0.4 | no | 18px |
| 28.44–29.56 | 711–739 | target_align | identity_and_fresh_geometry_associated | track21(target) | 20743 | -6° | 6.7 | 0.4 | yes | 18px |
| 29.60–29.60 | 740–740 | target_align | identity_and_fresh_geometry_associated | track24(target) | 21812 | -3° | 6.6 | 0.2 | yes | 4px |
| 29.64–29.64 | 741–741 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track24(target) | 21842 | -2° | 6.6 | 0.2 | no | 1px |
| 29.68–29.72 | 742–743 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track21(target) | 21972 | -2° | 6.6 | 0.2 | no | 0px |
| 29.76–35.36 | 744–884 | target_align | identity_and_fresh_geometry_associated | track21(target) | 21950 | -6° | 6.5 | 0.2 | yes | 7px |
| 35.40–35.72 | 885–893 | target_align | identity_and_fresh_geometry_associated | track25(target) | 34602 | +27° | 5.3 | 0.1 | yes | 2px |
| 35.76–38.52 | 894–963 | target_align | identity_and_fresh_geometry_associated | track21(target) | 35899 | -29° | 5.3 | 0.0 | yes | 6px |
| 38.56–39.08 | 964–977 | target_align | identity_and_fresh_geometry_associated | track25(target) | 46644 | -59° | 4.7 | 0.0 | yes | 5px |
| 39.12–39.36 | 978–984 | target_align | identity_and_fresh_geometry_associated | track21(target) | 49467 | -119° | 4.6 | 0.0 | yes | 6px |
| 39.40–39.44 | 985–986 | target_align | identity_and_fresh_geometry_associated | track28(target) | 51038 | -134° | 4.5 | 0.0 | yes | 4px |
| 39.48–39.72 | 987–993 | target_align | identity_and_fresh_geometry_associated | track21(target) | 51568 | -125° | 4.5 | 0.0 | yes | 4px |
| 39.76–39.80 | 994–995 | target_align | identity_and_fresh_geometry_associated | track25(target) | 53693 | +49° | 4.4 | 0.0 | yes | 2px |
| 39.84–41.64 | 996–1041 | target_align | identity_and_fresh_geometry_associated | track21(target) | 54370 | +45° | 4.4 | 0.0 | yes | 2px |
| 41.68–41.68 | 1042–1042 | target_align | identity_and_fresh_geometry_associated | track25(target) | 64531 | -91° | 4.0 | 0.0 | yes | 0px |
| 41.72–42.24 | 1043–1056 | target_align | identity_and_fresh_geometry_associated | track21(target) | 64610 | -78° | 4.0 | 0.0 | yes | 0px |
| 42.28–42.44 | 1057–1061 | target_align | identity_and_fresh_geometry_associated | track25(target) | 67042 | -135° | 3.9 | 0.0 | yes | 1px |
| 42.48–42.60 | 1062–1065 | target_align | identity_and_fresh_geometry_associated | track32(target) | 67951 | -161° | 3.8 | 0.0 | yes | 0px |
| 42.64–43.04 | 1066–1076 | target_align | identity_and_fresh_geometry_associated | track25(target) | 69114 | -152° | 3.8 | 0.0 | yes | 0px |
| 43.08–43.52 | 1077–1088 | target_align | identity_and_fresh_geometry_associated | track32(target) | 71868 | -141° | 3.7 | 0.0 | yes | 0px |
| 43.56–45.40 | 1089–1135 | target_align | identity_and_fresh_geometry_associated | track25(target) | 74633 | +159° | 3.6 | 0.0 | yes | 4px |
| 45.44–45.48 | 1136–1137 | target_align | identity_and_fresh_geometry_associated | track30(target) | 86336 | -88° | 3.2 | 0.0 | yes | 2px |
| 45.52–45.80 | 1138–1145 | target_align | identity_and_fresh_geometry_associated | track25(target) | 87011 | -79° | 3.2 | 0.0 | yes | 2px |
| 45.84–45.88 | 1146–1147 | target_align | identity_and_fresh_geometry_associated | track32(target) | 89883 | +2° | 3.1 | 0.0 | yes | 0px |
| 45.92–45.96 | 1148–1149 | target_align | identity_and_fresh_geometry_associated | track30(target) | 90602 | +34° | 3.1 | 0.0 | yes | 1px |
| 46.00–46.40 | 1150–1160 | target_align | identity_and_fresh_geometry_associated | track25(target) | 91272 | +94° | 3.0 | 0.0 | yes | 2px |
| 46.44–46.52 | 1161–1163 | target_align | identity_and_fresh_geometry_associated | track30(target) | 95521 | +53° | 2.9 | 0.0 | yes | 2px |
| 46.56–47.72 | 1164–1193 | target_align | identity_and_fresh_geometry_associated | track25(target) | 96711 | +50° | 2.9 | 0.0 | yes | 2px |
| 47.76–47.88 | 1194–1197 | target_align | identity_and_fresh_geometry_associated | track30(target) | 108871 | -3° | 2.7 | 0.0 | yes | 0px |
| 47.92–48.24 | 1198–1206 | target_align | identity_and_fresh_geometry_associated | track25(target) | 110539 | -11° | 2.6 | 0.0 | yes | 0px |
| 48.28–48.32 | 1207–1208 | target_align | identity_and_fresh_geometry_associated | track30(target) | 114698 | +0° | 2.5 | 0.0 | yes | 0px |
| 48.36–48.80 | 1209–1220 | target_align | identity_and_fresh_geometry_associated | track25(target) | 115721 | +5° | 2.5 | 0.0 | yes | 1px |
| 48.84–49.12 | 1221–1228 | target_align | identity_and_fresh_geometry_associated | track30(target) | 122634 | +79° | 2.4 | 0.0 | yes | 5px |
| 49.16–50.36 | 1229–1259 | target_align | identity_and_fresh_geometry_associated | track25(target) | 128159 | +94° | 2.3 | 0.0 | yes | 7px |
| 50.40–50.40 | 1260–1260 | target_align | identity_and_fresh_geometry_associated | track30(target) | 150208 | -14° | 2.1 | 0.0 | yes | 0px |
| 50.44–51.20 | 1261–1280 | target_align | identity_and_fresh_geometry_associated | track25(target) | 150674 | -4° | 2.1 | 0.0 | yes | 0px |
| 51.24–51.44 | 1281–1286 | target_align | identity_and_fresh_geometry_associated | track30(target) | 169889 | +80° | 1.9 | 0.0 | yes | 4px |
| 51.48–52.20 | 1287–1305 | target_align | identity_and_fresh_geometry_associated | track41(target) | 177319 | +21° | 1.9 | 0.0 | yes | 2px |
| 52.24–56.60 | 1306–1415 | target_align | identity_and_fresh_geometry_associated | track44(target) | 207304 | +56° | 1.7 | 0.0 | yes | 2px |
| 56.64–57.20 | 1416–1430 | target_align | identity_and_fresh_geometry_associated | track48(target) | 214473 | +103° | 1.1 | 0.0 | yes | 0px |
| 57.24–57.24 | 1431–1431 | target_align | identity_and_fresh_geometry_associated | track49(target) | 212731 | -139° | 1.0 | 0.0 | yes | 0px |
| 57.28–57.32 | 1432–1433 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track49(target) | 212699 | -139° | 1.0 | 0.0 | no | 0px |
| 57.36–59.00 | 1434–1475 | target_align | identity_and_fresh_geometry_associated | track49(target) | 212863 | -132° | 1.0 | 0.0 | yes | 0px |
| 59.04–59.52 | 1476–1488 | target_align | identity_and_fresh_geometry_associated | track50(target) | 226335 | +39° | 1.5 | 0.0 | yes | 0px |
| 59.56–60.12 | 1489–1503 | target_align | identity_and_fresh_geometry_associated | track49(target) | 196177 | +135° | 1.7 | 0.0 | yes | 7px |
| 60.16–61.60 | 1504–1540 | target_align | identity_and_fresh_geometry_associated | track51(target) | 161057 | +101° | 2.0 | 0.0 | yes | 6px |
| 61.64–61.84 | 1541–1546 | target_align | identity_and_fresh_geometry_associated | track56(target) | 111570 | +127° | 2.6 | 0.0 | yes | 10px |
| 61.88–62.48 | 1547–1562 | target_align | identity_and_fresh_geometry_associated | track51(target) | 106560 | -37° | 2.7 | 0.0 | yes | 8px |
| 62.52–63.16 | 1563–1579 | target_align | identity_and_fresh_geometry_associated | track56(target) | 95153 | -80° | 3.0 | 0.0 | yes | 10px |
| 63.20–63.56 | 1580–1589 | target_align | identity_and_fresh_geometry_associated | track51(target) | 85792 | -135° | 3.2 | 0.0 | yes | 8px |
| 63.60–63.96 | 1590–1599 | target_align | identity_and_fresh_geometry_associated | track56(target) | 82327 | -9° | 3.3 | 0.0 | yes | 7px |
| 64.00–64.24 | 1600–1606 | target_align | identity_and_fresh_geometry_associated | track51(target) | 80036 | -155° | 3.4 | 0.0 | yes | 10px |
| 64.28–64.44 | 1607–1611 | target_align | identity_and_fresh_geometry_associated | track56(target) | 79253 | +178° | 3.4 | 0.1 | yes | 11px |
| 64.48–64.96 | 1612–1624 | target_align | identity_and_fresh_geometry_associated | track56(target) | 78735 | +162° | 3.4 | 0.1 | yes | 12px |
| 65.00–65.24 | 1625–1631 | target_align | identity_and_fresh_geometry_associated | track51(target) | 79016 | +166° | 3.4 | 0.0 | yes | 10px |
| 65.28–65.28 | 1632–1632 | target_align | identity_and_fresh_geometry_associated | track56(target) | 80858 | +114° | 3.4 | 0.0 | yes | 2px |
| 65.32–65.76 | 1633–1644 | target_align | identity_and_fresh_geometry_associated | track52(target) | 80990 | +111° | 3.4 | 0.0 | yes | 1px |
| 65.80–65.84 | 1645–1646 | target_align | identity_and_fresh_geometry_associated | track56(target) | 84746 | +96° | 3.2 | 0.0 | yes | 2px |
| 65.88–66.40 | 1647–1660 | target_align | identity_and_fresh_geometry_associated | track52(target) | 85426 | +84° | 3.2 | 0.0 | yes | 2px |
| 66.44–66.56 | 1661–1664 | target_align | identity_and_fresh_geometry_associated | track56(target) | 89775 | +93° | 3.1 | 0.0 | yes | 0px |
| 66.60–66.88 | 1665–1672 | target_align | identity_and_fresh_geometry_associated | track52(target) | 90930 | -117° | 3.1 | 0.0 | yes | 1px |
| 66.92–66.92 | 1673–1673 | target_align | identity_and_fresh_geometry_associated | track56(target) | 93489 | -71° | 3.0 | 0.0 | yes | 2px |
| 66.96–67.44 | 1674–1686 | target_align | identity_and_fresh_geometry_associated | track52(target) | 94164 | -78° | 3.0 | 0.0 | yes | 2px |
| 67.48–67.60 | 1687–1690 | target_align | identity_and_fresh_geometry_associated | track56(target) | 99907 | +172° | 2.8 | 0.0 | yes | 1px |
| 67.64–68.48 | 1691–1712 | target_align | identity_and_fresh_geometry_associated | track52(target) | 101828 | -139° | 2.8 | 0.0 | yes | 1px |
| 68.52–69.12 | 1713–1728 | target_align | identity_and_fresh_geometry_associated | track56(target) | 112565 | -173° | 2.6 | 0.0 | yes | 4px |
| 69.16–69.48 | 1729–1737 | target_align | identity_and_fresh_geometry_associated | track52(target) | 121232 | +82° | 2.5 | 0.0 | yes | 2px |
| 69.52–69.52 | 1738–1738 | target_align | identity_and_fresh_geometry_associated | track58(target) | 126438 | +27° | 2.4 | 0.0 | yes | 2px |
| 69.56–69.68 | 1739–1742 | target_align | identity_and_fresh_geometry_associated | track56(target) | 127109 | +10° | 2.4 | 0.0 | yes | 2px |
| 69.72–70.08 | 1743–1752 | target_align | identity_and_fresh_geometry_associated | track52(target) | 129528 | -61° | 2.3 | 0.0 | yes | 0px |
| 70.12–70.40 | 1753–1760 | target_align | identity_and_fresh_geometry_associated | track56(target) | 135267 | -167° | 2.3 | 0.0 | yes | 2px |
| 70.44–70.72 | 1761–1768 | target_align | identity_and_fresh_geometry_associated | track52(target) | 140329 | -22° | 2.2 | 0.0 | yes | 0px |
| 70.76–70.84 | 1769–1771 | target_align | identity_and_fresh_geometry_associated | track58(target) | 147187 | +121° | 2.1 | 0.0 | yes | 4px |
| 70.88–71.32 | 1772–1783 | target_align | identity_and_fresh_geometry_associated | track56(target) | 149794 | +133° | 2.1 | 0.0 | yes | 5px |
| 71.36–72.08 | 1784–1802 | target_align | identity_and_fresh_geometry_associated | track58(target) | 163195 | +172° | 2.0 | 0.0 | yes | 3px |
| 72.12–77.56 | 1803–1939 | target_align | identity_and_fresh_geometry_associated | track62(target) | 189049 | +118° | 1.8 | 0.0 | yes | 1px |
| 77.60–79.00 | 1940–1975 | target_align | identity_and_fresh_geometry_associated | track73(target) | 214289 | +80° | 1.0 | 0.0 | yes | 0px |
| 79.04–86.00 | 1976–2150 | target_align | identity_and_fresh_geometry_associated | track75(target) | 210846 | +159° | 1.0 | 0.0 | yes | 0px |
| 86.04–88.04 | 2151–2201 | ground_hold | own_estimator_not_airborne | track75(target) | 149585 | -33° | 0.7 | 0.0 | no | 0px |
| 88.08–88.08 | 2202–2202 | ground_hold | own_estimator_not_airborne | track75(target) | 149573 | -21° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

A usable target was visible while a different object was being pursued:
- 20.68–20.76s: selected track21(none) while target had 3354 px of visible structure; selected object 87 px, target_probability 0.0033, wrong_object_probability 0.953.

Camera survey continued although a usable target was in view:
- 17.40–17.44s scanning with 1646 px of target structure visible.

## Observer-truth visibility arcs

- target visible 17.28–88.08s (70.8s), peak 226973 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 17.40000000000151, "first_usable_px": 1646, "first_target_select_t": 17.480000000001322, "first_target_approach_t": 17.480000000001322, "delay_s": 0.07999999999981355, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 2, "scan_span_s": 0.03999999999990678, "limit_s": 1.0, "window": [17.40000000000151, 17.440000000001415]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 3, "worst_span_s": 0.07999999999981355, "limit_s": 0.5, "spans": [{"t0": 20.679999999993864, "t1": 20.759999999993678, "selected": "none", "selected_boat": true, "target_prob": 0.0032846692483872175, "target_px": 3354, "selected_size_px": 86.79108428955078}]}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 1766, "frames_on_target": 1763, "fraction": 0.9983, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 3, "examples": [{"t": 20.679999999993864, "name": "none", "prob": 0.0032846692483872175, "wrong": 0.9529138207435608, "size": 86.79108428955078}, {"t": 20.71999999999377, "name": "none", "prob": 0.0032846692483872175, "wrong": 0.9529138207435608, "size": 86.79108428955078}, {"t": 20.759999999993678, "name": "none", "prob": 0.0032846692483872175, "wrong": 0.9529138207435608, "size": 86.79108428955078}]}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 1512, "lost_frames": 45, "good_frames": 1455, "lost_fraction": 0.0298, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 24.95999999998389, "metric_confirmed_at_start": true, "descent_span_s": 61.04000000015729}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 1.0, "limit_s": 1.0, "windows": [{"t0": 24.95999999998389, "t1": 25.67999999998221, "pad_err": 64.43795465407014}, {"t0": 26.639999999979974, "t1": 27.639999999977643, "pad_err": 45.54393483220351}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 3, "span_s": 88.08, "per_10s": 0.341, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 10, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.23999999999944066, "limit_s": 6.0, "holds": []}
- FAIL **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 179, "first_t": 57.32000000000424, "parent_recovery_frames": 373}
- FAIL **E01.10b_parent_recovery_share_below_limit** — {"share": 0.1693, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.0027497737093460928, "final_t": 88.08000000015112, "touchdown_s": 102.56400000012567}
- PASS **integrity.observer_join** — {"frames": 2203, "joined_frames": 2203}

Behavioural acceptance: **False** (4 failing checks).

## Artifacts

- frames: `frames.csv` (2203 rows)
- events: `events.jsonl` (93)
- timeline: `timeline.png`
- annotated video: `review_annotated.mp4`
- contact sheets: `sheets/`
- video join consistent: True
