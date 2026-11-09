# Packages

The target is one installable distribution per layer. The frozen benchmark
pins the current paths of most source trees, so only the unpinned package has
moved so far.

| Distribution | Source root | Status |
|---|---|---|
| `datagen` | [`packages/datagen/training_data_generation`](datagen/training_data_generation/) | Moved; old import path is a shim. |
| `aerodock` | `AERODOCK_MuJoCo/` | Metadata added in place; pinned by benchmark receipts. |
| `px4-mujoco-drone-simulation` | `px4-mujoco-drone-simulation/` | Existing metadata; pinned. |
| `landing-training` | `landing_training/` | Metadata added in place; pinned. |
| `benchmark` | `benchmark/` | Metadata added in place; pinned harness. |

Import names are intentionally unchanged for now (`usv`, `sim`,
`landing_training`, `training_data_generation`, `benchmark`). Renaming them
without path shims would break `runtime.json`, benchmark actors and Tidewater’s
bridge.

Install the current workspace with:

```powershell
python -m pip install -r requirements-dev.txt
```

The next code move is gated on a new benchmark snapshot: create the snapshot,
re-base the receipts, then relocate the pinned trees into this directory and
keep compatibility shims for one release.
