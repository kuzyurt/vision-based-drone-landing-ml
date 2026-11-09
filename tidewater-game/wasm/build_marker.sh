#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
source "${TIDEWATER_WASM_CACHE:-$HOME/.cache/tidewater-game}/emsdk/emsdk_env.sh" >/dev/null 2>&1
em++ "$root/wasm/marker_kernel.cpp" -O3 -msimd128 -std=c++17 -fno-exceptions -fno-rtti -sSTANDALONE_WASM=1 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=4194304 -sSTACK_SIZE=65536 -Wl,--no-entry -sEXPORTED_FUNCTIONS=_malloc,_free,_marker_paint,_marker_begin,_marker_info,_marker_residual,_marker_jacobian,_marker_fit,_marker_finish -o "$root/app/public/policy/marker_kernel.wasm"
