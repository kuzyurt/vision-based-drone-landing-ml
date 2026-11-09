# Flight narrative — E03_v60_forced

Scenario `windows_review_E03_yaw` kind=beach seed=3200000005 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=visible fault=gimbal_pan mode=expert
Frames 1117, task duration 44.64s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.20 | 0–5 | scan | complete_observed_360_before_inspection_pass | none | 6064 | +0° | 6.5 | 8.1 | no | 21px |
| 0.24–0.84 | 6–21 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 6058 | -0° | 6.6 | 8.1 | no | 46px |
| 0.88–2.48 | 22–62 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 6019 | +0° | 6.5 | 8.1 | no | 25px |
| 2.52–3.88 | 63–97 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 8885 | +0° | 6.5 | 6.4 | no | 27px |
| 3.92–4.28 | 98–107 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 15081 | +0° | 6.5 | 3.9 | no | 57px |
| 4.32–4.60 | 108–115 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 16985 | +0° | 6.5 | 3.3 | no | 64px |
| 4.64–4.92 | 116–123 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 18245 | +0° | 6.5 | 2.9 | no | 70px |
| 4.96–9.00 | 124–225 | target_align | identity_and_fresh_geometry_associated | track2(target) | 19226 | +0° | 6.5 | 2.5 | yes | 72px |
| 9.04–9.08 | 226–227 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track2(target) | 24462 | -25° | 6.3 | 0.1 | no | 6px |
| 9.12–9.80 | 228–245 | target_align | identity_and_fresh_geometry_associated | track2(target) | 24623 | -26° | 6.2 | 0.1 | yes | 8px |
| 9.84–9.92 | 246–248 | target_align | identity_and_fresh_geometry_associated | track4(target) | 25028 | -7° | 6.2 | 0.1 | yes | 3px |
| 9.96–10.60 | 249–265 | target_align | identity_and_fresh_geometry_associated | track2(target) | 25188 | -6° | 6.2 | 0.1 | yes | 10px |
| 10.64–10.80 | 266–270 | target_align | identity_and_fresh_geometry_associated | track4(target) | 26256 | -20° | 6.0 | 0.0 | yes | 9px |
| 10.84–11.24 | 271–281 | target_align | identity_and_fresh_geometry_associated | track2(target) | 26732 | -12° | 6.0 | 0.0 | yes | 4px |
| 11.28–11.28 | 282–282 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track2(target) | 28306 | -53° | 5.9 | 0.0 | no | 11px |
| 11.32–11.32 | 283–283 | target_align | identity_and_fresh_geometry_associated | track4(target) | 28358 | -52° | 5.9 | 0.0 | yes | 12px |
| 11.36–11.76 | 284–294 | target_align | identity_and_fresh_geometry_associated | track2(target) | 28348 | -49° | 5.8 | 0.0 | yes | 12px |
| 11.80–11.80 | 295–295 | target_align | identity_and_fresh_geometry_associated | track4(target) | 28850 | +13° | 5.8 | 0.0 | yes | 3px |
| 11.84–13.24 | 296–331 | target_align | identity_and_fresh_geometry_associated | track2(target) | 28937 | +1° | 5.8 | 0.0 | yes | 4px |
| 13.28–13.28 | 332–332 | target_align | identity_and_fresh_geometry_associated | track4(target) | 33085 | +17° | 5.5 | 0.0 | yes | 1px |
| 13.32–13.56 | 333–339 | target_align | identity_and_fresh_geometry_associated | track2(target) | 33215 | +46° | 5.4 | 0.0 | yes | 1px |
| 13.60–14.52 | 340–363 | target_align | identity_and_fresh_geometry_associated | track4(target) | 34088 | -4° | 5.4 | 0.0 | yes | 4px |
| 14.56–14.92 | 364–373 | target_align | identity_and_fresh_geometry_associated | track2(target) | 37078 | -42° | 5.2 | 0.0 | yes | 6px |
| 14.96–15.64 | 374–391 | target_align | identity_and_fresh_geometry_associated | track4(target) | 38752 | +37° | 5.1 | 0.0 | yes | 2px |
| 15.68–16.80 | 392–420 | target_align | identity_and_fresh_geometry_associated | track2(target) | 41604 | -91° | 4.9 | 0.0 | yes | 4px |
| 16.84–17.04 | 421–426 | target_align | identity_and_fresh_geometry_associated | track4(target) | 46287 | +5° | 4.7 | 0.0 | yes | 1px |
| 17.08–17.32 | 427–433 | target_align | identity_and_fresh_geometry_associated | track2(target) | 47524 | -36° | 4.6 | 0.0 | yes | 3px |
| 17.36–17.92 | 434–448 | target_align | identity_and_fresh_geometry_associated | track4(target) | 49109 | -93° | 4.6 | 0.0 | yes | 4px |
| 17.96–18.00 | 449–450 | target_align | identity_and_fresh_geometry_associated | track6(target) | 52770 | -127° | 4.5 | 0.0 | yes | 4px |
| 18.04–18.56 | 451–464 | target_align | identity_and_fresh_geometry_associated | track2(target) | 53152 | -112° | 4.5 | 0.0 | yes | 4px |
| 18.60–18.68 | 465–467 | target_align | identity_and_fresh_geometry_associated | track4(target) | 55863 | -156° | 4.3 | 0.0 | yes | 5px |
| 18.72–18.96 | 468–474 | target_align | identity_and_fresh_geometry_associated | track2(target) | 56311 | -179° | 4.3 | 0.0 | yes | 6px |
| 19.00–19.20 | 475–480 | target_align | identity_and_fresh_geometry_associated | track4(target) | 58022 | +130° | 4.3 | 0.0 | yes | 4px |
| 19.24–19.60 | 481–490 | target_align | identity_and_fresh_geometry_associated | track6(target) | 59316 | +5° | 4.2 | 0.0 | yes | 0px |
| 19.64–20.20 | 491–505 | target_align | identity_and_fresh_geometry_associated | track7(target) | 61044 | -134° | 4.1 | 0.0 | yes | 2px |
| 20.24–25.28 | 506–632 | target_align | identity_and_fresh_geometry_associated | track4(target) | 65536 | +31° | 3.9 | 0.0 | yes | 1px |
| 25.32–26.04 | 633–651 | target_align | identity_and_fresh_geometry_associated | track7(target) | 98800 | -77° | 2.9 | 0.0 | yes | 2px |
| 26.08–26.72 | 652–668 | target_align | identity_and_fresh_geometry_associated | track4(target) | 107231 | +94° | 2.7 | 0.0 | yes | 6px |
| 26.76–26.88 | 669–672 | target_align | identity_and_fresh_geometry_associated | track7(target) | 116227 | -4° | 2.5 | 0.0 | yes | 0px |
| 26.92–27.16 | 673–679 | target_align | identity_and_fresh_geometry_associated | track4(target) | 118595 | -16° | 2.5 | 0.0 | yes | 0px |
| 27.20–27.40 | 680–685 | target_align | identity_and_fresh_geometry_associated | track7(target) | 122602 | -22° | 2.4 | 0.0 | yes | 0px |
| 27.44–27.52 | 686–688 | target_align | identity_and_fresh_geometry_associated | track10(target) | 126115 | -39° | 2.4 | 0.0 | yes | 0px |
| 27.56–27.92 | 689–698 | target_align | identity_and_fresh_geometry_associated | track7(target) | 127509 | -47° | 2.4 | 0.0 | yes | 2px |
| 27.96–27.96 | 699–699 | target_align | identity_and_fresh_geometry_associated | track10(target) | 133031 | +26° | 2.3 | 0.0 | yes | 4px |
| 28.00–28.24 | 700–706 | target_align | identity_and_fresh_geometry_associated | track7(target) | 133583 | +28° | 2.3 | 0.0 | yes | 4px |
| 28.28–30.40 | 707–760 | target_align | identity_and_fresh_geometry_associated | track10(target) | 138082 | +62° | 2.2 | 0.0 | yes | 5px |
| 30.44–32.36 | 761–809 | target_align | identity_and_fresh_geometry_associated | track18(target) | 199893 | +69° | 1.7 | 0.0 | yes | 4px |
| 32.40–33.56 | 810–839 | target_align | identity_and_fresh_geometry_associated | track18(target) | 223597 | +50° | 1.3 | 0.0 | yes | 0px |
| 33.60–33.68 | 840–842 | target_align | identity_and_fresh_geometry_associated | track18(target) | 222036 | -48° | 1.3 | 0.0 | yes | 0px |
| 33.72–39.00 | 843–975 | target_align | identity_and_fresh_geometry_associated | track19(target) | 222165 | -56° | 1.3 | 0.0 | yes | 0px |
| 39.04–42.60 | 976–1065 | target_align | identity_and_fresh_geometry_associated | track22(target) | 208238 | -160° | 0.9 | 0.0 | yes | 0px |
| 42.64–44.60 | 1066–1115 | ground_hold | own_estimator_not_airborne | track22(target) | 152333 | -43° | 0.7 | 0.0 | no | 0px |
| 44.64–44.64 | 1116–1116 | ground_hold | own_estimator_not_airborne | track22(target) | 153253 | -27° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

