#!/usr/bin/env bash
set -euo pipefail
project=$1
runtime="$project/tidewater-game/simulation/runtime"
pid_file="$runtime/service.pid"
if [[ -f "$pid_file" ]]; then
  read -r pid < "$pid_file"
  if [[ -r "/proc/$pid/cmdline" ]] && tr '\0' '\n' < "/proc/$pid/cmdline" | grep -Fxq "$project/tidewater-game/simulation/server.py"; then
    kill -TERM "$pid"
  fi
  rm -f "$pid_file"
fi
