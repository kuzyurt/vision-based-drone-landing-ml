# Benchmark v63 — landing and finding, with and without radio

Generated 2026-10-23T12:21:26.529896+00:00 by `run_benchmark_v63.py`.  v62's tier organisation is preserved; this file re-cuts the same evidence by outcome and information condition.

## Headline

| cell | question | basis | n | primary | secondary |
|---|---|---|---:|---|---|
| **L-R** | Does the aircraft land on the boat with the radio channel available? | v60 | - | blocked | no radio input (see detail) |
| **L-R** | Does the aircraft land on the boat with the radio channel available? | r15 | 13 | physical 3/13 (23%) [8-50] | qualified 3/13 (23%) [8-50] |
| **L-0** | Does the aircraft land on the boat with no boat-position channel? | v60 | 16 | physical 9/16 (56%) [33-77] | qualified 7/12 (58%) [32-81] |
| **L-0** | Does the aircraft land on the boat with no boat-position channel? | r15 | 13 | physical 2/13 (15%) [4-42] | qualified 2/13 (15%) [4-42] |
| **F-R** | How well does it find the boat with the radio channel available? | v60 | - | blocked | no radio input (see detail) |
| **F-R** | How well does it find the boat with the radio channel available? | r15 | 13 | metric 4/13 (31%) [13-58] | sustained 3/13 (23%) [8-50] |
| **F-0** | How well does it find the boat with no boat-position channel? | v60 | 12 | decision lock 11/12 (92%) [65-98] | continuity>=.98 9/12 (75%) [47-91] |
| **F-0** | How well does it find the boat with no boat-position channel? | r15 | 13 | metric 2/13 (15%) [4-42] | sustained 2/13 (15%) [4-42] |

Rates are k/n with Wilson 95% in brackets.  v60 and R15 are never pooled: different controller, different scenario mix, different radio implementation.

## L-R — Does the aircraft land on the boat with the radio channel available?

### v60

**blocked.** no radio input exists in the v60 stack: expert_adapter_v60.py:419 sets observation['beacon'] = {valid: False, ...} before the protocol runs; PublicState and CandidateV60 have no radio field; 0 beacon-valid frames in all 21 recordings with steps

### r15

* n=13, physical 3/13 (23%) [8-50], qualified 3/13 (23%) [8-50] of analysed, unanalysed 0, collisions 0, median time to land 43.34 s

| flight | scenario | land | qualified | tier | metric frames | time (s) | abort |
|---|---|---:|---|---|---:|---:|---|
| `speed_0p6_radio` | speed_ladder 8.86 m / 1.97 m | 0 | 0 | - | 0 | 175.06 | deadline_or_manual_hold |
| `speed_1p0_radio` | speed_ladder 9.07 m / 1.97 m | 0 | 0 | - | 0 | 125.0 | bounded_recovery_exhausted |
| `speed_1p4_radio` | speed_ladder 9.22 m / 1.97 m | 0 | 0 | - | 0 | 101.11 | bounded_recovery_exhausted |
| `speed_1p8_radio` | speed_ladder 9.39 m / 1.97 m | 0 | 0 | - | 0 | 151.92 | bounded_recovery_exhausted |
| `speed_2p2_radio` | speed_ladder 9.53 m / 1.97 m | 0 | 0 | - | 0 | 153.45 | bounded_recovery_exhausted |
| `speed_2p8_radio` | speed_ladder 9.71 m / 1.97 m | 0 | 0 | - | 0 | 38.66 | bounded_recovery_exhausted |
| `close_oblique_radio` | harder_start 4.14 m / 1.69 m | 0 | 0 | - | 1 | 40.36 | bounded_recovery_exhausted |
| `far20_cloudy_radio` | harder_start 20.93 m / 4.49 m | 0 | 0 | - | 0 | 175.07 | deadline_or_manual_hold |
| `far40_late_radio` | harder_start 41.37 m / 6.48 m | 0 | 0 | - | 0 | 175.05 | deadline_or_manual_hold |
| `visible_0p6_radio` | visible_speed_ladder 8.92 m / 4.48 m | 1 | 1 | - | 743 | 41.14 | landed |
| `visible_1p4_radio` | visible_speed_ladder 9.15 m / 4.48 m | 0 | 0 | - | 0 | 175.07 | deadline_or_manual_hold |
| `midpoint_radio` | speed_boundary 9.05 m / 4.48 m | 1 | 1 | - | 774 | 43.34 | landed |
| `confirm_radio` | changed_start_confirmation 10.92 m / 4.99 m | 1 | 1 | - | 943 | 51.59 | landed |

