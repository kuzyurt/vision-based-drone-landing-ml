# Flight narrative — E01_nominal_v60b

Scenario `windows_review_E01_nominal` kind=beach seed=3200000000 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=visible fault=None mode=expert
Frames 1085, task duration 43.36s, outcome collision_failure.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.08 | 0–2 | scan | complete_observed_360_before_inspection_pass | none | 5884 | +0° | 6.5 | 8.2 | no | 20px |
| 0.12–0.12 | 3–3 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 5911 | +0° | 6.5 | 8.2 | no | 26px |
| 0.16–0.16 | 4–4 | inspect_candidate | plausible_boat_inspect_unknown_design | track2(target) | 5976 | -0° | 6.5 | 8.2 | no | 29px |
| 0.20–0.24 | 5–6 | target_inspect | target_likely_evidence_requires_inspection | track2(target) | 5989 | +0° | 6.5 | 8.2 | no | 30px |
| 0.28–2.16 | 7–54 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 5900 | +0° | 6.5 | 8.2 | no | 23px |
| 2.20–2.20 | 55–55 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 8197 | +0° | 6.5 | 6.7 | no | 16px |
| 2.24–2.28 | 56–57 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 8304 | +0° | 6.5 | 6.6 | no | 13px |
| 2.32–2.32 | 58–58 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 8576 | +0° | 6.5 | 6.5 | no | 7px |
| 2.36–2.36 | 59–59 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 8713 | +0° | 6.5 | 6.4 | no | 4px |
| 2.40–2.40 | 60–60 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 8858 | +0° | 6.5 | 6.4 | no | 2px |
| 2.44–2.52 | 61–63 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 8999 | +0° | 6.5 | 6.3 | no | 1px |
| 2.56–2.56 | 64–64 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 9444 | +0° | 6.5 | 6.1 | no | 7px |
| 2.60–2.64 | 65–66 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 9562 | +0° | 6.5 | 6.0 | no | 9px |
| 2.68–2.68 | 67–67 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 9880 | +0° | 6.5 | 5.9 | no | 12px |
| 2.72–2.76 | 68–69 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 10028 | +0° | 6.5 | 5.8 | no | 14px |
| 2.80–2.84 | 70–71 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 10346 | +0° | 6.5 | 5.6 | no | 17px |
| 2.88–3.16 | 72–79 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 10685 | +0° | 6.5 | 5.5 | no | 19px |
| 3.20–3.20 | 80–80 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 12144 | +0° | 6.5 | 4.9 | no | 36px |
| 3.24–3.24 | 81–81 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 12407 | +0° | 6.5 | 4.9 | no | 38px |
| 3.28–3.28 | 82–82 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 12525 | +0° | 6.5 | 4.8 | no | 40px |
| 3.32–3.32 | 83–83 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 12755 | +0° | 6.5 | 4.7 | no | 41px |
| 3.36–3.36 | 84–84 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 12968 | +0° | 6.5 | 4.6 | no | 43px |
| 3.40–3.64 | 85–91 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 13177 | +0° | 6.5 | 4.6 | no | 45px |
| 3.68–3.84 | 92–96 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 14635 | +0° | 6.5 | 4.1 | no | 55px |
| 3.88–3.88 | 97–97 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 15742 | +0° | 6.5 | 3.7 | no | 69px |
| 3.92–3.92 | 98–98 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 15939 | +0° | 6.5 | 3.7 | no | 71px |
| 3.96–4.00 | 99–100 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 16169 | +0° | 6.5 | 3.6 | no | 70px |
| 4.04–4.04 | 101–101 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 16534 | +0° | 6.5 | 3.5 | no | 68px |
| 4.08–4.12 | 102–103 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 16753 | +0° | 6.5 | 3.4 | no | 69px |
| 4.16–4.32 | 104–108 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 17133 | +0° | 6.5 | 3.3 | no | 71px |
| 4.36–4.40 | 109–110 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track3(target) | 17883 | +0° | 6.5 | 3.0 | no | 72px |
| 4.44–4.56 | 111–114 | target_inspect | target_likely_evidence_requires_inspection | track3(target) | 18225 | +0° | 6.5 | 2.9 | no | 74px |
| 4.60–5.00 | 115–125 | target_align | identity_and_fresh_geometry_associated | track3(target) | 18770 | +0° | 6.5 | 2.7 | yes | 73px |
| 5.04–5.32 | 126–133 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track3(target) | 19896 | +2° | 6.5 | 2.2 | no | 38px |
| 5.36–8.68 | 134–217 | target_align | identity_and_fresh_geometry_associated | track3(target) | 20766 | +0° | 6.4 | 2.0 | yes | 55px |
| 8.72–8.72 | 218–218 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track3(target) | 25051 | +9° | 6.2 | 0.1 | no | 10px |
| 8.76–28.00 | 219–700 | target_align | identity_and_fresh_geometry_associated | track3(target) | 25104 | +11° | 6.2 | 0.1 | yes | 11px |
| 28.04–40.24 | 701–1006 | target_align | identity_and_fresh_geometry_associated | track14(target) | 147161 | -74° | 2.1 | 0.0 | yes | 0px |
| 40.28–42.36 | 1007–1059 | scan | complete_observed_360_before_inspection_pass | none | 149933 | +12° | 0.7 | 0.0 | no | 0px |
| 42.40–43.32 | 1060–1083 | scan | complete_observed_360_before_inspection_pass | none | 184189 | +7° | 0.7 | 0.1 | no | 0px |
| 43.36–43.36 | 1084–1084 | scan | complete_observed_360_before_inspection_pass | none | 166030 | -14° | 0.7 | 0.2 | no | 0px |

