# Folder disposition

This is the migration decision table. “Pinned” means a benchmark receipt
records the folder’s files by path and SHA-256, so moving it now would break
that benchmark’s preflight. The pre-V2 receipts are archived in
`old/benchmark/environments/runtime.json`; the active V2 receipts are in
`benchmark/definition/runtime.json`.

| Current folder | Decision | Future home | Notes |
|---|---|---|---|
| `AERODOCK_MuJoCo/` | Keep, pinned | `packages/aerodock/` | Distribution metadata added in place; import name remains `usv`. |
| `px4-mujoco-drone-simulation/` | Keep, pinned | `packages/px4sim/` | Existing `pyproject.toml`; import name remains `sim`. |
| `landing_training/` | Keep, pinned | `packages/landing/` | Distribution metadata added in place; flat modules still need a later split. |
| `benchmark/` | Keep, active V2 | `packages/benchmark/` | Definitions and canonical evidence stay; the pre-V2 tree is archived at `old/benchmark/`. |
| `tidewater-game/` | Keep, pinned app | `apps/tidewater/` | `runtime.json` pins browser assets; move after a benchmark re-base. |
| `artifacts/` | Keep, pinned evidence | `experiments/evidence/` | Raw evidence, not source. Some runtime helpers still need promotion. |
| `training_runs/` | Keep for now | `experiments/runs/` | Benchmark revisions reference exact `training_runs/...` paths. |
| `datasets/` | Removed | `data/generated/` | Contents moved; the empty pointer folder was deleted. |
| `training_data_generation/` | Moved | `training_runs/training_data_generation/` | Source moved next to the runs that use it; original import path is now a compatibility shim. |
| `docs/` | Keep | `docs/` | Cross-cutting documentation and public media. |
| `training_runs/background_manual_20261025/` | Moved | `docs/operations/background-manual/` | Windows/WSL service notes, not an ML run. |
| Root `*.log`, `handoff_*.txt` | Moved | `docs/operations/` | Working notes are no longer loose at the repository root. |

## Future roots

These paths are target contracts, not directories yet. Their placeholder
READMEs were removed so the repository does not imply components that have not
arrived.

### Apps

Tidewater remains at `tidewater-game/`. `runtime.json` pins these browser
assets by path and SHA-256, so it cannot move before a benchmark re-base:

- `tidewater-game/app/public/landing/physics/configuration.json`
- `tidewater-game/app/public/landing/physics/px4-startup.json`
- `tidewater-game/app/public/landing/wasm/px4.mjs`
- `tidewater-game/app/public/landing/wasm/px4.wasm`

The eventual layout is `apps/tidewater/{web,bridge,wasm,design,docs}`; the app
keeps its own `LICENSE`, `CREDITS.md` and asset notices.

### Third-party code

PX4-Autopilot is currently a nested checkout at
`landing_training/.vendor/PX4-Autopilot/`. It is not project source and must not
be edited. The future `third_party/` root should hold it as a submodule or a
setup-script fetch pinned to an exact commit, or be referenced by an environment
variable. Never copy PX4 build output into a wheel or commit it.

### Curated data

Reviewed, stable inputs will live at `data/curated/<purpose>/<YYYY-MM-DD>/`
with a `README.md` and `manifest.json`. The manifest records `dataset_id`,
`schema_version`, `purpose`, `code_commit`, `producer_command`, `seeds`,
`case_ids`, `file_hashes`, `license` and `review_status`. No curated set has
been promoted yet; the current review sets remain under `data/generated/`.

### Experiments

The future roots replace paths that are currently pinned:

| Future root | Current source | Gate |
|---|---|---|
| `experiments/runs/` | `training_runs/` | Benchmark revisions reference exact paths. |
| `experiments/benchmarks/` | `old/benchmark/runs/`, `probes/`, `audits/` | Frozen harness receipts. |
| `experiments/evidence/` | `artifacts/` | `runtime.json` hashes evidence files. |
| `experiments/archive/` | future | Superseded policies and frozen revisions. |

Every run gets a `run.json` with `run_id`, `purpose`, `status`, `code_commit`,
`dirty_patch_sha256`, `environment_sha256`, `config_sha256`, `model_hashes`,
`started_utc`, `finished_utc`, `outcome` and `report_path`. Archives stay
immutable; do not rewrite an archived receipt.

### Model weight store

`models/registry.json` is the current index. `models/sha256/` is the future
canonical store, one file per unique hash; it is not created yet. A run
references a hash and never copies a weight into its own directory.

## Candidates we do not need long-term

These are listed for later cleanup. **Nothing here was deleted.**

- `.cloud-attachments/` — imported conversation artifact, not project source.
- `old/benchmark/_superseded_inventory/` — old inventory; archive or remove after
  confirming no historical report links to it.
- `old/benchmark/probes/`, `old/benchmark/audits/`, `old/benchmark/runs/` — raw
  experiment output; keep as evidence locally, not as source, and migrate to
  `experiments/` when practical.
- `landing_training/.venv/` — local interpreter; recreate from requirements.
- `landing_training/.vendor/PX4-Autopilot/` — nested checkout; belongs under
  `third_party/` or a pinned setup script.
- `landing_training/build/`, `px4-mujoco-drone-simulation/build/` — generated
  MuJoCo scenes; regenerate from source.
- `landing_training/outputs/`, `landing_training/checkpoints/`,
  `landing_training/datasets/` — generated review/training outputs.
- `tidewater-game/history/` — historical benchmark media; archive under
  `experiments/archive/` when the app’s one fixture reference is updated.
- `tidewater-game/node_modules/`, `tidewater-game/app/dist/`,
  `tidewater-game/simulation/runtime/` — local install/build/runtime output.
- `px4-mujoco-drone-simulation/**/__pycache__/` — tracked bytecode was removed
  from the index; ignore and regenerate.
- Root scheduler/console logs — already moved to `docs/operations/logs/`.

## Not obsolete

`AGENTS.md`, `LICENSE`, `README.md`, `docs/`, the benchmark definitions and the
pinned source trees are intentional parts of the project.
