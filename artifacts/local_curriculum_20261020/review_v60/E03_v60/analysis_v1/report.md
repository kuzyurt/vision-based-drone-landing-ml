# Flight narrative — E03_v60

Scenario `windows_review_E03_yaw` kind=beach seed=3200000005 distance=8.0m height=6.0m boat_speed=0.3m/s initial_target=visible fault=gimbal_pan mode=expert
Frames 1138, task duration 45.48s, outcome collision_failure.

Reading guide: `T` = observer-only truth about the real target in the actual rendered frame (structural pixels, visible structure parts), `sel` = the actor's selected candidate and the observer-truth instance its selected pixel falls inside. `bear err` = angle between camera optical axis and the true target bearing.

## Decision timeline

| t (s) | frames | intent | reason | sel | T px | bear err | h (m) | dist (m) | descent | pad err |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00–0.08 | 0–2 | scan | complete_observed_360_before_inspection_pass | none | 6045 | +0° | 6.5 | 8.1 | no | 21px |
| 0.12–0.28 | 3–7 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 6061 | +0° | 6.6 | 8.1 | no | 28px |
| 0.32–3.72 | 8–93 | target_inspect | target_likely_evidence_requires_inspection | track1(target) | 5986 | +0° | 6.6 | 8.1 | no | 18px |
| 3.76–3.80 | 94–95 | target_inspect | confirmed_boat_needs_fresh_pad_geometry | track1(target) | 15048 | +0° | 6.5 | 3.9 | no | 57px |
| 3.84–4.04 | 96–101 | target_align | identity_and_fresh_geometry_associated | track1(target) | 15447 | +0° | 6.5 | 3.8 | yes | 61px |
| 4.08–4.12 | 102–103 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 16642 | +1° | 6.5 | 3.4 | no | 65px |
| 4.16–4.28 | 104–107 | target_align | identity_and_fresh_geometry_associated | track1(target) | 17007 | +0° | 6.5 | 3.3 | yes | 67px |
| 4.32–4.84 | 108–121 | target_align | identity_and_fresh_geometry_associated | track3(target) | 17736 | -1° | 6.5 | 3.1 | yes | 69px |
| 4.88–4.88 | 122–122 | target_align | identity_and_fresh_geometry_associated | track1(target) | 18910 | -1° | 6.5 | 2.5 | yes | 10px |
| 4.92–4.92 | 123–123 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 19002 | -1° | 6.5 | 2.4 | no | 7px |
| 4.96–5.12 | 124–128 | target_align | identity_and_fresh_geometry_associated | track1(target) | 19082 | -1° | 6.5 | 2.4 | yes | 4px |
| 5.16–5.36 | 129–134 | target_align | identity_and_fresh_geometry_associated | track3(target) | 19580 | -0° | 6.5 | 2.2 | yes | 9px |
| 5.40–5.56 | 135–139 | target_align | identity_and_fresh_geometry_associated | track1(target) | 20128 | +1° | 6.5 | 2.0 | yes | 9px |
| 5.60–5.64 | 140–141 | target_align | identity_and_fresh_geometry_associated | track1(none) | 20845 | +0° | 6.5 | 1.8 | yes | 39px |
| 5.68–5.68 | 142–142 | target_align | identity_and_fresh_geometry_associated | track3(target) | 21162 | -0° | 6.5 | 1.7 | yes | 56px |
| 5.72–6.04 | 143–151 | target_align | identity_and_fresh_geometry_associated | track1(target) | 21386 | -0° | 6.5 | 1.6 | yes | 62px |
| 6.08–6.24 | 152–156 | target_align | identity_and_fresh_geometry_associated | track3(target) | 21533 | -1° | 6.5 | 1.2 | yes | 71px |
| 6.28–6.28 | 157–157 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track3(target) | 21921 | -1° | 6.5 | 1.0 | no | 69px |
| 6.32–6.44 | 158–161 | target_align | identity_and_fresh_geometry_associated | track3(target) | 21901 | -1° | 6.5 | 0.9 | yes | 67px |
| 6.48–6.60 | 162–165 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track3(target) | 21910 | -1° | 6.5 | 0.8 | no | 55px |
| 6.64–6.84 | 166–171 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 21697 | -2° | 6.6 | 0.7 | no | 34px |
| 6.88–7.08 | 172–177 | target_align | identity_and_fresh_geometry_associated | track1(target) | 21689 | -2° | 6.6 | 0.6 | yes | 40px |
| 7.12–7.20 | 178–180 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 21615 | +0° | 6.6 | 0.5 | no | 3px |
| 7.24–7.96 | 181–199 | target_align | identity_and_fresh_geometry_associated | track1(target) | 21681 | -1° | 6.6 | 0.4 | yes | 5px |
| 8.00–8.00 | 200–200 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 22147 | +15° | 6.5 | 0.3 | no | 5px |
| 8.04–8.08 | 201–202 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track3(target) | 22185 | +14° | 6.5 | 0.2 | no | 5px |
| 8.12–8.80 | 203–220 | target_align | identity_and_fresh_geometry_associated | track3(target) | 22275 | +4° | 6.5 | 0.2 | yes | 3px |
| 8.84–9.36 | 221–234 | target_align | identity_and_fresh_geometry_associated | track1(target) | 22563 | -10° | 6.5 | 0.1 | yes | 8px |
| 9.40–9.44 | 235–236 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 22871 | -22° | 6.4 | 0.1 | no | 5px |
| 9.48–9.68 | 237–242 | target_align | identity_and_fresh_geometry_associated | track1(target) | 22853 | -22° | 6.4 | 0.1 | yes | 5px |
| 9.72–10.20 | 243–255 | target_align | identity_and_fresh_geometry_associated | track3(target) | 22812 | -177° | 6.4 | 0.1 | yes | 7px |
| 10.24–10.64 | 256–266 | target_align | identity_and_fresh_geometry_associated | track1(target) | 23326 | +12° | 6.4 | 0.1 | yes | 7px |
| 10.68–10.68 | 267–267 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 24522 | -20° | 6.2 | 0.1 | no | 9px |
| 10.72–10.96 | 268–274 | target_align | identity_and_fresh_geometry_associated | track1(target) | 24555 | -23° | 6.2 | 0.1 | yes | 8px |
| 11.00–11.04 | 275–276 | target_align | identity_and_fresh_geometry_associated | track3(target) | 25162 | -24° | 6.2 | 0.1 | yes | 2px |
| 11.08–12.12 | 277–303 | target_align | identity_and_fresh_geometry_associated | track1(target) | 25322 | -34° | 6.2 | 0.1 | yes | 4px |
| 12.16–12.16 | 304–304 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track1(target) | 26965 | +27° | 6.0 | 0.0 | no | 3px |
| 12.20–13.04 | 305–326 | target_align | identity_and_fresh_geometry_associated | track1(target) | 26950 | +15° | 6.0 | 0.0 | yes | 4px |
| 13.08–13.08 | 327–327 | target_align | identity_and_fresh_geometry_associated | track3(target) | 28736 | -29° | 5.8 | 0.0 | yes | 6px |
| 13.12–17.88 | 328–447 | target_align | identity_and_fresh_geometry_associated | track1(target) | 28901 | -26° | 5.8 | 0.0 | yes | 7px |
| 17.92–18.12 | 448–453 | target_align | identity_and_fresh_geometry_associated | track3(target) | 45346 | -62° | 4.8 | 0.0 | yes | 4px |
| 18.16–19.28 | 454–482 | target_align | identity_and_fresh_geometry_associated | track1(target) | 46449 | +10° | 4.7 | 0.0 | yes | 1px |
| 19.32–19.32 | 483–483 | target_align | identity_and_fresh_geometry_associated | track3(target) | 51281 | +23° | 4.5 | 0.0 | yes | 1px |
| 19.36–20.12 | 484–503 | target_align | identity_and_fresh_geometry_associated | track1(target) | 51514 | +8° | 4.5 | 0.0 | yes | 2px |
| 20.16–20.28 | 504–507 | target_align | identity_and_fresh_geometry_associated | track3(target) | 56811 | -120° | 4.3 | 0.0 | yes | 2px |
| 20.32–20.56 | 508–514 | target_align | identity_and_fresh_geometry_associated | track1(target) | 57718 | -170° | 4.3 | 0.0 | yes | 3px |
| 20.60–20.72 | 515–518 | target_align | identity_and_fresh_geometry_associated | track3(target) | 59001 | +170° | 4.2 | 0.0 | yes | 6px |
| 20.76–20.80 | 519–520 | target_align | identity_and_fresh_geometry_associated | track6(target) | 59821 | +165° | 4.2 | 0.0 | yes | 4px |
| 20.84–21.52 | 521–538 | target_align | identity_and_fresh_geometry_associated | track3(target) | 60381 | +157° | 4.2 | 0.0 | yes | 4px |
| 21.56–21.84 | 539–546 | target_align | identity_and_fresh_geometry_associated | track8(target) | 64333 | -114° | 4.0 | 0.0 | yes | 0px |
| 21.88–22.12 | 547–553 | target_align | identity_and_fresh_geometry_associated | track3(target) | 65963 | -157° | 3.9 | 0.0 | yes | 2px |
| 22.16–22.48 | 554–562 | target_align | identity_and_fresh_geometry_associated | track8(target) | 67614 | +178° | 3.9 | 0.0 | yes | 0px |
| 22.52–22.64 | 563–566 | target_align | identity_and_fresh_geometry_associated | track6(target) | 69642 | -130° | 3.8 | 0.0 | yes | 1px |
| 22.68–22.92 | 567–573 | target_align | identity_and_fresh_geometry_associated | track3(target) | 70419 | -155° | 3.7 | 0.0 | yes | 1px |
| 22.96–23.00 | 574–575 | target_align | identity_and_fresh_geometry_associated | track8(target) | 71747 | -102° | 3.7 | 0.0 | yes | 1px |
| 23.04–23.32 | 576–583 | target_align | identity_and_fresh_geometry_associated | track3(target) | 72421 | -62° | 3.7 | 0.0 | yes | 1px |
| 23.36–23.44 | 584–586 | target_align | identity_and_fresh_geometry_associated | track8(target) | 74144 | -159° | 3.6 | 0.0 | yes | 0px |
| 23.48–24.76 | 587–619 | target_align | identity_and_fresh_geometry_associated | track3(target) | 75150 | -179° | 3.6 | 0.0 | yes | 0px |
| 24.80–24.80 | 620–620 | target_align | identity_and_fresh_geometry_associated | track8(target) | 84222 | -130° | 3.3 | 0.0 | yes | 2px |
| 24.84–27.72 | 621–693 | target_align | identity_and_fresh_geometry_associated | track3(target) | 84600 | -124° | 3.3 | 0.0 | yes | 2px |
| 27.76–27.84 | 694–696 | target_align | identity_and_fresh_geometry_associated | track8(target) | 110945 | -109° | 2.6 | 0.0 | yes | 1px |
| 27.88–28.28 | 697–707 | target_align | identity_and_fresh_geometry_associated | track3(target) | 112218 | -13° | 2.6 | 0.0 | yes | 0px |
| 28.32–28.32 | 708–708 | target_align | identity_and_fresh_geometry_associated | track8(target) | 117504 | +30° | 2.5 | 0.0 | yes | 2px |
| 28.36–29.28 | 709–732 | target_align | identity_and_fresh_geometry_associated | track3(target) | 118193 | +39° | 2.5 | 0.0 | yes | 2px |
| 29.32–29.36 | 733–734 | target_align | identity_and_fresh_geometry_associated | track14(target) | 133341 | -33° | 2.3 | 0.0 | yes | 0px |
| 29.40–29.60 | 735–740 | target_align | identity_and_fresh_geometry_associated | track8(target) | 134656 | -55° | 2.3 | 0.0 | yes | 2px |
| 29.64–30.28 | 741–757 | target_align | identity_and_fresh_geometry_associated | track3(target) | 139333 | -84° | 2.2 | 0.0 | yes | 4px |
| 30.32–30.40 | 758–760 | target_align | identity_and_fresh_geometry_associated | track14(target) | 154108 | +0° | 2.1 | 0.0 | yes | 0px |
| 30.44–30.68 | 761–767 | target_align | identity_and_fresh_geometry_associated | track8(target) | 156959 | +20° | 2.0 | 0.0 | yes | 0px |
| 30.72–31.00 | 768–775 | target_align | identity_and_fresh_geometry_associated | track3(target) | 163974 | +63° | 2.0 | 0.0 | yes | 2px |
| 31.04–31.32 | 776–783 | target_align | identity_and_fresh_geometry_associated | track8(target) | 172322 | +147° | 1.9 | 0.0 | yes | 0px |
| 31.36–32.32 | 784–808 | target_align | identity_and_fresh_geometry_associated | track3(target) | 180982 | -97° | 1.8 | 0.0 | yes | 1px |
| 32.36–32.72 | 809–818 | target_align | identity_and_fresh_geometry_associated | track8(target) | 218874 | +126° | 1.6 | 0.0 | yes | 3px |
| 32.76–33.56 | 819–839 | target_align | identity_and_fresh_geometry_associated | track17(target) | 226483 | +102° | 1.5 | 0.0 | yes | 0px |
| 33.60–34.76 | 840–869 | target_align | identity_and_fresh_geometry_associated | track17(target) | 223668 | -75° | 1.3 | 0.0 | yes | 0px |
| 34.80–38.72 | 870–968 | target_align | identity_and_fresh_geometry_associated | track17(target) | 222848 | +149° | 1.3 | 0.0 | yes | 0px |
| 38.76–39.76 | 969–994 | target_align | identity_and_fresh_geometry_associated | track21(target) | 215254 | +148° | 1.0 | 0.0 | yes | 0px |
| 39.80–42.36 | 995–1059 | target_align | identity_and_fresh_geometry_associated | track22(target) | 209362 | +89° | 0.9 | 0.0 | yes | 0px |
| 42.40–42.96 | 1060–1074 | target_align | identity_and_fresh_geometry_associated+descent_blocked_no_fresh_geometry | track22(target) | 170726 | -44° | 0.7 | 0.0 | no | 0px |
| 43.00–43.52 | 1075–1088 | local_downlook | arrest_descent_and_inspect_below | track22(target) | 170804 | -16° | 0.7 | 0.0 | no | 0px |
| 43.56–45.44 | 1089–1136 | local_downlook | bounded_fresh_downward_observation | track22(target) | 167849 | +20° | 0.7 | 0.0 | no | 0px |
| 45.48–45.48 | 1137–1137 | local_downlook | upward_clearance_unverified | track22(target) | 230400 | +10° | 0.7 | 0.3 | no | 0px |

