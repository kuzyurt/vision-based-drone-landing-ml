# Handoff - teacher-repair session (2026-10-21, second pass)

## Read in this order

1. [ADDENDUM_E03_REPAIR.md](ADDENDUM_E03_REPAIR.md) - the E03 repair: five flights,
   the dead-code bug it exposed, the rule that replaced it, and what the flights
   cannot settle.
2. [REPORT_FLIGHT_REVIEW_V61.md](REPORT_FLIGHT_REVIEW_V61.md) - method, calibration,
   pilot results, the training result *and why it is not promoted*, and the real
   cause of the E02 wrong-object confirmation.
3. [benchmark_v62/BENCHMARK_V62.md](benchmark_v62/BENCHMARK_V62.md) and its
   [RESULTS_V62.md](benchmark_v62/RESULTS_V62.md) - the paired old-against-new suite,
   the three tiers that can run here, and the two that cannot yet.
4. [PILOT_MATRIX.md](PILOT_MATRIX.md) - one row per batch episode with tier and
   failures (batch membership is [PILOT_CASES.json](PILOT_CASES.json)).
5. Any `review_v60/<case>/record/RECORD.md` - the readable flight record. Start with
   `E03_v60_forced` (fallback firing) and `E04_v60` (recovery branch).
6. `review_v60/E02_v60/decoy_probe.json` - the measurement that blocks v61 promotion.

## State of the work

* **Review instrument**: `tools/inspect_flight.py` + `tools/approve_batch.py`. Every
  check is recomputed from `steps.jsonl`, `analysis_v1/frames.csv`, `verdict.json`,
  `video_join.json` and `preview_result.json`; each verdict carries sha256 of the
  evidence. Negative control receipted in `controls/NEGATIVE_CONTROL.json`.
* **Pilot batch**: 7 SILVER (E01c, E03_repair, E03_forced, E04, E05, E06, E07), 3
  REJECT (E02 wrong-object confirmation, E03 baseline collision, E08 stopped by the
  mission return reserve). No GOLD: every episode presses the deck for ~1 s after
  contact (`physical.no_press_after_contact`).
* **E08 now lands** (`review_v61/E08_v61c`, `outcome = landed`,
  `disarm_reason = px4_landed`, `strict_physical_target_landing = true`, 4323 frames,
  172.9 s, touchdown 189.08 s, PX4 landed 194.73 s). It is the first E08 flight to
  reach the deck. Still **REJECT**, and correctly so: `selection_continuity` is 93.69 %
  against a 98 % limit. That is not a label artefact - between 30 and 36.5 s the
  selected box sits at pixel (318-322, 178-185), dead centre, while the truth target is
  108-149 px to its left, so the aircraft genuinely closed on a `decoy_debris` object
  from 49 m to 39 m before recovering and landing on the boat. Same failure family as
  E02 (a plausible-looking object at range wins), at a much smaller scale. Identity and
  authority are clean: 3146 confirmed frames, 0 on the wrong object, 0 descent frames
  off target.
* **E08 was not a control deadlock** (an earlier note said so). It closed from
  52 m to 10 m at 2 m/s and was stopped at 53.5 s by `return_time_reserve` because
  the mission's planning range was gated on `control_phase == 'visual_acquire'`, a
  phase the v60 expert never emits - so no finish estimate existed in any v60
  flight (0 coarse-range frames in 13 of 14 traces). Fixed in
  `mission_sources/mission_safety.py`, verified by replay and
  `tools/test_mission_coarse_v61.py`. Re-flown as `review_v61/E08_v61`.
* **The re-flights were not the controlled test they were described as.** Both
  `review_v61/E08_v61` and `E08_v61b` were flown by `run_windows_review_v61.py`, which
  pins `models/perception_v61/best.pt` - the recogniser this handoff lists as *not
  promoted*. Compared with `E08_v60`, the receipts show a different recogniser, protocol,
  adapter, autopilot adapter and harness, and `E08_v60` cannot be reproduced today because
  the adapter hash it pins (`fd06a59b...`) no longer exists on disk. `E08_v61b` therefore
  says nothing about the mission-layer fix; it is one more unpromoted-recogniser flight.
  `tools/compare_flights.py` now refuses the comparison (`not_controlled_basis_differs`)
  instead of reporting a divergence it cannot attribute, and the runner records
  `probe_gate` and `checkpoint` and refuses a gate that does not cover the weights flown.
* **`reorient_candidate` could freeze the aircraft indefinitely.** `E08_v61b` spent 32 s
  at 0.00 rad/s yaw with the selection pinned to a remembered track that was never
  re-observed (age grew 4 s -> 36 s). The adapter yaws toward the stale bearing, the
  stale bearing already matched the heading, and no path bounded the wait - the only
  escape was the mission budget. `SearchProtocolV60._reorient` now resumes the survey
  after `REORIENT_TIMEOUT_S = 3.0`, keeps the object (lost sight is not evidence) and
  logs `reorient_timeout`. Counterexample test: 8.00 s of 8.00 s before, <= 3.5 s after.
