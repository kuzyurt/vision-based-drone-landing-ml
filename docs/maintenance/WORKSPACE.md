# Workspace map and cleanup candidates

Inspected 25 October 2026. No experiment evidence or deletion candidates were
deleted. `artifacts/` is deliberately retained as project history.

## Where things belong

| Folder | Responsibility |
|---|---|
| `landing_training/` | Importable simulation, teaching, recording and original training modules |
| `training_runs/` | Versioned run implementations, data, manifests and outputs; active work lives here |
| `artifacts/` | Preserved experiments, frozen policy bundles and evidence; keep |
| `benchmark/` | Matched evaluation, model snapshots, receipts, reports and dashboard |
| `tidewater-game/` | Browser game, WASM integration, app assets and game history |
| `AERODOCK_MuJoCo/` | Reference boat simulation and CAD |
| `px4-mujoco-drone-simulation/` | Reference drone simulation and CAD |
| `docs/` | Cross-project guides, architecture, presentation media, research and documentation tools |

## What was organized

- Root README now leads with the Tidewater landing; training and game details
  have dedicated READMEs and navigation pages.
- Moved `research_repo_comprehension/` to `docs/research/repository-comprehension/`.
- Preserved the previous training overview in
  [`landing_training/docs/history/`](../../landing_training/docs/history/OVERVIEW_BEFORE_2026-10-25.md).
- Preserved the previous Tidewater technical guide in
  [`tidewater-game/docs/`](../../tidewater-game/docs/RUNTIME_REFERENCE.md).
- Copied the completed benchmark's four summary/report receipts into
  `benchmark/reports/2026-10-25/`, outside ignored per-flight run storage.
  The original run and traces remain in place.
- Added architecture and benchmark figures, media provenance, reproducible
  CPU-only exporters, and root ignore rules for interpreter/test/OS caches.

## Protect the current training run

At inspection, PID **740** was executing
`training_runs/search_revision_20261025/operations/cheap_fixes_20261025/train_cheap.py`.
The live PID can change; consult its run receipts before future maintenance.

Do not move or edit `training_runs/`, frozen bundles, benchmark weight snapshots,
simulation assets, Python source modules, or the training environment during this
run. The curated view points into older run directories; an older date does not
make a directory obsolete. Source paths and hashes are also part of collection
approval and benchmark reproduction contracts.

The `landing_training/` source files intentionally stay at their established
paths. Its [source map](../../landing_training/docs/SOURCE_MAP.md) groups them by
responsibility. Moving them into new Python subpackages needs a separate migration
after training, with imports, fingerprints and archived runtime dependencies reviewed.

## Disposable clutter

Sizes are approximate snapshots. These have no experiment or source value, but
none were removed. Leave any cache used by the active process alone until it ends.

| Candidate | Size | Condition |
|---|---:|---|
| `benchmark/.pytest_cache/` | <0.1 MiB | Disposable pytest bookkeeping |
| `benchmark/__pycache__/` | <0.1 MiB | Regenerates from source; no benchmark worker was running |
| `landing_training/__pycache__/` | 0.2 MiB | After training; preserve current run dependencies now |
| `px4-mujoco-drone-simulation/sim/__pycache__/` | 0.1 MiB | After training; some bytecode is tracked and should eventually be removed from Git |
| `AERODOCK_MuJoCo/usv/__pycache__/` | 0.2 MiB | After training; regenerates from source |
| `tidewater-game/history/pc_benchmark/**/*.log`, `*.pid` | Small | Logs/PID files from completed historical local servers; confirm no live owner |

## Rebuildable folders, if disk space matters

These still have a purpose. Deleting them trades disk space for reinstall/rebuild
time; they are not unused source files.

| Candidate | Size | What would be required again |
|---|---:|---|
| `tidewater-game/app/dist/` | 265.0 MiB | `npm run build`; do not remove while serving that build |
| `tidewater-game/app/node_modules/` | 303.1 MiB | `npm ci`; check that no game/build task needs it |
| `landing_training/build/` | 532.9 MiB | Scene/collision/LOD regeneration; **protected during training** |

## Historical material to review, not automatically delete

| Candidate | Size | Why it may be redundant / why it is retained |
|---|---:|---|
| `tidewater-game/history/pc_benchmark/` | 124.0 MiB | Separate old checkout and dependencies; no production reference found. Preserve measurements and inspect its nested Git repository for unique changes before deciding |
| `tidewater-game/history/windows_render/` | 708.4 MiB | Render trials, duplicated encodes, replay states and archives. Its recorded example has a collision-failure receipt; it is not the success demo. Keep evidence/replay inputs if reproducibility matters |
| `tidewater-game/history/tidewater_morning_20261011/` | 44.6 MiB | Superseded framing and render experiments; may be archived elsewhere if no longer useful |
| `docs/research/repository-comprehension/research_plan.md` | Small | Completed research plan, useful only as methodology history |

`benchmark/_superseded_inventory/` (0.5 MiB) and `benchmark/probes/` (80.5 MiB)
still explain inventory corrections and compatibility checks. Keep them with the
benchmark evidence. Keep `.freebuff/` as local tool metadata unless that tool is
retired. Keep all licenses, original CAD assets, lockfiles, the training `.venv/`
and `.vendor/`, and the successful source recordings referenced by media provenance.

There is no verified unused Python module to delete in this pass. Existing
historical bundles import one another, so deletion based only on filenames or
age would break reproducibility.
