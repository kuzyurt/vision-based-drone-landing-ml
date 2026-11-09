# Drone landing: environment, training and policy history

This folder contains the original coupled boat/drone simulation and training
pipeline. The project now has trained policies; the latest candidate combines
learned vision, geometric registration, explicit control and PX4.

## Start here

| Read | Purpose |
|---|---|
| [Current policy](docs/CURRENT_POLICY.md) | Exact candidate, deployment locations, measured results and limits |
| [Development report](docs/reports/LANDING_POLICY_DEVELOPMENT_REPORT_2026-10-17.md) | Chronological account of the problems, ideas and solutions |
| [Source map](docs/SOURCE_MAP.md) | Modules grouped by responsibility, with direct file links |
| [Historical environment guide](docs/history/ENVIRONMENT_REVIEW_BASELINE.md) | Original setup, review, collection and baseline-training instructions |

The development report was moved without changing its contents. The historical
guide describes the earlier review stage; its original status statements and
stress ranges are not the current policy status or qualification envelope.

## Current status

The latest **R15 hardening revision** is preserved in its
[frozen bundle](../artifacts/landing_hardening_20261018/candidate_r15/policy.json)
and is integrated into [Tidewater](../tidewater-game/README.md#trained-drone-landing-policy).
It completed **58/60 fresh no-radio boat landings**, with two home fallbacks and
zero collisions/water strikes; separate safe-home checks passed **10/10**.
Actual Tidewater runtime checks landed on both an unpowered and independently
moving boat. Neural weights stayed unchanged while tracking, approach and
bounded recovery were hardened. See the
[18 October report](../tidewater-game/benchmarks/flight-parity/landing-hardening-20261018.md)
for the measured envelope and remaining limits.

The root `policy.py` and `train.py` remain the original baseline implementation.
Use the [current-policy reference](docs/CURRENT_POLICY.md) to find the newer
runtime and its evidence. Hardware deployment remains unqualified.

## Folder layout

```text
landing_training/
├── README.md
├── docs/
│   ├── CURRENT_POLICY.md
│   ├── SOURCE_MAP.md
│   ├── reports/
│   │   └── LANDING_POLICY_DEVELOPMENT_REPORT_2026-10-17.md
│   └── history/
│       └── ENVIRONMENT_REVIEW_BASELINE.md
├── *.py                       Original importable modules and command entry points
├── dataset_plan.json          Original collection plan
├── schema.json                Original recording contract
├── requirements*.txt          Reproducible dependency inputs
├── setup.sh                   Linux setup entry point
└── build/                     Preserved generated scene/geometry cache; Git-ignored
```

Source and config paths stay stable because approval fingerprints and external
imports depend on them. The source map groups them for navigation. Existing
`python -m landing_training.<module>` commands still use their original paths;
this cleanup does not migrate them to the newer candidate runtime.

## Working with the files

- Run baseline commands from the repository root. Native PX4 preparation and
  execution require the documented Linux/WSL environment.
- Review bundles and approvals remain bound to their exact source/artifact
  fingerprints. This organization changes documentation, not runtime inputs.
- Keep recordings, approvals, checkpoints and failed experiments. Do not treat
  them as scratch or move them just to tidy the source tree.
- Treat the nominal collection plan and historical guide as baseline records.
  Consult the candidate manifest and scored experiment reports for later work.
- Keep generated caches out of Git. The existing build cache has been preserved;
  only verified interpreter bytecode was removed during this cleanup.

The large dataset and recordings are on the VM. This local organization does not
move or modify remote data, frozen policy bundles or the running game.
