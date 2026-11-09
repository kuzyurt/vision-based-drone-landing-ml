# Flight narrative — E04_v60

Scenario `windows_review_E04_close_loss` kind=beach seed=3200000006 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=visible fault=gimbal_tilt mode=expert
Frames 1647, task duration 65.84s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.04 | 0–1 | scan | complete_observed_360_before_inspection_pass | none | 6089 | +0° | 6.5 | 8.1 | no | 23px |
| 0.08–0.12 | 2–3 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 6087 | +0° | 6.6 | 8.1 | no | 26px |
| 0.16–2.84 | 4–71 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 6079 | +0° | 6.6 | 8.1 | no | 28px |
| 2.88–3.12 | 72–78 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 11121 | +0° | 6.5 | 5.3 | no | 21px |
| 3.16–3.44 | 79–86 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 12355 | -0° | 6.5 | 4.8 | no | 28px |
| 3.48–3.64 | 87–91 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 13857 | +0° | 6.5 | 4.3 | no | 33px |
| 3.68–3.68 | 92–92 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 14867 | +0° | 6.5 | 3.9 | no | 48px |
| 3.72–3.72 | 93–93 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 15055 | +0° | 6.5 | 3.9 | no | 49px |
| 3.76–3.76 | 94–94 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 15295 | +0° | 6.5 | 3.8 | no | 51px |
| 3.80–3.80 | 95–95 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 15478 | +0° | 6.5 | 3.7 | no | 52px |
| 3.84–3.84 | 96–96 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 15667 | +0° | 6.5 | 3.7 | no | 55px |
| 3.88–4.52 | 97–113 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 15841 | +0° | 6.5 | 3.6 | no | 56px |
| 4.56–5.52 | 114–138 | target_align | identity_and_fresh_geometry_associated | track1(target) | 18617 | +0° | 6.5 | 2.7 | yes | 71px |
| 5.56–5.56 | 139–139 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 20099 | +1° | 6.5 | 1.9 | no | 7px |
| 5.60–6.48 | 140–162 | target_align | identity_and_fresh_geometry_associated | track1(target) | 20132 | +1° | 6.5 | 1.8 | yes | 7px |
| 6.52–6.52 | 163–163 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 21748 | -0° | 6.5 | 1.0 | no | 63px |
| 6.56–7.04 | 164–176 | target_align | identity_and_fresh_geometry_associated | track1(target) | 21759 | -0° | 6.5 | 0.9 | yes | 63px |
| 7.08–7.44 | 177–186 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 22089 | -3° | 6.5 | 0.6 | no | 30px |
| 7.48–7.64 | 187–191 | target_align | identity_and_fresh_geometry_associated | track1(target) | 22227 | -1° | 6.5 | 0.4 | yes | 34px |
| 7.68–7.80 | 192–195 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 22186 | +2° | 6.5 | 0.3 | no | 5px |
| 7.84–7.88 | 196–197 | target_align | identity_and_fresh_geometry_associated | track1(target) | 22170 | -1° | 6.5 | 0.3 | yes | 0px |
| 7.92–8.04 | 198–201 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 22210 | -4° | 6.5 | 0.3 | no | 11px |
| 8.08–8.72 | 202–218 | target_align | identity_and_fresh_geometry_associated | track1(target) | 22213 | -3° | 6.5 | 0.3 | yes | 13px |
| 8.76–8.88 | 219–222 | target_align | identity_and_fresh_geometry_associated | track1(none) | 22325 | -4° | 6.5 | 0.2 | yes | 1px |
| 8.92–9.16 | 223–229 | target_align | identity_and_fresh_geometry_associated | track1(target) | 22505 | -10° | 6.5 | 0.2 | yes | 15px |
| 9.20–9.76 | 230–244 | target_align | identity_and_fresh_geometry_associated | track2(target) | 22976 | -3° | 6.5 | 0.2 | yes | 14px |
| 9.80–9.80 | 245–245 | target_align | identity_and_fresh_geometry_associated | track1(target) | 24055 | -20° | 6.3 | 0.1 | yes | 4px |
| 9.84–9.88 | 246–247 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 24072 | -16° | 6.3 | 0.1 | no | 4px |
| 9.92–10.12 | 248–253 | target_align | identity_and_fresh_geometry_associated | track1(target) | 24250 | -12° | 6.3 | 0.1 | yes | 7px |
| 10.16–10.56 | 254–264 | target_align | identity_and_fresh_geometry_associated | track2(target) | 24538 | -17° | 6.2 | 0.1 | yes | 7px |
| 10.60–10.84 | 265–271 | target_align | identity_and_fresh_geometry_associated | track1(target) | 24836 | -11° | 6.2 | 0.1 | yes | 6px |
| 10.88–11.20 | 272–280 | target_align | identity_and_fresh_geometry_associated | track2(target) | 25146 | +18° | 6.2 | 0.1 | yes | 0px |
| 11.24–11.48 | 281–287 | target_align | identity_and_fresh_geometry_associated | track1(target) | 25628 | -32° | 6.1 | 0.1 | yes | 7px |
| 11.52–11.56 | 288–289 | target_align | identity_and_fresh_geometry_associated | track2(target) | 26238 | -64° | 6.1 | 0.1 | yes | 5px |
| 11.60–12.24 | 290–306 | target_align | identity_and_fresh_geometry_associated | track1(target) | 26499 | -55° | 6.0 | 0.1 | yes | 6px |
| 12.28–13.00 | 307–325 | target_align | identity_and_fresh_geometry_associated | track2(target) | 28076 | -24° | 5.9 | 0.0 | yes | 5px |
| 13.04–13.76 | 326–344 | target_align | identity_and_fresh_geometry_associated | track1(target) | 29985 | -32° | 5.7 | 0.0 | yes | 4px |
| 13.80–13.96 | 345–349 | target_align | identity_and_fresh_geometry_associated | track2(target) | 32298 | -1° | 5.5 | 0.0 | yes | 6px |
| 14.00–14.24 | 350–356 | target_align | identity_and_fresh_geometry_associated | track3(target) | 32829 | -10° | 5.5 | 0.0 | yes | 4px |
| 14.28–14.28 | 357–357 | target_align | identity_and_fresh_geometry_associated | track2(target) | 33546 | +35° | 5.4 | 0.0 | yes | 1px |
| 14.32–14.96 | 358–374 | target_align | identity_and_fresh_geometry_associated | track1(target) | 33787 | +32° | 5.4 | 0.0 | yes | 2px |
| 15.00–15.40 | 375–385 | target_align | identity_and_fresh_geometry_associated | track3(target) | 36055 | -12° | 5.2 | 0.0 | yes | 5px |
| 15.44–15.68 | 386–392 | target_align | identity_and_fresh_geometry_associated | track1(target) | 37855 | -6° | 5.2 | 0.0 | yes | 4px |
| 15.72–15.72 | 393–393 | target_align | identity_and_fresh_geometry_associated | track3(target) | 38731 | -26° | 5.1 | 0.0 | yes | 3px |
| 15.76–16.00 | 394–400 | target_align | identity_and_fresh_geometry_associated | track2(target) | 38802 | -26° | 5.1 | 0.0 | yes | 4px |
| 16.04–16.24 | 401–406 | target_align | identity_and_fresh_geometry_associated | track3(target) | 39760 | +140° | 5.0 | 0.0 | yes | 2px |
| 16.28–16.92 | 407–423 | target_align | identity_and_fresh_geometry_associated | track2(target) | 40598 | -93° | 5.0 | 0.0 | yes | 6px |
| 16.96–17.28 | 424–432 | target_align | identity_and_fresh_geometry_associated | track1(target) | 42752 | +19° | 4.9 | 0.0 | yes | 2px |
| 17.32–17.72 | 433–443 | target_align | identity_and_fresh_geometry_associated | track2(target) | 44417 | -24° | 4.8 | 0.0 | yes | 4px |
| 17.76–18.00 | 444–450 | target_align | identity_and_fresh_geometry_associated | track1(target) | 46952 | -88° | 4.7 | 0.0 | yes | 5px |
| 18.04–18.52 | 451–463 | target_align | identity_and_fresh_geometry_associated | track3(target) | 48631 | -135° | 4.6 | 0.0 | yes | 5px |
| 18.56–19.64 | 464–491 | target_align | identity_and_fresh_geometry_associated | track2(target) | 51408 | +158° | 4.5 | 0.0 | yes | 3px |
| 19.68–19.68 | 492–492 | target_align | identity_and_fresh_geometry_associated | track3(target) | 56711 | -137° | 4.3 | 0.0 | yes | 0px |
| 19.72–20.56 | 493–514 | target_align | identity_and_fresh_geometry_associated | track2(target) | 56969 | -130° | 4.3 | 0.0 | yes | 1px |
| 20.60–20.68 | 515–517 | target_align | identity_and_fresh_geometry_associated | track5(target) | 62683 | +90° | 4.1 | 0.0 | yes | 2px |
| 20.72–21.08 | 518–527 | target_align | identity_and_fresh_geometry_associated | track2(target) | 63225 | +148° | 4.0 | 0.0 | yes | 2px |
| 21.12–21.16 | 528–529 | target_align | identity_and_fresh_geometry_associated | track5(target) | 65142 | +178° | 4.0 | 0.0 | yes | 2px |
| 21.20–22.88 | 530–572 | target_align | identity_and_fresh_geometry_associated | track2(target) | 65557 | +177° | 3.9 | 0.0 | yes | 2px |
| 22.92–23.20 | 573–580 | target_align | identity_and_fresh_geometry_associated | track5(target) | 74974 | +173° | 3.6 | 0.0 | yes | 0px |
| 23.24–27.24 | 581–681 | target_align | identity_and_fresh_geometry_associated | track2(target) | 76660 | -67° | 3.5 | 0.0 | yes | 0px |
| 27.28–27.32 | 682–683 | target_align | identity_and_fresh_geometry_associated | track6(target) | 111872 | -39° | 2.6 | 0.0 | yes | 2px |
| 27.36–28.36 | 684–709 | target_align | identity_and_fresh_geometry_associated | track2(target) | 113035 | -44° | 2.6 | 0.0 | yes | 2px |
| 28.40–28.64 | 710–716 | target_align | identity_and_fresh_geometry_associated | track6(target) | 126812 | -9° | 2.4 | 0.0 | yes | 0px |
| 28.68–29.12 | 717–728 | target_align | identity_and_fresh_geometry_associated | track2(target) | 130704 | -2° | 2.3 | 0.0 | yes | 3px |
| 29.16–29.16 | 729–729 | target_align | identity_and_fresh_geometry_associated | track12(target) | 138976 | +30° | 2.2 | 0.0 | yes | 2px |
| 29.20–29.48 | 730–737 | target_align | identity_and_fresh_geometry_associated | track6(target) | 139767 | +31° | 2.2 | 0.0 | yes | 2px |
| 29.52–29.56 | 738–739 | target_align | identity_and_fresh_geometry_associated | track12(target) | 146313 | +27° | 2.1 | 0.0 | yes | 3px |
| 29.60–30.04 | 740–751 | target_align | identity_and_fresh_geometry_associated | track2(target) | 148135 | +20° | 2.1 | 0.0 | yes | 2px |
| 30.08–30.32 | 752–758 | target_align | identity_and_fresh_geometry_associated | track10(target) | 159089 | -75° | 2.0 | 0.0 | yes | 2px |
| 30.36–30.52 | 759–763 | target_align | identity_and_fresh_geometry_associated | track12(target) | 166512 | -104° | 1.9 | 0.0 | yes | 2px |
| 30.56–30.80 | 764–770 | target_align | identity_and_fresh_geometry_associated | track11(target) | 172426 | -71° | 1.9 | 0.0 | yes | 2px |
| 30.84–30.96 | 771–774 | target_align | identity_and_fresh_geometry_associated | track12(target) | 181654 | +79° | 1.8 | 0.0 | yes | 2px |
| 31.00–31.68 | 775–792 | target_align | identity_and_fresh_geometry_associated | track10(target) | 187405 | +50° | 1.8 | 0.0 | yes | 2px |
| 31.72–32.32 | 793–808 | target_align | identity_and_fresh_geometry_associated | track16(target) | 215267 | -41° | 1.6 | 0.0 | yes | 0px |
| 32.36–33.20 | 809–830 | target_align | identity_and_fresh_geometry_associated | track14(target) | 226376 | +19° | 1.5 | 0.0 | yes | 0px |
| 33.24–33.68 | 831–842 | target_align | identity_and_fresh_geometry_associated | track14(target) | 223631 | +60° | 1.3 | 0.0 | yes | 0px |
| 33.72–33.80 | 843–845 | target_align | identity_and_fresh_geometry_associated | track18(target) | 227061 | +53° | 1.2 | 0.0 | yes | 0px |
| 33.84–34.40 | 846–860 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track18(target) | 228106 | +54° | 1.2 | 0.0 | no | 0px |
| 34.44–34.80 | 861–870 | local_downlook | arrest_descent_and_inspect_below | track18(target) | 174076 | +53° | 1.3 | 0.0 | no | 0px |
| 34.84–35.44 | 871–886 | local_downlook | bounded_fresh_downward_observation | track18(target) | 40976 | +85° | 1.4 | 0.0 | no | 30px |
| 35.48–35.68 | 887–892 | recovery_climb | bounded_clearance_gated_climb | track18(target) | 1014 | +75° | 1.7 | 0.0 | no | 164px |
| 35.72–36.28 | 893–907 | recovery_climb | bounded_clearance_gated_climb | track18(target) | 1239 | +28° | 1.8 | 0.0 | no | 155px |
| 36.32–37.24 | 908–931 | recovery_climb | bounded_clearance_gated_climb | track23(target) | 49095 | +6° | 2.0 | 0.2 | no | 59px |
| 37.28–37.36 | 932–934 | recovery_climb | bounded_clearance_gated_climb | track32(target) | 119170 | +3° | 2.4 | 0.4 | no | 6px |
| 37.40–37.44 | 935–936 | target_align | identity_and_fresh_geometry_associated | track32(target) | 116975 | +2° | 2.5 | 0.5 | yes | 7px |
| 37.48–37.80 | 937–945 | target_align | identity_and_fresh_geometry_associated | track23(target) | 115402 | +2° | 2.5 | 0.5 | yes | 6px |
| 37.84–38.68 | 946–967 | target_align | identity_and_fresh_geometry_associated | track32(target) | 105923 | +2° | 2.7 | 0.6 | yes | 8px |
| 38.72–38.96 | 968–974 | target_align | identity_and_fresh_geometry_associated | track23(target) | 88728 | +2° | 3.0 | 0.7 | yes | 8px |
| 39.00–40.24 | 975–1006 | target_align | identity_and_fresh_geometry_associated | track32(target) | 84014 | +2° | 3.1 | 0.7 | yes | 6px |
| 40.28–40.96 | 1007–1024 | target_align | identity_and_fresh_geometry_associated | track23(target) | 73702 | +2° | 3.6 | 0.7 | yes | 6px |
| 41.00–41.08 | 1025–1027 | target_align | identity_and_fresh_geometry_associated | track23(target) | 71074 | +2° | 3.6 | 0.6 | yes | 6px |
| 41.12–41.36 | 1028–1034 | target_align | identity_and_fresh_geometry_associated | track32(target) | 70972 | +3° | 3.6 | 0.6 | yes | 9px |
| 41.40–41.80 | 1035–1045 | target_align | identity_and_fresh_geometry_associated | track23(target) | 72034 | +5° | 3.7 | 0.6 | yes | 10px |
| 41.84–44.16 | 1046–1104 | target_align | identity_and_fresh_geometry_associated | track32(target) | 66406 | +2° | 3.6 | 0.5 | yes | 4px |
| 44.20–48.68 | 1105–1217 | target_align | identity_and_fresh_geometry_associated | track24(target) | 83746 | -20° | 3.3 | 0.0 | yes | 1px |
| 48.72–48.76 | 1218–1219 | target_align | identity_and_fresh_geometry_associated | track36(target) | 134975 | +41° | 2.2 | 0.0 | yes | 3px |
| 48.80–49.20 | 1220–1230 | target_align | identity_and_fresh_geometry_associated | track24(target) | 136648 | +40° | 2.2 | 0.0 | yes | 2px |
| 49.24–49.72 | 1231–1243 | target_align | identity_and_fresh_geometry_associated | track36(target) | 146726 | +91° | 2.1 | 0.0 | yes | 4px |
| 49.76–49.80 | 1244–1245 | target_align | identity_and_fresh_geometry_associated | track38(target) | 159615 | +3° | 2.0 | 0.0 | yes | 2px |
| 49.84–50.08 | 1246–1252 | target_align | identity_and_fresh_geometry_associated | track36(target) | 161436 | -52° | 2.0 | 0.0 | yes | 1px |
| 50.12–50.52 | 1253–1263 | target_align | identity_and_fresh_geometry_associated | track38(target) | 167703 | -86° | 1.9 | 0.0 | yes | 0px |
| 50.56–50.84 | 1264–1271 | target_align | identity_and_fresh_geometry_associated | track36(target) | 178139 | -74° | 1.9 | 0.0 | yes | 1px |
| 50.88–51.44 | 1272–1286 | target_align | identity_and_fresh_geometry_associated | track35(target) | 187506 | +116° | 1.8 | 0.0 | yes | 6px |
| 51.48–51.56 | 1287–1289 | target_align | identity_and_fresh_geometry_associated | track36(target) | 211992 | +91° | 1.6 | 0.0 | yes | 10px |
| 51.60–55.20 | 1290–1380 | target_align | identity_and_fresh_geometry_associated | track35(target) | 218138 | +73° | 1.6 | 0.0 | yes | 8px |
| 55.24–56.28 | 1381–1407 | target_align | identity_and_fresh_geometry_associated | track50(target) | 214619 | +141° | 1.1 | 0.0 | yes | 0px |
| 56.32–63.76 | 1408–1594 | target_align | identity_and_fresh_geometry_associated | track51(target) | 214613 | -1° | 1.0 | 0.0 | yes | 0px |
| 63.80–65.80 | 1595–1645 | ground_hold | own_estimator_not_airborne | track51(target) | 149644 | -14° | 0.7 | 0.0 | no | 0px |
| 65.84–65.84 | 1646–1646 | ground_hold | own_estimator_not_airborne | track51(target) | 149576 | -27° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

