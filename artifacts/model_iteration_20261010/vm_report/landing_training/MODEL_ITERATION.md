# Failed policy pilot: model iteration

The production state remains `needs_model_iteration`. Do not resume it merely
because offline loss decreases.

The preserved epoch-3 checkpoint was evaluated on 12 validation scenarios:
12 mission-deadline aborts, zero landings, and zero unsafe outcomes. The
checkpoint's action Huber loss was 0.00189716 versus 0.000906620 for the
previous-action persistence baseline.

## Verified failure mechanism

* Recorded policy trajectories repeatedly lose the marker and enter
  reacquisition. Their pan angle accumulates many complete rotations and moves
  far outside the expert training distribution.
* On 12 validation expert recordings, keeping recorded visual features and
  sensor states fixed while feeding the model's predicted previous action back
  increases mean normalized pan-command squared error from 0.0207323 to
  1.05547 (50.9 times). Descent-command error rises from 0.00365026 to
  0.220503 (60.4 times). This is an offline feedback probe, not a flight result.
* Comparing cached features, recomputed features, batched recurrence, and
  one-frame runtime recurrence found small numerical differences
  (maximum normalized action difference about 0.00108). Large action error is
  already present on recorded expert inputs. No large preprocessing mismatch
  was identified in that probe.

These measurements establish unstable action feedback and angle distribution
drift. They do not establish that correcting those two issues is sufficient
for landing.

## Experimental representation

`periodic_no_action_v1` replaces the six previous-action values inside the
model with sine/cosine pairs for yaw, gimbal pan, and gimbal tilt. It zeroes the
three corresponding raw-angle slots. The recorded sensor schema stays at 32
values. The checkpoint explicitly records its representation; old checkpoints
use the unchanged legacy path. The ordinary trainer refuses an incompatible
resume.

`iterate_policy` fits normalization using training features only. Constant
validity flags and timing fields receive explicit scale floors. It starts new
prediction heads, copies the frozen visual encoder from the preserved source
checkpoint, trains with learning rate 0.0003, and selects weights using the
existing dataset-weighted validation loss. All hyperparameters and committed
epoch results are saved. This multi-change experiment does not isolate the
benefit of each individual change.

The trainer verifies the source checkpoint/dataset/review relationship, unchanged
visual extraction, every consumed feature file's SHA256, its encoder/source
provenance, split isolation, shapes, and imitation masks. It consumes all 960
training and 120 validation feature recordings. Test recordings are excluded.
It does not consume or rehash raw RGB; the original trainer's source hashes are
preserved in checkpoint/cache provenance. It writes only a new output directory,
never production recordings, caches, approvals, or checkpoints.

## Run an iteration

Run on the VM with its existing environment and an unused output directory:

```bash
LANDING_REUSE_APPROVED_RUNTIME=1 MUJOCO_GL=egl \
landing_training/.venv/bin/python -m landing_training.iterate_policy \
  --manifest /absolute/path/to/datasets/expert/manifest.json \
  --review /absolute/path/to/original/approved/bundle \
  --source-checkpoint /absolute/path/to/preserved/production/best.pt \
  --feature-cache /absolute/path/to/checkpoints/production/features \
  --source-repo /absolute/path/to/original/repository \
  --output /absolute/path/to/unused/iteration/directory \
  --epochs 10 --device cuda
```

Original checkpoints remain readable through `PolicyRuntime`. The experiment
refuses an occupied output directory; interrupted outputs remain available for
inspection rather than being overwritten.

Closed-loop evaluation is mandatory before interpreting an iteration as an
improvement. The production pilot criterion and full validation/test evaluation
requirements remain unchanged.
