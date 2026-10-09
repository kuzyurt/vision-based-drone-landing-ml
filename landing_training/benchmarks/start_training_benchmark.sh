#!/usr/bin/env bash
# Start this inside detached tmux to survive loss of the SSH connection.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

AERODOCK_BENCHMARK_PYTHON="$PWD/landing_training/.venv/bin/python"
if [ ! -x "$AERODOCK_BENCHMARK_PYTHON" ]; then
  printf '%s\n' 'Missing landing_training/.venv/bin/python; run the repository setup first.' >&2
  exit 1
fi
mkdir -p landing_training/build landing_training/outputs
exec 9>landing_training/build/training_benchmark.lock
if ! flock -n 9; then
  printf '%s\n' 'A training benchmark is already running.' >&2
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
AERODOCK_BENCHMARK_OUTPUT="$PWD/landing_training/outputs/training_benchmark_$(date -u +%Y%m%dT%H%M%S)_$$"
mkdir "$AERODOCK_BENCHMARK_OUTPUT"
printf '%s\n' "$AERODOCK_BENCHMARK_OUTPUT" > landing_training/outputs/latest_training_benchmark.txt.tmp
mv landing_training/outputs/latest_training_benchmark.txt.tmp landing_training/outputs/latest_training_benchmark.txt
set +e
"$AERODOCK_BENCHMARK_PYTHON" -u -m landing_training.benchmarks.training \
  "$@" --output "$AERODOCK_BENCHMARK_OUTPUT" \
  2>&1 | tee "$AERODOCK_BENCHMARK_OUTPUT/console.log"
AERODOCK_BENCHMARK_EXIT="${PIPESTATUS[0]}"
set -e
printf '%s\n' "$AERODOCK_BENCHMARK_EXIT" > "$AERODOCK_BENCHMARK_OUTPUT/exit_code.txt"
exit "$AERODOCK_BENCHMARK_EXIT"