| start stratum | n | landed | metric | sustained |
|---|---:|---|---|---|
| visible_start | 4 | 3/4 (75%) [30-95] | 3/4 (75%) [30-95] | 3/4 (75%) [30-95] |
| hard_start | 9 | 0/9 (0%) [0-30] | 1/9 (11%) [2-44] | 0/9 (0%) [0-30] |

## L-0 — Does the aircraft land on the boat with no boat-position channel?

### v60

* n=16, physical 9/16 (56%) [33-77], policy-attributable 9/14 (64%) [39-84] (2 harness crashes excluded), qualified 7/12 (58%) [32-81] of analysed, unanalysed 4, collisions 2, median time to land 51.53 s

| flight | scenario | land | qualified | tier | metric frames | time (s) | abort |
|---|---|---:|---|---|---:|---:|---|
| `E01_nominal_v60b` | windows_review_E01_nominal 8.0 m / 6.0 m | 0 | 0 | REJECT | 823 | 38.78 | collision_failure |
| `E01_nominal_v60c` | windows_review_E01_nominal 8.0 m / 6.0 m | 1 | 1 | SILVER | 947 | 40.71 | landed |
| `E02_v60` | windows_review_E02_distractors 20.0 m / 6.0 m | 0 | 0 | REJECT | 0 | None | development_diagnostic_stop |
| `E03_v60` | windows_review_E03_yaw 8.0 m / 6.0 m | 0 | 0 | REJECT | 826 | 42.04 | collision_failure |
| `E03_v60_forced` | windows_review_E03_yaw 8.0 m / 6.0 m | 1 | 1 | SILVER | 904 | 41.65 | landed |
| `E03_v60_ondeck` | windows_review_E03_yaw 8.0 m / 6.0 m | 0 | - | - | 877 | None | crashed_before_terminal_result |
| `E03_v60_repair` | windows_review_E03_yaw 8.0 m / 6.0 m | 1 | 1 | SILVER | 990 | 42.99 | landed |
| `E03_v60_rest` | windows_review_E03_yaw 8.0 m / 6.0 m | 1 | - | - | 963 | None | landed |
| `E04_v60` | windows_review_E04_close_loss 8.0 m / 6.0 m | 1 | 1 | SILVER | 1325 | 60.08 | landed |
| `E05_v60` | windows_review_E05_visible_start 8.0 m / 6.0 m | 1 | 1 | SILVER | 927 | 40.48 | landed |
| `E06_v60` | windows_review_E06_search_near 8.0 m / 6.0 m | 1 | 1 | SILVER | 1426 | 82.4 | landed |
| `E07_v60` | windows_review_E07_search_mid 28.0 m / 6.0 m | 1 | 1 | SILVER | 911 | 71.45 | landed |
| `E08_v60` | windows_review_E08_search_far 52.0 m / 8.0 m | 0 | 0 | REJECT | 0 | None | development_diagnostic_stop |
| `E08_v61` | windows_review_E08_search_far 52.0 m / 8.0 m | 0 | - | - | 0 | None | crashed_before_terminal_result |
| `E08_v61b` | windows_review_E08_search_far 52.0 m / 8.0 m | 0 | - | - | 0 | None | development_diagnostic_stop |
| `E08_v61c` | windows_review_E08_search_far 52.0 m / 8.0 m | 1 | 0 | REJECT | 1564 | 167.2 | landed |

