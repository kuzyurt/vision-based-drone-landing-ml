# Flight narrative — E05_v60

Scenario `windows_review_E05_visible_start` kind=beach seed=3200000050 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=visible fault=None mode=expert
Frames 1151, task duration 46.00s, outcome landed.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.08 | 0–2 | scan | complete_observed_360_before_inspection_pass | none | 6035 | +0° | 6.5 | 8.1 | no | 23px |
| 0.12–2.20 | 3–55 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 6069 | +0° | 6.5 | 8.1 | no | 30px |
| 2.24–3.36 | 56–84 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 8353 | +0° | 6.5 | 6.6 | no | 5px |
| 3.40–3.52 | 85–88 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 13328 | +0° | 6.5 | 4.5 | no | 49px |
| 3.56–3.68 | 89–92 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 14252 | +1° | 6.5 | 4.2 | no | 62px |
| 3.72–3.96 | 93–99 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 15169 | +0° | 6.5 | 3.9 | no | 74px |
| 4.00–4.00 | 100–100 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 16582 | +0° | 6.5 | 3.5 | no | 74px |
| 4.04–4.04 | 101–101 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 16733 | +0° | 6.5 | 3.4 | no | 74px |
| 4.08–4.08 | 102–102 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 16888 | +0° | 6.5 | 3.4 | no | 74px |
| 4.12–4.92 | 103–123 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 17066 | +0° | 6.5 | 3.3 | no | 73px |
| 4.96–6.92 | 124–173 | target_align | identity_and_fresh_geometry_associated | track2(target) | 19697 | +0° | 6.5 | 2.3 | yes | 71px |
| 6.96–6.96 | 174–174 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track2(target) | 22680 | -2° | 6.5 | 0.6 | no | 28px |
| 7.00–9.08 | 175–227 | target_align | identity_and_fresh_geometry_associated | track2(target) | 22660 | -1° | 6.5 | 0.5 | yes | 27px |
| 9.12–9.64 | 228–241 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track2(target) | 25509 | -8° | 6.1 | 0.1 | no | 6px |
| 9.68–10.28 | 242–257 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track2(target) | 26134 | -34° | 6.0 | 0.0 | no | 11px |
| 10.32–11.00 | 258–275 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track1(target) | 25143 | -26° | 6.1 | 0.0 | no | 64px |
| 11.04–14.12 | 276–353 | target_align | identity_and_fresh_geometry_associated | track1(target) | 26361 | +8° | 6.1 | 0.2 | yes | 2px |
| 14.16–18.76 | 354–469 | target_align | identity_and_fresh_geometry_associated | track2(target) | 30437 | -26° | 5.7 | 0.0 | yes | 5px |
| 18.80–18.84 | 470–471 | target_align | identity_and_fresh_geometry_associated | track4(target) | 46309 | -66° | 4.7 | 0.0 | yes | 4px |
| 18.88–19.20 | 472–480 | target_align | identity_and_fresh_geometry_associated | track2(target) | 46850 | -43° | 4.7 | 0.0 | yes | 3px |
| 19.24–19.56 | 481–489 | target_align | identity_and_fresh_geometry_associated | track4(target) | 49323 | -103° | 4.6 | 0.0 | yes | 4px |
| 19.60–22.52 | 490–563 | target_align | identity_and_fresh_geometry_associated | track2(target) | 51797 | -134° | 4.5 | 0.0 | yes | 5px |
| 22.56–24.24 | 564–606 | target_align | identity_and_fresh_geometry_associated | track4(target) | 67837 | +64° | 3.9 | 0.0 | yes | 2px |
| 24.28–25.24 | 607–631 | target_align | identity_and_fresh_geometry_associated | track2(target) | 77175 | -31° | 3.5 | 0.0 | yes | 2px |
| 25.28–27.56 | 632–689 | target_align | identity_and_fresh_geometry_associated | track5(target) | 82635 | -7° | 3.3 | 0.0 | yes | 2px |
| 27.60–28.08 | 690–702 | target_align | identity_and_fresh_geometry_associated | track8(target) | 103349 | +9° | 2.8 | 0.0 | yes | 0px |
| 28.12–29.28 | 703–732 | target_align | identity_and_fresh_geometry_associated | track5(target) | 109147 | -1° | 2.6 | 0.0 | yes | 1px |
| 29.32–29.72 | 733–743 | target_align | identity_and_fresh_geometry_associated | track8(target) | 126921 | -33° | 2.4 | 0.0 | yes | 4px |
| 29.76–30.20 | 744–755 | target_align | identity_and_fresh_geometry_associated | track5(target) | 132812 | -40° | 2.3 | 0.0 | yes | 3px |
| 30.24–30.72 | 756–768 | target_align | identity_and_fresh_geometry_associated | track8(target) | 140764 | +66° | 2.2 | 0.0 | yes | 2px |
| 30.76–31.56 | 769–789 | target_align | identity_and_fresh_geometry_associated | track13(target) | 151660 | +77° | 2.1 | 0.0 | yes | 3px |
| 31.60–31.84 | 790–796 | target_align | identity_and_fresh_geometry_associated | track9(target) | 173961 | +20° | 1.9 | 0.0 | yes | 0px |
| 31.88–34.40 | 797–860 | target_align | identity_and_fresh_geometry_associated | track7(target) | 183950 | +74° | 1.8 | 0.0 | yes | 2px |
| 34.44–37.36 | 861–934 | target_align | identity_and_fresh_geometry_associated | track15(target) | 222943 | +133° | 1.3 | 0.0 | yes | 0px |
| 37.40–43.92 | 935–1098 | target_align | identity_and_fresh_geometry_associated | track22(target) | 213703 | +95° | 1.0 | 0.0 | yes | 0px |
| 43.96–45.96 | 1099–1149 | ground_hold | own_estimator_not_airborne | track22(target) | 149321 | -62° | 0.7 | 0.0 | no | 0px |
| 46.00–46.00 | 1150–1150 | ground_hold | own_estimator_not_airborne | track22(target) | 149404 | -53° | 0.7 | 0.0 | no | 0px |

