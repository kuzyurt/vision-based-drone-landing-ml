# Experiments

Experiment outputs are split from the code that produces them.

| Folder | Current source | Status |
|---|---|---|
| [`runs/`](runs/) | `training_runs/` | Kept in place: benchmark revisions reference exact run paths. |
| [`benchmarks/`](benchmarks/) | `benchmark/runs/`, `benchmark/probes/`, `benchmark/audits/` | Kept in place: the frozen harness records receipt paths. |
| [`evidence/`](evidence/) | `artifacts/` | Kept in place: `runtime.json` pins evidence files by hash. |
| [`archive/`](archive/) | future | For superseded policies and frozen revisions. |

The eventual contract is one `run.json` per run:

```text
run_id, purpose, status, code_commit, dirty_patch_sha256, environment_sha256,
config_sha256, model_hashes, started_utc, finished_utc, outcome, report_path
```

No run is considered comparable to another unless it records the same suite and
runtime snapshot. Raw outputs are local evidence, not source.
