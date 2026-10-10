#!/usr/bin/env bash
# Run inside detached tmux on the existing CUDA VM. Upload is mandatory.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
AERODOCK_REVIEW_PYTHON="$PWD/landing_training/.venv/bin/python"
AERODOCK_REVIEW_STAMP="$(date -u +%Y%m%dT%H%M%SZ)_$$"
AERODOCK_REVIEW_OUTPUT="${1:-$PWD/landing_training/outputs/diverse_review_$AERODOCK_REVIEW_STAMP}"
AERODOCK_REVIEW_REPO="kuzyurt/vision-based-drone-landing-ml"
AERODOCK_REVIEW_TAG="landing-diverse-review-$AERODOCK_REVIEW_STAMP"
AERODOCK_REVIEW_STAGE="preflight"
AERODOCK_REVIEW_WORKERS="${AERODOCK_REVIEW_WORKERS:-8}"
AERODOCK_REVIEW_STARTED=$SECONDS
if [[ ! -x "$AERODOCK_REVIEW_PYTHON" ]]; then
  printf '%s\n' 'Existing landing_training/.venv is missing.' >&2
  exit 1
fi
mkdir -p "$AERODOCK_REVIEW_OUTPUT" landing_training/build
AERODOCK_REVIEW_OUTPUT="$(realpath "$AERODOCK_REVIEW_OUTPUT")"
printf '%s\n' "$AERODOCK_REVIEW_OUTPUT" > landing_training/outputs/latest_diverse_review.txt
exec > >(tee -a "$AERODOCK_REVIEW_OUTPUT/console.log") 2>&1
exec 9>landing_training/build/cloud_collection_launch.lock
if ! flock -n 9; then
  printf '%s\n' 'Another collection/pipeline/review launcher owns this VM workflow.' >&2
  exit 1
fi
export MUJOCO_GL=egl
export MUJOCO_EGL_DEVICE_ID=0
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
if [[ -f /usr/share/glvnd/egl_vendor.d/10_nvidia.json ]]; then
  export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json
fi
review_status() {
  "$AERODOCK_REVIEW_PYTHON" - "$AERODOCK_REVIEW_OUTPUT" "$AERODOCK_REVIEW_STAGE" "$1" "$2" "$((SECONDS-AERODOCK_REVIEW_STARTED))" <<'PY'
import json,sys
from datetime import datetime,timezone
from pathlib import Path
from landing_training.collection_session import atomic_json
folder,stage,status,code,seconds=sys.argv[1:]
report={'status':status,'stage':stage,'exit_code':int(code),
    'updated_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':int(seconds),
    'elapsed_hours':int(seconds)/3600,'output_directory':folder,
    'github_release_url_file':str(Path(folder)/'github_release_url.txt'),
    'github_download_url_file':str(Path(folder)/'github_download_url.txt')}
package=Path(folder)/'landing-diverse-review.package.json'
if package.exists():report['package']=json.loads(package.read_text())
for key in ('github_release_url','github_download_url'):
    path=Path(folder)/(key+'.txt')
    if path.exists():report[key]=path.read_text().strip()
atomic_json(Path(folder)/'run_report.json',report)
PY
}
review_exit() {
  local AERODOCK_REVIEW_CODE=$?
  trap - EXIT
  if [[ "$AERODOCK_REVIEW_CODE" == 0 ]]; then
    review_status completed 0
  else
    review_status failed "$AERODOCK_REVIEW_CODE" || true
    printf 'Review stopped during %s; inspect %s/console.log\n' "$AERODOCK_REVIEW_STAGE" "$AERODOCK_REVIEW_OUTPUT"
  fi
  exit "$AERODOCK_REVIEW_CODE"
}
trap review_exit EXIT
review_status running 0
command -v gh >/dev/null
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
gh auth status
# Check the authenticated account can upload to this repository before rendering.
gh api "repos/$AERODOCK_REVIEW_REPO" --jq '.permissions.push' | "$AERODOCK_REVIEW_PYTHON" -c \
  'import sys; assert sys.stdin.read().strip()=="true", "GitHub account lacks upload permission"'
