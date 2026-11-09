# E03 repair: the disarm fallback was unreachable, and what it took to prove it

*2026-10-21, second pass of the teacher-repair phase. Every number below is read
from `preview_result.json`, `steps.jsonl`, `source_receipt.json` or
`record/RECORD.md` in `artifacts/local_curriculum_20261020/review_v60/`.*

The first pass left one open item: E03 touched the deck, hovered armed, and ended
`collision_failure`; the disarm-at-rest code was written but never flown. This
pass flew it four times. Two of those flights ended `landed` for reasons that had
nothing to do with the new code, one crashed because the new code called a
function that refuses to run, and the last one exercised the rule properly.

## 1. The five E03 flights

| case | harness | outcome | `disarm_reason` | frames | tier |
|---|---|---|---|---|---|
| `E03_v60` | `run_windows_review_v60.py` | `collision_failure` | — | 1138 | **REJECT** |
| `E03_v60_repair` | `run_windows_review_v60_repair.py` | `landed` | `px4_landed` | 1215 | SILVER |
| `E03_v60_rest` | `run_windows_review_v60_rest.py` (speed-gated rule) | `landed` | `px4_landed` | 1180 | SILVER, not a batch member |
| `E03_v60_ondeck` | same harness, same rule | **crashed** | — | 1141 written | NO-DATA |
| `E03_v60_forced` | `run_windows_review_v60_rest.py` + forced disarm | `landed` | **`rest_on_deck`** | 1117 | SILVER |

Same scenario, same v60 teacher, same frozen v47 recogniser in all five
(`recognizer_sha256 = fd12bb89…`, `protocol_sha256 = 0be9b529…`). Only the
termination code differs after the first row.

## 2. What the first two repairs actually proved

`E03_v60_repair` and `E03_v60_rest` both landed, and both disarmed through
`px4_landed` - PX4's own land detector. The new fallback never fired:

* `E03_v60_rest` recorded the measurements at the moment of disarm:
  `clearance_m = -0.0027`, **`speed_m_s = 0.3008`**, **`dwell_s = 0.0`**,
  `px4_landed = true`.
* The rule as written then required `speed < 0.2`. A body pressed onto the deck at
  full descent command oscillates at ~0.3 m/s, so the speed gate rejected exactly
  the state the rule existed for. The dwell counter never even accumulated.

So the honest reading of those two flights is: the landing came from the teacher
change (probability sanitisation) and from PX4 latching, not from the new code.

## 3. The bug that made the branch dead code

`E03_v60_ondeck` is the flight where the rule did fire. It crashed with:

```
RuntimeError: Ordinary disarm requires PX4 airborne-to-landed transition
```

`NativePX4.request_disarm()` refuses to send a disarm unless PX4 reports the
airborne-to-landed transition - the very transition a touch-and-hold never
produces. **The fallback shipped in the previous pass could never have run.** It
was written, reviewed, and never executed; nothing in the previous pass could
have caught that without flying it.

The fix is a forced disarm in the Windows adapter, which is where PX4-specific
command framing already lives:

```python
def request_forced_disarm(self):
    if not self.was_airborne or not self.armed: raise RuntimeError(...)
    self.command(mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 21196)
```

`21196` is PX4's magic parameter for a forced disarm. The Linux parent package is
untouched; the change is scoped to `windows_px4_v2.py`.

## 4. The rule, and why speed is not part of it

`artifacts/local_curriculum_20261020/disarm_policy.py` now holds the rule as a
pure function so it can be tested without a flight:

* `physical_rest` - continuous contact ≥ 0.8 s and speed < 0.2 m/s (unchanged).
* `rest_on_deck` - **within 5 mm of the deck for 1.0 s**, speed ignored.

The dwell is what makes it safe, not a speed gate: a descending vehicle cannot
hold the last five millimetres for a full second, because the deck is solid and
stops it. Before spending a flight, the predicate was evaluated offline against
three recorded E03 trajectories (armed, clearance ≤ 5 mm, 25 consecutive frames):

| trajectory | would fire at task t | actual end of flight |
|---|---|---|
| `E03_v60` baseline | 43.0 s | `collision_failure` at 45.0 s |
| `E03_v60_repair` | 43.96 s | `px4_landed` at 45.12 s |
| `E03_v60_rest` | 42.36 s | `px4_landed` at 45.12 s |

