#!/usr/bin/env bash
# Launched in WSL by the local simulator; source/build stay in Linux home.
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
px4_dir="$HOME/.cache/smartdrone2/PX4-Autopilot"
host_ip="$1"
cd "$px4_dir"
export PX4_SYS_AUTOSTART=10016
export PX4_SIM_MODEL=none_iris
export PX4_SIM_HOST_ADDR="$host_ip"
export SD2_WINDOWS_HOST="$host_ip"
export SD2_PROJECT="$project_dir"
mkdir -p "$HOME/.cache/smartdrone2/runtime"
bash "$project_dir/sim/px4_stop.sh"
echo $$ > "$HOME/.cache/smartdrone2/runtime/px4.pid"
exec ./build/px4_sitl_default/bin/px4 -d "$px4_dir/build/px4_sitl_default/etc" -w "$HOME/.cache/smartdrone2/runtime" -s "$project_dir/sim/px4_rcS.sh"
