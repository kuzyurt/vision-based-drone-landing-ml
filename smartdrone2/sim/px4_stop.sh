#!/usr/bin/env bash
set -euo pipefail
pid_file="$HOME/.cache/smartdrone2/runtime/px4.pid"
if [[ -f "$pid_file" ]]; then
    read -r task_px4_pid < "$pid_file"
    expected="$HOME/.cache/smartdrone2/PX4-Autopilot/build/px4_sitl_default/bin/px4"
    actual="$(readlink -f "/proc/$task_px4_pid/exe" || true)"
    if [[ "$actual" == "$expected" ]]; then kill -TERM "$task_px4_pid"; fi
fi