A usable target was visible while a different object was being pursued:
- 8.76–8.88s: selected track1(none) while target had 22325 px of visible structure; selected object 80 px, target_probability 0.0498, wrong_object_probability 0.779.

Camera survey continued although a usable target was in view:
- 0.00–0.04s scanning with 6089 px of target structure visible.

## Observer-truth visibility arcs

- target visible 0.00–65.84s (65.8s), peak 230400 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 0.0, "first_usable_px": 6089, "first_target_select_t": 0.08000000000009777, "first_target_approach_t": 0.08000000000009777, "delay_s": 0.08000000000009777, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 2, "scan_span_s": 0.040000000000048885, "limit_s": 1.0, "window": [0.0, 0.040000000000048885]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 4, "worst_span_s": 0.12000000000014666, "limit_s": 0.5, "spans": [{"t0": 8.760000000010706, "t1": 8.880000000010853, "selected": "none", "selected_boat": true, "target_prob": 0.04977346584200859, "target_px": 22325, "selected_size_px": 79.52037048339844}]}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 1645, "frames_on_target": 1641, "fraction": 0.9976, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 4, "examples": [{"t": 8.760000000010706, "name": "none", "prob": 0.04977346584200859, "wrong": 0.7786045670509338, "size": 79.52037048339844}, {"t": 8.800000000010755, "name": "none", "prob": 0.04977346584200859, "wrong": 0.7786045670509338, "size": 79.52037048339844}, {"t": 8.840000000010804, "name": "none", "prob": 0.04977346584200859, "wrong": 0.7786045670509338, "size": 79.52037048339844}, {"t": 8.880000000010853, "name": "none", "prob": 0.04977346584200859, "wrong": 0.7786045670509338, "size": 79.52037048339844}]}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 1370, "lost_frames": 32, "good_frames": 1323, "lost_fraction": 0.0234, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 4.560000000005573, "metric_confirmed_at_start": true, "descent_span_s": 59.20000000002928}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 0.48, "limit_s": 1.0, "windows": [{"t0": 4.560000000005573, "t1": 5.0400000000061596, "pad_err": 71.11258679024411}, {"t0": 6.080000000007431, "t1": 6.480000000007919, "pad_err": 52.11765535785354}, {"t0": 6.560000000008017, "t1": 6.840000000008359, "pad_err": 63.00198409574099}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 6, "span_s": 65.84, "per_10s": 0.911, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 16, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.0, "limit_s": 6.0, "holds": []}
- FAIL **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 177, "first_t": 33.91999999996315, "parent_recovery_frames": 282}
- FAIL **E01.10b_parent_recovery_share_below_limit** — {"share": 0.1712, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.002549287765526209, "final_t": 65.84000000004478, "touchdown_s": 80.19900000001888}
- PASS **integrity.observer_join** — {"frames": 1647, "joined_frames": 1647}

Behavioural acceptance: **False** (4 failing checks).

## Artifacts

- frames: `frames.csv` (1647 rows)
- events: `events.jsonl` (109)
- timeline: `timeline.png`
- annotated video: `review_annotated.mp4`
- contact sheets: `sheets/`
- video join consistent: True
