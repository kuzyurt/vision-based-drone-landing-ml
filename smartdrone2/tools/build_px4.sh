#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
cd "$HOME/.cache/smartdrone2/PX4-Autopilot"
make px4_sitl_default -j4 > ../px4_build.log 2>&1
