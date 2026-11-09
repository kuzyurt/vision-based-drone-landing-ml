# Audit of benchmark v62 and the evidence base

**Verdict.** The arithmetic is real; several labels are not. 30 checks: **15 verified,
7 mislabeled, 1 vacuous, 7 claims refuted.** No fabricated number was found — the v62
runner and the weight ladder reproduce exactly. The two findings that change decisions:

1. **`E08_v61c` is a physical landing but a REJECT.** It fails
   `authority.selection_continuity` at 93.69 % against 98 % (3564/3804 frames on the
   truth target; 240 frames off it). v62's flight tier reports the physical outcome but
   not the record's REJECT.
2. **The v60 teacher stack has no radio input.** `expert_adapter_v60.py:419` overwrites
   the beacon to `valid=False`; `PublicState` and `CandidateV60` have no radio field.
   Every one of the 21 review recordings with steps has **0** beacon-valid frames.
   The "with radio" half of the requested matrix cannot be measured on v60.

A third fact explains most of the confusion: **the v61 checkpoint was flown** — E08_v61
and E08_v61b used `5d7df9eb` and both failed; the landing, E08_v61c, used **v47**
(`fd12bb89`). "v61" names two different things: a weights checkpoint and a flight batch.

## 1. What was run

| command | result |
|---|---|
| `python test_benchmark_v62.py` | 32/32 properties pass |
| `python run_benchmark_v62.py` | 20 rows, 15 decided, identical summary to the committed `results.json` |
| `python run_weight_ladder_v62.py` | all three rows and the 1294-crop counts reproduce exactly |
| `python audit_v63.py` | 30 checks above |
| `python run_benchmark_v63.py` | four-cell re-cut, `results_v63.json` |
| `python test_benchmark_v63.py` | 28 self-checks pass |

No flight, renderer or PX4 was run. This is an audit of recordings, receipts and
recomputable measurements.

## 2. Verified (15)

| claim | evidence |
|---|---|
| v62's markdown matches its JSON | 20 rows / 15 decided in both |
| the verdict tally is the tally over the rows | recomputed exactly |
| E02's scale case confirms the decoy | `confirmed_set=[9]` in both arms, target is 7 |
| the ladder uses 1294 crops from three recordings | 259 (E01) + 599 (E02) + 436 (E08) |
| three checkpoints ran on the identical crop set | per-checkpoint crop totals 259/599/436 |
| E08 25–40 s cannot judge the verifier | every class below 0.05 at 0.85; `debris_informative=false` |
| the corpus spans 3 adapters, 5 protocols, 10 harnesses | 22 receipted recordings |
| exactly one recording matches the tree on disk | `E08_v61c` (`7611b9a4`/`505547e2`) |
| both v62 flight pairs are blocked | f01: missing `mission_safety_sha256`; f02: adapter change |
| R15 radio rows received radio samples | 13/13 radio rows `radio_valid_frames>0`; 13/13 visual rows 0 |
| R15 has 26 flights and 5 boat landings | 3 radio, 2 visual |
| only E03_v60_forced used the new disarm branch | `rest_on_deck`; repair/rest used `px4_landed` |
| the E08_v61b freeze is real | 800/800 `reorient_candidate` frames from 64–96 s; yaw command 0.005–0.008 rad/s (rounded to 0.00) |
| every flight record's evidence hash matches | 12 records, all `steps.jsonl`/`frames.csv`/`verdict.json`/`video_join.json`/`review.mp4` hashes recomputed |
| the v62 basis hashes are the files on disk | protocol, adapter, public state, disarm policy and arms module all match `results.json` |

## 3. Mislabeled (7) — the number is real, the name overclaims

