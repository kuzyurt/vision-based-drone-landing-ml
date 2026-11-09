# Reading a rendered flight instead of looking at it

*Status 2026-10-21, teacher-repair phase. Everything below is computed from files in
`artifacts/local_curriculum_20261020/review_v60/`; no number is copied from an episode's
own claims.*

> **Update, same day:** the E03 row below is the rejected baseline. It has since been
> repaired and re-flown (`E03_v60_forced`: `landed`, `disarm_reason = rest_on_deck`,
> SILVER, no hard failures). That work also found that the previous pass's
> disarm-at-rest branch could never execute, because `request_disarm()` is gated on
> PX4's own land detector. See [ADDENDUM_E03_REPAIR.md](ADDENDUM_E03_REPAIR.md); the
> matrix and section 5 below describe the batch as flown *before* the repair.

## 1. Why screenshots are the wrong instrument

A review episode is 1000-2200 frames of 640x360 RGB plus three other records of the same
flight: the executed decision trace (`steps.jsonl`), the observer-truth timeline
(`analysis_v1/frames.csv`), and a hash-join proving the analysed frames are the frames in
`review.mp4`. A sampled screenshot answers "does this look like a boat" but cannot answer
the questions that decide whether an episode is usable as a demonstration:

* what did the actor believe, and what did it command, at that instant?
* was the object it descended on the *physical* target, or a decoy that looks identical at
  this resolution?
* did it start descending before identity and geometry were actually fresh?
* did the video encode the same moment the trace describes?

Those are relational facts across records. So the reviewer is a **join**, not a picture:
`tools/inspect_flight.py` recomputes every check from the three records, writes a readable
`record/RECORD.md`, and assigns a tier. `tools/approve_batch.py` runs it over a directory
and writes one matrix.

## 2. What the record contains

`RECORD.md` is the artefact an LLM (or a human) reads top to bottom:

1. **Header** - scenario, frames, duration, outcome, first lock time, share of frames on the
   truth target, and the exact list of failed hard/soft checks.
2. **Check table** - 24 checks with their numbers, each marked hard or soft.
3. **Macro timeline** - runs shorter than 0.75 s folded into their neighbour: how long the
   aircraft spent in each behaviour, altitude and range start->end, clearance, and the share
   of frames where the selected object was the truth target. This is the "story" of the
   flight in ~15 lines.
4. **Phase ledger** - the same, unfurled, including the reason string the actor wrote for
   each decision and the command means.
5. **Intent changes** - every change of intent with its stated reason and the evidence at
   that frame.
6. **Survey / inspection / recovery ledgers** - coverage, inspected views, candidate
   rejections, and recovery episodes split into *climb interruptions* (altitude gained) and
   *visibility management* (flag held at cruise altitude).
7. **Descent profile** - a 2 s sample of altitude, range, clearance, speed, bearing error,
   target pixels, metric freshness and the descent command.
8. **Contradictions** - calibrated, with severity, not raw rule fires.
9. **What the record cannot settle** - explicitly: re-identification across occlusion and
   appearance-level decoy confusion need the annotated clip at the named timestamps.
10. **Provenance** - sha256 of every evidence file the verdict covers.

## 3. Tiers, and what each one licenses

| tier | meaning | use |
|---|---|---|
| **GOLD** | every hard and soft check passes, no contradiction | clean demonstration |
| **SILVER** | physically landed on the truth target, but named deviations exist | perception labels usable (observer truth); policy imitation only after reading the deviations |
| **REJECT** | a physical/authority truth check failed or a severe contradiction exists | preserved, never used for training |

A guard event is not a failure. The invariant log records that the adapter *blocked* a
descent; the frame-level check verifies the block actually happened (no descent command
while the selection was off-target or the metric stale). Treating the log itself as a
failure made every safe refusal look like a violation.

## 4. Calibration: bugs this instrument found in its own first version

The first gate rejected every episode, including clean landings. Each cause was a real
defect in the analysis, not in the flights:

