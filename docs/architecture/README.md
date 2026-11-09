# Repository architecture

This repository is organized by **lifecycle**: source, inputs, generated data,
experiment evidence, and third-party code each have one home. It is also a
**compatibility migration**: the frozen benchmark pins the current paths of the
simulators and policy code, so those files stay in place until a new benchmark
snapshot deliberately re-bases them.

## Verified dependency direction

The code already has a layered dependency graph:

```text
aerodock (boat) ─┐
                 ├─> landing ─> datagen
px4sim (drone) ──┘      │
                        ├─> benchmark
                        └─> tidewater bridge
runtime-support ───────> benchmark
target-learning ───────> benchmark
```

Lower layers never import higher layers. The migration makes that direction
explicit through packages and removes implicit path coupling where it is safe.

## Target layout

```text
packages/          installable Python distributions
  aerodock/        boat simulator
  px4sim/          drone simulator
  landing/         policy, teachers, training
  datagen/         synthetic data generation
  benchmark/       evaluation harness
  runtime-support/ promoted Windows/mission runtime helpers
  target-learning/ promoted label and teacher adapters
apps/
  tidewater/       browser game and Python bridge
data/
  curated/         reviewed inputs and manifests
  generated/       reproducible outputs, ignored by default
models/
  registry.json    policy ID -> SHA-256
  sha256/          one copy per unique weight
experiments/
  runs/            training runs
  benchmarks/      benchmark episodes
  evidence/        reports, media and raw evidence
  archive/         superseded policies and frozen revisions
third_party/       pinned external checkouts
docs/              cross-cutting documentation
tools/             repository maintenance checks
```

## The pinned boundary

`benchmark/environments/runtime.json` records exact paths and SHA-256 values for:

- 171 source files,
- 18 assets,
- 14 harness files.

`benchmark/runner.py` verifies those receipts before every trial. Moving
`AERODOCK_MuJoCo`, `px4-mujoco-drone-simulation`, `landing_training`,
`benchmark`, `tidewater-game` or `artifacts` would make the frozen benchmark
fail preflight. Therefore this migration does **not** move those trees. It adds
packaging metadata at their current roots and records their future locations
above. A future benchmark generation can re-base the receipts and then move the
code.

## What moved in this pass

- `datasets/` → `data/generated/` (generated review datasets).
- `training_data_generation/` → `packages/datagen/training_data_generation/`,
  with the original import path kept as a compatibility shim.
- `training_runs/background_manual_20261025/` → `docs/operations/background-manual/`.
- Root logs and the investigation handoff → `docs/operations/`.

No pinned source folder was removed or renamed. No GitHub workflows were added.

## Rules

- Source never lives under `data/` or `experiments/`.
- Generated output never lives inside a package or app source tree.
- One artifact, one home, one manifest, one ID.
- Model weights are addressed by SHA-256; do not copy the same weight per run.
- Every run and dataset carries a manifest with code commit, command, seeds and
  hashes.
- Old paths remain as shims or pointers until their references are verified.

See [FOLDER_DISPOSITION.md](FOLDER_DISPOSITION.md) for the folder-by-folder
decision and the list of candidates that can be retired later.
