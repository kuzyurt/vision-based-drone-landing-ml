# Flight narrative — E08_v60

Scenario `windows_review_E08_search_far` kind=beach seed=3200000003 distance=52.0m height=8.0m boat_speed=0.3m/s initial_target=outside_camera fault=None mode=expert
Frames 1338, task duration 53.48s, outcome flying.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–20.60 | 0–515 | scan | complete_observed_360_before_inspection_pass | none | 0 | -140° | 8.5 | 52.2 | no | — |
| 20.64–20.72 | 516–518 | inspect_candidate | weak_extent_candidate_inspect_from_safe_standoff | track19(none) | 0 | -31° | 8.5 | 58.6 | no | — |
| 20.76–39.80 | 519–995 | inspect_candidate | plausible_boat_inspect_unknown_design | track19(target) | 118 | -29° | 8.5 | 58.6 | no | 322px |
| 39.84–40.52 | 996–1013 | inspect_candidate | plausible_boat_inspect_unknown_design | track19(target) | 301 | +0° | 8.4 | 32.9 | no | 2px |
| 40.56–48.96 | 1014–1224 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 322 | +0° | 8.4 | 31.7 | no | 2px |
| 49.00–49.04 | 1225–1226 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 1340 | +0° | 8.4 | 17.3 | no | 10px |
| 49.08–49.12 | 1227–1228 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 1362 | +0° | 8.4 | 17.1 | no | 10px |
| 49.16–49.44 | 1229–1236 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 1381 | +0° | 8.4 | 17.0 | no | 11px |
| 49.48–49.48 | 1237–1237 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 1481 | -0° | 8.4 | 16.4 | no | 9px |
| 49.52–49.96 | 1238–1249 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 1492 | -0° | 8.4 | 16.4 | no | 9px |
| 50.00–50.76 | 1250–1269 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 1667 | -0° | 8.4 | 15.6 | no | 6px |
| 50.80–50.80 | 1270–1270 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 2007 | -0° | 8.4 | 14.2 | no | 7px |
| 50.84–50.84 | 1271–1271 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 2025 | -0° | 8.4 | 14.1 | no | 6px |
| 50.88–50.96 | 1272–1274 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 2057 | -0° | 8.4 | 14.1 | no | 7px |
| 51.00–51.00 | 1275–1275 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 2127 | -0° | 8.4 | 13.9 | no | 10px |
| 51.04–51.44 | 1276–1286 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 2140 | -0° | 8.4 | 13.8 | no | 12px |
| 51.48–51.92 | 1287–1298 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 2409 | +0° | 8.4 | 13.0 | no | 24px |
| 51.96–51.96 | 1299–1299 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 2705 | +0° | 8.4 | 12.2 | no | 14px |
| 52.00–52.08 | 1300–1302 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 2720 | +0° | 8.4 | 12.1 | no | 14px |
| 52.12–52.12 | 1303–1303 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 2836 | +0° | 8.4 | 11.9 | no | 14px |
| 52.16–52.16 | 1304–1304 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 2851 | +0° | 8.4 | 11.9 | no | 15px |
| 52.20–52.60 | 1305–1315 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 2892 | +0° | 8.4 | 11.8 | no | 16px |
| 52.64–52.72 | 1316–1318 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 3285 | +0° | 8.4 | 11.0 | no | 30px |
| 52.76–52.88 | 1319–1322 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 3364 | +0° | 8.4 | 10.8 | no | 27px |
| 52.92–52.96 | 1323–1324 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 3524 | +0° | 8.4 | 10.6 | no | 29px |
| 53.00–53.24 | 1325–1331 | target_inspect | target_likely_evidence_requires_inspection | track19(target) | 3591 | +0° | 8.4 | 10.4 | no | 30px |
| 53.28–53.44 | 1332–1336 | target_inspect | target_likely_evidence_requires_inspection | track23(target) | 3883 | -0° | 8.4 | 10.0 | no | 37px |
| 53.48–53.48 | 1337–1337 | None | None | none | 4093 | -0° | 8.4 | 9.6 | no | 30px |

## Contradictions found in the recording

## Observer-truth visibility arcs

- target visible 17.52–20.60s (3.1s), peak 123 px, identity support 0.00
- target visible 20.72–53.48s (32.8s), peak 4093 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 39.83999999994282, "first_usable_px": 301, "first_target_select_t": 20.759999999987283, "first_target_approach_t": 20.759999999987283, "delay_s": -19.079999999955536, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 0, "scan_span_s": 0.0, "limit_s": 1.0, "window": null}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 0, "worst_span_s": 0.0, "limit_s": 0.5, "spans": []}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 819, "frames_on_target": 818, "fraction": 0.9988, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 3, "examples": [{"t": 20.639999999987563, "name": "none", "prob": 0.021078314632177353, "wrong": 0.2933513820171356, "size": 9.741961479187012}, {"t": 20.67999999998747, "name": "none", "prob": 0.021078314632177353, "wrong": 0.2933513820171356, "size": 9.741961479187012}, {"t": 20.719999999987376, "name": "none", "prob": 0.021078314632177353, "wrong": 0.2933513820171356, "size": 9.741961479187012}]}
- FAIL **E01.7_descent_keeps_useful_framing** — {"reason": "no descent permission frames"}
- FAIL **E01.8_descent_started_after_identity_and_geometry** — {"reason": "never descended"}
- PASS **E01.9_no_chatter** — {"intent_changes": 3, "span_s": 53.48, "per_10s": 0.561, "limit": 6.0}
- PASS **E01.9_descent_permission_stable** — {"reversals": 0, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 2.719999999993661, "limit_s": 6.0, "holds": [{"t0": 20.639999999987563, "t1": 23.359999999981223, "phase": "inspect_candidate"}]}
- PASS **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 0, "first_t": null, "parent_recovery_frames": 311}
- FAIL **E01.10b_parent_recovery_share_below_limit** — {"share": 0.2324, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- FAIL **E01.11_physical_termination** — {"outcome": "flying", "landed": false, "armed": true, "final_clearance": 7.726496575332459, "final_t": 53.4799999999923, "touchdown_s": null}
- PASS **integrity.observer_join** — {"frames": 1338, "joined_frames": 1338}

Behavioural acceptance: **False** (5 failing checks).

## Artifacts

- frames: `frames.csv` (1338 rows)
- events: `events.jsonl` (28)
- timeline: `timeline.png`
- annotated video: `review_annotated.mp4`
- contact sheets: `sheets/`
- video join consistent: True
