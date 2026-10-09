#!/usr/bin/env bash
# Run inside a detached tmux session. No production data bypasses review approval.
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
AERODOCK_LAUNCH_DIR="$AERODOCK_REPO_DIR/landing_training/outputs/collection_launch_$(date -u +%Y%m%dT%H%M%S)_$$"
mkdir -p "$AERODOCK_LAUNCH_DIR"
AERODOCK_DATASET_DIR="${AERODOCK_DATASET_DIR:-$AERODOCK_REPO_DIR/landing_training/datasets/expert}"
AERODOCK_REVIEW_BUNDLE="${1:-auto}"
printf '%s\n' "$AERODOCK_LAUNCH_DIR" > landing_training/outputs/latest_collection_launch.txt

write_launch_status() {
  "$AERODOCK_PYTHON" - "$AERODOCK_LAUNCH_DIR" "$1" "$2" "$3" "$AERODOCK_DATASET_DIR" <<'PY'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from landing_training.collection_session import atomic_json
folder=Path(sys.argv[1]);status=sys.argv[2];code=int(sys.argv[3]);elapsed=int(sys.argv[4])
path=folder/'results/latest.json'
result=json.loads(path.read_text()) if path.is_file() else None
if status=='finished':
    status=result['status'] if result else 'blocked' if code==2 else 'cancelled' if code==130 else 'failed'
    if not result and (folder/'current_review/manifest.json').is_file() and code==2:
        status='user_review_required'
atomic_json(folder/'launch_status.json',{
    'status':status,'exit_code':code if status!='starting' else None,
    'updated_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':elapsed,
    'dataset_directory':sys.argv[5], 'console_log':str(folder/'console.log'),
    'collection_report':str(path) if result else None,
    'review_page':str(folder/'current_review/index.html') if (folder/'current_review/index.html').is_file() else None,
    'dataset_GB':result['dataset_GB'] if result else None,
    'episodes_total':result['episodes_total'] if result else None,
    'stop_reason':result['stop_reason'] if result else 'See console.log; collection did not pass preflight.'})
PY
}
finish() {
  local AERODOCK_EXIT_CODE=$?
  trap - EXIT
  write_launch_status finished "$AERODOCK_EXIT_CODE" "$SECONDS"
  printf '\nReports and log: %s\n' "$AERODOCK_LAUNCH_DIR"
  exit "$AERODOCK_EXIT_CODE"
}
trap finish EXIT
write_launch_status starting 0 0
printf 'Dataset: %s\nReports: %s\n' "$AERODOCK_DATASET_DIR" "$AERODOCK_LAUNCH_DIR"

"$AERODOCK_PYTHON" - <<'PY' 2>&1 | tee "$AERODOCK_LAUNCH_DIR/console.log"
import json
from landing_training.collection_benchmark import renderer_info
info=renderer_info()
print(json.dumps(info,indent=2),flush=True)
if info['software_rendering']:
    raise RuntimeError('GPU rendering required; repair NVIDIA EGL before launching flights.')
PY

if [[ "$AERODOCK_REVIEW_BUNDLE" == auto ]]; then
  if "$AERODOCK_PYTHON" - <<'PY' > "$AERODOCK_LAUNCH_DIR/review_preflight.log" 2>&1
from landing_training.collect import approved_bundle
print(approved_bundle('auto'))
PY
  then
    AERODOCK_REVIEW_BUNDLE="$(tail -n 1 "$AERODOCK_LAUNCH_DIR/review_preflight.log")"
  else
    printf '%s\n' 'No current approved review exists. Exporting ten current review videos first.' \
      'Production collection will remain blocked until the user verifies this bundle.' | tee -a "$AERODOCK_LAUNCH_DIR/console.log"
    cat "$AERODOCK_LAUNCH_DIR/review_preflight.log" >> "$AERODOCK_LAUNCH_DIR/console.log"
    "$AERODOCK_PYTHON" -m landing_training.qualify 2>&1 | tee -a "$AERODOCK_LAUNCH_DIR/console.log"
    "$AERODOCK_PYTHON" -m landing_training.review \
      --output "$AERODOCK_LAUNCH_DIR/current_review" 2>&1 | tee -a "$AERODOCK_LAUNCH_DIR/console.log"
    "$AERODOCK_PYTHON" - "$AERODOCK_LAUNCH_DIR/current_review/manifest.json" <<'PY' 2>&1 | tee -a "$AERODOCK_LAUNCH_DIR/console.log"
import json
from pathlib import Path
import sys
if not json.loads(Path(sys.argv[1]).read_text()).get('qualification_passed'):
    raise RuntimeError('Current review did not qualify; inspect its reports before collection.')
PY
    printf '\nReview the videos and recorded data at: %s/current_review/index.html\n' "$AERODOCK_LAUNCH_DIR" | tee -a "$AERODOCK_LAUNCH_DIR/console.log"
    exit 2
  fi
fi

"$AERODOCK_PYTHON" -m landing_training.collect \
  --review "$AERODOCK_REVIEW_BUNDLE" \
  --output "$AERODOCK_DATASET_DIR" \
  --max-episodes 1200 --workers 64 --instance-base 20 \
  --gl egl --require-gpu \
  --min-free-gb 32 --max-dataset-gb 1500 \
  --quarantine-partial --report-dir "$AERODOCK_LAUNCH_DIR/results" \
  2>&1 | tee -a "$AERODOCK_LAUNCH_DIR/console.log"
