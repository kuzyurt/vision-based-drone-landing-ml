# Retained performance reports

These JSON files preserve collection optimization and worker-tuning evidence.
They describe specific source revisions, machines and workloads; they are not
current production progress or portable speed guarantees.

| Report | Contents |
|---|---|
| [collection_optimization_20261009.json](collection_optimization_20261009.json) | Before/after collection measurements and stage timing |
| [autotune_validation_20261009.json](autotune_validation_20261009.json) | Tuner validation and measured resource/configuration evidence |
| [autotune_six_workers_20261009.json](autotune_six_workers_20261009.json) | Collection comparison through six workers |

Historical test module names inside reports refer to their original locations.
Current regression tests live in `../tests/`.

New benchmarks, review bundles and pipeline results are written under ignored
`../outputs/`. Production losses and policy weights are under `../checkpoints/`.
Retain those artifacts separately when transferring or reproducing an experiment.
