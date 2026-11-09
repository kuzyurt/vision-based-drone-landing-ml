# Documentation

| Read | Purpose |
|---|---|
| [Project overview](../README.md) | Landing demo, architecture and measured progress |
| [Training](../landing_training/README.md) | MuJoCo world, teacher, model and workflow |
| [Tidewater](../tidewater-game/README.md) | Play locally and understand the browser simulation |
| [Benchmark](../benchmark/README.md) | Evaluation contract, inventory and dashboard |
| [Verified comparison](../benchmark/reports/2026-10-25/RESULTS.md) | Durable report from the completed 60-flight comparison |
| [Media](media/README.md) | Recording provenance and asset regeneration |
| [Workspace notes](maintenance/WORKSPACE.md) | Folder responsibilities and deletion candidates |

`architecture_review_20261024/` preserves the detailed architecture investigation
and original diagrams. Its teacher diagram describes that review snapshot;
the current README uses the simpler R15 policy flow in `media/`.

`research/repository-comprehension/` holds the repository research previously
stored at the root. It is background reading, not a runtime dependency.

`tools/` contains CPU-only documentation export scripts. They do not import
training modules, run flights or update model weights.
