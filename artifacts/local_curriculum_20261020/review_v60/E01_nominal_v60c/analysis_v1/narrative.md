# Flight narrative — E01_nominal_v60c

Scenario `windows_review_E01_nominal` kind=beach seed=3200000000 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=visible fault=None mode=expert
Frames 1162, task duration 46.44s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.08 | 0–2 | scan | complete_observed_360_before_inspection_pass | none | 5930 | +0° | 6.5 | 8.2 | no | 20px |
| 0.12–0.16 | 3–4 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 5921 | +0° | 6.5 | 8.2 | no | 26px |
| 0.20–0.20 | 5–5 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 5994 | +0° | 6.5 | 8.2 | no | 30px |
| 0.24–0.36 | 6–9 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 5955 | +0° | 6.5 | 8.2 | no | 28px |
| 0.40–0.40 | 10–10 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 5899 | +0° | 6.5 | 8.2 | no | 1px |
| 0.44–3.28 | 11–82 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 5920 | +0° | 6.5 | 8.2 | no | 7px |
| 3.32–3.48 | 83–87 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 12716 | +0° | 6.5 | 4.7 | no | 41px |
| 3.52–3.56 | 88–89 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 13737 | +0° | 6.5 | 4.4 | no | 50px |
| 3.60–3.64 | 90–91 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 14160 | +0° | 6.5 | 4.2 | no | 54px |
| 3.68–3.68 | 92–92 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 14557 | +0° | 6.5 | 4.1 | no | 56px |
| 3.72–4.80 | 93–120 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 14807 | +0° | 6.5 | 4.0 | no | 58px |
| 4.84–5.16 | 121–129 | target_align | identity_and_fresh_geometry_associated | track2(target) | 19442 | +1° | 6.5 | 2.5 | yes | 70px |
| 5.20–5.20 | 130–130 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track2(target) | 20275 | -1° | 6.5 | 2.1 | no | 64px |
| 5.24–6.32 | 131–158 | target_align | identity_and_fresh_geometry_associated | track2(target) | 20325 | -0° | 6.5 | 2.1 | yes | 64px |
| 6.36–6.52 | 159–163 | target_align | identity_and_fresh_geometry_associated | track4(target) | 20800 | +2° | 6.5 | 1.5 | yes | 11px |
| 6.56–6.60 | 164–165 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track4(target) | 21419 | -0° | 6.5 | 1.3 | no | 55px |
| 6.64–6.72 | 166–168 | target_align | identity_and_fresh_geometry_associated | track4(target) | 21568 | -1° | 6.5 | 1.3 | yes | 63px |
| 6.76–7.40 | 169–185 | target_align | identity_and_fresh_geometry_associated | track2(target) | 21720 | -0° | 6.5 | 1.1 | yes | 67px |
| 7.44–7.60 | 186–190 | target_align | identity_and_fresh_geometry_associated | track4(target) | 22301 | -1° | 6.5 | 0.6 | yes | 36px |
| 7.64–7.80 | 191–195 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track4(target) | 22254 | -3° | 6.5 | 0.5 | no | 16px |
| 7.84–8.12 | 196–203 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track2(target) | 22395 | -3° | 6.5 | 0.4 | no | 24px |
| 8.16–10.88 | 204–272 | target_align | identity_and_fresh_geometry_associated | track2(target) | 22522 | -0° | 6.5 | 0.3 | yes | 52px |
| 10.92–10.92 | 273–273 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track2(target) | 26657 | -20° | 6.0 | 0.1 | no | 5px |
| 10.96–15.92 | 274–398 | target_align | identity_and_fresh_geometry_associated | track2(target) | 26726 | -17° | 6.0 | 0.1 | yes | 5px |
| 15.96–16.56 | 399–414 | target_align | identity_and_fresh_geometry_associated | track4(target) | 40950 | -39° | 5.0 | 0.0 | yes | 2px |
| 16.60–17.44 | 415–436 | target_align | identity_and_fresh_geometry_associated | track2(target) | 44812 | +6° | 4.8 | 0.0 | yes | 1px |
| 17.48–17.48 | 437–437 | target_align | identity_and_fresh_geometry_associated | track5(target) | 48372 | -88° | 4.6 | 0.0 | yes | 4px |
| 17.52–18.68 | 438–467 | target_align | identity_and_fresh_geometry_associated | track2(target) | 48496 | -80° | 4.6 | 0.0 | yes | 5px |
| 18.72–18.76 | 468–469 | target_align | identity_and_fresh_geometry_associated | track7(target) | 54268 | -157° | 4.4 | 0.0 | yes | 3px |
| 18.80–18.80 | 470–470 | target_align | identity_and_fresh_geometry_associated | track4(target) | 54620 | -166° | 4.4 | 0.0 | yes | 3px |
| 18.84–19.08 | 471–477 | target_align | identity_and_fresh_geometry_associated | track2(target) | 54977 | -174° | 4.4 | 0.0 | yes | 3px |
| 19.12–19.32 | 478–483 | target_align | identity_and_fresh_geometry_associated | track4(target) | 56718 | -169° | 4.3 | 0.0 | yes | 2px |
| 19.36–19.60 | 484–490 | target_align | identity_and_fresh_geometry_associated | track2(target) | 58645 | +75° | 4.2 | 0.0 | yes | 1px |
| 19.64–20.32 | 491–508 | target_align | identity_and_fresh_geometry_associated | track4(target) | 60622 | -46° | 4.2 | 0.0 | yes | 0px |
| 20.36–21.12 | 509–528 | target_align | identity_and_fresh_geometry_associated | track2(target) | 64831 | +156° | 4.0 | 0.0 | yes | 3px |
| 21.16–21.24 | 529–531 | target_align | identity_and_fresh_geometry_associated | track4(target) | 67971 | -117° | 3.8 | 0.0 | yes | 1px |
| 21.28–23.68 | 532–592 | target_align | identity_and_fresh_geometry_associated | track2(target) | 68513 | -110° | 3.8 | 0.0 | yes | 2px |
| 23.72–23.92 | 593–598 | target_align | identity_and_fresh_geometry_associated | track5(target) | 83687 | +180° | 3.3 | 0.0 | yes | 4px |
| 23.96–25.56 | 599–639 | target_align | identity_and_fresh_geometry_associated | track2(target) | 85345 | -120° | 3.2 | 0.0 | yes | 3px |
| 25.60–25.68 | 640–642 | target_align | identity_and_fresh_geometry_associated | track4(target) | 99785 | -107° | 2.8 | 0.0 | yes | 0px |
| 25.72–25.84 | 643–646 | target_align | identity_and_fresh_geometry_associated | track5(target) | 101098 | -112° | 2.8 | 0.0 | yes | 1px |
| 25.88–26.56 | 647–664 | target_align | identity_and_fresh_geometry_associated | track2(target) | 102755 | -114° | 2.8 | 0.0 | yes | 1px |
| 26.60–27.28 | 665–682 | target_align | identity_and_fresh_geometry_associated | track4(target) | 110469 | -158° | 2.6 | 0.0 | yes | 1px |
| 27.32–28.16 | 683–704 | target_align | identity_and_fresh_geometry_associated | track2(target) | 120189 | -164° | 2.5 | 0.0 | yes | 4px |
| 28.20–28.52 | 705–713 | target_align | identity_and_fresh_geometry_associated | track4(target) | 131832 | -84° | 2.3 | 0.0 | yes | 0px |
| 28.56–28.88 | 714–722 | target_align | identity_and_fresh_geometry_associated | track2(target) | 138148 | +102° | 2.2 | 0.0 | yes | 2px |
| 28.92–29.20 | 723–730 | target_align | identity_and_fresh_geometry_associated | track4(target) | 146070 | +107° | 2.1 | 0.0 | yes | 4px |
| 29.24–29.24 | 731–731 | target_align | identity_and_fresh_geometry_associated | track11(target) | 153939 | +54° | 2.1 | 0.0 | yes | 2px |
| 29.28–29.52 | 732–738 | target_align | identity_and_fresh_geometry_associated | track2(target) | 154979 | +44° | 2.0 | 0.0 | yes | 2px |
| 29.56–29.88 | 739–747 | target_align | identity_and_fresh_geometry_associated | track4(target) | 162202 | -170° | 2.0 | 0.0 | yes | 2px |
| 29.92–31.32 | 748–783 | target_align | identity_and_fresh_geometry_associated | track2(target) | 171745 | -179° | 1.9 | 0.0 | yes | 2px |
| 31.36–31.48 | 784–787 | target_align | identity_and_fresh_geometry_associated | track16(target) | 220842 | +164° | 1.6 | 0.0 | yes | 6px |
| 31.52–31.72 | 788–793 | target_align | identity_and_fresh_geometry_associated | track19(target) | 226719 | -170° | 1.6 | 0.0 | yes | 0px |
| 31.76–32.00 | 794–800 | target_align | identity_and_fresh_geometry_associated | track16(target) | 226341 | +179° | 1.5 | 0.0 | yes | 0px |
| 32.04–32.56 | 801–814 | target_align | identity_and_fresh_geometry_associated | track19(target) | 225625 | +161° | 1.4 | 0.0 | yes | 0px |
| 32.60–44.36 | 815–1109 | target_align | identity_and_fresh_geometry_associated | track13(target) | 223613 | -113° | 1.3 | 0.0 | yes | 0px |
| 44.40–46.40 | 1110–1160 | ground_hold | own_estimator_not_airborne | track13(target) | 149759 | -44° | 0.7 | 0.0 | no | 0px |
| 46.44–46.44 | 1161–1161 | ground_hold | own_estimator_not_airborne | track13(target) | 149778 | -17° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

