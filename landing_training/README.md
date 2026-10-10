# AERODOCK airborne landing training

Train a drone to find, approach and land on a moving AERODOCK boat using its
onboard camera and telemetry. This folder combines the
[boat simulator](../AERODOCK_MuJoCo/README.md) and
[PX4 drone simulator](../px4-mujoco-drone-simulation/README.md) in one MuJoCo
environment, with native PX4 flight control, an expert controller and a recurrent
imitation-learning policy.

The workflow covers environment qualification, human-reviewed recordings,
parallel expert data collection, training and closed-loop evaluation. It is a
simulation research baseline; real hardware calibration and deployment remain
separate work. Run-specific progress, weights and results are generated locally
and are not included in this source checkout.

## The landing task

Each recording starts with the drone already airborne. It may initially see the
boat or need to search using a coarse radio beacon and the articulated camera.
The expert approaches facing the boat, matches its motion, aligns with the raised
pad and descends. The drone's legs remain visible and collidable. Both boat lids
stay open and the platform stays raised throughout every episode.

The boat and drone share physics, contact forces and a simulation clock. PX4
controls attitude and motors; the policy predicts velocity, yaw-rate and gimbal
commands at **25 Hz**. A successful landing requires stable support and PX4
disarming, rather than a brief touch of the deck.

## Data and model

The deterministic plan contains **1,200 episodes**: **960 training**, **120
validation** and **120 test**. Five map families, both route directions, airborne
starts up to 60 m away, wind, waves, camera variation and simulated faults provide
coverage. Paired directions share a world and stay in the same split. The 70%
nominal / 30% fault allocation describes scenario settings, not a promised landing
success rate.

The policy combines **640 × 360 RGB**, **32 numeric inputs**, a MobileNetV3 Small
encoder and a causal GRU. It has **1,550,768 parameters**, with **623,760
trainable** in the default frozen-encoder configuration. Fixed visual features
are prepared once and reused across epochs. Validation selects the checkpoint;
test worlds are reserved for final evaluation.

An approved review bundle and passing data checks are required before training.
Collection renders only the drone camera and stores lossless HDF5 images with
matching JSONL input/output rows. Review videos additionally show the external
view and a numeric side panel.

## Run it

Run commands from the **repository root**. The supported cloud workflow uses
Linux, Python 3.12, native PX4 SITL, NVIDIA EGL and CUDA PyTorch. The
[operating guide](docs/operations.md) covers fresh setup, review approval,
benchmarks, direct commands and Windows/WSL support.

On an already configured machine with an approved review, start or resume the
pipeline in a detached tmux session:

```bash
bash landing_training/resume_cloud_pipeline.sh
python3 -m landing_training.status --watch 10
```

Completed episodes and compatible checkpoints are reused. Closing SSH or stopping
the status watcher leaves the detached pipeline running. Configuration, approved
runtime and data provenance must remain compatible when resuming.

The default cloud pipeline uses 64 collection workers, four image readers and
eight evaluation workers. These are settings measured for the project's L4 VM;
benchmark a different machine before selecting its collection worker count.
Storage guards cap the dataset at 1,500 decimal GB and reserve additional space
for feature caches, checkpoints and evaluation.

## Find your way around

| Location | Purpose |
|---|---|
| [docs/operations.md](docs/operations.md) | Setup, commands, monitoring and recovery |
| [docs/technical_report.md](docs/technical_report.md) | Physics, dataset design, policy and experimental phases |
| [docs/source_map.md](docs/source_map.md) | Runtime modules grouped by responsibility |
| [tests/](tests/) | Regression tests for recording, audits, training and recovery |
| [benchmarks/](benchmarks/) | Reference and optimized training benchmarks |
| [reports/](reports/) | Retained collection performance evidence |
| [dataset_plan.json](dataset_plan.json), [schema.json](schema.json) | Dataset settings and observation/action contract |
| `datasets/`, `checkpoints/`, `outputs/` | Generated recordings, weights, progress and evaluation reports; ignored by Git |
| `.vendor/`, `.venv/`, `build/` | Local PX4 sources, Python environment and build products; ignored by Git |

Runtime modules and launchers remain at the package root so existing commands,
recorded provenance and resume paths stay usable. All reusable benchmark and
diagnostic tools are retained. Generated recordings, approvals, retries and
checkpoints are evidence and should be backed up with the source revision.

The final outputs are an audited expert dataset, latest/best policy checkpoints,
timestamped loss CSVs, measured stage durations and validation/test flight
reports. Those reports establish the simulator's measured results; model loss
alone does not establish landing reliability.
