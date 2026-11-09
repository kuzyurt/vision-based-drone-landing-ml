# Benchmark v62 - results

Generated 2026-10-23T10:51:39.025620+00:00 by `run_benchmark_v62.py`.

| tier | case | situation | baseline | repaired | verdict |
|---|---|---|---:|---:|---|
| decision | `d01_visible_opportunity` | older | 4/4 | 4/4 | **pass_both** |
| decision | `d02_competing_buoy` | older | 3/3 | 3/3 | **pass_both** |
| decision | `d03_target_appears_mid_survey` | older | 3/3 | 3/3 | **pass_both** |
| decision | `d04_evidence_growth_at_range` | older | 3/3 | 3/3 | **pass_both** |
| decision | `d05_scale_ambiguity_20m` | older | 0/3 | 0/3 | **fail_both** |
| decision | `d06_reorient_freeze` | newer | 1/4 | 4/4 | **repaired_only** |
| decision | `d07_retired_candidate_timestamp` | newer | 0/3 | 3/3 | **repaired_only** |
| decision | `d08_rest_on_deck_disarm` | newer | 1/3 | 3/3 | **repaired_only** |
| flight | `f01_e08_long_approach` | newer | development_diagnostic_stop | landed | **blocked_uncontrolled_basis** |
| flight | `f02_e03_deck_dwell` | newer | collision_failure | landed | **blocked_uncontrolled_basis** |
| weights | `v38` | newer | target 64.8%@.85 / 17.6%@.98 | decoy 17.6%@.98 | **promotion_refused** |
| weights | `v47` | newer | target 42.5%@.85 / 5.1%@.98 | decoy 16.6%@.98 | **promotion_refused** |
| weights | `v61` | newer | target 100.0%@.85 / 98.7%@.98 | decoy 71.0%@.98 | **promotion_refused** |
| mission | `m01_e08_long_approach` | newer | - | - | pass |
| mission | `m02_e02_hovering_decoy` | older | - | - | pass |
| mission | `m03_e01_short_flight` | older | - | - | pass |
| mission | `m04_e07_mid_range` | older | - | - | pass |
| tidewater | `t01_unpowered_boat` | tidewater | - | - | blocked_no_v60_bridge |
| tidewater | `t02_visible_1m0_radio` | tidewater | - | - | blocked_no_v60_bridge |
| tidewater | `t03_low_start_0m6_no_radio` | tidewater | - | - | blocked_no_v60_bridge |

## Weight ladder (deployed sampler, identical crops)

| weights | role | E01 target >=.98 | E02 blank clone >=.98 | E02 all decoys >=.98 | E08 debris >=.98 | stored held-out recall |
|---|---|---:|---:|---:|---:|---:|
| `v38` | first approved-curriculum recogniser (experimental, not qualified) | 17.6% | 24.2% | 17.6% | blind | 51.3% |
| `v47` | pinned by every review flight and by the deployed bundle | 5.1% | 22.8% | 16.6% | blind | 49.3% |
| `v61` | trained 2026-10-21 on seven approved episodes, not promoted | 98.7% | 97.6% | 71.0% | blind | 99.2% |

Device `cuda`, stride 5, sampler `object_verifier_v12.rgb_regions (2.5x proposal box, zero padded)`. `weight_ladder.json` carries per-class figures for every decoy class and both thresholds.

## Rows that do not pass, and which criterion says so

* `d05_scale_ambiguity_20m` (fail_both) - baseline: never_confirms_the_decoy, confirms_the_true_target, no_confirmation_before_target_visible; repaired: never_confirms_the_decoy, confirms_the_true_target, no_confirmation_before_target_visible
* `p01_weight_ladder [v38]` (promotion_refused) - both: target_likely_on_nominal, decoy_confirm_20m
* `p01_weight_ladder [v47]` (promotion_refused) - both: target_likely_on_nominal, decoy_confirm_20m
* `p01_weight_ladder [v61]` (promotion_refused) - both: decoy_confirm_20m

## Blocked rows

* `f01_e08_long_approach` (blocked_uncontrolled_basis): fields changed outside the repair scope ['actor_source_sha256'], not hashed on one side ['mission_safety_sha256']
* `f02_e03_deck_dwell` (blocked_uncontrolled_basis): fields changed outside the repair scope ['actor_source_sha256', 'adapter_sha256'], not hashed on one side []
* `t01_unpowered_boat` (blocked_no_v60_bridge): No v60 decision layer in the Tidewater stack: the October flights ran the R15 browser bundle through a staged runtime on the Linux VM. Running these rows needs (a) the staging receipt and runtime, and (b) an IPC bridge from Tidewater's observation schema to IdentityExpertV60 plus the mission layer.
* `t02_visible_1m0_radio` (blocked_no_v60_bridge): No v60 decision layer in the Tidewater stack: the October flights ran the R15 browser bundle through a staged runtime on the Linux VM. Running these rows needs (a) the staging receipt and runtime, and (b) an IPC bridge from Tidewater's observation schema to IdentityExpertV60 plus the mission layer.
* `t03_low_start_0m6_no_radio` (blocked_no_v60_bridge): No v60 decision layer in the Tidewater stack: the October flights ran the R15 browser bundle through a staged runtime on the Linux VM. Running these rows needs (a) the staging receipt and runtime, and (b) an IPC bridge from Tidewater's observation schema to IdentityExpertV60 plus the mission layer.

## Summary

* rows: 20, decided: 15
* verdicts: {"blocked_no_v60_bridge": 3, "blocked_uncontrolled_basis": 2, "fail_both": 1, "pass": 4, "pass_both": 4, "promotion_refused": 3, "repaired_only": 3}
* rows where the arms differ: 3
* rows that fail in both arms: 1

## Basis

```json
{
  "benchmark": "benchmark_v62",
  "protocol_sha256": "7611b9a4517419dd27a07c499b28d316fdd9c8fb5ce8c2de1887df400edba385",
  "adapter_sha256": "505547e29278b658e82c7b7568677a671e993b72b435d2bd6493a1fbf5c5b2a7",
  "public_state_sha256": "0e79b4b2b893d97a05e4fa10f1ef744e505d1f17d59d9ed73f6e34a9e77e522b",
  "disarm_policy_sha256": "0b0ca94903cc84a82db7e87213ae282d7325cef89b2a0ee3c5be97ea9a2f7502",
  "arms_module_sha256": "016f64362bab5699b0e8559a5fde7ee50bf5a9f34f6f609a03d5f49158992635",
  "recogniser": "v47 (frozen, fd12bb89...); not re-run by this tier",
  "mission_layer": "unmodified by this tier (see the replay tier)",
  "same_process": true,
  "only_rule_toggled": "reorient timeout, rejection-shape normalisation, deck-dwell disarm"
}
```