| claim | what the code actually does | impact |
|---|---|---|
| d05's criteria test their names | `never_confirms_the_decoy` is `confirmed_set == [7]`; `no_confirmation_before_target_visible` is `confirmation_track == 7` and never checks the time | the row still fails correctly; the two names do not describe the tests |
| the decision harness feeds vertical speed | `state()` sets `own_vertical_speed_m_s=yaw_rate` | all cases use `yaw_rate=0`, so no published row changes; the field is wrong |
| a blind E08 criterion is a measured 0 % | `debris_confirm=0.0` stored while `debris_informative=false` | a JSON reader can take 0 % as a refusal the verifier never earned |
| the ladder's per-crop gate is the protocol gate | ladder uses support ≥ 0.80 per crop; protocol TARGET uses support ≥ 0.5, an 0.8 s peak and 3 votes | 42.5 % (v47) is a per-crop lower bound, not the track's target-likely rate |
| R15 `first_metric_simulation_s` is a latency | simulation-absolute; 45.11 s > 41.14 s flight time in `visible_0p6_radio` | no R15 acquisition latency is reported by v63 |
| the v62 Tidewater check looks in the right place | it checks `landing_hardening_20261018/tidewater_runtime`; the runtime is under `r15_final_game_verified/tidewater_runtime` | the blocker is real, but the prerequisite dict is wrong |
| v60 event times share `duration_s`'s clock | touchdown 60.67 s absolute vs duration 46.44 s | v63 subtracts the task start (touchdown 40.71 s) |

## 4. Vacuous (1)

`no descent without a confirmed and selected target` — `descent_frames_off_target=0`
in all 14 arm-rows, and no case ever commands descent. The invariant is true because
the situation never occurs. v62 reports it as a pass.

## 5. Refuted (7) — do not repeat these

| claim under test | finding |
|---|---|
| `E08_v61c` is a qualified success | physical landing, **REJECT**; continuity 93.69 % < 98 %; 96 soft frames of press after contact |
| the v61 checkpoint was never flown | E08_v61 (crashed at 14.0 s, `TypeError`) and E08_v61b (100 s stop) used `5d7df9eb`; E08_v61c used v47 |
| the review flights exercise radio | 0 beacon-valid frames in all 21 recordings; adapter line 419 forces invalid |
| a valid beacon can reach `SearchProtocolV60` | no radio field in `PublicState`/`CandidateV60`; the adapter overwrites it before the protocol |
| visual visibility separates R15 outcomes | min visibility 0.9939; **all 26** flights see the boat; 21 still fail; metric frames 0–1 vs 690–943 |
| R15 radio drives search/control | runtime sets `reliable=False` and hands the controller an invalid beacon; radio enters learned pose fusion only |
| 22 recordings = 22 completed flights | 21 with steps, **16 reached handoff** (14 terminal + 2 crashes), **12 with records**; 5 startup aborts <1.2 s |

## 6. The four cells, as measured

| cell | v60 | R15 |
|---|---|---|
| **L-R** | **blocked** (no radio input) | 3/13 physical (23 %, CI 8–50); visible start 3/4, hard start 0/9 |
| **L-0** | 9/16 physical (56 %, CI 33–77; policy-attributable 9/14); 7/12 qualified (58 %) | 2/13 physical (15 %, CI 4–42); visible start 2/4, hard start 0/9 |
| **F-R** | **blocked** | 4/13 metric (31 %); 3/13 sustained; visible 3/4, hard 1/9 (one frame) |
| **F-0** | 11/12 decision lock (92 %); 9/12 continuity ≥ .98; 10/12 metric tracked | 2/13 metric (15 %); visible 2/4, hard 0/9 |

Read the R15 rows by stratum, not by aggregate: **the hard-start stratum (18 flights: 12 at
~2 m plus 6 close/far look-away starts) is 0/9 landings with and without radio.** The
visible-start difference is 3/4 vs 2/4, n=4 per cell. There
is no evidence of a radio landing benefit, and no evidence against one at this sample size.

The v60 9/16 is also a mix, not a general rate: **7/10 at ≤10 m, 0/1 at 20 m, 2/5 at
≥25 m.** The far-stratum successes are E07 (28 m) and E08_v61c (52 m, REJECT on
continuity); the 20 m case is E02, the decoy failure.

