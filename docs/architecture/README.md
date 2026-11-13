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

The tree below is the destination, not a claim that every folder exists today.
Paths marked *future* are documented contracts; create them only when real
content can move there.

```text
packages/          installable Python distributions
  aerodock/        boat simulator
  px4sim/          drone simulator
  landing/         policy, teachers, training
  benchmark/       evaluation harness
  runtime-support/ promoted Windows/mission runtime helpers
  target-learning/ promoted label and teacher adapters
apps/              future; browser app after a benchmark re-base
  tidewater/       browser game and Python bridge
data/
  curated/         future; reviewed inputs and manifests
  generated/       reproducible outputs, ignored by default
models/
  registry.json    policy ID -> SHA-256
  sha256/          future; one copy per unique weight
experiments/       future; created after receipts are re-based
  runs/            training runs
  benchmarks/      benchmark episodes
  evidence/        reports, media and raw evidence
  archive/         superseded policies and frozen revisions
third_party/       future; pinned external checkouts
docs/              cross-cutting documentation
tools/             repository maintenance checks
```

Synthetic data generation is not a distribution: its source lives at
`training_runs/training_data_generation/`, next to the runs that use it.

Only the roots with real content are materialized today: `data/generated/`,
`models/registry.json`, `docs/operations/` and `tools/`. The other paths above
are target contracts documented in [FOLDER_DISPOSITION.md](FOLDER_DISPOSITION.md);
no empty placeholder directories are kept.

## The pinned boundary

`old/benchmark/environments/runtime.json` records exact paths and SHA-256 values for:

- 171 source files,
- 18 assets,
- 14 harness files.

`old/benchmark/runner.py` verifies those receipts before every trial. Moving
`AERODOCK_MuJoCo`, `px4-mujoco-drone-simulation`, `landing_training`,
`old/benchmark`, `tidewater-game` or `artifacts` would make the archived
benchmark fail preflight. The active V2 benchmark is `benchmark/`; its own
pinned receipts live in `benchmark/definition/runtime.json`.

## What moved in this pass

- `datasets/` → `data/generated/` (generated review datasets); the empty
  pointer folder was later deleted.
- `training_data_generation/` → `training_runs/training_data_generation/`,
  with the original import path kept as a compatibility shim.
- `training_runs/background_manual_20261025/` → `docs/operations/background-manual/`.
- Root logs and the investigation handoff → `docs/operations/`.
- Pre-V2 `benchmark/` → `old/benchmark/`; `benchmarkV2/` promoted to `benchmark/`.

Pinned simulator and source trees were not moved. No GitHub workflows were added.

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