| symptom | cause | fix |
|---|---|---|
| all episodes failed survey/continuity | acceptance checks were read from `summary.checks`, but they live in `verdict["checks"]` keyed by name with `pass_` | read the right structure |
| "descent while not on target" on climb frames | `frames.csv` `down` is **positive when descending**; the first gate assumed the opposite | sign fixed and documented, check restricted to clearance < 3 m |
| every episode "selected a non-target" | `selected_name` is the truth label of the *selected box*; the annotator drops the mask for 2-7 frames while the track is unchanged | sub-0.35 s `none` gaps interpolated only between identical labels |
| E02 passed the "is a boat" check while sitting on a decoy | the check used a whitelist of decoy names; the scene named it `decoy_blank_clone` | any truth name other than `target` is a non-target object |
| E04 "descended with weak identity" for 77 frames | the 3-class head alternates target/wrong below 3 m while `identity_support` stays >0.84; the head is not the safety gate | truth decides the violation; head flips are reported as a perception diagnostic |
| E06/E07 "unbounded recovery" | a recovery flag held at cruise altitude during a long approach was counted as an interruption | interrupted only when altitude is gained or the phase is `recovery_*` |

Negative control: copying a SILVER episode and changing only `preview_result.outcome` to
`collision_failure` flips the tier to REJECT (`physical.landed_on_target`). The gate reacts
to evidence, not to the episode's self-report. The receipt is
`controls/NEGATIVE_CONTROL.json` (genuine SILVER / tampered REJECT, same files otherwise).

## 5. Pilot result (seven situations, one run each)

| case | tier | outcome | lock t | on target | decisive reason |
|---|---|---|---|---|---|
| E01_nominal_v60c | SILVER | landed | 0.12 s | 100 % | 3.8 s of downward command at contact before disarm |
| E04_v60 | SILVER | landed | 0.08 s | 100 % | same; 7.2 s bounded recovery climb from 1.2 m is the scenario's purpose |
| E05_v60 | SILVER | landed | 0.12 s | 100 % | same |
| E06_v60 | SILVER | landed | 17.5 s | 100 % | same; metric gap at 1.0 m triggered a 7.2 s climb recovery |
| E07_v60 | SILVER | landed | 18.1 s | 100 % | same |
| E03_v60 | REJECT | collision_failure | 0.12 s | 100 % | touched the deck, then hovered armed with zero commands; PX4 never latched `landed`, so the episode ended as a collision |
| E02_v60 | REJECT | diagnostic stop | 17.1 s | **1.0 %** | confirmed `decoy_blank_clone` at t=19.6 s and stayed on it for 2075 frames; the real target was selected for 21 frames |
| E08_v60 | REJECT | diagnostic stop | 20.8 s | 99.9 % | closed from 52 m to 10 m at 2 m/s, then the *mission* return-time reserve stopped it at 53.5 s with 126 s of budget left (see 5.1) |

Two of the three rejections are *not* tooling artefacts: E02 is a genuine wrong-object
confirmation, and E03 is a genuine terminal-state bug (no disarm at contact).

E02 hit the protocol's own 100 s search timeout while hovering over its decoy. E08 did **not**
stop for that reason - an earlier version of this report said it "held until the search
timeout at 8.4 m", which was wrong twice over: 8.4 m was its **altitude**, and its range was
52 m at the start. It approached the whole time and was stopped by the mission layer. See 5.1.

### 5.1 Why E08 stopped: a planning estimate that could never be computed

Measured from `E08_v60/steps.jsonl`, not from the episode's self-report:

| fact | value |
|---|---|
| initial range to the boat (recorded initial-view receipt) | 52.19 m at 8.4 m altitude |
| range at the last frame | 10.37 m |
| forward command while inspecting | +2.00 m/s, essentially uninterrupted |
| t of mission fallback | 53.48 s, `fallback_trigger = return_time_reserve` |
| `mission_coarse_range_m` | `None` on 1338/1338 frames |
| `mission_supported_visual_finish` | `False` on 1338/1338 frames |

The mission layer plans a return: `return_seconds` (108.6 s from 58 m of accumulated route) and
the reserve `remaining < 1.25 * return_seconds` (126.5 < 135.7 at t=53.5). The reserve is
disarmed by a *supported visual finish*, which requires a coarse range estimate. That estimate
was gated on

```
coarse = diagnostics['control_phase'] == 'visual_acquire' and ...
```

