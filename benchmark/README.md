# Drone policy benchmark

**9 November 2026: wave-gate teacher full-20 result.** The separate wave-aware policy completed the revised twenty-case set at **99.17/100**, with **20/20 valid flights and 20/20 strict target landings**. All category scores are 100 except mission speed at 91.66. [Full-20 results](reports/2026-11-04-teacher-four/FULL20_RESULTS.md) and [verification](reports/2026-11-04-teacher-four/FULL20_verification.json). The 4 November targeted four-case run remains; the 25/26 October comparison and frozen teacher identity/78.3 are unchanged. The full-20 score is on revised plan `3c2b501…`, not the old plan.

**26 October: revised moving-target decoy cases.** For the city/rock zero-radio
decoy searches and rock combined-stress case, use the separately versioned
[bounded-search revision](revisions/bounded_search_20261026/README.md). It measures
actual camera visibility and keeps the moving boat near the decoy search area.
Its README contains the new-student, teacher and R15 run commands. The original
command and results below remain the frozen v3 comparison.

The approved two-worker run evaluates the teacher on the three replacements and
the fresh search student on all twenty cases. Its
[live results](runs/bounded_teacher3_student20_20261026_v1/RESULTS.md) and
[progress](runs/bounded_teacher3_student20_20261026_v1/progress.json) update as
flights finish; the full old comparison below retains its original provenance.

![Completed matched comparison: teacher, R15 and older policy](figures/model-comparison.png)

**Completed 25 October 2026:** teacher **16/20**, R15 **11/20**, older radio-robust
policy **8/20** strict target landings. Weighted scores also include acquisition
and speed. [Preserved results and failure analysis](reports/2026-10-25/RESULTS.md)
and [verification](reports/2026-10-25/verification.json) are outside ignored raw-run
storage. All 60 cases were valid. The new search head is not part of this comparison.

This is a real MuJoCo/PX4 mission evaluation suite. The selected comparison is
the privileged teacher reference, R15 and the earlier radio-robust policy,
20 identical cases per actor. The dashboard identifies each exact run and is
regenerated after each flight. Qualification checks and interrupted runs are
preserved separately; incomplete suites have no overall score. Historical
success claims and example percentages are not imported.
See [the pre-execution review](REVIEW_20261024.md) for issues found and corrected
before this comparison.

Completed run: [preserved final summary](reports/2026-10-25/SUMMARY.md).

Open [the HTML dashboard](ui/index.html) directly in a browser. It works offline
without a server. [Every policy, weight, architecture and timestamp](models/INVENTORY.md)
is listed separately, with machine-readable receipts in `models/inventory.json`.

## Why this benchmark exists

The mission is to find the correct boat from onboard RGB and declared sensors,
obtain a trustworthy pad pose, match the moving deck and physically land. These
are different skills. A scripted search using the real target coordinate, an
expert-assisted learner, a marker that merely enters the image, contact with an
armed aircraft, and a safe home return do not establish successful autonomous
target landing.

The original `landing_training/policy.py` is a historical MobileNet/GRU action
network. The available R15 lineage instead estimates pose, registers the marker
geometrically and uses explicit guarded control plus PX4. Observable teachers
add recognition, object tracks and search rules. They appear as distinct actors,
not as improved neural student weights. Learned-policy trials never call DAgger
or `Expert.act()` during the task. The current privileged teacher is explicitly
separate: its private visible-instance oracle and visible-pad geometry drive
the teacher controller. `Expert.prepare()` performs physical takeoff before the
timed task; `bounded()` clips every actor to the common action envelope.

## Layout

```text
benchmark/
  models/
    INVENTORY.md             Every loose weight and full-policy configuration
    inventory.json           Hashes, architectures, original locations, timestamps
    weights/<sha256>.<ext>    Actual deduplicated checkpoint copies
    <policy-id>/
      model.json             Full policy identity and original-source receipts
      policy.json            Preserved calibration/configuration
      architecture.json      Architecture and exact source references
      weights.json           Named checkpoint Ã¢â€ â€™ stored hash mapping
  environments/
    suite.json               Frozen explicit cases, map seeds and scoring weights
    runtime.json             Pinned scene/PX4/source/asset hashes
  runtime/px4_bridge.mjs      Separate bridge for this working tree's PX4 build
  runs/<new-run-id>/          Created only by the explicit run command
    run.json                 Selected policies/cases, backend, versions and machine
    <policy>/<case>/          Raw trace, scene/start receipts, PX4 logs and result
  ui/                        Static HTML/CSS/JS, generated inventory/results data
  tests/                     Offline design/scoring/receipt tests, no simulation
```