* **There is now an old-against-new benchmark**: `benchmark_v62/`
  ([BENCHMARK_V62.md](benchmark_v62/BENCHMARK_V62.md), results in
  [RESULTS_V62.md](benchmark_v62/RESULTS_V62.md), runner `run_benchmark_v62.py`,
  self-test `test_benchmark_v62.py`). 19 declared rows: 14 decided, 5 blocked;
  3 rows separate the arms (reorient bound, retired-timestamp crash, deck dwell),
  1 fails in both (E02 scale ambiguity, by design - the benchmark must be able to
  fail), 4 pass in both as regression guards, 4 mission rows pass, 2 perception
  rows fail (v61 is worse than v47 on the decoy and must not be promoted), and
  5 are blocked. Both arms run the same file in one process; the baseline is a
  subclass that restores the pre-repair rule verbatim.
* **The flight tier found no controlled pair, and the reason is not the
  recogniser.** Across the 22 recordings there are 3 adapter versions, 5 protocol
  versions and 10 harness versions. The adapter changed from `fd06a59b` to
  `505547e2` between the E04-E08 flights and the E03 repair, and the old adapter
  is no longer on disk. Every SILVER row in the pilot matrix was flown by protocol
  `0be9b529`, not by the protocol now on disk (`7611b9a4`). **`E08_v61c` is the
  only flight whose receipt matches the current tree**, so both declared flight
  pairs (`E08_v60`->`E08_v61c`, `E03_v60`->`E03_v60_forced`) are
  `blocked_uncontrolled_basis`: the outcomes differ (stop->landed,
  collision->landed) but the flights also differ in adapter, and for E08 in a
  mission layer that was never hashed. The pilot matrix describes an older tree.
* **`replay_mission_v61.py` had its two arms mislabelled.** `recorded_fallback`
  was in fact the *replayed* decision, and the recorded flag was only used inside
  the boolean `same_as_recorded`. A benchmark that compares those two numbers
  cannot afford that ambiguity. It now reports `recorded_fallback`,
  `replayed_fallback`, `same_as_recorded` and
  `replay_creates_planning_range` separately. Consequences: E08_v60 recorded
  `return_time_reserve` at 53.48 s and now replays with no fallback and a
  decreasing 53.6 -> 14.7 m estimate; E02_v60 replays to the same `search_timeout`
  at the same time, i.e. the safety stop survives.
* **The first draft of the baseline arm was wrong** and the benchmark caught it at
  frame 50: it read `self.search_height_enu_m`, a field that never existed. A
  reconstructed "historical" rule is a claim like any other; it is now checked by
  the self-test (the baseline must reproduce the 32 s freeze, the TypeError and
  the missed dwell) rather than trusted.
* **E03 is repaired and measured**: `E03_v60_forced` lands with
  `disarm_reason = rest_on_deck`, firing 1.12 s after first contact on a 1.0 s
  within-5-mm dwell, no hard failures.
* **The weight ladder is measured** (`benchmark_v62/REPORT_VERSIONS_V62.md`,
  `weight_ladder.json`): three checkpoints exist (v38 `52f1c07a`, v47 `fd12bb89`,
  v61 `5d7df9eb`), all `rgb_only`, all run on the same 1294 crops from E01, E02 and
  the E08 approach window, sampled with the deployed `rgb_regions` grid sampler at
  both protocol gates (0.85 inspect, 0.98 confirm). Result: on the E02 blank clone
  v38/v47/v61 confirm 24.2 % / 22.8 % / **97.6 %** of crops; every other decoy class
  is rejected outright by all three; for v47 the clone scores *higher* than the true
  target (mean 0.930 vs 0.726). No rung is promotable and v47 remains deployed.
  In the E08 25-40 s window every class scores < 0.05 for every checkpoint: the
  verifier is blind at 39-52 m, so the debris deviation came from the detector's
  proposals, not from these weights.
* **The earlier decoy numbers used the wrong sampler.** `probe_decoy_discrimination`
  crops with nearest-neighbour clamped indexing; the deployed path grid-samples with
  zero padding. On the same 599 crops that moves v47 from 94.5 % to 22.8 % and v61
  from 99.8 % to 97.6 % on the clone, and the false-cross board from 69.2 % to 0 %.
  The direction of the conclusion survives, its size does not.
* **Perception v61**: trained on the earlier SILVER set, episode-held-out validation
  at the deployed gate 99.16 % target acceptance, 0/72 wrong-object and 0/362
  background acceptances - **not promoted**: on E02's recorded frames it accepts the
  blank clone 97.6 % of the time at the deployed sampler (v47: 22.8 %).
* **Tests**: `tools/test_protocol_v60.py` all checks pass (one stale grace-window
  expectation corrected); `tools/test_disarm_policy.py` 9/9.

## Bugs this pass found and fixed

