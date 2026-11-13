# AeroDock Benchmark V2

A clean, frozen four-policy benchmark for the 20-case maritime landing suite.
The benchmark code, policy assets, and canonical evidence live here; the
existing simulator, source bundles, and pinned PX4 assets are shared
repository-level dependencies and are not duplicated.

The previous benchmark tree is archived at `old/benchmark/` for provenance and
comparison. It is not imported by this package.

## Result

Canonical evidence is complete for all four participants:

| Policy | Score | Strict landings | Valid cases |
| --- | ---: | ---: | ---: |
| Privileged teacher / wave-aware gate | 99.16594561880042 | 20/20 | 20/20 |
| Fresh search student / frozen R15 | 87.7710373737363 | 18/20 | 20/20 |
| R15 / archived export | 57.49461407701248 | 11/20 | 20/20 |
| Radio-robust / 15 October | 54.88614553000801 | 7/20 | 20/20 |

`benchmark.json` is generated from evidence and is the viewer's data source. A
policy lock is not proof of a scored acquisition; treat `condition_valid` as
scenario validity, not as a landing grade.

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
    r15/                   20 canonical episodes
    radio/                 20 canonical episodes
  harness/                runner, scoring, tracker, digest, routes, and PX4 bridge
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
