# Flight narrative — E03_v60_repair

Scenario `windows_review_E03_yaw` kind=beach seed=3200000005 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=visible fault=gimbal_pan mode=expert
Frames 1215, task duration 48.56s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.16 | 0–4 | scan | complete_observed_360_before_inspection_pass | none | 6060 | +0° | 6.5 | 8.1 | no | 21px |
| 0.20–3.80 | 5–95 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 6017 | -0° | 6.6 | 8.1 | no | 38px |
| 3.84–4.28 | 96–107 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 14918 | +0° | 6.5 | 4.0 | no | 59px |
| 4.32–4.32 | 108–108 | target_inspect | target_likely_evidence_requires_inspection | track4(target) | 17159 | +0° | 6.5 | 3.2 | no | 61px |
| 4.36–5.48 | 109–137 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 17372 | +0° | 6.5 | 3.2 | no | 63px |
| 5.52–6.40 | 138–160 | target_align | identity_and_fresh_geometry_associated | track2(target) | 20451 | -0° | 6.5 | 2.0 | yes | 61px |
| 6.44–6.44 | 161–161 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track2(target) | 20605 | -0° | 6.6 | 1.5 | no | 14px |
| 6.48–6.48 | 162–162 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track4(target) | 20614 | -0° | 6.6 | 1.4 | no | 24px |
| 6.52–6.96 | 163–174 | target_align | identity_and_fresh_geometry_associated | track4(target) | 20714 | -0° | 6.6 | 1.4 | yes | 35px |
| 7.00–7.00 | 175–175 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track4(target) | 20930 | +0° | 6.6 | 1.0 | no | 66px |
| 7.04–7.08 | 176–177 | target_align | identity_and_fresh_geometry_associated | track4(target) | 21014 | +1° | 6.7 | 0.9 | yes | 60px |
| 7.12–7.16 | 178–179 | target_align | identity_and_fresh_geometry_associated | track2(target) | 20994 | +1° | 6.7 | 0.9 | yes | 49px |
| 7.20–7.24 | 180–181 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track2(target) | 21068 | +1° | 6.7 | 0.8 | no | 50px |
| 7.28–7.40 | 182–185 | target_align | identity_and_fresh_geometry_associated | track2(target) | 21037 | +1° | 6.7 | 0.7 | yes | 50px |
| 7.44–7.56 | 186–189 | target_align | identity_and_fresh_geometry_associated | track4(target) | 21138 | -0° | 6.7 | 0.6 | yes | 45px |
| 7.60–7.60 | 190–190 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track4(target) | 21165 | +1° | 6.7 | 0.5 | no | 29px |
| 7.64–7.76 | 191–194 | target_align | identity_and_fresh_geometry_associated | track4(target) | 21125 | +0° | 6.7 | 0.5 | yes | 23px |
| 7.80–7.92 | 195–198 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track4(target) | 21186 | -2° | 6.7 | 0.4 | no | 16px |
| 7.96–8.68 | 199–217 | target_align | identity_and_fresh_geometry_associated | track4(target) | 21121 | -4° | 6.7 | 0.4 | yes | 12px |
| 8.72–8.96 | 218–224 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track4(target) | 22113 | +7° | 6.6 | 0.1 | no | 10px |
| 9.00–9.44 | 225–236 | target_align | identity_and_fresh_geometry_associated | track4(target) | 22538 | -10° | 6.5 | 0.1 | yes | 13px |
| 9.48–9.60 | 237–240 | target_align | identity_and_fresh_geometry_associated | track5(target) | 22724 | -18° | 6.5 | 0.1 | yes | 2px |
| 9.64–9.88 | 241–247 | target_align | identity_and_fresh_geometry_associated | track4(target) | 22891 | -53° | 6.4 | 0.1 | yes | 4px |
| 9.92–10.00 | 248–250 | target_align | identity_and_fresh_geometry_associated | track5(target) | 23459 | -6° | 6.3 | 0.1 | yes | 4px |
| 10.04–10.12 | 251–253 | target_align | identity_and_fresh_geometry_associated | track4(target) | 23665 | +5° | 6.3 | 0.1 | yes | 6px |
| 10.16–10.24 | 254–256 | target_align | identity_and_fresh_geometry_associated | track2(target) | 24037 | +18° | 6.3 | 0.1 | yes | 4px |
| 10.28–10.28 | 257–257 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track2(target) | 24479 | +49° | 6.2 | 0.1 | no | 4px |
| 10.32–10.40 | 258–260 | target_align | identity_and_fresh_geometry_associated | track2(target) | 24419 | +48° | 6.2 | 0.1 | yes | 5px |
| 10.44–10.56 | 261–264 | target_align | identity_and_fresh_geometry_associated | track4(none) | 24745 | +6° | 6.2 | 0.0 | yes | 8px |
| 10.60–10.60 | 265–265 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track4(none) | 25119 | -15° | 6.2 | 0.0 | no | 13px |
| 10.64–10.64 | 266–266 | target_align | identity_and_fresh_geometry_associated | track4(none) | 25144 | -17° | 6.2 | 0.0 | yes | 16px |
| 10.68–10.84 | 267–271 | target_align | identity_and_fresh_geometry_associated | track2(target) | 25172 | -18° | 6.2 | 0.0 | yes | 19px |
| 10.88–10.88 | 272–272 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track2(target) | 25170 | -180° | 6.2 | 0.0 | no | 2px |
| 10.92–10.92 | 273–273 | target_align | identity_and_fresh_geometry_associated | track2(target) | 25284 | +174° | 6.2 | 0.0 | yes | 7px |
| 10.96–11.08 | 274–277 | target_align | identity_and_fresh_geometry_associated | track5(target) | 25349 | +179° | 6.2 | 0.0 | yes | 8px |
| 11.12–11.48 | 278–287 | target_align | identity_and_fresh_geometry_associated | track2(target) | 25419 | -32° | 6.1 | 0.0 | yes | 6px |
| 11.52–12.44 | 288–311 | target_align | identity_and_fresh_geometry_associated | track4(target) | 25840 | -10° | 6.1 | 0.0 | yes | 4px |
| 12.48–12.72 | 312–318 | target_align | identity_and_fresh_geometry_associated | track2(target) | 28486 | -30° | 5.8 | 0.0 | yes | 8px |
| 12.76–13.56 | 319–339 | target_align | identity_and_fresh_geometry_associated | track4(target) | 28949 | -80° | 5.8 | 0.0 | yes | 3px |
| 13.60–13.60 | 340–340 | target_align | identity_and_fresh_geometry_associated | track7(target) | 31380 | -19° | 5.6 | 0.0 | yes | 4px |
| 13.64–13.68 | 341–342 | target_align | identity_and_fresh_geometry_associated | track5(target) | 31480 | -24° | 5.6 | 0.0 | yes | 4px |
| 13.72–14.52 | 343–363 | target_align | identity_and_fresh_geometry_associated | track4(target) | 31673 | -31° | 5.6 | 0.0 | yes | 3px |
| 14.56–14.60 | 364–365 | target_align | identity_and_fresh_geometry_associated | track5(target) | 33749 | -24° | 5.4 | 0.0 | yes | 6px |
| 14.64–14.68 | 366–367 | target_align | identity_and_fresh_geometry_associated | track7(target) | 34028 | -14° | 5.4 | 0.0 | yes | 6px |
| 14.72–15.80 | 368–395 | target_align | identity_and_fresh_geometry_associated | track4(target) | 34297 | -7° | 5.4 | 0.0 | yes | 4px |
| 15.84–15.88 | 396–397 | target_align | identity_and_fresh_geometry_associated | track5(target) | 37600 | -63° | 5.2 | 0.0 | yes | 6px |
| 15.92–17.20 | 398–430 | target_align | identity_and_fresh_geometry_associated | track4(target) | 37759 | -59° | 5.1 | 0.0 | yes | 6px |
| 17.24–17.28 | 431–432 | target_align | identity_and_fresh_geometry_associated | track5(target) | 43724 | -79° | 4.8 | 0.0 | yes | 7px |
| 17.32–18.40 | 433–460 | target_align | identity_and_fresh_geometry_associated | track4(target) | 43987 | -83° | 4.8 | 0.0 | yes | 5px |
| 18.44–18.44 | 461–461 | target_align | identity_and_fresh_geometry_associated | track5(target) | 49832 | -102° | 4.6 | 0.0 | yes | 4px |
| 18.48–18.72 | 462–468 | target_align | identity_and_fresh_geometry_associated | track7(target) | 49962 | -117° | 4.6 | 0.0 | yes | 4px |
| 18.76–18.76 | 469–469 | target_align | identity_and_fresh_geometry_associated | track6(target) | 51149 | -170° | 4.5 | 0.0 | yes | 4px |
| 18.80–19.04 | 470–476 | target_align | identity_and_fresh_geometry_associated | track5(target) | 51335 | -159° | 4.5 | 0.0 | yes | 5px |
| 19.08–19.28 | 477–482 | target_align | identity_and_fresh_geometry_associated | track6(target) | 52631 | -178° | 4.4 | 0.0 | yes | 4px |
| 19.32–19.60 | 483–490 | target_align | identity_and_fresh_geometry_associated | track5(target) | 53924 | +12° | 4.4 | 0.0 | yes | 1px |
| 19.64–25.88 | 491–647 | target_align | identity_and_fresh_geometry_associated | track4(target) | 55859 | +9° | 4.3 | 0.0 | yes | 3px |
| 25.92–25.92 | 648–648 | target_align | identity_and_fresh_geometry_associated | track6(target) | 94903 | +104° | 3.0 | 0.0 | yes | 4px |
| 25.96–26.08 | 649–652 | target_align | identity_and_fresh_geometry_associated | track9(target) | 95254 | +101° | 2.9 | 0.0 | yes | 4px |
| 26.12–27.32 | 653–683 | target_align | identity_and_fresh_geometry_associated | track4(target) | 96741 | +103° | 2.9 | 0.0 | yes | 4px |
| 27.36–27.44 | 684–686 | target_align | identity_and_fresh_geometry_associated | track9(target) | 110359 | -94° | 2.6 | 0.0 | yes | 2px |
| 27.48–27.48 | 687–687 | target_align | identity_and_fresh_geometry_associated | track11(target) | 111613 | -123° | 2.6 | 0.0 | yes | 2px |
| 27.52–27.52 | 688–688 | target_align | identity_and_fresh_geometry_associated | track9(target) | 112051 | -133° | 2.6 | 0.0 | yes | 1px |
| 27.56–28.04 | 689–701 | target_align | identity_and_fresh_geometry_associated | track6(target) | 112481 | -135° | 2.6 | 0.0 | yes | 1px |
| 28.08–28.44 | 702–711 | target_align | identity_and_fresh_geometry_associated | track12(target) | 118536 | +1° | 2.5 | 0.0 | yes | 2px |
| 28.48–28.72 | 712–718 | target_align | identity_and_fresh_geometry_associated | track6(target) | 124354 | +105° | 2.4 | 0.0 | yes | 5px |
| 28.76–29.32 | 719–733 | target_align | identity_and_fresh_geometry_associated | track9(target) | 128925 | +127° | 2.3 | 0.0 | yes | 8px |
| 29.36–29.84 | 734–746 | target_align | identity_and_fresh_geometry_associated | track6(target) | 139831 | -60° | 2.2 | 0.0 | yes | 0px |
| 29.88–30.24 | 747–756 | target_align | identity_and_fresh_geometry_associated | track12(target) | 151033 | -84° | 2.1 | 0.0 | yes | 2px |
| 30.28–30.44 | 757–761 | target_align | identity_and_fresh_geometry_associated | track8(target) | 161047 | +53° | 2.0 | 0.0 | yes | 2px |
| 30.48–30.68 | 762–767 | target_align | identity_and_fresh_geometry_associated | track12(target) | 166552 | +82° | 2.0 | 0.0 | yes | 3px |
| 30.72–31.00 | 768–775 | target_align | identity_and_fresh_geometry_associated | track8(target) | 173441 | +89° | 1.9 | 0.0 | yes | 4px |
| 31.04–31.28 | 776–782 | target_align | identity_and_fresh_geometry_associated | track12(target) | 182994 | -168° | 1.8 | 0.0 | yes | 1px |
| 31.32–32.08 | 783–802 | target_align | identity_and_fresh_geometry_associated | track8(target) | 191661 | -113° | 1.8 | 0.0 | yes | 1px |
| 32.12–32.32 | 803–808 | target_align | identity_and_fresh_geometry_associated | track18(target) | 222984 | +100° | 1.6 | 0.0 | yes | 4px |
| 32.36–33.24 | 809–831 | target_align | identity_and_fresh_geometry_associated | track21(target) | 226689 | +153° | 1.5 | 0.0 | yes | 0px |
| 33.28–34.44 | 832–861 | target_align | identity_and_fresh_geometry_associated | track21(target) | 223732 | +56° | 1.3 | 0.0 | yes | 0px |
| 34.48–38.08 | 862–952 | target_align | identity_and_fresh_geometry_associated | track21(target) | 223028 | +145° | 1.3 | 0.0 | yes | 0px |
| 38.12–38.76 | 953–969 | target_align | identity_and_fresh_geometry_associated | track23(target) | 214342 | +23° | 1.1 | 0.0 | yes | 0px |
| 38.80–39.48 | 970–987 | target_align | identity_and_fresh_geometry_associated | track24(target) | 215104 | +148° | 1.0 | 0.0 | yes | 0px |
| 39.52–46.48 | 988–1162 | target_align | identity_and_fresh_geometry_associated | track25(target) | 213573 | +168° | 1.0 | 0.0 | yes | 0px |
| 46.52–48.52 | 1163–1213 | ground_hold | own_estimator_not_airborne | track25(target) | 149726 | -23° | 0.7 | 0.0 | no | 0px |
| 48.56–48.56 | 1214–1214 | ground_hold | own_estimator_not_airborne | track25(target) | 149648 | -36° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