1. **The disarm fallback was unreachable.** `NativePX4.request_disarm()` raises
   without a PX4-reported airborne-to-landed transition, which a touch-and-hold never
   produces. `E03_v60_ondeck` crashed on exactly that call. Fixed with
   `WindowsPX4.request_forced_disarm()` (MAV_CMD_COMPONENT_ARM_DISARM, param2 21196).
2. **The speed gate defeated the rule.** A body pressed onto the deck oscillates at
   ~0.3 m/s, so `speed < 0.2` rejected the state the rule existed for. The rule now
   uses a 1.0 s within-5-mm dwell and ignores speed; the dwell is the safety
   property.
3. **Tooling**: digest glyph map clamped for boxes outside the frame; batch
   membership made explicit; flight comparison now reports the start-state gap.
4. **The mission's planning range could never be computed** (this pass, found by
   replay): the coarse estimate was gated on `control_phase == 'visual_acquire'`, a
   phase the v60 expert never emits, so no finish estimate existed in any v60 flight
   and the return-time reserve ended every long approach on its own (E08: 53 s).
   `mission_safety.py` now takes the actor's selected track and range interval, and
   measures the closing rate instead of assuming 0.7 m/s.
5. **A retired candidate crashed the teacher** (this pass, found by the first E08
   re-flight at 14 s): the inherited `inspection_feedback_v25` helper writes a bare
   timestamp into `protocol.rejected`, which v60 reads as `(time, reason)`. The first
   E08 flight (`review_v61/E08_v61`, 350 frames) died on it. Fixed by normalising both
   shapes in `protocol_priority_v60.py`, with a regression test; the probe gate was
   re-run (`runtime_probe_windows_v61.json`, 16 frames, `finite_actions: true`).

## Blockers / open

0. **The E08 fix is replayed, not yet flown.** `tools/replay_mission_v61.py`
   reproduces the recorded 53.48 s stop before the change and keeps flying after it,
   but a replay cannot show that a different mission decision ends in a landing.
   `review_v61/E08_v61` is that flight; its receipt pins
   `mission_safety_sha256 = cd0b349c...` (this is new - the mission layer was
   previously not hashed at all). That flight crashed at 14 s on bug 5 above, so the
   actual re-flight is `review_v61/E08_v61b`.

1. **E02 is a scale ambiguity, not a classifier bug.** A 191 px cyan panel at 20 m is
   geometrically identical to the real 30 px pad at 6 m under the assumed boat-height
   plane; the teacher's implied length (1.48 m) looks plausible. Needs parallax or a
   size sanity gate before confirmation (section 7 of the report).
2. **Press after contact is designed-in, not fixed.** `touchdown_commit` holds a
   descent command until the autopilot declares landing. The fallback now caps the
   press at ~1.1 s instead of 3.7 s, but a real deck would still be loaded. The
   upstream fix (cut descent on measured contact) is not attempted.
3. **No repeats.** One flight per configuration; nothing here is a rate.
4. **Forced disarm is unqualified on hardware** and only exists in the Windows review
   adapter.

## Next actions, in order of value

0. **Re-fly the older situations on the current tree.** Nothing else can produce a
   controlled old-against-new flight row, and the pilot matrix currently describes
   protocol `0be9b529` with adapter `fd06a59b`, not what is on disk. Minimum useful
   set: E01, E03, E06, E08 - one situation per decision branch, flown from the same
   harness and the same adapter so the benchmark's flight tier can say
   `flight_pass` instead of `blocked_uncontrolled_basis`. Run the benchmark before
   and after; it already states what should change.
1. Implement the **parallax + size sanity gate** in the protocol before any
   confirmation; re-fly E02. This is the only path that can turn E02 into a
   demonstration, and row `d05_scale_ambiguity_20m` is already failing in both arms
   waiting for it.
2. Stop pressing: make the teacher cut descent once contact is measured, then re-fly
   E03 and expect the `no_press_after_contact` soft failure to disappear - the first
   possible GOLD.
3. Read `review_v61/E08_v61c` once it lands (it has landed; see the result above) and compare it against `E08_v60` with
   `tools/compare_flights.py`, which now states the basis. It is flown on the v47
   recogniser this batch's SILVER flights used, with the mission repair and the reorient
   bound, so the comparison is about those two changes and not about a new recogniser.
   If the reserve still fires, the measured closure or the estimate is wrong and the
   numbers are in the record.
4. Build the v62 crop cache under an explicit rule that admits **observer-labelled
   hard negatives** from rejected flights (E02 blank clone, false-cross board) while
   keeping the flight rejected for policy learning. Retrain; make the decoy probe the
   acceptance test.
5. Re-run the whole batch once 1 and 2 land, and add a flight row per configuration
   to `benchmark_v62`. A benchmark row that never fails is a regression guard, not
   a comparison.
6. **Tidewater**: build the missing IPC bridge from Tidewater's observation schema
   to `IdentityExpertV60` + `MissionLayer`, then the three declared `t0*` rows can run
   here - the MuJoCo and PX4 WASM modules and the headless probe are already present
   locally, only the staged runtime receipt is absent.
