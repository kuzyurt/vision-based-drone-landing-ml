# Benchmark episodes

Raw benchmark episodes currently live under `benchmark/runs/`, with diagnostic
material under `benchmark/probes/` and `benchmark/audits/`.

They are kept in place because `benchmark/environments/runtime.json` and the
per-run receipts record exact relative paths and hashes. The tracked benchmark
definitions, reports and figures remain under `benchmark/` and are part of the
source snapshot.

Future episodes should write under `experiments/benchmarks/<run-id>/` once the
harness receipt schema is re-based. Until then, do not move or rewrite a run
that a report cites.