Weights are copied once per unique SHA-256. Controller/search sources remain in
their preserved repository locations and are verified before every trial; a
trial stages its own bundle. No old bundle is rewritten. Filesystem modification
times and snapshot capture times are reported explicitly. They must not be
presented as training timestamps when training provenance does not supply one.
Archive members are also inspected without unpickling, hashed, listed and copied
by unique content hash. Full archived flight pipelines are not automatically
promoted into runnable policies or silently substituted for missing runtime code.

## Test design

Each policy suite has **20 flights maximum**: ten representative conditions,
each repeated on a second procedural map/seed. Every policy receives identical
cases. This is a quick comparative screen, not a statistically strong safety
qualification; two repeats can reveal obvious regressions but cannot establish
reliability.

| Category | Flights | Conditions | Weight |
|---|---:|---|---:|
| Landing / boat speed | 4 | 0.6 and 1.5 m/s boat; 30 m visible start; two maps/seeds each | 20% |
| Wind | 2 | 4 m/s wind; 0.6 m/s boat; two maps/seeds | 15% |
| Waves | 2 | 0.15 m configured waves; 0.6 m/s boat; two maps/seeds | 15% |
| Acquisition | 10 | 30 m radio-on baseline; at 100 m, radio on/off Ãƒâ€” static distractor boats present/absent; two maps/seeds | 30% |
| Combined | 2 | 100 m, 1 m/s boat, 4 m/s wind, 0.15 m waves, radio off, distractors; two maps/seeds | 10% |
| Mission speed | Reuses all 20 | Time credit only on strict target landings | 10% |

All cases use a 6 m initial deck clearance and a 240 s task budget. The boat
starts its route when the task starts; takeoff is outside the timed task. A
benchmark-only Scenario subclass extends the original 60 m/180 s validator to
100 m/240 s. Long starts and stronger weather are explicitly marked
extrapolation, not previously qualified conditions. Speed is derived from the
same flights, so it adds no runs.

The maps are the project's procedural MuJoCo coastal worlds produced by
`BoatSim.new_world`, not five interchangeable stock XML files. The explicit map,
world/path seeds, rotation and route direction define each environment. The four
far radio/distractor conditions share their map/route/spawn seeds and use a
seaward side view so the target is resolvable after the camera finds it. Both
decoy variants load the exact same reviewed six-boat MJB. The no-decoy variant hides
every authored decoy geom and sets its collision masks to zero. The decoy variant
uses the project's existing non-overlapping placement routine, with three similar
and three dissimilar boat decoys. These are static physical distractor boats,
not dynamic other-boat traffic; moving traffic
is not supported by this benchmark yet. The target CAD,
drone CAD, mass properties, ocean forces, solver and physical touchdown scorer
are unchanged. Actual initial range (Ã‚Â±0.75 m), target pixels, placement and
achieved bearing are recorded; a case that violates its purpose is invalid.

Radio-on supplies independent, seeded 1 Hz noisy deck position/velocity fixes
(0.25 m and 0.025 m/s Gaussian sigma), age, validity and dock-ready status.
Radio-off removes the entire beacon field, including readiness; own PX4
odometry/GNSS remains. Models explicitly normalize absent radio themselves.
There is no true target coordinate, segmentation, object ID, scoring field or
truth-based waypoint in the actor's observation. Declared own-home, nominal boat
height and static recovery/corridor priors match the existing mission interface.

## Scoring and evidence

- **Strict landing:** original environment outcome `landed`; stable, disarmed
  target-deck support for at least 2 s; zero collision/water strike, wrong-target
  contact or assisted task frames. Ordinary disarm requires PX4's landed flag.
  The scorer never force-disarms the aircraft using target truth.
- **Acquisition:** an accepted/confirmed metric pad estimate within 0.75 m of
  actual target position for ten consecutive 25 Hz decisions (0.4 s), first
  achieved by 120 s, with no false acquisitions or physical failures. An accepted
  estimate more than 2 m from the target records a false-acquisition event.
  Verification happens after the policy decision and never feeds the actor.
  Acquisition can succeed even when subsequent landing fails; the trace and
  separate strict landing counts expose that difference.