## Contradictions found in the recording

Camera survey continued although a usable target was in view:
- 0.00–0.08s scanning with 5884 px of target structure visible.
- 40.28–43.36s scanning with 149933 px of target structure visible.

## Observer-truth visibility arcs

- target visible 0.00–43.36s (43.4s), peak 226890 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 0.0, "first_usable_px": 5884, "first_target_select_t": 0.12000000000014666, "first_target_approach_t": 0.12000000000014666, "delay_s": 0.12000000000014666, "limit_s": 1.0}
- FAIL **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 81, "scan_span_s": 43.35999999994186, "limit_s": 1.0, "window": [0.0, 43.35999999994186]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 0, "worst_span_s": 0.0, "limit_s": 0.5, "spans": []}
- FAIL **E01.4_selection_continuity_after_lock** — {"frames_after": 1082, "frames_on_target": 1004, "fraction": 0.9279, "limit": 0.95}
- PASS **E01.4_no_false_boat_claim_drives_selection** — {"frames": 0, "examples": []}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 883, "lost_frames": 32, "good_frames": 828, "lost_fraction": 0.0362, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 4.600000000005622, "metric_confirmed_at_start": true, "descent_span_s": 35.63999999994351}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 0.68, "limit_s": 1.0, "windows": [{"t0": 4.600000000005622, "t1": 4.960000000006062, "pad_err": 73.06161783043132}, {"t0": 5.360000000006551, "t1": 5.480000000006697, "pad_err": 54.536684901082864}, {"t0": 6.320000000007724, "t1": 7.000000000008555, "pad_err": 48.093658625644196}]}
- FAIL **E01.9_no_chatter** — {"intent_changes": 33, "span_s": 43.36, "per_10s": 7.611, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 6, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.0, "limit_s": 6.0, "holds": []}
- FAIL **E01.10_no_spurious_recovery** — {"recovery_frames": 137, "first_t": 0.12000000000014666, "metric_loss_frames": 127}
- FAIL **E01.11_physical_termination** — {"outcome": "collision_failure", "landed": false, "armed": true, "final_clearance": 0.005680211823346604, "final_t": 43.35999999994186, "touchdown_s": 58.699999999953896}
- PASS **integrity.observer_join** — {"frames": 1085, "joined_frames": 1085}

Behavioural acceptance: **False** (6 failing checks).