It fires after touchdown in all three and never during the descent. Nine test
scenarios cover the cases that must not fire: a fast descent, a bounce of 0.6 s,
skimming 1 cm above the deck, hovering 30 cm above it, a disarmed vehicle, a
vehicle that never flew, and a second disarm inside the one-second guard.

## 5. The flight that proves it

`E03_v60_forced` receipt:

```
outcome            landed
disarm_reason      rest_on_deck
disarm_detail      task_s 42.60, clearance -0.0032 m, speed 0.300 m/s,
                   dwell 1.00 s, contact_s 0.71, px4_landed false
disarmed_contact   2.001 s      -> physical event landed@64.62 s
frames             1117
```

The fallback fired 1.12 s after first contact, ~2.5 s before PX4 would have
latched, and the episode ended `landed` because the env only needs two seconds of
disarmed contact. Tier: **SILVER**, no hard failure, no failed hard acceptance
criterion (the earlier `E01.4_no_false_boat_claim_drives_selection` now passes at
0 frames).

The cost of the press is measured and reduced, not removed: downward command is
still full-scale for **1.08 s / 28 frames** after first contact, against
**3.72 s / 94 frames** in `E03_v60_repair` and an unrecovered press in the
baseline. That is the remaining soft check `physical.no_press_after_contact`. The
proper fix is upstream - the teacher should cut descent on measured contact
instead of pressing until the autopilot declares landing - and is not attempted
here; the fallback is a safety net, not a substitute for it.

## 6. What these flights cannot settle

* **They are not bitwise comparable.** PX4 preparation ends on a condition, not a
  fixed step count: the two runs start 3.6-3.9 mm apart and diverge behaviourally
  at task 0.12 s (`target_inspect` versus `scan`). `tools/compare_flights.py`
  reports the start gap and calls such a comparison behavioural for that reason.
  So the landing of `E03_v60_repair` cannot be attributed to any single teacher
  edit; only the *disarm branch that fired* is attributable, and its receipt says
  `px4_landed`.
* **n = 1 per configuration.** No statistical claim is made about how often PX4
  latches, or how often the fallback is needed.
* **One scene, small sea state** (`wave_height 0.03 m`, boat speed 0.3 m/s). A
  real deck in a swell is a different problem, and a forced disarm while a boat
  rolls is not qualified by this.
* The forced disarm is a **review-harness cleanup path**, not a flight-controller
  feature qualified on hardware. `production_qualified` stays false in every
  receipt.

## 7. Test and tool fixes made on the way

* `tools/test_disarm_policy.py` - 9 scenarios, new.
* `tools/test_protocol_v60.py` - one stale expectation corrected: it required
  descent to stop on the first frame without fresh geometry, while the protocol
  deliberately keeps the permission for `GEOMETRY_GRACE_S = 0.6` s (a documented
  anti-flap rule). The test now asserts both sides of that window: descent
  survives a 0.24 s marker loss and is revoked after 0.94 s. This is a check
  changed because the requested behaviour differs from what it asserted, and the
  behaviour it now asserts is verified by the same test.
* `tools/llm_flight_digest.py` - `scene_map` indexed past its glyph grid when a
  truth box was partly outside the frame (E03's long-range frames). Both ends are
  now clamped; the mapping is unchanged for boxes inside the frame.
* `tools/approve_batch.py` - gained `--cases`, so the batch is a named list
  (`PILOT_CASES.json`) instead of "every `E*` directory", which had started to
  include abandoned first attempts.
* `tools/compare_flights.py` - reports the start-state gap and refuses to claim
  bitwise comparability when the runs start apart.

## 8. Reproduction

```bash
cd artifacts/local_curriculum_20261020
python probe_gate_v60.py --tag _repair                     # binds v47 + current teacher
python run_windows_review_v60_rest.py --job review_v60/jobs/E03_v60_forced.json
python ../teacher_repair_20261020/tools/flight_microscope.py review_v60/E03_v60_forced
python ../teacher_repair_20261020/tools/llm_flight_digest.py  review_v60/E03_v60_forced
python ../teacher_repair_20261020/tools/approve_batch.py review_v60 \
       --cases ../teacher_repair_20261020/PILOT_CASES.json
python ../teacher_repair_20261020/tools/test_disarm_policy.py
python ../teacher_repair_20261020/tools/test_protocol_v60.py
```

Each flight needs ≥ 2.0 GiB free at admission; these ran at 6.2-6.9 GiB
available with a 1.47 GiB process RSS and 4.3-4.7 GiB free during the flight, so
the admission guard was met without changing it.