| distance band | n | landed | qualified | decision lock | continuity |
|---|---:|---|---|---:|---:|
| near_<=10m | 10 | 7/10 (70%) [40-89] | 6/8 (75%) [41-93] | 8/8 (100%) [68-100] | 1.0 |
| mid_11_24m | 1 | 0/1 (0%) [0-79] | 0/1 (0%) [0-79] | 0/1 (0%) [0-79] | 0.01 |
| far_>=25m | 5 | 2/5 (40%) [12-77] | 1/3 (33%) [6-79] | 3/3 (100%) [44-100] | 1.0 |

### r15

* n=13, physical 2/13 (15%) [4-42], qualified 2/13 (15%) [4-42] of analysed, unanalysed 0, collisions 0, median time to land 36.5 s

| flight | scenario | land | qualified | tier | metric frames | time (s) | abort |
|---|---|---:|---|---|---:|---:|---|
| `speed_0p6_visual` | speed_ladder 8.92 m / 1.97 m | 0 | 0 | - | 0 | 135.52 | bounded_recovery_exhausted |
| `speed_1p0_visual` | speed_ladder 9.07 m / 1.97 m | 0 | 0 | - | 0 | 81.78 | bounded_recovery_exhausted |
| `speed_1p4_visual` | speed_ladder 9.18 m / 1.97 m | 0 | 0 | - | 0 | 173.44 | bounded_recovery_exhausted |
| `speed_1p8_visual` | speed_ladder 9.37 m / 1.97 m | 0 | 0 | - | 0 | 175.05 | deadline_or_manual_hold |
| `speed_2p2_visual` | speed_ladder 9.53 m / 1.97 m | 0 | 0 | - | 0 | 120.06 | bounded_recovery_exhausted |
| `speed_2p8_visual` | speed_ladder 9.72 m / 1.97 m | 0 | 0 | - | 0 | 39.52 | bounded_recovery_exhausted |
| `close_oblique_visual` | harder_start 4.13 m / 1.69 m | 0 | 0 | - | 0 | 85.55 | bounded_recovery_exhausted |
| `far20_cloudy_visual` | harder_start 20.98 m / 4.5 m | 0 | 0 | - | 0 | 175.05 | deadline_or_manual_hold |
| `far40_late_visual` | harder_start 41.53 m / 6.48 m | 0 | 0 | - | 0 | 175.08 | deadline_or_manual_hold |
| `visible_0p6_visual` | visible_speed_ladder 8.91 m / 4.47 m | 0 | 0 | - | 0 | 175.05 | deadline_or_manual_hold |
| `visible_unpowered_visual` | stationary_diagnostic 8.52 m / 4.48 m | 1 | 1 | - | 706 | 37.15 | landed |
| `visible_slow_visual` | speed_boundary 8.81 m / 4.48 m | 1 | 1 | - | 690 | 35.86 | landed |
| `confirm_visual` | changed_start_confirmation 10.86 m / 4.99 m | 0 | 0 | - | 0 | 175.06 | deadline_or_manual_hold |

| start stratum | n | landed | metric | sustained |
|---|---:|---|---|---|
| visible_start | 4 | 2/4 (50%) [15-85] | 2/4 (50%) [15-85] | 2/4 (50%) [15-85] |
| hard_start | 9 | 0/9 (0%) [0-30] | 0/9 (0%) [0-30] | 0/9 (0%) [0-30] |

## F-R — How well does it find the boat with the radio channel available?

### v60

**blocked.** no radio input exists in the v60 stack: expert_adapter_v60.py:419 sets observation['beacon'] = {valid: False, ...} before the protocol runs; PublicState and CandidateV60 have no radio field; 0 beacon-valid frames in all 21 recordings with steps

### r15

* n=13, metric acquisition 4/13 (31%) [13-58], sustained 3/13 (23%) [8-50], median metric frames 0.0 (found 758.5), median flight 125.0 s