- **Speed:** `100 Ãƒâ€” clamp((240 Ã¢Ë†â€™ landing_time) / (240 Ã¢Ë†â€™ reference), 0, 1)` on
  strict target landings, otherwise zero. `reference = spawn_distance/2 + 6/0.18
  + 10` seconds, a common command-envelope/descent/confirmation reference rather
  than a model-specific best time. Speed macro-averages the five source
  categories, so no test category dominates speed. Synchronized action
  inference p50/p95 and 40 ms deadline misses are also recorded as diagnostics;
  hardware latency does not change mission-score weights.
- **Actual conditions:** after a 10 s boat acceleration allowance, at least 80%
  of measured deck horizontal speeds must be within max(0.15 m/s, 20% requested)
  of the requested boat speed. A completed route invalidates the motion condition.
  Early failed flights still count as failures when speed samples are not yet
  available. Wind and deck motion are in the raw trace; configured wave height
  is an ocean-model setting, not a claim about measured sea-state statistics.
- **Aggregation:** equal case weights within each category, then the table's
  weighted sum, bounded 0Ã¢â‚¬â€œ100%. A policy needs all 20 valid cases for a total.
  Timeouts, fallback and failed boat missions score zero for landing and speed.
  Missing data, infrastructure errors and unmet scene/motion conditions are
  unscored, prevent a total, and remain visible in coverage. Category landing
  counts include Wilson 95% intervals; paired trials are correlated, so these
  are descriptive intervals, not an independent population guarantee.

Every result binds policy identity, exact suite, runtime, machine and dependency
versions. The report rejects changed/missing raw traces and foreign/duplicate
cases, and keeps separate runs separate. Compare policies in the **same run**.
Partial category values are explicitly provisional. Original historical reports
and videos are not ingested because they mix truth-based experts, assisted
controllers, changed start distributions, early stops and different platforms.

## Commands (from the repository root)

These commands **do not run benchmarks**:

```powershell
python -B -m benchmark list
python -B -m benchmark preflight --policy <exact-id-from-list>
python -B -m unittest discover -s benchmark/tests -v
node benchmark/tests/ui.test.cjs
python -B -m benchmark report
```

`python -B -m benchmark prepare` refreshes the local inventory, deduplicated weight
copies, plan and runtime pins. It performs no model inference or flights. Use it
only when intentionally creating a new snapshot after reviewing source/model
changes; it does not make old results comparable with the new snapshot. Preserve
the old benchmark folder if its receipts/results need long-term reproduction.

**The following command launches flights:**

```powershell
python -B -m benchmark run --policy <policy-id-A> <policy-id-B>
```

A first explicit compatibility flight can later use
`--case acquisition-far-visual-traffic-city-r0 --name compatibility-check`.
Subsets, `--category` and `--map` are diagnostic and cannot create a full score.
New run directories are required; results are never overwritten or silently
resumed. Workers run sequentially in isolated processes. The suite is capped at
20 flights per policy (240 s simulated budget each; wall time depends on machine
and policy).

The implemented backend is **Windows Python MuJoCo + Node real PX4 WASM**, using
the project's existing transport and onboard renderer. Linux/native PX4 and
Tidewater UI-worker results are separate benchmarks and cannot be mixed here.
Use the project's existing simulation/training Python environment with MuJoCo
3.14, Torch/torchvision, NumPy, SciPy, Pillow, pymavlink and OpenCV; Node must be
on PATH. `preflight` checks installed dependencies and exact receipts without
starting inference. It does not prove future flight compatibility. Model contract
probes check loading and finite six-command outputs with radio present/absent;
they do not measure flight performance. The static geometry audit is
`python -B -m benchmark.audit`. Physical takeoff, delivered boat motion and
outcomes are checked again in each benchmark flight.

No training data is collected/admitted, model weights updated, production policy
selected, or website published by this suite.

## Matched inference hardware

`benchmark run --device cuda ...` runs every selected learned actor on the same
GPU; the run receipt records its name and CUDA version. CPU remains the default.
GPU action timing synchronizes before and after inference. The teacher has no
neural network and remains a privileged reference. Physics and mission scoring
use the same lockstep backend for all actors; compute latency is reported
separately and is not silently converted into flight performance.

The 24 October comparison selects the available RTX 2060. An initial R15 CPU
flight reached descent, but its approximately 142 ms decisions exceeded the
40 ms control interval; its partial trace is retained as a diagnostic with no
completed score. Both CUDA pipelines are checked before the matched runs.

Completed 25 October: [verified comparison and failure analysis](reports/2026-10-25/RESULTS.md). All 60 cases are valid; the workers have finished.