A usable target was visible while a different object was being pursued:
- 10.44–10.64s: selected track4(none) while target had 24745 px of visible structure; selected object 102 px, target_probability 0.0081, wrong_object_probability 0.836.

Camera survey continued although a usable target was in view:
- 0.00–0.16s scanning with 6060 px of target structure visible.

## Observer-truth visibility arcs

- target visible 0.00–48.56s (48.6s), peak 226905 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 0.0, "first_usable_px": 6060, "first_target_select_t": 0.20000000000024443, "first_target_approach_t": 0.20000000000024443, "delay_s": 0.20000000000024443, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 5, "scan_span_s": 0.16000000000019554, "limit_s": 1.0, "window": [0.0, 0.16000000000019554]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 6, "worst_span_s": 0.20000000000024443, "limit_s": 0.5, "spans": [{"t0": 10.440000000012759, "t1": 10.640000000013004, "selected": "none", "selected_boat": true, "target_prob": 0.008073409087955952, "target_px": 24745, "selected_size_px": 102.12762451171875}]}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 1210, "frames_on_target": 1204, "fraction": 0.995, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 6, "examples": [{"t": 10.440000000012759, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}, {"t": 10.480000000012808, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}, {"t": 10.520000000012857, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}, {"t": 10.560000000012906, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}, {"t": 10.600000000012955, "name": "none", "prob": 0.008073409087955952, "wrong": 0.8357416987419128, "size": 102.12762451171875}]}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 1005, "lost_frames": 24, "good_frames": 962, "lost_fraction": 0.0239, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 5.520000000006746, "metric_confirmed_at_start": true, "descent_span_s": 40.95999999994517}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 0.4, "limit_s": 1.0, "windows": [{"t0": 5.520000000006746, "t1": 5.640000000006893, "pad_err": 60.55163086160438}, {"t0": 6.560000000008017, "t1": 6.960000000008506, "pad_err": 45.0111097397076}, {"t0": 7.040000000008604, "t1": 7.1600000000087505, "pad_err": 59.508402768012516}, {"t0": 7.280000000008897, "t1": 7.440000000009093, "pad_err": 50.039984012787215}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 3, "span_s": 48.56, "per_10s": 0.618, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 20, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.0, "limit_s": 6.0, "holds": []}
- PASS **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 0, "first_t": null, "parent_recovery_frames": 111}
- PASS **E01.10b_parent_recovery_share_below_limit** — {"share": 0.0914, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.003653084107406057, "final_t": 48.559999999961846, "touchdown_s": 62.990999999943895}
- PASS **integrity.observer_join** — {"frames": 1215, "joined_frames": 1215}

Behavioural acceptance: **False** (2 failing checks).