| flight | group | metric frames | found | flight s | status |
|---|---|---:|---:|---:|---|
| `speed_0p6_radio` | speed_ladder | 0 | 0 | 175.06 | deadline_or_manual_hold |
| `speed_1p0_radio` | speed_ladder | 0 | 0 | 125.0 | bounded_recovery_exhausted |
| `speed_1p4_radio` | speed_ladder | 0 | 0 | 101.11 | bounded_recovery_exhausted |
| `speed_1p8_radio` | speed_ladder | 0 | 0 | 151.92 | bounded_recovery_exhausted |
| `speed_2p2_radio` | speed_ladder | 0 | 0 | 153.45 | bounded_recovery_exhausted |
| `speed_2p8_radio` | speed_ladder | 0 | 0 | 38.66 | bounded_recovery_exhausted |
| `close_oblique_radio` | harder_start | 1 | 1 | 40.36 | bounded_recovery_exhausted |
| `far20_cloudy_radio` | harder_start | 0 | 0 | 175.07 | deadline_or_manual_hold |
| `far40_late_radio` | harder_start | 0 | 0 | 175.05 | deadline_or_manual_hold |
| `visible_0p6_radio` | visible_speed_ladder | 743 | 1 | 41.14 | landed |
| `visible_1p4_radio` | visible_speed_ladder | 0 | 0 | 175.07 | deadline_or_manual_hold |
| `midpoint_radio` | speed_boundary | 774 | 1 | 43.34 | landed |
| `confirm_radio` | changed_start_confirmation | 943 | 1 | 51.59 | landed |

| start stratum | n | landed | metric | sustained |
|---|---:|---|---|---|
| visible_start | 4 | 3/4 (75%) [30-95] | 3/4 (75%) [30-95] | 3/4 (75%) [30-95] |
| hard_start | 9 | 0/9 (0%) [0-30] | 1/9 (11%) [2-44] | 0/9 (0%) [0-30] |

## F-0 — How well does it find the boat with no boat-position channel?

### v60

* n=12, decision lock 11/12 (92%) [65-98], continuity>=.98 9/12 (75%) [47-91], metric tracked 10/12 (83%) [55-95], median lock 0.2 s, median continuity 1.0

| flight | dist/height | lock s | continuity | tracked | first tracked s | touchdown s | tier |
|---|---|---:|---:|---:|---:|---:|---|
| `E01_nominal_v60b` | 8.0 / 6.0 m | 0.12 | 0.9279 | 1 | 3.16 | 38.78 | REJECT |
| `E01_nominal_v60c` | 8.0 / 6.0 m | 0.12 | 1.0 | 1 | 4.6 | 40.71 | SILVER |
| `E02_v60` | 20.0 / 6.0 m | 17.08 | 0.0101 | 0 | - | - | REJECT |
| `E03_v60` | 8.0 / 6.0 m | 0.12 | 1.0 | 1 | 3.72 | 42.04 | REJECT |
| `E03_v60_forced` | 8.0 / 6.0 m | 0.24 | 1.0 | 1 | 3.24 | 41.65 | SILVER |
| `E03_v60_repair` | 8.0 / 6.0 m | 0.2 | 1.0 | 1 | 4.2 | 42.99 | SILVER |
| `E04_v60` | 8.0 / 6.0 m | 0.08 | 1.0 | 1 | 3.4 | 60.08 | SILVER |
| `E05_v60` | 8.0 / 6.0 m | 0.12 | 1.0 | 1 | 3.64 | 40.48 | SILVER |
| `E06_v60` | 8.0 / 6.0 m | 17.48 | 1.0 | 1 | 24.92 | 82.4 | SILVER |
| `E07_v60` | 28.0 / 6.0 m | 18.08 | 1.0 | 1 | 36.72 | 71.45 | SILVER |
| `E08_v60` | 52.0 / 8.0 m | 20.76 | 0.9988 | 0 | - | - | REJECT |
| `E08_v61c` | 52.0 / 8.0 m | 20.76 | 0.9369 | 1 | 54.8 | 167.2 | REJECT |

| distance band | n | landed | qualified | decision lock | continuity |
|---|---:|---|---|---:|---:|
| near_<=10m | 8 | 6/8 (75%) [41-93] | 6/8 (75%) [41-93] | 8/8 (100%) [68-100] | 1.0 |
| mid_11_24m | 1 | 0/1 (0%) [0-79] | 0/1 (0%) [0-79] | 0/1 (0%) [0-79] | 0.01 |
| far_>=25m | 3 | 2/3 (67%) [21-94] | 1/3 (33%) [6-79] | 3/3 (100%) [44-100] | 1.0 |

