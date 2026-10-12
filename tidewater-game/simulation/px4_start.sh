#!/usr/bin/env bash
set -euo pipefail

action=${3:-start}
px4_dir=$1
if [[ "$action" == "stop" ]]; then
  runtime=$2
  pid_file="$runtime/px4.pid"
  if [[ -f "$pid_file" ]]; then
    read -r pid < "$pid_file"
    expected="$px4_dir/build/px4_sitl_default/bin/px4"
    actual="$(readlink -f "/proc/$pid/exe" || true)"
    if [[ "$actual" == "$expected" ]]; then kill -TERM "$pid"; fi
    rm -f "$pid_file"
  fi
  exit 0
fi

project_dir=$2
runtime=$3
host_ip=$4
binary="$px4_dir/build/px4_sitl_default/bin/px4"
[[ -x "$binary" ]]
[[ "$(git -C "$px4_dir" rev-parse HEAD)" == "6ea3539157ca358c70a515878b77077af7d4611d" ]]
cd "$px4_dir"
export PX4_SYS_AUTOSTART=10016
export PX4_SIM_MODEL=none_iris
export PX4_SIM_HOST_ADDR="$host_ip"
export DRONE_SIM_WINDOWS_HOST="$host_ip"
export TIDEWATER_SIM_PROJECT="$project_dir"
export TIDEWATER_SIM_RUNTIME="$runtime"
mkdir -p "$runtime"
# PX4's lockstep logger writes at flight rates. Keep its working files on WSL's
# Linux filesystem so Windows mount I/O cannot stall the actuator/sensor cycle.
px4_work="${TIDEWATER_PX4_WORKDIR:-$HOME/.cache/tidewater-game/px4-runtime}"
mkdir -p "$px4_work"
echo $$ > "$runtime/px4.pid"
exec "$binary" -d "$px4_dir/build/px4_sitl_default/etc" -w "$px4_work" -s "$project_dir/tidewater-game/simulation/px4_rcS.sh"
