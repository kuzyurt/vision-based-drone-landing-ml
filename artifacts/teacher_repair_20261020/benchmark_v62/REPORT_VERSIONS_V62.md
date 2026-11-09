# Versions and weights, measured - 2026-10-23

Every number below was produced by a command in this directory on this host.
Nothing is quoted from an earlier report except where the line says so.

## 1. What was run

| tier | scope | command | result file |
|---|---|---|---|
| decision | 8 situations x 2 arms (pre-repair vs repaired) in one process | `run_benchmark_v62.py` | `results.json` |
| weight ladder | 3 checkpoints x 3 recorded episodes, 1294 identical crops | `run_weight_ladder_v62.py` | `weight_ladder.json` |
| flight | 2 recorded flight pairs, compared field by field through their receipts | `run_benchmark_v62.py` | `results.json` |
| mission | 4 recordings replayed through the repaired mission layer | `run_benchmark_v62.py` | `results.json` |
| tidewater | 3 situations declared | `run_benchmark_v62.py` | `results.json` (blocked) |
| self-test | 32 properties of the benchmark itself | `test_benchmark_v62.py` | stdout |

## 2. The weight ladder

Same crops, same deployed sampler (`object_verifier_v12.rgb_regions`, 2.5x box,
zero-padded), same two gates. `>=.85` = the protocol inspects it; `>=.98` with
three votes = it may be descended on.

| weights | role | sha256 | E01 target >=.85 | E01 target >=.98 | E02 clone >=.98 | E02 all decoys >=.98 | E08 25-40 s | stored held-out recall |
|---|---|---|---:|---:|---:|---:|---|---:|
| v38 | first approved-curriculum recogniser, never qualified | `52f1c07a09aa` | 64.8 % | 17.6 % | **24.2 %** | 17.6 % | blind | 51.3 % |
| v47 | pinned by every review flight and the deployed bundle | `fd12bb896037` | 42.5 % | 5.1 % | **22.8 %** | 16.6 % | blind | 49.3 % |
| v61 | trained 21 Oct on 7 approved episodes, not promoted | `5d7df9eb1194` | 100.0 % | 98.7 % | **97.6 %** | 71.0 % | blind | 99.2 % |

Per-class detail on E02 (599 crops, 421 of them the clone):

| class | crops | v47 >=.98 | v61 >=.98 | v47 mean p | v61 mean p |
|---|---:|---:|---:|---:|---:|
| `decoy_blank_clone` | 421 | 22.8 % | 97.6 % | 0.930 | 0.995 |
| `target` | 20 | 20.0 % | 25.0 % | 0.726 | 0.699 |
| `decoy_false_cross_board` | 26 | 0 % | 0 % | 0.0004 | 0.011 |
| `decoy_buoy`, `_dark`, `_debris`, `_false_cross_boat`, `_red`, `_similar` | 132 | 0 % | 0 % | < 0.002 | < 0.002 |

## 3. Flight record per weight set

| weights | flights that used it | outcome |
|---|---|---|
| v38 | none in the review batch | predecessor of v47; no flight evidence |
| v47 | E01, E02, E03 (4x), E04, E05, E06, E07, E08_v60, **E08_v61c** | 7 landed (E02 rejected on wrong object, E08_v60 stopped), E08_v61c landed |
| v61 | E08_v61, E08_v61b | crash at 14 s; 32 s freeze at 0.00 rad/s; **no landing** |

First successful review flight: `E01_nominal_cpu_v3`, v47, 1882 frames, landed, 900.6 s
wall. First successful deployed policy: R15 bundle, unpowered boat, 40.4 s (Tidewater,
18 Oct, recorded - not reproduced here). The walk from "first" to "now" therefore has
two different spines, and only the recogniser spine is measurable on this host.

## 4. What the numbers say

* **No rung is promotable.** All three confirm the clone on 17-97 % of its crops against a 5 % bar.
* **v47 is the best of the three on the failure that matters** (16.6 % vs 71.0 %), and it is the only weight set with a landing on record. It stays deployed.
* **The clone outscores the true target for v47**: mean 0.930 vs 0.726, peak 0.9988 vs 0.9917. The recogniser does not merely fail to separate them; at this scale it prefers the decoy.
* **v61 did what it was trained to do and nothing more**: true-target acceptance 98.7 % (matches its 99.2 % claim) while clone acceptance rose to 97.6 %. The fine-tune learned the target on the episodes it saw and the clone on none.
* **Per-crop rates are not decision rates.** The protocol confirms on 3 frames above 0.98 out of hundreds. At 22.8 % per crop, v47 reaching 3 votes in ~2000 frames is certain - which is exactly what E02 did (2075 frames on the clone).
* **Every other decoy class is rejected outright** by all three (0 % at both gates). The problem is one object at one scale, not a general classifier weakness.
* **The E08 25-40 s window cannot judge weights**: target boxes are 15x17 px, debris 13x8 px, and every checkpoint returns < 0.05 for every class. The flight's 9 s deviation onto the debris was driven by the detector's proposals, not by these weights. No weight set fixes that range.
* **The earlier decoy table was measured with the wrong sampler.** `tools/probe_decoy_discrimination.py` crops with nearest-neighbour clamped indexing; the deployed path grid-samples with zero padding. On the same 599 crops that moves v47 from 94.5 % to 22.8 % and v61 from 99.8 % to 97.6 %. The direction of the old conclusion survives; its size and its implication ("v47 is also fooled") do not.

## 5. Coverage - what ran and what did not

| row | state | reason |
|---|---|---|
| decision, 8 situations | ran, 4 pass both, 3 repaired-only, 1 fails both | scripted observations, not flights |
| weights, 3 checkpoints x 3 episodes | ran, 1294 crops, GPU | - |
| flight, E08 and E03 pairs | **blocked** | receipts differ in adapter (`fd06a59b` -> `505547e2`) outside the repair scope; E08 mission layer unhashed on the baseline |
| mission, 4 replays | ran, 4 pass | recorded arm is the recording, not a re-run |
| tidewater, 3 situations | **blocked** | no staged runtime and no bridge from Tidewater's observation schema to the v60 actor |
| weights, v44b/v52/v53/v59 | **not possible** | those checkpoints are not on this disk; only the training scripts are |
| controller bundles (v5, R8, R14, R15) | **blocked** | need the browser ONNX/WebGPU stack; recorded Tidewater evidence only: R4 unpowered 40.4 s, moving 47.7 s; R15 5 of 26 stress flights landed |

## 6. Caveats

* 1294 crops, not 1294 independent samples: stride 5 at 25 Hz is 0.2 s apart and consecutive crops of one object share lighting, pose and hull.
* 20 target crops in E02: enough to show the clone beats the target, not enough to estimate a rate.
* The ladder measures the verifier alone. The deployed decision is a cascade (detector proposals -> verifier -> votes); the flight record is the only evidence about the cascade.
* Choosing the best rung on the E02 clone would be fitting the test. The criteria were fixed before the run and the clone is one of nine classes.