## Contradictions found in the recording

Camera survey continued although a usable target was in view:
- 0.00–0.08s scanning with 6035 px of target structure visible.

## Observer-truth visibility arcs

- target visible 0.00–46.00s (46.0s), peak 226882 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 0.0, "first_usable_px": 6035, "first_target_select_t": 0.12000000000014666, "first_target_approach_t": 0.12000000000014666, "delay_s": 0.12000000000014666, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 3, "scan_span_s": 0.08000000000009777, "limit_s": 1.0, "window": [0.0, 0.08000000000009777]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 0, "worst_span_s": 0.0, "limit_s": 0.5, "spans": []}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 1148, "frames_on_target": 1148, "fraction": 1.0, "limit": 0.95}
- PASS **E01.4_no_false_boat_claim_drives_selection** — {"frames": 0, "examples": []}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 926, "lost_frames": 26, "good_frames": 846, "lost_fraction": 0.0281, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 4.960000000006062, "metric_confirmed_at_start": true, "descent_span_s": 38.959999999934354}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 0.76, "limit_s": 1.0, "windows": [{"t0": 4.960000000006062, "t1": 5.160000000006306, "pad_err": 70.64347103589971}, {"t0": 5.960000000007284, "t1": 6.720000000008213, "pad_err": 51.52184002925361}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 5, "span_s": 46.0, "per_10s": 1.087, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 6, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.5200000000006355, "limit_s": 6.0, "holds": []}
- PASS **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 0, "first_t": null, "parent_recovery_frames": 140}
- PASS **E01.10b_parent_recovery_share_below_limit** — {"share": 0.1216, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- PASS **E01.11_physical_termination** — {"outcome": "landed", "landed": true, "armed": false, "final_clearance": -0.0019738178094023673, "final_t": 45.99999999994948, "touchdown_s": 60.44399999994983}
- PASS **integrity.observer_join** — {"frames": 1151, "joined_frames": 1151}

Behavioural acceptance: **False** (1 failing checks).

## Artifacts

- frames: `frames.csv` (1151 rows)
- events: `events.jsonl` (37)
- timeline: `timeline.png`
- annotated video: `review_annotated.mp4`
- contact sheets: `sheets/`
- video join consistent: True