`visual_acquire` is a phase name from the **parent** policy. The v60 evidence-priority expert
emits `scan`, `inspect_candidate`, `target_inspect`, `target_align`, ... and never that name,
so in v60 flights the whole block was dead code: `coarse_samples` stayed empty, the finish
estimate was never produced, and the reserve decided every long approach on its own. Across
the 14 episodes with a step trace, `mission_coarse_range_m` is non-`None` on **2** frames in
total (E04, where a legacy phase leaked through) and 0 everywhere else.

So E08 is not a perception or protocol failure. It is a harness layer planning with an
estimator that was unreachable, and a conservative reserve then acting on the resulting
worst-case assumption ("no finish possible") against a vehicle that was 10 m from the boat
with 126 s left.

Fix, in `mission_sources/mission_safety.py`:

1. **Planning visibility from evidence the actor actually publishes** - its selected track
   and that track's bearing-plane range interval - while keeping the parent-policy test for
   policies that still emit it. The interval's upper bound is already the conservative range
   (it spans the declared plane uncertainty), so no second inflation is applied.
2. **Measured closing rate instead of a constant 0.7 m/s.** The old approach leg assumed the
   parent policy's closure, half of what the v60 expert commands at stand-off; the closure is
   now measured from the coarse range series (medians of the first and last third of a 6 s
   window), floored at 0.4 m/s so a hovering or receding estimate stays pessimistic.

What this does **not** change: the reserve itself, the 3 s pressure hysteresis, the stall
detector, and the rule that an unclosed finish is refused. `tools/test_mission_coarse_v61.py`
pins the four cases (closing, hovering, silent actor, legacy actor) and fails on the pre-fix
gate with `coarse=0, supported=0`.

Verification method, and its limit: `tools/replay_mission_v61.py` replays a recorded episode's
observations through the mission layer with a stub policy, so the mission decisions can be
recomputed without a flight. It reproduces the recorded E08 stop exactly (53.48 s,
`return_time_reserve`) before the fix; after the fix the same replay keeps flying, with a
coarse range of 55.5 -> 11.4 m and a shrinking finish estimate. It still has to be confirmed by
an actual flight: the replay cannot show that a different mission decision leads to a landing.
Re-flown as `review_v61/E08_v61`, then `E08_v61b`, then `E08_v61c`.

### 5.2 The re-flights were not the controlled test they were reported as

`E08_v61` crashed at 14 s on the retired-candidate bug (5.3 below). `E08_v61b` flew the whole
100 s search window and never approached the boat: range grew 52.8 -> 83.6 m while the aircraft
orbited 8 m from home at 8.4 m altitude and the *search timeout* fired. Both flights were run by
`run_windows_review_v61.py`, which pins `models/perception_v61/best.pt` - the recogniser section
6 describes as **not promoted** - while `E08_v60` was flown by `run_windows_review_v60_rest.py`
on `perception_training_v47/best.pt`.

From the two `source_receipt.json` files, every pinned input differs:

| basis | E08_v60 | E08_v61b |
|---|---|---|
| recogniser | `fd12bb89...` (v47) | `5d7df9eb...` (v61) |
| protocol | `0be9b529...` | `81eb1620...` |
| adapter | `fd06a59b...` | `505547e2...` |
| harness | `7b46ef41...` | `(v61 runner)` |

So `E08_v61b` cannot support or refute the mission-layer repair; the divergence it shows begins
at 6.92 s, long before any mission decision. Worse, `E08_v60` is **not exactly reproducible
today**: the adapter hash it pins is not the adapter on disk, and `mission_safety_sha256` was
not recorded at all, so the flight's own basis cannot be rebuilt. That is a provenance defect,
not just a bookkeeping one.

What changed because of it:

* `tools/compare_flights.py` reads both receipts and returns `not_controlled_basis_differs`
  instead of a divergence verdict when any basis hash differs. Re-running the old comparison
  now produces that verdict.
* `run_windows_review_v61.py` takes `--gate` and `--checkpoint`, **fails** when the probe gate
  does not cover the weights being flown, and records both in the receipt.

### 5.3 `reorient_candidate` could freeze the aircraft