Camera survey continued although a usable target was in view:
- 0.00–0.08s scanning with 5930 px of target structure visible.

## Observer-truth visibility arcs

- target visible 0.00–46.44s (46.4s), peak 226824 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 0.0, "first_usable_px": 5930, "first_target_select_t": 0.12000000000014666, "first_target_approach_t": 0.12000000000014666, "delay_s": 0.12000000000014666, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 3, "scan_span_s": 0.08000000000009777, "limit_s": 1.0, "window": [0.0, 0.08000000000009777]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 0, "worst_span_s": 0.0, "limit_s": 0.5, "spans": []}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 1159, "frames_on_target": 1159, "fraction": 1.0, "limit": 0.95}
- PASS **E01.4_no_false_boat_claim_drives_selection** — {"frames": 0, "examples": []}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 972, "lost_frames": 37, "good_frames": 919, "lost_fraction": 0.0381, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 4.840000000005915, "metric_confirmed_at_start": true, "descent_span_s": 39.519999999935735}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 0.72, "limit_s": 1.0, "windows": [{"t0": 4.840000000005915, "t1": 5.160000000006306, "pad_err": 69.58807369082723}, {"t0": 5.240000000006404, "t1": 5.360000000006551, "pad_err": 63.50196847342608}, {"t0": 6.520000000007968, "t1": 6.520000000007968, "pad_err": 47.5}, {"t0": 6.640000000008115, "t1": 7.360000000008995, "pad_err": 62.517997408746226}, {"t0": 8.160000000009973, "t1": 8.28000000001012, "pad_err": 51.61879502661797}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 11, "span_s": 46.44, "per_10s": 2.369, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 10, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.0, "limit_s": 6.0, "holds": []}
- PASS **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 0, "first_t": null, "parent_recovery_frames": 102}
- PASS **E01.10b_parent_recovery_share_below_limit** — {"share": 0.0878, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.003362362813821018, "final_t": 46.43999999995158, "touchdown_s": 60.66699999994931}
- PASS **integrity.observer_join** — {"frames": 1162, "joined_frames": 1162}

Behavioural acceptance: **False** (1 failing checks).