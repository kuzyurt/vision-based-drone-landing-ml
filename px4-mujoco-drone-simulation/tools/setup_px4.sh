#!/usr/bin/env bash
# Run in WSL Ubuntu 22.04. Downloads only official PX4 sources.
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
px4_dir="$HOME/.cache/px4-mujoco-drone-simulation/PX4-Autopilot"
expected_commit=6ea3539157ca358c70a515878b77077af7d4611d
if [[ ! -d "$px4_dir/.git" ]]; then
  mkdir -p "$(dirname "$px4_dir")"
  git clone --depth 1 --branch v1.16.0 https://github.com/PX4/PX4-Autopilot.git "$px4_dir"
fi
actual_commit="$(git -C "$px4_dir" rev-parse HEAD)"
if [[ "$actual_commit" != "$expected_commit" ]]; then
  echo "Unexpected PX4 checkout at $px4_dir; this project requires v1.16.0 ($expected_commit)." >&2
  exit 1
fi
git -C "$px4_dir" submodule update --init --recursive --jobs 4
if [[ "${1:-}" == '--install-deps' ]]; then
  bash "$px4_dir/Tools/setup/ubuntu.sh" --no-nuttx --no-sim-tools
fi
python3 "$project_dir/sim/patch_px4_battery.py"
bash "$project_dir/tools/build_px4.sh"
echo 'PX4 ready. Start the Windows simulator with: python -m sim.server'