Camera survey continued although a usable target was in view:
- 0.00–0.20s scanning with 6064 px of target structure visible.

## Observer-truth visibility arcs

- target visible 0.00–44.64s (44.6s), peak 226901 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 0.0, "first_usable_px": 6064, "first_target_select_t": 0.2400000000002933, "first_target_approach_t": 0.2400000000002933, "delay_s": 0.2400000000002933, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 6, "scan_span_s": 0.20000000000024443, "limit_s": 1.0, "window": [0.0, 0.20000000000024443]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 0, "worst_span_s": 0.0, "limit_s": 0.5, "spans": []}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 1111, "frames_on_target": 1111, "fraction": 1.0, "limit": 0.95}
- PASS **E01.4_no_false_boat_claim_drives_selection** — {"frames": 0, "examples": []}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 939, "lost_frames": 24, "good_frames": 885, "lost_fraction": 0.0256, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 4.960000000006062, "metric_confirmed_at_start": true, "descent_span_s": 37.63999999993729}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 0.72, "limit_s": 1.0, "windows": [{"t0": 4.960000000006062, "t1": 5.120000000006257, "pad_err": 71.5629093874753}, {"t0": 5.840000000007137, "t1": 6.560000000008017, "pad_err": 45.59879384369722}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 3, "span_s": 44.64, "per_10s": 0.672, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 6, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.0, "limit_s": 6.0, "holds": []}
- PASS **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 0, "first_t": null, "parent_recovery_frames": 103}
- PASS **E01.10b_parent_recovery_share_below_limit** — {"share": 0.0922, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.0019258928479359838, "final_t": 44.63999999994313, "touchdown_s": 61.64999999994702}
- PASS **integrity.observer_join** — {"frames": 1117, "joined_frames": 1117}

Behavioural acceptance: **False** (1 failing checks).