### r15

* n=13, metric acquisition 2/13 (15%) [4-42], sustained 2/13 (15%) [4-42], median metric frames 0.0 (found 698.0), median flight 135.52 s

| flight | group | metric frames | found | flight s | status |
|---|---|---:|---:|---:|---|
| `speed_0p6_visual` | speed_ladder | 0 | 0 | 135.52 | bounded_recovery_exhausted |
| `speed_1p0_visual` | speed_ladder | 0 | 0 | 81.78 | bounded_recovery_exhausted |
| `speed_1p4_visual` | speed_ladder | 0 | 0 | 173.44 | bounded_recovery_exhausted |
| `speed_1p8_visual` | speed_ladder | 0 | 0 | 175.05 | deadline_or_manual_hold |
| `speed_2p2_visual` | speed_ladder | 0 | 0 | 120.06 | bounded_recovery_exhausted |
| `speed_2p8_visual` | speed_ladder | 0 | 0 | 39.52 | bounded_recovery_exhausted |
| `close_oblique_visual` | harder_start | 0 | 0 | 85.55 | bounded_recovery_exhausted |
| `far20_cloudy_visual` | harder_start | 0 | 0 | 175.05 | deadline_or_manual_hold |
| `far40_late_visual` | harder_start | 0 | 0 | 175.08 | deadline_or_manual_hold |
| `visible_0p6_visual` | visible_speed_ladder | 0 | 0 | 175.05 | deadline_or_manual_hold |
| `visible_unpowered_visual` | stationary_diagnostic | 706 | 1 | 37.15 | landed |
| `visible_slow_visual` | speed_boundary | 690 | 1 | 35.86 | landed |
| `confirm_visual` | changed_start_confirmation | 0 | 0 | 175.06 | deadline_or_manual_hold |

| start stratum | n | landed | metric | sustained |
|---|---:|---|---|---|
| visible_start | 4 | 2/4 (50%) [15-85] | 2/4 (50%) [15-85] | 2/4 (50%) [15-85] |
| hard_start | 9 | 0/9 (0%) [0-30] | 0/9 (0%) [0-30] | 0/9 (0%) [0-30] |

## Optional metrics (per basis, not a score)

| basis | metric | value | note |
|---|---|---:|---|
| v60 | median time to first truth lock, near start (<=10 m) | 0.12 s | task-relative |
| v60 | median time to first truth lock, far start (>10 m) | 20.76 s | task-relative |
| v60 | median selection continuity | 1.0 | limit 0.98 |
| v60 | median touchdown (landed) | 51.53 s | event corrected |
| v60 | median metric-tracked frames (analysed) | 919.0 | frames |
| r15 | median accepted metric frames | 0.0 | 0–1 for all 21 failures |
| r15 | max image visibility, all flights | 1.000 | does not separate outcomes |
| r15 | radio-valid frames, radio-on flights | 3063.0 | channel exercised |
| r15 | radio position still linked at the last frame | 10/13 | availability |
| r15 | learned position-fusion weight > 0.01 | 3/13 | reliance, not availability |
| r15 | median learned position-fusion weight | 0.0 | 0 means the model ignored radio position |

## Excluded attempts

| attempt | duration s | reason |
|---|---:|---|
| `E01_nominal_v60d` | 0.92 | startup_abort |
| `E01_v60` | 0.0 | startup_abort |
| `E01_v60_r2` | 0.24 | startup_abort |
| `E01_v60_r3` | 1.16 | startup_abort |
| `E01_v60_r4` | 0.92 | startup_abort |

## Blocked cells

