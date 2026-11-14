# Layout migration — 11 November 2026

Modules moved from the package root into purpose folders. Their historical
`landing_training.<module>` import names are unchanged: `__init__.py` resolves
each legacy name to its new file. `python -m landing_training.<module>` commands
keep working.

No policy source bytes, weights, scores, or evidence files were changed.

## New layout

```text
landing_training/
  __init__.py          legacy-name resolver
  sim/                 world, PX4, geometry and paths
  teacher/             privileged, smooth and wave teachers
  data/                episodes, recording, review, audit, approval gate
  training/            original imitation policy and training
  tools/               qualification, benchmarks, reports, rendering, setup
  tests/               focused unittest modules
  docs/                current reference, reports, history
```

## Mapping

| Old | New |
|---|---|
| `config.py` | `sim/config.py` |
| `scene.py` | `sim/scene.py` |
| `environment.py` | `sim/environment.py` |
| `px4.py` | `sim/px4.py` |
| `collision_pieces.py` | `sim/collision_pieces.py` |
| `visual_lod.py` | `sim/visual_lod.py` |
| `paths.py` | `sim/paths.py` |
| `privileged_teacher.py` | `teacher/privileged_teacher.py` |
| `smooth_landing.py` | `teacher/smooth_landing.py` |
| `wave_teacher.py` | `teacher/wave_teacher.py` |
| `expert.py` | `teacher/expert.py` |
| `recording.py` | `data/recording.py` |
| `collect.py` | `data/collect.py` |
| `review.py` | `data/review.py` |
| `audit.py` | `data/audit.py` |
| `run_episode.py` | `data/run_episode.py` |
| `gate.py` | `data/gate.py` |
| `policy.py` | `training/policy.py` |
| `train.py` | `training/train.py` |
| `evaluate.py` | `training/evaluate.py` |
| `qualify.py` | `tools/qualify.py` |
| `benchmark.py` | `tools/benchmark.py` |
| `collection_benchmark.py` | `tools/collection_benchmark.py` |
| `limits_report.py` | `tools/limits_report.py` |
| `stress_review.py` | `tools/stress_review.py` |
| `rendering.py` | `tools/rendering.py` |
| `ocean_preview.py` | `tools/ocean_preview.py` |
| `setup_px4.py` | `tools/setup_px4.py` |
| `test_privileged_teacher.py` | `tests/test_privileged_teacher.py` |
| `test_smooth_landing.py` | `tests/test_smooth_landing.py` |

## Receipts

`benchmark/definition/runtime.json` and the teacher policy records now point at
the new paths. Unchanged files kept their SHA-256; only the files that had to
know their new location were edited:

- `__init__.py` — legacy-name resolver
- `sim/scene.py`, `sim/paths.py` — package/repository root depth
- `data/gate.py` — fingerprints the grouped tree
- `tools/setup_px4.py`, `tools/collection_benchmark.py` — package root depth

Policy identity hashes were not rewritten: the teacher's policy source bytes are
unchanged, so old evidence still matches its `policy_identity_sha256`. Approval
bundles created against the old layout must be regenerated because the approval
gate fingerprints paths as well as contents.

## Verification

- 30 legacy module names imported successfully.
- `python -m landing_training.qualify --help` works.
- 23 focused unittests pass.
- Teacher benchmark preflight reports zero errors.
