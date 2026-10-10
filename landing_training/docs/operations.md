# Operating guide

All Linux commands run from the repository root. Keep an active experiment on
its current checkout; update after it finishes or after a controlled stop.
Generated data, approvals and checkpoints belong to the machine that ran them
and are ignored by Git. Copy those artifacts separately when migrating a run.

## Setup

Use Python 3.12. Linux prerequisites are Git, GCC/G++, Make, `uv`, FFmpeg/FFprobe,
DejaVu fonts and an EGL implementation. Detached cloud launchers also need
`tmux` and `flock`; GitHub review upload needs authenticated `gh`. No separate
boat server, drone server, Gazebo or DDS service is required.

For a fresh **CPU development environment**, the existing setup script installs
locked core dependencies, CPU PyTorch/Torchvision and the pinned native PX4 build:

```bash
bash landing_training/setup.sh
```

For a fresh **NVIDIA collection/training machine**, use the CUDA wheels instead
of the CPU training requirements:

```bash
export UV_CACHE_DIR=/tmp/aerodock-uv-cache
export PYTHONDONTWRITEBYTECODE=1
uv venv --python 3.12 landing_training/.venv
uv pip install --python landing_training/.venv/bin/python -r landing_training/requirements-lock.txt
uv pip install --python landing_training/.venv/bin/python \
  --index-url https://download.pytorch.org/whl/cu126 \
  torch==2.7.1+cu126 torchvision==0.22.1+cu126
landing_training/.venv/bin/python -m landing_training.setup_px4
```

Reuse a working `.venv`. On the configured L4 VM, installing
`requirements-training.txt` or rerunning `setup.sh` replaces CUDA PyTorch with
CPU wheels. The pinned PX4 v1.16.0 revision is
`6ea3539157ca358c70a515878b77077af7d4611d`; build details and the battery decoding
patch are recorded in `build/px4_build.json`.

### Check rendering and CUDA

An NVIDIA device listed by `nvidia-smi` does not establish GPU rendering. Check
MuJoCo's actual renderer before benchmarking or collecting:

```bash
export MUJOCO_GL=egl
export MUJOCO_EGL_DEVICE_ID=0
# On NVIDIA hosts where this installed vendor file exists:
export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
landing_training/.venv/bin/python - <<'PY'
import json, torch
from landing_training.collection_benchmark import renderer_info
info = renderer_info()
print(json.dumps(info, indent=2))
print('CUDA available:', torch.cuda.is_available())
assert not info['software_rendering'], 'Hardware EGL is required for the cloud workflow'
assert torch.cuda.is_available(), 'CUDA PyTorch is required for the cloud workflow'
PY
```

If the NVIDIA vendor file is absent, repair the host's NVIDIA EGL installation
first. `llvmpipe`/`softpipe` is CPU rendering. CPU development and local benchmarks
remain available, but the cloud workflow deliberately refuses software rendering
and missing CUDA.

## Review before collection

Export a new bundle with ten varied flights in parallel:

```bash
MUJOCO_GL=egl landing_training/.venv/bin/python -m landing_training.qualify
MUJOCO_GL=egl landing_training/.venv/bin/python -m landing_training.review \
  --diverse --workers 8 --output landing_training/outputs/current_review
```

Use a fresh output directory after a substantive runtime change. Review export
includes its recording audit and writes `index.html`, raw HDF5/JSONL, scenarios,
qualification evidence, `planned_collection.json` and `approval.template.json`.
Inspect all videos, input/output rows, dock state, outcomes, physics evidence and
planned ranges. After the human reviewer explicitly approves, copy the template
to `approval.json`, change `status` to `approved` and fill in `reviewer`. Preserve
the generated manifest hash and complete `reviewed_episodes` list. The software
never supplies its own human approval.

To render, package and upload from an authenticated NVIDIA VM:

```bash
tmux new-session -d -s landing-review -c "$PWD" \
  'bash landing_training/start_diverse_review.sh'
```

This uses eight workers by default and uploads a bounded video/metadata ZIP plus
SHA256 to a GitHub prerelease. It leaves full recordings on the VM. Package-only
reproduction uses `python -m landing_training.review_package --bundle PATH
--output ZIP_PATH --max-mb 80 --workers 4`. The latest upload path is in
`outputs/latest_diverse_review.txt`; its directory contains download/release URL
files, `run_report.json` and `console.log`. Upload does not approve the bundle.