* `L-R` / v60: no radio input exists in the v60 stack: expert_adapter_v60.py:419 sets observation['beacon'] = {valid: False, ...} before the protocol runs; PublicState and CandidateV60 have no radio field; 0 beacon-valid frames in all 21 recordings with steps
* `F-R` / v60: no radio input exists in the v60 stack: expert_adapter_v60.py:419 sets observation['beacon'] = {valid: False, ...} before the protocol runs; PublicState and CandidateV60 have no radio field; 0 beacon-valid frames in all 21 recordings with steps
* `all v60 cells on Tidewater` / v60: no IPC bridge from Tidewater's observation schema to IdentityExpertV60 + the mission layer.  The staged runtime exists under landing_hardening_20261018/r15_final_game_verified/tidewater_runtime, and the MuJoCo/PX4 WASM world runs; the v60 actor is what is missing.  The R15 rows are the deployed R15 controller, not a v60 result.

## Basis

```json
{
  "benchmark": "benchmark_v63",
  "definitions": {
    "basis_v60": "teacher stack, Windows MuJoCo, protocol_priority_v60 + expert_adapter_v60; all review flights are radio-off because the adapter forces the beacon invalid",
    "basis_r15": "deployed R15 Tidewater stack, October 2026 audited corpus; radio is the simulated boat-position channel (0.25 m sigma, 1 Hz), not a search cue",
    "radio": "a valid boat-position channel.  v60: not implemented.  R15: radio_valid_frames > 0. Availability is not reliance: the learned position-fusion weight is reported separately, and direct radio control bypass is disabled.",
    "physical_landing": "strict touchdown on the boat deck, stable, disarmed; v60 preview_result.strict_physical_target_landing, R15 audited landed+stable",
    "qualified_landing": "physical landing with no hard authority/physical failure (v60 record tier not REJECT; R15 landed, stable, support_count>=1, no collision).  A flight without a record is 'not analysed', never qualified.",
    "found_decision": "v60 record lock_t is not None and target_fraction >= 0.50: the selected track is the truth target and stays so for at least half the remaining frames",
    "qualified_find": "v60 target_fraction >= 0.98, the record's own selection-continuity limit",
    "metric_tracked": "v60 at least one frame with learner_diagnostics.metric_acceptance == 'tracked'; R15 metric_frames > 0.  This is geometric registration, not visual detection.",
    "sustained_metric": "R15 metric_frames >= 10, a sequence rather than a single accepted frame",
    "landing_rate_denominator": "v60: flights that reached policy handoff (duration >= 5 s), including crashes before a terminal result; startup aborts are excluded.  A crash counts as a failed attempt, and a separate policy-attributable rate excludes harness crashes.  R15: every audited flight.",
    "finding_rate_denominator": "v60: flights with a record/record.json (authority labels required). R15: every audited flight.",
    "latency": "v60 time-to-lock is task-relative (record.lock_t).  v60 touchdown is physical_event_time - task_start_abs.  R15 has no handoff timestamp; first_metric_simulation_s is absolute and is not reported as a latency.",
    "no_pooling": "v60 and R15 rates are never added.  Scenario mix differs (v60 mostly 8 m visible starts; 18 of 26 R15 flights are hard starts), so cross-basis differences are not causal."
  },
  "protocol_sha256": "7611b9a4517419dd27a07c499b28d316fdd9c8fb5ce8c2de1887df400edba385",
  "adapter_sha256": "505547e29278b658e82c7b7568677a671e993b72b435d2bd6493a1fbf5c5b2a7",
  "public_state_sha256": "0e79b4b2b893d97a05e4fa10f1ef744e505d1f17d59d9ed73f6e34a9e77e522b",
  "disarm_policy_sha256": "0b0ca94903cc84a82db7e87213ae282d7325cef89b2a0ee3c5be97ea9a2f7502",
  "v47_sha256": "fd12bb896037b928fdb88a10a76ab1a0038538d6624042afe8788f0a1ffd19ff",
  "v61_sha256": "5d7df9eb1194654ec3933c0dadf9bc0917f1bfd050361ba6b624996e06f181d8",
  "r15_corpus_sha256": "908207015eceb0feceaee252096c50fe36ced42a4ec684775c1c8a42c21a84a9",
  "v60_rows": 16,
  "r15_rows": 26,
  "same_process": false,
  "note": "two independent evidence bases; no row is comparable across them"
}
```
