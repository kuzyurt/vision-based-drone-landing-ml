# Benchmark v63 — landing and finding, with and without radio

**Question.** Not "did this rule change?" (v62) but "what can the system do, under
the two outcomes and the one information condition that change the task?"

```
                     radio available            no radio
landing on boat      L-R                        L-0
finding the boat     F-R                        F-0
```

Two evidence bases exist. They are reported side by side and **never pooled**:

| basis | stack | radio | corpus |
|---|---|---|---|
| `v60` | teacher: `protocol_priority_v60` + `expert_adapter_v60`, Windows MuJoCo | **absent** (adapter forces beacon invalid) | `review_v60/`, `review_v61/` |
| `r15` | deployed Tidewater: R15 pose model, browser MuJoCo/PX4 | simulated boat-position channel, 0.25 m σ, 1 Hz | October 2026 audited corpus |

A cell with no rows on a basis is `blocked` with the measured reason. It is never a
pass, a fail, or silently omitted.

## Definitions (declared before the numbers)

| term | definition |
|---|---|
| `radio` | a valid boat-position channel. v60: not implemented. R15: `radio_valid_frames > 0`. |
| `physical_landing` | strict touchdown on the boat deck, stable, disarmed. v60 `preview_result.strict_physical_target_landing`; R15 `landed` + `physical.stable` + `support_count>=1` + no collision. |
| `qualified_landing` | physical landing with no hard authority/physical failure. v60 `record.tier != REJECT`; R15 same as physical (all five are stable, no collision). A flight without a record is `not analysed`, never qualified. |
| `found_decision` | v60 `record.lock_t is not None` **and** `target_fraction >= 0.50`: the selected track is the truth target and stays so for at least half the remaining frames. |
| `qualified_find` | v60 `target_fraction >= 0.98`, the record's own continuity limit. |
| `metric_tracked` | v60 at least one frame with `metric_acceptance == "tracked"`; R15 `metric_frames > 0`. This is geometric registration, not visual detection. |
| `sustained_metric` | R15 `metric_frames >= 10`, a sequence rather than one accepted frame. |
| landing denominator | v60 flights that reached policy handoff (duration ≥ 5 s), including crashes before a terminal result; startup aborts are excluded. A crash is a failed attempt, and a separate policy-attributable rate excludes harness crashes. R15 every audited flight. |
| finding denominator | v60 flights with `record/record.json` (truth labels + authority checks required); R15 every audited flight. |
| latency | v60 lock is task-relative (`record.lock_t`); v60 touchdown is `physical_event_time − task_start_abs`. R15 has **no handoff timestamp**: `first_metric_simulation_s` is simulation-absolute and is not reported as a latency. |
| no pooling | v60 and R15 rates are never added. Scenario mix differs (v60 mostly 8 m visible starts; 18 of 26 R15 flights are hard starts), so cross-basis differences are not causal. |

## What each cell measures

| cell | primary | secondary | optional |
|---|---|---|---|
| **L-R** | physical landings / radio-on flights | qualified / analysed | time to land, collisions |
| **L-0** | physical landings / radio-off flights | qualified / analysed | time to land, collisions |
| **F-R** | R15 metric acquisition / flights; v60 blocked | R15 sustained acquisition | metric frames, flight time, strata |
| **F-0** | v60 decision lock / analysed flights; R15 metric acquisition | v60 continuity ≥ .98; R15 sustained | lock time, first tracked, touchdown |

R15 cells carry a start-stratum table. The corpus has two populations: visible-start
flights (4 radio, 4 visual) and hard starts (9 each: six ~2 m speed-ladder starts plus
three close/far look-away starts). Aggregating them would attribute a start-condition
effect to radio.

R15 "with radio" means the channel was **available**, not that the policy relied on it.
The learned position-fusion weight is > 0.01 in 3/13 radio flights — exactly the three
landings — and ≈0 in the rest. The report gives availability (`radio_valid_frames`) and
reliance (fusion weight) as separate metrics.

## Inclusion rules

* A **v60 flight** is a recording with `steps.jsonl` and duration ≥ 5 s. It enters landing
  rates whether it ended with a `preview_result` or crashed before one; a crash is a failed
  attempt, and the report also gives the policy-attributable rate with harness crashes
  removed. It enters finding rates only with `record/record.json`.
* Startup aborts (<5 s) are listed under **Excluded attempts**; they never reached policy
  handoff and are not failures of the policy.
* An **R15 flight** is every row of `audited_results.json` (26). The corpus's own
  caveats (one map, exploratory sample, simulated radio) are copied into the result
  metadata.

## What this benchmark proves, and what it does not

| it proves | it does not prove |
|---|---|
| the recorded v60 flights' physical and authority outcomes, per scenario | that the current tree would fly the same way today; only `E08_v61c` matches the tree |
| the R15 October landing/finding outcomes with and without radio | that radio caused the difference; the visible-start cells are n=4 and the hard-start cells are 0/9 both |
| that v60 cannot be scored radio-on | that v60 would not benefit from radio if it were implemented |
| that visual visibility is not the bottleneck in R15 | why metric registration fails; that is a perception/geometry question |
| that a transient truth lock is not a find | a decision-level false-confirmation rate for the weights; that needs a track-level replay |

## Reproduce

```bash
cd artifacts/teacher_repair_20261020/benchmark_v63
python audit_v63.py            # 30 truthfulness checks on v62 and the evidence
python run_benchmark_v63.py    # writes results_v63.json and RESULTS_V63.md
python test_benchmark_v63.py   # 28 self-checks
```

Pure Python; no flight, renderer or PX4.

## Adding a row

1. Name the cell and the basis. A row that spans two bases is not allowed.
2. Declare the metric before reading the result; if it is an R15 latency, say which
   clock it is on.
3. If the cell is empty because the input does not exist, add a `blocked` entry with
   the file and line that removes it — not a prose excuse.
4. Keep scenario strata; an aggregate over visible and hard starts is a start-effect
   measurement wearing a radio label.
