#!/usr/bin/env bash
# Run inside a detached tmux session. Python owns stages and signal-safe reports.
set -euo pipefail
AERODOCK_REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$AERODOCK_REPO_DIR"
AERODOCK_PYTHON="$AERODOCK_REPO_DIR/landing_training/.venv/bin/python"
if [[ ! -x "$AERODOCK_PYTHON" ]]; then
  printf '%s\n' 'Missing landing_training/.venv; finish the existing environment setup first.' >&2
  exit 1
fi
mkdir -p landing_training/build
exec 9>landing_training/build/cloud_collection_launch.lock
if ! flock -n 9; then
  printf '%s\n' 'A cloud collection launcher is already running. Reattach to its tmux session.' >&2
  exit 1
fi
export MUJOCO_GL=egl
export MUJOCO_EGL_DEVICE_ID=0
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
AERODOCK_EGL_VENDOR=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
if [[ -f "$AERODOCK_EGL_VENDOR" ]]; then
  export __EGL_VENDOR_LIBRARY_FILENAMES="$AERODOCK_EGL_VENDOR"
fi
exec "$AERODOCK_PYTHON" -u -m landing_training.cloud_collection \
  --review "${1:-auto}" \
  --output "${AERODOCK_DATASET_DIR:-$AERODOCK_REPO_DIR/landing_training/datasets/expert}"
