#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR=/tmp/aerodock-uv-cache
export PYTHONDONTWRITEBYTECODE=1
export MUJOCO_GL=egl
export XDG_CACHE_HOME=/tmp/aerodock-xdg-cache
for required in uv git gcc g++ make ffmpeg ffprobe; do
    command -v "$required" >/dev/null
done
test -f /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
if [ ! -x landing_training/.venv/bin/python ]; then
    uv venv --python 3.12 landing_training/.venv
fi
uv pip install --python landing_training/.venv/bin/python -r landing_training/requirements-lock.txt
uv pip install --python landing_training/.venv/bin/python -r landing_training/requirements-training.txt
landing_training/.venv/bin/python -m landing_training.setup_px4
