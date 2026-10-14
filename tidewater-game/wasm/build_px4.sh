#!/usr/bin/env bash
set -euo pipefail
project=$(cd "$(dirname "$0")/../.." && pwd)
cache="${TIDEWATER_WASM_CACHE:-$HOME/.cache/tidewater-game}"
source_dir="$cache/px4-wasm-source"
sdk="$cache/emsdk"
reference="${TIDEWATER_NATIVE_REFERENCE:-$source_dir}"
bash "$project/tidewater-game/wasm/bootstrap.sh"
export PATH="$cache/build-python/bin:$PATH"
python3 "$project/tidewater-game/wasm/prepare_px4.py" "$source_dir" "$reference"
"$sdk/emsdk" activate 4.0.10 >/dev/null
source "$sdk/emsdk_env.sh" >/dev/null 2>&1
emcmake cmake -S "$source_dir" -B "$cache/px4-wasm-build" -G Ninja \
  -DCONFIG=px4_sitl_browser -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  -DCMAKE_C_FLAGS='-pthread -Wno-error' -DCMAKE_CXX_FLAGS='-pthread -Wno-error' \
  -DCMAKE_EXE_LINKER_FLAGS='-pthread -sPTHREAD_POOL_SIZE=32 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=134217728 -sMODULARIZE=1 -sEXPORT_ES6=1 -sENVIRONMENT=web,worker,node -sEXPORTED_FUNCTIONS=_main,_malloc,_free,_tw_init,_tw_command,_tw_sim_write,_tw_sim_read,_tw_offboard_write,_tw_heartbeat,_tw_setpoint,_tw_vehicle_command,_tw_battery,_tw_sensors,_tw_observation,_tw_actuators,_tw_actuator_signal,_tw_command_async,_tw_command_result -sEXPORTED_RUNTIME_METHODS=FS,ccall,HEAPF64,HEAPU8,PThread'
cmake --build "$cache/px4-wasm-build" --target px4 -j "${TIDEWATER_BUILD_JOBS:-4}"
mkdir -p "$project/tidewater-game/app/public/landing/wasm"
cp "$cache/px4-wasm-build/bin/px4.mjs" "$cache/px4-wasm-build/bin/px4.wasm" "$project/tidewater-game/app/public/landing/wasm/"
python3 "$project/tidewater-game/wasm/record_build.py" "$cache"