R15 radio availability is not radio reliance. The learned position-fusion weight is
> 0.01 in only **3/13** radio flights — and those are exactly the three landings
(`visible_0p6_radio`, `midpoint_radio`, `confirm_radio`, all visible starts). The fourth
visible radio flight (1.4 m/s) had lost the link at the last frame and failed. Velocity
fusion is ≈0.35 in 10/13. n=3: a correlation, not a causal effect.

## 6b. Weights (supporting measurement, not a cell)

| checkpoint | target ≥ .85 (E01) | target ≥ .98 (E01) | all decoys ≥ .98 (E02) | blank clone ≥ .98 | stored held-out recall | promotable |
|---|---:|---:|---:|---:|---:|---|
| v38 | 64.8 % | 17.6 % | 17.6 % | 24.2 % | 51.3 % | no |
| v47 (deployed) | 42.5 % | 5.1 % | 16.6 % | 22.8 % | 49.3 % | no |
| v61 | **100 %** | **98.7 %** | **71.0 %** | **97.6 %** | 99.2 % | no |

No checkpoint passes `target ≥ 95 % at .85` **and** `decoys ≤ 5 % at .98`. v61 passes the
target criterion and fails refusal; v47/v38 fail the target criterion. v47 remains deployed
because it is the only checkpoint with the flight record and the best decoy refusal.

Two cautions that decide how much this table is worth:

* It is **per crop**, with support ≥ 0.80. The protocol confirms on a **0.8 s peak** with
  **3 votes** and classifies TARGET at support ≥ 0.5. At 25 Hz a 0.8 s window holds 20
  frames; a 22.8 % per-crop rate makes a peak near-certain. The per-crop number is a lower
  bound, not a false-confirmation probability.
* v61 weights **were** flown: E08_v61 (TypeError at 14.0 s) and E08_v61b (100 s stop,
  effectively frozen yaw) used `5d7df9eb`. Both failures are code paths, not a clean
  test of the weights; the corrected code flew v47, so v61 has never been flown with the
  fixes in place.

## 7. Understanding of the system (rechecked against code and files)

**Two stacks, one airframe.**

* `v60` teacher: 640×360 RGB → v47 verifier (`object_verifier_v12`, `rgb_only`) →
  `CandidateV60` → `SearchProtocolV60` → `ExpertAdapterV60` → R15 pose controller →
  `mission_safety` → PX4. Review flights are Windows MuJoCo; radio is forced off.
* `r15` deployed: Tidewater browser MuJoCo/PX4, R15 radio-robust pose model, mission
  layer; radio is a 0.25 m σ, 1 Hz boat-position channel used in learned pose fusion.

**Radio semantics.** Not a search cue in either stack. v60: absent. R15: the runtime
sets `reliable=False` and passes an invalid beacon to the controller; the radio only
enters the pose model's uncertainty/fusion input. "Finding with radio" therefore means
"pose fusion with radio", not "beacon-guided search". The fusion weights show the model
mostly ignored the position: > 0.01 in 3/13, exactly the three landings; velocity fusion
≈0.35 in 10/13. Report availability (`radio_valid_frames`) and reliance (fusion weight)
separately.

**Landing has three grades.** Physical (touchdown, stable, disarmed); qualified (no hard
authority/physical failure); record tier (GOLD/SILVER/REJECT). E08_v61c is grade 1 but
not grade 2. E03_v60 is neither (collision). E01c/E03_forced/E03_repair/E04–E07 are
SILVER, no hard failures.

**Finding has three grades.** Visible (max visibility); decision lock on the truth target
(`lock_t`, `target_fraction`); metric registration (`metric_acceptance=="tracked"`,
R15 `metric_frames`). Visibility is 1.0 in every R15 flight, so it is not a finding
metric. E08_v60 reached 0.4 m from the true pad with **zero** tracked frames: it found
the boat visually and never measured it. E08_v61c first tracked at 54.8 s and touched
down at 167.2 s — 112 s of tracked approach.

**The bottleneck is metric registration and selection continuity, not detection.**
E02: lock at 17.08 s on the truth target, then 1.01 % continuity, 0 tracked frames,
2096 frames of `target_inspect`, minimum true-pad distance 10.5 m — it confirmed the
20 m blank clone. E08_v61c: 93.69 % continuity, 240 frames off target, REJECT.

