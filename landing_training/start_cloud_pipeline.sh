#!/usr/bin/env bash
# Detached tmux owns this process; pipeline reports and checkpoints survive SSH.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
AERODOCK_PIPELINE_PYTHON="$PWD/landing_training/.venv/bin/python"
if [[ ! -x "$AERODOCK_PIPELINE_PYTHON" ]]; then
  printf '%s\n' 'Missing existing Python environment.' >&2
  exit 1
fi
mkdir -p landing_training/build
exec 9>landing_training/build/cloud_collection_launch.lock
if ! flock -n 9; then
  printf '%s\n' 'A collection or pipeline launcher already owns this VM workflow.' >&2
  exit 1
fi
export MUJOCO_GL=egl
export MUJOCO_EGL_DEVICE_ID=0
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
if [[ -f /usr/share/glvnd/egl_vendor.d/10_nvidia.json ]]; then
  export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
fi
exec "$AERODOCK_PIPELINE_PYTHON" -u -m landing_training.workflow "$@"
