#!/usr/bin/env bash
# Start a unique detached session, keep launch errors, and reuse the frozen data.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ "${1:-}" == --inside-tmux ]]; then
  exec >> "$2" 2>&1
  export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl
  AERODOCK_RESUME_REVIEW="$(landing_training/.venv/bin/python - <<'PY'
import json
from pathlib import Path
state = Path('landing_training/outputs/pipeline_state.json')
data = json.loads(state.read_text()) if state.exists() else {}
bundle = data.get('review_bundle')
if not bundle:
    run = Path('landing_training/outputs/latest_diverse_review.txt').read_text().strip()
    bundle = str(Path(run) / 'bundle')
bundle = Path(bundle).resolve()
if not (bundle / 'approval.json').is_file():
    raise SystemExit('Existing approved review bundle is missing: ' + str(bundle))
print(bundle)
PY
)"
  exec bash landing_training/start_cloud_pipeline.sh \
    --review "$AERODOCK_RESUME_REVIEW" \
    --no-review-export --reuse-approved-runtime
fi

command -v tmux >/dev/null
command -v flock >/dev/null
if [[ ! -x landing_training/.venv/bin/python ]]; then
  printf '%s\n' 'Existing landing_training/.venv is missing.' >&2
  exit 1
fi
mkdir -p landing_training/build landing_training/outputs
if ! flock -n landing_training/build/cloud_collection_launch.lock true; then
  printf '%s\n' 'A review/collection/pipeline already owns this VM; no duplicate started.'
  exit 0
fi
AERODOCK_RESUME_STAMP="$(date -u +%Y%m%dT%H%M%SZ)_$$"
AERODOCK_RESUME_SESSION="landing-pipeline-$AERODOCK_RESUME_STAMP"
AERODOCK_RESUME_LOG="$PWD/landing_training/outputs/resume_launcher_$AERODOCK_RESUME_STAMP.log"
printf -v AERODOCK_RESUME_COMMAND 'bash landing_training/resume_cloud_pipeline.sh --inside-tmux %q' "$AERODOCK_RESUME_LOG"
tmux new-session -d -s "$AERODOCK_RESUME_SESSION" -c "$PWD" "$AERODOCK_RESUME_COMMAND"
printf '%s\n' "$AERODOCK_RESUME_LOG" > landing_training/outputs/latest_resume_launcher.txt
printf '%s\n' "$AERODOCK_RESUME_SESSION" > landing_training/outputs/latest_pipeline_session.txt
printf 'Detached session: %s\nLauncher log: %s\n' "$AERODOCK_RESUME_SESSION" "$AERODOCK_RESUME_LOG"
printf '%s\n' 'Check progress: python3 -m landing_training.status --watch 10'