"$AERODOCK_REVIEW_PYTHON" - <<'PY'
import shutil
from landing_training.collection_benchmark import renderer_info
info=renderer_info();print(info,flush=True)
assert not info['software_rendering'] and 'nvidia' in info['vendor'].lower(), 'NVIDIA EGL rendering required'
assert shutil.disk_usage('landing_training/outputs').free >= 12*10**9, 'At least 12 GB free review workspace required'
PY
AERODOCK_REVIEW_STAGE="qualification"; review_status running 0
"$AERODOCK_REVIEW_PYTHON" -u -m landing_training.qualify
AERODOCK_REVIEW_STAGE="parallel_review"; review_status running 0
"$AERODOCK_REVIEW_PYTHON" -u -m landing_training.review --diverse \
  --workers "$AERODOCK_REVIEW_WORKERS" --output "$AERODOCK_REVIEW_OUTPUT/bundle"
AERODOCK_REVIEW_STAGE="package"; review_status running 0
"$AERODOCK_REVIEW_PYTHON" -u -m landing_training.review_package \
  --bundle "$AERODOCK_REVIEW_OUTPUT/bundle" \
  --output "$AERODOCK_REVIEW_OUTPUT/landing-diverse-review.zip" --max-mb 80 --workers 4
"$AERODOCK_REVIEW_PYTHON" - "$AERODOCK_REVIEW_OUTPUT" <<'PY'
import json,sys
from pathlib import Path
folder=Path(sys.argv[1]);result=json.loads((folder/'landing-diverse-review.package.json').read_text())
manifest=json.loads((folder/'bundle/manifest.json').read_text())
notes=(f'Ten parallel expert review flights across five maps and both route directions.\n\n'
       f'Airborne distances approximately 3–51 m; heights 2.2–8 m; boat speeds approximately 0.18–0.88 m/s. '
       f'Calm, wind, waves, combined weather, camera blindness, radio dropout and dock-readiness delay. '
       f'The dock lids stay open and the landing plate stays raised. Videos include recorded input/output overlays.\n\n'
       f'ZIP size: {result["archive_MB"]:.2f} decimal MB (80 MB limit). '
       f'Includes videos, full JSONL telemetry, scenarios, audits and qualification; raw RGB HDF5 remains on the VM.\n\n'
       f'Source SHA256: `{manifest["source_sha256"]}`. '
       f'User review is pending; these recordings are excluded from production training.\n')
(folder/'release_notes.md').write_text(notes)
PY
AERODOCK_REVIEW_STAGE="github_upload"; review_status running 0
gh release create "$AERODOCK_REVIEW_TAG" \
  "$AERODOCK_REVIEW_OUTPUT/landing-diverse-review.zip" \
  "$AERODOCK_REVIEW_OUTPUT/landing-diverse-review.zip.sha256" \
  --repo "$AERODOCK_REVIEW_REPO" --target codex/landing-training --prerelease \
  --title "AERODOCK diverse review — $AERODOCK_REVIEW_STAMP" \
  --notes-file "$AERODOCK_REVIEW_OUTPUT/release_notes.md" \
  | tee "$AERODOCK_REVIEW_OUTPUT/github_release_url.txt"
gh api "repos/$AERODOCK_REVIEW_REPO/releases/tags/$AERODOCK_REVIEW_TAG" \
  > "$AERODOCK_REVIEW_OUTPUT/github_release.json"
"$AERODOCK_REVIEW_PYTHON" - "$AERODOCK_REVIEW_OUTPUT" <<'PY'
import json,sys
from pathlib import Path
folder=Path(sys.argv[1]);release=json.loads((folder/'github_release.json').read_text())
asset=next(item for item in release['assets'] if item['name']=='landing-diverse-review.zip')
assert asset['state']=='uploaded', 'GitHub asset is not uploaded'
assert asset['size']==(folder/'landing-diverse-review.zip').stat().st_size, 'GitHub asset size differs'
(folder/'github_download_url.txt').write_text(asset['browser_download_url']+'\n')
PY
test -s "$AERODOCK_REVIEW_OUTPUT/github_download_url.txt"
AERODOCK_REVIEW_STAGE="finished"
printf '\nGitHub ZIP download: '
cat "$AERODOCK_REVIEW_OUTPUT/github_download_url.txt"
