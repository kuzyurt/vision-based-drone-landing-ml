#!/usr/bin/env bash
set -euo pipefail
cache="${TIDEWATER_WASM_CACHE:-$HOME/.cache/tidewater-game}"
pin=6ea3539157ca358c70a515878b77077af7d4611d
sdk_pin=62a853cd3b3134398ce85cde8bb5cbb2ef0194cb
for tool in git python3; do command -v "$tool" >/dev/null || { echo "Developer prerequisite missing: $tool" >&2; exit 1; }; done
mkdir -p "$cache"
export PIP_CACHE_DIR="$cache/pip-cache"
project=$(cd "$(dirname "$0")/../.." && pwd)
if [[ ! -x "$cache/build-python/bin/python" ]]; then python3 -m venv "$cache/build-python"; fi
"$cache/build-python/bin/python" -m pip install --disable-pip-version-check -r "$project/tidewater-game/wasm/requirements-build.txt"
export PATH="$cache/build-python/bin:$PATH"
if [[ ! -d "$cache/emsdk/.git" ]]; then git clone --depth 1 --branch 4.0.10 https://github.com/emscripten-core/emsdk.git "$cache/emsdk"; fi
[[ $(git -C "$cache/emsdk" rev-parse HEAD) == "$sdk_pin" ]] || { echo 'Emsdk source pin mismatch' >&2; exit 1; }
"$cache/emsdk/emsdk" install 4.0.10
"$cache/emsdk/emsdk" activate 4.0.10
if [[ ! -d "$cache/px4-wasm-source/.git" ]]; then
    reference_args=()
    if [[ -n "${TIDEWATER_NATIVE_REFERENCE:-}" ]]; then
        reference_args=(--reference-if-able "$TIDEWATER_NATIVE_REFERENCE" --dissociate)
    fi
    git clone "${reference_args[@]}" --depth 1 --branch v1.16.0 https://github.com/PX4/PX4-Autopilot.git "$cache/px4-wasm-source"
fi
[[ $(git -C "$cache/px4-wasm-source" rev-parse HEAD) == "$pin" ]] || { echo 'PX4 source pin mismatch' >&2; exit 1; }
git -C "$cache/px4-wasm-source" submodule update --init --recursive --jobs 4 src/modules/mavlink/mavlink src/lib/events/libevents src/lib/heatshrink/heatshrink src/drivers/gps/devices src/lib/crypto/monocypher