Measured in `E08_v61b`: from 64 s the selection stayed on track 11 while its age grew 4 -> 36 s,
with the commanded yaw rate at **0.00 rad/s for 32 s** and no forward velocity. The adapter yaws
toward the remembered bearing, the remembered bearing already matched the heading, so the error
was zero, and nothing bounded the wait. Only the 100 s search timeout ended it.

The protocol now bounds it: `SearchProtocolV60._reorient` resumes the survey after
`REORIENT_TIMEOUT_S = 3.0`, keeps the object (losing sight is not evidence that it is the wrong
object, so it is not rejected) and logs `reorient_timeout`. Counterexample test in
`tools/test_protocol_v60.py`: with the bound removed the same scenario spends 8.00 s of 8.00 s in
`reorient_candidate`; with it, <= 3.5 s, then `scan`.

### 5.4 Result: `E08_v61c` lands, and why it is still a REJECT

`review_v61/E08_v61c` was flown on the **v47** recogniser (same as `E08_v60`), with the mission
repair and the reorient bound. Receipt: `recognizer fd12bb89...`, `protocol 7611b9a4...`,
`mission_safety cd0b349c...`, gate `runtime_probe_windows_v60_missionfix.json`.

| | E08_v60 | E08_v61c |
|---|---|---|
| outcome | development stop at 53.5 s | **landed** |
| disarm | - | `px4_landed` |
| strict physical target landing | false | **true** |
| frames / duration | 1338 / 53.5 s | 4323 / 172.9 s |
| range at end | 10.4 m | 0.0 m (on the deck) |
| touchdown | - | 189.08 s, vertical 0.12 m/s |

The return reserve no longer fires: the flight runs past the 100 s search timeout because a
supported finish exists. That is the mission repair doing its job in an actual flight, not a
replay.

It is still **REJECT**, and the reviewer is right. `authority.selection_continuity` = 93.69 %
against 98 %. That is a real deviation, not a labelling artefact: from 30.0 s to 36.5 s the
selected box sits at pixel (318-322, 178-185) - camera centre - while the annotated target is
108-149 px to its left, and the aircraft closes on that other object from 49 m to 39 m. It is
labelled `decoy_debris`. The object is boat-like (`selected_boat` true, identity support
0.52-0.73), so this is the E02 failure family in miniature: a plausible object at range wins
the selection, and here the flight recovers on its own after ~9 s.

Everything about identity and authority is clean: 3146 confirmed frames with **0** on the wrong
object, **0** descent frames with clearance < 3 m off target, lock at 20.76 s, 0 survey frames
after the target was visible, framing kept in descent 0 lost frames. Remaining soft failures:
`no_press_after_contact` (96 frames, 3.8 s - the known terminal bug) and
`digest.matches_recording` (no digest was generated for this case yet).

Comparison disclosure: `tools/compare_flights.py` reports `not_controlled_basis_differs` for
`E08_v60 -> E08_v61c` because the protocol also changed (the reorient bound). The recogniser is
identical on both sides. So this flight supports "the mission repair plus the reorient bound
reach the deck from 52 m"; the mission layer alone is still supported only by the replay.

## 6. Recogniser fine-tune (perception v61) - trained, measured, **not promoted**

Data: only the five SILVER episodes, `APPROVAL_V2.json` receipt required, crops sampled
exactly like deployed `rgb_regions` (2.5x box, 96x96, zero padding outside the frame).
5601 crops: 3294 target, 273 non-target object, 2034 background. Split by **episode**, never
by crop: E06 is held out entirely.

Parent: the frozen v47 verifier (`object_verifier_v12`, `rgb_only`). Ten epochs, class
weights `[3, 1, 1.2]`.

Held-out E06, at the deployed gate (`p_target >= 0.98` and `support >= 0.8`):

| metric | value |
|---|---|
| target acceptance | 99.16 % |
| wrong-object acceptance | 0 / 72 |
| background acceptance | 0 / 362 |
| AUROC | 0.9995 |

That looked like a clean win. It is not, and the check that shows why is the next section:
the same two checkpoints were applied to the **recorded frames of the flight that failed**,
and v61 is worse exactly where it matters.

### 6.1 Decoy probe on E02's recorded RGB (`review_v60/E02_v60/decoy_probe.json`)

