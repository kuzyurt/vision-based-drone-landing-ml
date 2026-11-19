# Benchmark

Five policies fly the same 20 MuJoCo missions with PX4 in the loop.

![Five policies on the same 20 missions](../docs/media/benchmark-comparison.png)

| Policy | Score | Landed | What it is |
|---|---:|---:|---|
| Privileged teacher, wave-aware gate | 99.2 | 20 / 20 | Uses simulator truth. Upper reference, source of training labels. |
| **Final version** | **84.9** | **18 / 20** | Main network and search head, the build that runs in the realistic browser game. Uses the boat's radio in the missions that offer it. Flown once, 19 November. |
| Search student, 8 November | 87.8 | 18 / 20 | Main network and pad finder (R15), frozen, plus the search head. Camera and own sensors only; this adapter blocks all boat-radio input. |
| R15 | 57.5 | 11 / 20 | Main network and pad finder, before the search head existed. Trusts the camera for position and takes only boat velocity from the radio. |
| Radio-robust, 15 October | 54.9 | 7 / 20 | Earlier hybrid that leaned on the boat's radio. Landed 7 of 14 with radio, 0 of 6 without. |

All 100 flights were valid. For the four older policies, exact values and every
episode are in [`benchmark.json`](benchmark.json). The final version is scored
with the same rules; its score, results and text digests are in
[`evidence/final/`](evidence/final/summary.json). The tracker only reads the
four inventory policies, so it is not in `benchmark.json`.

## What is measured

| Category | Weight | Missions |
|---|---:|---|
| Find the target boat | 30 % | 10: near and 100 m starts, radio on/off, with and without decoy boats |
| Landing / boat speed | 20 % | 4: 0.6 and 1.5 m/s |
| Wind | 15 % | 2: 4 m/s crosswind |
| Waves | 15 % | 2: 0.15 m |
| Combined | 10 % | 2: wind, waves, 100 m search and decoys together |
| Mission speed | 10 % | Time to a successful landing |

A landing counts only when the drone is disarmed and stable on the pad.

The final version fails two missions with waves (one moderate-wave mission and
the combined rock mission). In both it reaches the pad and then hovers 0.5 to
0.9 m above it, waiting for a fresh measurement of the pad markings, until the
240 s limit. The 8 November search student fails the two combined missions: in
one it never confirms the target and falls back, in the other it reaches 30 cm
above the pad, loses it from view and collides.

`condition_valid` means the scenario ran as specified; it is not a landing
grade. A policy's own "lock" is not a scored acquisition.

The previous benchmark is archived unchanged in `old/benchmark/`.

## Layout

```text
benchmark/
  benchmark.json          generated tracker and viewer data
  definition/
    suite.json            frozen 20-case suite
    runtime.json          pinned source, asset, and harness receipts
  policies/
    inventory.json        the three inventory policies used by the runner
    <policy>/             normalized model, policy, architecture, and weights
    student/              frozen search-student source and identity receipt
    weights/              content-addressed weights used by the four policies
  evidence/
    teacher/               20 canonical episodes
    student/               20 canonical episodes (18 strict landings)
    final/                 final version: results, cases, text digests, score
    r15/                   20 canonical episodes
    radio/                 20 canonical episodes
  harness/                runner, scoring, tracker, digest, routes, PX4 bridge,
                          and the adapter that flies the browser-game build
  viewer/index.html       static comparison viewer
  runs/                   new flights; intentionally empty
  tests/                  focused digest tests
```

Each canonical episode contains only `result.json`, `case.json`, `steps.jsonl`,
and the two diagnostic digest files. Logs, staging folders, failed candidates,
old revisions, and training data were deliberately not copied.

## Commands

Run from the repository root, where the shared simulator and source bundles are
available:

```powershell
python -B -m benchmark track
python -B -m benchmark run --name r15_20261111 --policy r15-archived-export-67a80a63
python -B -m benchmark run --name radio_20261111 --policy radio-robust-20261015-policy-bundle-44826e5a
```

`track` never starts MuJoCo, PX4, or a policy. It rebuilds `benchmark.json`
from recorded episodes. A new flight writes to `runs/` and updates the tracker;
canonical evidence is never rewritten.

The worker subprocess imports the active `benchmark` package, not the archived
`old/benchmark` tree. New flights are separate working data and are not
canonical evidence.

To fly the final version (the browser-game build) on the same missions,
without touching the pinned harness files:

```powershell
python -B -u -m benchmark.harness.tidewater_run run --name NAME [--case ID ...] [--workers 3]
```

It runs `student.onnx` on the CPU and writes to `runs/NAME` like any other new
flight. MuJoCo has no sun, so the sun-glare filter stays inactive. The tracker
does not list these runs; score them with `benchmark.harness.scoring.aggregate`.

## Viewer

Serve the repository root and open the V2 viewer:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000/benchmark/viewer/index.html`. The viewer
fetches `../benchmark.json` relative to its own page.

## Student identity

The student policy is the canonical `fresh-search-f62c10a2` bundle. Its policy
identity receipt (`policies/student/identity.json`) is carried from the
canonical bundle unchanged; moving the package changed path resolution, not the
policy identity or its checkpoint. The V2 adapter still declares the same
zero-radio input allowlist and uses the same checkpoint and frozen R15 base.

## Tests

```powershell
python -m unittest benchmark.tests.test_rollout_digest -v
```

The digest test is independent of the simulator. The benchmark requires the
same Windows/PX4, MuJoCo, PyTorch, and source-bundle prerequisites as the
original runner.