## Contradictions found in the recording

A usable target was visible while a different object was being pursued:
- 5.60–5.64s: selected track1(none) while target had 20845 px of visible structure; selected object 114 px, target_probability 0.0187, wrong_object_probability 0.900.

Camera survey continued although a usable target was in view:
- 0.00–0.08s scanning with 6045 px of target structure visible.

## Observer-truth visibility arcs

- target visible 0.00–45.48s (45.5s), peak 230400 px, identity support 1.00

## Verdict

- PASS **E01.2_initial_opportunity_used** — {"first_usable_t": 0.0, "first_usable_px": 6045, "first_target_select_t": 0.12000000000014666, "first_target_approach_t": 0.12000000000014666, "delay_s": 0.12000000000014666, "limit_s": 1.0}
- PASS **E01.3_no_pointless_survey_while_opportunity_visible** — {"scan_frames": 3, "scan_span_s": 0.08000000000009777, "limit_s": 1.0, "window": [0.0, 0.08000000000009777]}
- PASS **E01.4_no_non_target_outranks_visible_target** — {"frames": 2, "worst_span_s": 0.040000000000048885, "limit_s": 0.5, "spans": [{"t0": 5.600000000006844, "t1": 5.640000000006893, "selected": "none", "selected_boat": true, "target_prob": 0.018654903396964073, "target_px": 20845, "selected_size_px": 114.00318145751953}]}
- PASS **E01.4_selection_continuity_after_lock** — {"frames_after": 1135, "frames_on_target": 1133, "fraction": 0.9982, "limit": 0.95}
- FAIL **E01.4_no_false_boat_claim_drives_selection** — {"frames": 2, "examples": [{"t": 5.600000000006844, "name": "none", "prob": 0.018654903396964073, "wrong": 0.8997204899787903, "size": 114.00318145751953}, {"t": 5.640000000006893, "name": "none", "prob": 0.018654903396964073, "wrong": 0.8997204899787903, "size": 114.00318145751953}]}
- PASS **E01.7_descent_keeps_useful_framing** — {"descent_frames": 940, "lost_frames": 39, "good_frames": 891, "lost_fraction": 0.0415, "limit": 0.1}
- PASS **E01.8_descent_started_after_identity_and_geometry** — {"first_descent_t": 3.840000000004693, "metric_confirmed_at_start": true, "descent_span_s": 38.519999999939074}
- PASS **E01.7_descent_framing_no_long_loss** — {"longest_lost_descent_s": 0.6, "limit_s": 1.0, "windows": [{"t0": 3.840000000004693, "t1": 4.040000000004937, "pad_err": 60.502066080424065}, {"t0": 4.160000000005084, "t1": 4.640000000005671, "pad_err": 67.26812023536856}, {"t0": 5.640000000006893, "t1": 6.240000000007626, "pad_err": 48.00260409602796}, {"t0": 6.320000000007724, "t1": 6.4400000000078705, "pad_err": 67.00186564566691}]}
- PASS **E01.9_no_chatter** — {"intent_changes": 3, "span_s": 45.48, "per_10s": 0.66, "limit": 6.0}
- FAIL **E01.9_descent_permission_stable** — {"reversals": 20, "limit": 3}
- PASS **E01.9_no_unnecessary_hold** — {"worst_hold_s": 0.0, "limit_s": 6.0, "holds": []}
- FAIL **E01.10_no_spurious_recovery** — {"recovery_executed_frames": 63, "first_t": 42.999999999942276, "parent_recovery_frames": 159}
- PASS **E01.10b_parent_recovery_share_below_limit** — {"share": 0.1397, "limit": 0.15, "note": "parent visibility-recovery flag while the expert owned the commands"}
- FAIL **E01.11_physical_termination** — {"outcome": "collision_failure", "landed": false, "armed": true, "final_clearance": 0.0072210378765921734, "final_t": 45.47999999994728, "touchdown_s": 62.07999999994602}
- PASS **integrity.observer_join** — {"frames": 1138, "joined_frames": 1138}

Behavioural acceptance: **False** (4 failing checks).

## Artifacts

- frames: `frames.csv` (1138 rows)
- events: `events.jsonl` (82)
- timeline: `timeline.png`
- annotated video: `review_annotated.mp4`
- contact sheets: `sheets/`
- video join consistent: True