**The repairs are real but narrower than the reports imply.** Reorient bound: d06
baseline 32.0 s frozen, repaired 3.04 s. Rejection shape: d07 baseline TypeError,
repaired survives. Deck dwell: only E03_v60_forced exercised `rest_on_deck`; E03_repair
and E03_v60_rest landed via PX4's own `px4_landed`. The other two E03 landings are not
evidence for the new branch.

## 8. Assumptions, rechecked

| # | assumption | status | evidence |
|---:|---|---|---|
| 1 | v60 review flights are radio-off | **verified** | 0 beacon-valid frames in 21 recordings |
| 2 | the v60 protocol consumes radio | **refuted** | adapter line 419; no radio field in the types |
| 3 | radio improves R15 search | **not supported** | hard start 0/9 both; visible 3/4 vs 2/4 (n=4) |
| 4 | R15 visibility equals finding | **refuted** | min 0.9939; all 26 see the boat; 21 fail |
| 5 | E08_v61c is a clean success | **refuted** | REJECT, continuity 93.69 % |
| 6 | v61 weights were never flown | **refuted** | E08_v61 / E08_v61b used 5d7df9eb |
| 7 | v62's numbers are fabricated | **refuted** | runner and ladder reproduce exactly |
| 8 | per-crop rate = confirmation probability | **refuted** | 0.8 s peak + 3 votes; per-crop is a lower bound |
| 9 | landing time = `duration_s` | **refuted** | event times are absolute (60.67 vs 46.44) |
| 10 | final pad distance measures landing accuracy | **refuted** | boat keeps moving; landed flights end 14–52 m away |
| 11 | Tidewater is blocked only by a missing runtime | **refuted** | runtime exists under `r15_final_game_verified/`; the v60 bridge is missing |
| 12 | the v62 flight pairs are controlled | **verified** | both blocked; f01 missing mission hash, f02 adapter change |
| 13 | the E03 repair landed via the new branch | **only E03_v60_forced** | `rest_on_deck`; repair/rest `px4_landed` |
| 14 | 22 recordings are 22 usable flights | **refuted** | 21 steps, 16 reached handoff (2 crashes), 12 records |
| 15 | the only gates are 0.85 / 0.98 | **refuted** | also extent 24/18 px, plausible length 0.65 m, support 0.5/0.8, 3 votes, interrupt 32 px/0.92 |

One precision note: the E08_v61b "32 s at 0.00 rad/s" is a rounded display. From
64–96 s all 800 frames are `reorient_candidate`, but the commanded yaw is
0.005–0.008 rad/s, not exactly zero. The freeze is real; the two-decimal zero is not
literal.

## 9. What this cannot settle

* **v60 radio-on.** No input path exists. Building one is a feature change, not a
  benchmark; the cell stays blocked until then.
* **v60 on Tidewater.** No IPC bridge from Tidewater's observation schema to
  `IdentityExpertV60` + mission. The staged runtime and the MuJoCo/PX4 world are present.
* **R15 acquisition latency.** No handoff timestamp in the audited corpus; the absolute
  metric time is not a latency.
* **Decision-level false-confirmation rate for the weights.** The ladder is per-crop;
  the protocol confirms on a 0.8 s peak with 3 votes. A track-level replay is the next
  measurement, not a re-label of the existing one.
* **Causal radio effect.** Confounded by start stratum and n=4 in the visible cells.
* **Cross-basis comparison.** Invalid: different controller, scenario mix and radio
  implementation.

## 10. Files

* [audit_v63.py](audit_v63.py) — the 30 checks, writes `audit_v63.json`.
* [run_benchmark_v63.py](run_benchmark_v63.py) — the four-cell runner.
* [BENCHMARK_V63.md](BENCHMARK_V63.md) — definitions and inclusion rules.
* [RESULTS_V63.md](RESULTS_V63.md) — generated per-row report.
* [test_benchmark_v63.py](test_benchmark_v63.py) — 28 self-checks.
