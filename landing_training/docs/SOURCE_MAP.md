# Source map

All Python modules retain their original import and command paths. The approval
gate fingerprints their contents and paths, and Tidewater's native integration
imports several modules directly. Files are grouped physically under `sim/`,
`teacher/`, `data/`, `training/`, `tools/` and `tests/`; the package's
`__init__.py` resolves the historical flat module names to those files.

## Simulation and geometry

| File | Responsibility |
|---|---|
| [config.py](../sim/config.py) | Scenario definitions, validation and baseline review scenarios |
| [scene.py](../sim/scene.py) | Combined CAD scene, assets and compiled simulation geometry |
| [environment.py](../sim/environment.py) | Coupled simulation, dynamics and clocks |
| [px4.py](../sim/px4.py) | Native PX4 integration and simulation interface |
| [collision_pieces.py](../sim/collision_pieces.py) | Generated deck collision geometry |
| [visual_lod.py](../sim/visual_lod.py) | Visual mesh simplification/cache generation |

## Episodes, data and review

| File | Responsibility |
|---|---|
| [privileged_teacher.py](../teacher/privileged_teacher.py) | Visible-instance oracle, search decisions and current privileged teaching labels |
| [smooth_landing.py](../teacher/smooth_landing.py) | Smoothed explicit teacher landing controller |
| [wave_teacher.py](../teacher/wave_teacher.py) | Wave-aware teacher variant; original search rules, clearance-scaled descent gate |
| [expert.py](../teacher/expert.py) | Baseline expert and simulated beacon |
| [run_episode.py](../data/run_episode.py) | Episode execution and recording orchestration |
| [recording.py](../data/recording.py) | Synchronized records and numeric observations |
| [collect.py](../data/collect.py) | Approved dataset collection |
| [review.py](../data/review.py) | Review bundle export |
| [audit.py](../data/audit.py) | Recorded episode audit |
| [gate.py](../data/gate.py) | Approval checks and source/artifact fingerprints |

## Original learning pipeline

The active multi-boat search implementation is in
[training_runs/search_revision_20261025](../../training_runs/search_revision_20261025/).
Its source, curated dataset and output paths are protected while training runs.

| File | Responsibility |
|---|---|
| [policy.py](../training/policy.py) | Original recurrent imitation policy/runtime |
| [train.py](../training/train.py) | Original training workflow |
| [evaluate.py](../training/evaluate.py) | Held-out evaluation for that baseline workflow |

These are the original baseline entry points. The final policy's networks and
control code are listed in [ARCHITECTURE.md](ARCHITECTURE.md#versions).

## Qualification, measurements and rendering

| File | Responsibility |
|---|---|
| [qualify.py](../tools/qualify.py) | Environment consistency and qualification checks |
| [benchmark.py](../tools/benchmark.py) | Review-only speed/weather flight trials |
| [collection_benchmark.py](../tools/collection_benchmark.py) | Collection throughput and worker-count measurements |
| [limits_report.py](../tools/limits_report.py) | Speed/weather evidence report |
| [stress_review.py](../tools/stress_review.py) | Supplementary stress review exports |
| [rendering.py](../tools/rendering.py) | Review rendering and video output |
| [ocean_preview.py](../tools/ocean_preview.py) | Ocean appearance preview |

## Setup and contracts

| File | Responsibility |
|---|---|
| [setup.sh](../setup.sh) | Linux environment preparation |
| [setup_px4.py](../tools/setup_px4.py) | Native PX4 preparation/build |
| [paths.py](../sim/paths.py) | Imports for sibling simulator packages |
| [__init__.py](../__init__.py) | Python package entry |
| [requirements.txt](../requirements.txt) | Core dependency ranges |
| [requirements-lock.txt](../requirements-lock.txt) | Pinned prepared-environment dependencies |
| [requirements-training.txt](../requirements-training.txt) | Baseline CPU PyTorch dependencies |
| [pyproject.toml](../pyproject.toml) | Package metadata and setuptools distribution config |
| [schema.json](../schema.json) | Original recording contract |
| [dataset_plan.json](../dataset_plan.json) | Original proposed collection plan |

The baseline plan and dependency pins are preserved reproducibility inputs, not
a summary of every later experiment. The latest candidate's manifest records its
own provenance.

## Tests

| File | Responsibility |
|---|---|
| [test_privileged_teacher.py](../tests/test_privileged_teacher.py) | Decision-boundary tests: hidden truth cannot choose the search destination |
| [test_smooth_landing.py](../tests/test_smooth_landing.py) | Descent-gate hysteresis, camera control and command limits |

## Generated and external material

`build/`, `.vendor/`, `.venv/`, `outputs/`, `datasets/`, `checkpoints/` and
`__pycache__/` are ignored by this package's Git rules. The local workspace also
contains `.vendor/`, `.venv/` and interpreter caches; these are protected during
active training. Compiled scene, collision and visual LOD caches are preserved.

The repository-level `artifacts/` contains preserved experiment evidence and
frozen policy bundles. It is separate from the importable baseline package.
