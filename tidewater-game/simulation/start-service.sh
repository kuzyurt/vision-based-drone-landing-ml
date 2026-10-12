#!/usr/bin/env bash
set -euo pipefail
project=$1
game_env="${TIDEWATER_PYTHON_ENV:-$HOME/.cache/tidewater-game/python}"
runtime="$project/tidewater-game/simulation/runtime"
mkdir -p "$runtime"
if [[ -f "$runtime/service.pid" ]]; then
  read -r existing_pid < "$runtime/service.pid"
  if [[ -r "/proc/$existing_pid/cmdline" ]] && tr '\0' '\n' < "/proc/$existing_pid/cmdline" | grep -Fxq "$project/tidewater-game/simulation/server.py"; then
    echo 'Tidewater physics service is already running.'
    exit 0
  fi
fi
if [[ ! -x "$game_env/bin/python" ]]; then
  python3 -m venv --without-pip "$game_env"
fi
if ! "$game_env/bin/python" -m pip --version >/dev/null 2>&1; then
  purelib=$("$game_env/bin/python" -c 'import sysconfig; print(sysconfig.get_path("purelib"))')
  python3 -m pip install --no-deps --target "$purelib" pip==24.3.1
fi
if ! "$game_env/bin/python" -c 'import mujoco, numba, cv2, scipy, fast_simplification, fastapi, uvicorn, websockets, pymavlink, orjson' >/dev/null 2>&1; then
  "$game_env/bin/python" -m pip install -r "$project/tidewater-game/simulation/requirements-runtime.txt"
fi
export NUMBA_CACHE_DIR="$runtime/native-cache-linux"
export MUJOCO_GL=disable
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
echo $$ > "$runtime/service.pid"
exec "$game_env/bin/python" "$project/tidewater-game/simulation/server.py"
