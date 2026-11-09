# Source map

All Python modules retain their original import and command paths. The approval
gate fingerprints their contents and paths, and Tidewater's native integration
imports several modules directly. Grouping them here keeps navigation clear
without changing the reviewed runtime or invalidating existing path contracts.

## Simulation and geometry

| File | Responsibility |
|---|---|
| [config.py](../config.py) | Scenario definitions, validation and baseline review scenarios |
| [scene.py](../scene.py) | Combined CAD scene, assets and compiled simulation geometry |
| [environment.py](../environment.py) | Coupled simulation, dynamics and clocks |
| [px4.py](../px4.py) | Native PX4 integration and simulation interface |
| [collision_pieces.py](../collision_pieces.py) | Generated deck collision geometry |
| [visual_lod.py](../visual_lod.py) | Visual mesh simplification/cache generation |

## Episodes, data and review

| File | Responsibility |
|---|---|
| [privileged_teacher.py](../privileged_teacher.py) | Visible-instance oracle, search decisions and current privileged teaching labels |
| [smooth_landing.py](../smooth_landing.py) | Smoothed explicit teacher landing controller |
| [expert.py](../expert.py) | Baseline expert and simulated beacon |
| [run_episode.py](../run_episode.py) | Episode execution and recording orchestration |
| [recording.py](../recording.py) | Synchronized records and numeric observations |
| [collect.py](../collect.py) | Approved dataset collection |
| [review.py](../review.py) | Review bundle export |
| [audit.py](../audit.py) | Recorded episode audit |
| [gate.py](../gate.py) | Approval checks and source/artifact fingerprints |

## Original learning pipeline

The active multi-boat search implementation is in
[training_runs/search_revision_20261025](../../training_runs/search_revision_20261025/README.md).
Its source, curated dataset and output paths are protected while training runs.

| File | Responsibility |
|---|---|
| [policy.py](../policy.py) | Original recurrent imitation policy/runtime |
| [train.py](../train.py) | Original training workflow |
| [evaluate.py](../evaluate.py) | Held-out evaluation for that baseline workflow |

The current frozen vision-first implementation is linked from
[CURRENT_POLICY.md](CURRENT_POLICY.md). Do not confuse these baseline entry points
with the newer candidate's training/runtime.

## Qualification, measurements and rendering

| File | Responsibility |
|---|---|
| [qualify.py](../qualify.py) | Environment consistency and qualification checks |
| [benchmark.py](../benchmark.py) | Review-only speed/weather flight trials |
| [collection_benchmark.py](../collection_benchmark.py) | Collection throughput and worker-count measurements |
| [limits_report.py](../limits_report.py) | Speed/weather evidence report |
| [stress_review.py](../stress_review.py) | Supplementary stress review exports |
| [rendering.py](../rendering.py) | Review rendering and video output |
| [ocean_preview.py](../ocean_preview.py) | Ocean appearance preview |

## Setup and contracts

| File | Responsibility |
|---|---|
| [setup.sh](../setup.sh) | Linux environment preparation |
| [setup_px4.py](../setup_px4.py) | Native PX4 preparation/build |
| [paths.py](../paths.py) | Imports for sibling simulator packages |
| [__init__.py](../__init__.py) | Python package entry |
| [requirements.txt](../requirements.txt) | Core dependency ranges |
| [requirements-lock.txt](../requirements-lock.txt) | Pinned prepared-environment dependencies |
| [requirements-training.txt](../requirements-training.txt) | Baseline CPU PyTorch dependencies |
| [schema.json](../schema.json) | Original recording contract |
| [dataset_plan.json](../dataset_plan.json) | Original proposed collection plan |

The baseline plan and dependency pins are preserved reproducibility inputs, not
a summary of every later experiment. The latest candidate's manifest records its
own provenance.

## Generated and external material

`build/`, `.vendor/`, `.venv/`, `outputs/`, `datasets/`, `checkpoints/` and
`__pycache__/` are ignored by this package's Git rules. The local workspace also
contains `.vendor/`, `.venv/` and interpreter caches; these are protected during
active training. Compiled scene, collision and visual LOD caches are preserved.

The repository-level `artifacts/` contains preserved experiment evidence and
frozen policy bundles. It is separate from the importable baseline package.
