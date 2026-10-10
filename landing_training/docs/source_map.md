# Source map

Commands use `python -m landing_training.MODULE` from the repository root.
Runtime modules keep their existing paths to preserve imports, launcher commands
and approved simulation fingerprints.

## Environment and control

| Files | Responsibility |
|---|---|
| [scene.py](../scene.py), [collision_pieces.py](../collision_pieces.py), [visual_lod.py](../visual_lod.py) | Merge original assets, preserve landing-bay contacts and prepare render geometry |
| [environment.py](../environment.py) | Shared physics, water/air forces, observations and terminal outcomes |
| `px4.py`, [runtime.py](../runtime.py), `px4_wsl.sh`, `setup_px4.py` | Native/WSL PX4 process ownership, sensor exchange, lockstep and pinned firmware build |
| [expert.py](../expert.py), [supervision.py](../supervision.py) | Teacher actions, observable overrides and imitation masks |
| [rendering.py](../rendering.py), [run_episode.py](../run_episode.py) | Camera capture, review overlay and one complete flight |
| [config.py](../config.py), [paths.py](../paths.py) | Seeded scenarios and sibling simulator imports |

## Review and data collection

| Files | Responsibility |
|---|---|
| [review.py](../review.py), [review_cases.py](../review_cases.py), [review_package.py](../review_package.py), [audit.py](../audit.py) | Export, inspect and package review videos and their raw rows |
| [gate.py](../gate.py), [qualify.py](../qualify.py) | User approval/provenance and environment qualification checks |
| [collect.py](../collect.py), [recording.py](../recording.py), [execution.py](../execution.py) | Collect flights, write HDF5/JSONL and schedule independent workers |
| [collection_session.py](../collection_session.py), [outcome_retries.py](../outcome_retries.py) | Storage admission, persistent reports, bounded retries and retained attempts |
| [dataset_audit.py](../dataset_audit.py), [audit_execution.py](../audit_execution.py) | Full metadata checks, retry evidence and bounded parallel audit workers |

[audit.py](../audit.py) validates review videos against their recordings. [dataset_audit.py](../dataset_audit.py)
validates production data. These tools have different evidence contracts.

## Learning, evaluation and orchestration

| Files | Responsibility |
|---|---|
| [policy.py](../policy.py) | Spatial image features, telemetry encoder, GRU, bounded actions and inference |
| [training_pipeline.py](../training_pipeline.py), [train.py](../train.py) | Feature caches/readers, recurrent batches, losses, normalization and checkpoints |
| [evaluate.py](../evaluate.py) | Closed-loop validation/test rollouts and diagnostic traces |
| [workflow.py](../workflow.py), [cloud_collection.py](../cloud_collection.py) | Resumable stage orchestration and child-process lifecycle |
| [progress.py](../progress.py), [status.py](../status.py), [resource_monitor.py](../resource_monitor.py) | Loss history, progress display and CPU/RAM/GPU samples |
| [start_cloud_pipeline.sh](../start_cloud_pipeline.sh), [resume_cloud_pipeline.sh](../resume_cloud_pipeline.sh) | Full workflow launch and detached resume |
| [start_diverse_review.sh](../start_diverse_review.sh), [start_cloud_collection.sh](../start_cloud_collection.sh) | Review/upload workflow and collection-only launcher |

## Benchmarks, tests and retained diagnostics

[collection_benchmark.py](../collection_benchmark.py) measures the production collection path;
[autotune.py](../autotune.py) scans hardware and compares worker/backend settings.
[benchmarks/training.py](../benchmarks/training.py) retains the serial training reference;
[benchmarks/compare_training.py](../benchmarks/compare_training.py) compares it with parallel RGB and cached features.
[benchmarks/start_training_benchmark.sh](../benchmarks/start_training_benchmark.sh) saves a complete benchmark run.

[benchmark.py](../benchmark.py) runs expert operating-envelope trials, [limits_report.py](../limits_report.py)
summarizes their evidence, and [stress_review.py](../stress_review.py) exports the selected stress
flights. [ocean_preview.py](../ocean_preview.py) compares a saved baseline renderer with the current
water appearance. These remain useful diagnostics; saved baseline/evidence files
are prerequisites where specified by each tool's `--help`.

`tests/` contains regression suites and shared synthetic fixtures, including both
training benchmark suites. [qualify.py](../qualify.py) remains a runtime entry point because
review generation invokes it. See the [operating guide](operations.md#checks)
for discovery and qualification commands.
