# Folder disposition

This is the migration decision table. “Pinned” means
`benchmark/environments/runtime.json` records the folder’s files by path and
SHA-256, so moving it now would break the frozen benchmark preflight.

| Current folder | Decision | Future home | Notes |
|---|---|---|---|
| `AERODOCK_MuJoCo/` | Keep, pinned | `packages/aerodock/` | Distribution metadata added in place; import name remains `usv`. |
| `px4-mujoco-drone-simulation/` | Keep, pinned | `packages/px4sim/` | Existing `pyproject.toml`; import name remains `sim`. |
| `landing_training/` | Keep, pinned | `packages/landing/` | Distribution metadata added in place; flat modules still need a later split. |
| `benchmark/` | Keep, pinned harness | `packages/benchmark/` | Definitions and reports stay; raw runs/probes/audits/models are output/evidence. |
| `tidewater-game/` | Keep, pinned app | `apps/tidewater/` | `runtime.json` pins browser assets; move after a benchmark re-base. |
| `artifacts/` | Keep, pinned evidence | `experiments/evidence/` | Raw evidence, not source. Some runtime helpers still need promotion. |
| `training_runs/` | Keep for now | `experiments/runs/` | Benchmark revisions reference exact `training_runs/...` paths. |
| `datasets/` | Moved | `data/generated/` | Contents moved; `datasets/README.md` remains as a pointer. |
| `training_data_generation/` | Moved | `packages/datagen/` | Source moved; original import path is now a compatibility shim. |
| `docs/` | Keep | `docs/` | Cross-cutting documentation and public media. |
| `training_runs/background_manual_20261025/` | Moved | `docs/operations/background-manual/` | Windows/WSL service notes, not an ML run. |
| Root `*.log`, `handoff_*.txt` | Moved | `docs/operations/` | Working notes are no longer loose at the repository root. |

## Candidates we do not need long-term

These are listed for later cleanup. **Nothing here was deleted.**

- `.cloud-attachments/` — imported conversation artifact, not project source.
- `benchmark/_superseded_inventory/` — old inventory; archive or remove after
  confirming no historical report links to it.
- `benchmark/probes/`, `benchmark/audits/`, `benchmark/runs/` — raw experiment
  output; keep as evidence locally, not as source, and migrate to
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