Every truth-annotated instance in E02 was sampled and scored by the three checkpoints
that exist (599 crops, stride 5, deployed `rgb_regions` sampler - see
`benchmark_v62/REPORT_VERSIONS_V62.md` and `weight_ladder.json`):

| object | crops | v47 @0.98 | v61 @0.98 | v47 mean p | v61 mean p |
|---|---|---|---|---|---|
| `decoy_blank_clone` | 421 | 22.8 % | **97.6 %** | 0.930 | 0.995 |
| `target` | 20 | 20.0 % | 25.0 % | 0.726 | 0.699 |
| `decoy_false_cross_board` | 26 | 0 % | 0 % | 0.0004 | 0.011 |
| every other decoy | 132 | 0 % | 0 % | < 0.002 | < 0.002 |

The fine-tune raised true-target acceptance to 98.7 % on E01 (matching its claim) and raised
clone acceptance to 97.6 % on E02. It must not be promoted, and the E02 flight was not run
with it. Two corrections to the earlier numbers: the first version of this table used a
nearest-neighbour crop instead of the deployed grid sample, which overstated v47 on the
clone (94.5 % -> 22.8 %) and overstated v61 on the false cross (69.2 % -> 0 %). The clone is
still the one object neither checkpoint separates from the target, and for v47 it scores
*higher* than the true target.

## 7. Why E02 actually failed (the finding that matters)

`decoy_blank_clone` is a large cyan-panelled object. Measured on the recorded frames:

* its annotation box is **191 px** wide at a true range of about **20 m**;
* **31 %** of that box passes a strict cyan test (target: 0.9 %, because the real target is
  30 px wide at the same range);
* the teacher's range model intersects the bearing with the declared boat-height plane and
  concluded ~6 m, giving an implied length of **1.48 m** - a perfectly plausible boat.

So the failure is a *scale ambiguity*, not a classifier weakness. A cyan panel that is six
times the apparent size of the real pad, seen from 20 m, is geometrically indistinguishable
from the real pad seen from 6 m by a single RGB frame plus an assumed height. Both
checkpoints call it a target because, at that resolution, it *is* a pad. Fine-tuning cannot
fix that; only a second measurement can:

1. **Parallax before commitment.** Require two sightings separated by at least 1.5 m of own
   translation, triangulate range, and reject a candidate whose triangulated size is
   implausible (the pad's declared physical size is known).
2. **Size sanity gate.** Reject any "pad" whose implied physical width exceeds ~2x the
   declared pad width, regardless of how cyan it looks.
3. **Marker geometry, not marker colour.** The deployed marker head fires at 0.97 on the
   clone; colour is the wrong invariant. Use the marker's known shape/corners.
4. **Hard negatives from the failing flight** must enter v62 training under an explicit data
   rule - E02 stays REJECT for policy learning, but its observer-labelled crops are the only
   examples of this failure mode that exist.

## 8. What changed in the teacher for the v61 flights

1. **Candidate probabilities are sanitised** before the protocol sees them: a bank-sourced
   candidate could carry `None`, and a v12 softmax triple can sum to 1 + 1e-8, both of which
   the protocol correctly rejects. Values are now clamped to [0, 1]; absent values fall back
   conservatively to 0.
2. **Disarm at physical rest**: the harness only disarmed when PX4's own land detector
   latched, which needs downward thrust; a held hover one centimetre above the deck never
   latches. The harness now also disarms after 0.8 s of physical contact with speed < 0.2
   m/s and records `disarm_reason` (`px4_landed` vs `physical_rest`). The sim still requires
   two seconds of *disarmed* contact before it reports `landed`, so the outcome remains a
   physical measurement, not a courtesy.

## 9. Reproduction

```
python tools/inspect_flight.py review_v60/E04_v60 --situation E04
python tools/replay_mission_v61.py review_v60/E08_v60 --every 4
python tools/test_mission_coarse_v61.py
python tools/approve_batch.py review_v60
python train/build_episode_crops_v61.py --cases <silver episodes>
python train/train_recognizer_v61.py --val-situations E06 --epochs 10 --patience 10
python train/qualify_review_v61.py --val-situations E06
python probe_gate_v61.py
python run_windows_review_v61.py --job review_v61/jobs/E02_v61.json
```
