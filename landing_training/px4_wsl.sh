#!/usr/bin/env bash
# Own one PX4 process per runtime directory; never stop unrelated SITL instances.
set -euo pipefail
operation="$1"
runtime="$2"
if [[ "$operation" == start ]]; then
    vendor="$3"
    host="$4"
    instance="$5"
    cd "$vendor"
    mkdir -p "$runtime"
    printf '%s\n' "$vendor/build/px4_sitl_landing/bin/px4" > "$runtime/px4.binary"
    export PX4_SYS_AUTOSTART=10016 PX4_SIM_MODEL=none_iris PX4_SIM_HOST_ADDR="$host"
    # Startup can block awaiting the simulator. Own its shell children too.
    exec setsid --fork --wait bash -c '
        runtime="$1"; vendor="$2"; instance="$3"
        printf "%s\n" "$$" > "$runtime/px4.pid"
        exec "$vendor/build/px4_sitl_landing/bin/px4" -d "$vendor/build/px4_sitl_landing/etc" -w "$runtime" -s "$runtime/rcS" -i "$instance"
    ' bash "$runtime" "$vendor" "$instance"
elif [[ "$operation" == stop ]]; then
    [[ -f "$runtime/px4.pid" && -f "$runtime/px4.binary" ]] || exit 0
    read -r pid < "$runtime/px4.pid"
    read -r binary < "$runtime/px4.binary"
    [[ "$pid" =~ ^[0-9]+$ ]] || exit 1
    owns_process() {
        [[ "$(readlink "/proc/$pid/exe" 2>/dev/null || true)" == "$(readlink -f "$binary")" ]] &&
            grep -z -F -x -q -- "$runtime" "/proc/$pid/cmdline" 2>/dev/null
    }
    if owns_process; then
        group="$(ps -o pgid= -p "$pid" | tr -d ' ')"
        if [[ "$group" == "$pid" ]]; then
            kill -TERM -- "-$pid" 2>/dev/null || true
            for _ in {1..50}; do kill -0 -- "-$pid" 2>/dev/null || exit 0; sleep .1; done
            kill -KILL -- "-$pid" 2>/dev/null || true
        else
            kill -TERM "$pid" 2>/dev/null || true
            for _ in {1..50}; do owns_process || exit 0; sleep .1; done
            if owns_process; then kill -KILL "$pid" 2>/dev/null || true; fi
        fi
    fi
else
    exit 2
fi