## Collect → train → evaluate

For a new configured cloud run, use a detached session and select the approved
bundle and measured worker count explicitly:

```bash
tmux new-session -d -s landing-pipeline -c "$PWD" \
  'bash landing_training/start_cloud_pipeline.sh --review landing_training/outputs/current_review --no-review-export --workers 64'
python3 -m landing_training.status --watch 10
```

Without an approved review, the default launcher exports review videos and stops
at `user_review_required`. `--no-review-export` instead stops without rendering
more videos. The full workflow audits the 240-episode expert pilot, checks storage,
collects all 1,200 episodes, audits them, prepares features and trains. It then
runs a 12-flight validation pilot before continuing the ten-epoch budget and
final validation/test flights. See the [technical report](technical_report.md)
for quality criteria and learning checks.

Defaults are 64 collection workers, four image readers, eight evaluation workers,
CUDA, three initial epochs and ten total epochs with patience three. Run
`python -m landing_training.workflow --help` using the project interpreter to see
all options. Freeze configuration once a persistent run starts.

The cloud workflow caps the dataset at 1,500 decimal GB, reserves at least 32 GB
free, and additionally reserves feature/evaluation space (about 95 GB total for
this plan), plus in-flight shutdown margin. Storage guards may stop collection
before the cap. They retain partial recordings and never silently train on an
incomplete dataset.

### Status, timing and loss

```bash
python3 -m landing_training.status --watch 10
AERODOCK_LAST_RUN="$(cat landing_training/outputs/latest_pipeline_launch.txt)"
cat "$AERODOCK_LAST_RUN/summary.txt"
tail -n 40 "$AERODOCK_LAST_RUN/console.log"
```

The persistent `outputs/pipeline_state.json` and per-attempt
`pipeline_report.json` contain completed counts/percentages, retry counts,
GB/free disk, current stage and cumulative hours. Collection/pipeline heartbeat
updates every 30 seconds; training and audit progress update about every five
seconds. A stale heartbeat or `failed` state requires reading the saved reason
and console traceback.

| Artifact | Contents |
|---|---|
| `checkpoints/production/latest.pt`, `best.pt` | Resume state and validation-selected model |
| `checkpoints/production/features/` | Reusable frozen-encoder feature caches |
| `checkpoints/production/loss_history.csv` | One row per committed epoch, UTC time, cumulative training hours and validation metrics |
| `checkpoints/production/loss_updates.csv` | Finer training-loss samples, optimizer step and attempt ID |
| `checkpoints/production/history.json`, `training_progress.json` | Committed metrics and live counters |
| Current launch's evaluation directories | Closed-loop JSONL traces and aggregate reports |

For a chronological loss chart, plot `training_elapsed_hours` against
`validation_loss` or `validation_action_huber` from `loss_history.csv`.
Use `loss_updates.csv` for finer training samples. Training lane mean and
validation loss use different weighting. Stage timing reports
`collection_hours`, `collection_audit_hours`,
`training_hours_including_preparation` and `evaluation_hours`; retries count,
offline time between launches does not.

### Resume and recover

```bash
bash landing_training/resume_cloud_pipeline.sh
python3 -m landing_training.status --watch 10
```

The resume wrapper creates a unique detached tmux session using the existing
approved review, frozen settings and explicit compatible-runtime reuse. It works
inside or outside another tmux session. SSH loss and Ctrl+C in the status watcher
do not stop it. Locks prevent duplicate workflow launches. Launcher errors are
saved at the path in `outputs/latest_resume_launcher.txt`.

Completed indexed episodes are skipped; compatible complete unindexed recordings
can be recovered. Incomplete attempts are retained under `partial_attempts/`.
Nominal outcome retries live under `retry_attempts/EPISODE/attempt_NNN/` and are
journalled before/after flight. Training resumes from the last complete epoch;
compatible completed evaluations are reused. Source/data/configuration changes
are checked. Approval reuse requires unchanged runtime and plan; the specifically
verified short-rock-tile crash fix has a narrow compatibility exception.
Do not edit approval manifests or dataset hashes to bypass these checks.

## Dataset layout

```text
datasets/expert/
├── manifest.json
├── training_0000_forward/       # one airborne episode, not a batch
│   ├── observations.h5         # RGB + matching metadata rows
│   ├── steps.jsonl
│   ├── scenario.json
│   ├── summary.json
│   └── px4/                   # process/runtime evidence
├── validation_…/
├── test_…/
├── retry_attempts/             # preserved outcome retries
└── partial_attempts/           # preserved interrupted attempts
```

The plan has 1,200 selected episodes; retained attempts add directories. After a
successful retry the manifest can point to that attempt instead of the original
folder. Always use the manifest rather than inferring selected data from names.
Back up the dataset, matching review/approval, checkpoint directory, reports and
Git revision together. Build products and bytecode are regenerable; approvals,
original recordings and failed attempts remain experiment evidence.

## Benchmarks and individual stages

Run benchmarks separately from collection/training so resource measurements are
interpretable. The tuner scans CPU allocation, RAM, renderer and GPU counters:

```bash
landing_training/.venv/bin/python -m landing_training.autotune --scan-only
landing_training/.venv/bin/python -m landing_training.autotune \
  --require-gpu --max-workers 64 --max-minutes 30 --confirm-scenarios 3
# Compare only specific counts:
landing_training/.venv/bin/python -m landing_training.autotune \
  --require-gpu --worker-counts 32,64 --max-minutes 30 --confirm-scenarios 3
```

Short probes measure throughput. Full-flight confirmation is still sampled;
`--confirm-scenarios 20` covers the complete benchmark scenario matrix.
The training comparison preserves the serial reference and measures parallel
RGB, cached epochs, one-time preparation and a tiny-fragment learning check:

```bash
tmux new-session -d -s landing-train-bench -c "$PWD" \
  'bash landing_training/benchmarks/start_training_benchmark.sh --device cuda'
```

Use `--review PATH` if automatic review discovery does not find your bundle.
`outputs/latest_training_benchmark.txt` points to the saved summary/report/log.
Temporary benchmark weights are discarded. Small warm-cache workloads are not
production timing or model-accuracy guarantees.

Direct stage commands remain available:

```bash
landing_training/.venv/bin/python -m landing_training.collect --help
landing_training/.venv/bin/python -m landing_training.dataset_audit --help
landing_training/.venv/bin/python -m landing_training.train --help
landing_training/.venv/bin/python -m landing_training.evaluate --help
```

`start_cloud_collection.sh` is the older collection-only launcher; use the full
pipeline for automatic audit, training and evaluation. Diagnostic tools are
listed in the [source map](source_map.md).

## Checks

Tests now live in `tests/`. Discover them with package-aware imports:

```bash
PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl landing_training/.venv/bin/python \
  -m unittest discover -s landing_training/tests -t . -v
```

The suite includes a camera-render equivalence test. Physics qualification and
native PX4 flight qualification are separate, potentially slower checks:

```bash
MUJOCO_GL=egl landing_training/.venv/bin/python -m landing_training.qualify
MUJOCO_GL=egl landing_training/.venv/bin/python -m landing_training.qualify --flights
```

## Windows rendering with WSL PX4

Camera capture, recording and simulation can run under Windows Python using
`glfw`; the pinned PX4 firmware still runs in WSL2 Ubuntu 22.04. Build it there
first. From PowerShell at the repository root:

```powershell
py -3.12 -m venv landing_training/.venv-windows
landing_training/.venv-windows/Scripts/python -m pip install -r landing_training/requirements-lock.txt
landing_training/.venv-windows/Scripts/python -m pip install -r landing_training/requirements-training.txt
$env:PX4_WSL_DISTRO = "Ubuntu-22.04"
landing_training/.venv-windows/Scripts/python -m landing_training.collection_benchmark --gl glfw --workers 1,2 --repeats 3
```

If PX4 is built in a separate Linux checkout, set `LANDING_PX4_WSL_ROOT` to that
checkout's `landing_training/.vendor/PX4-Autopilot` path. Windows must permit the
WSL connections to the simulator's TCP/UDP ports. Each launcher records firmware
provenance and stops only its owned PX4 process. The detached cloud pipeline is
Linux-specific.
