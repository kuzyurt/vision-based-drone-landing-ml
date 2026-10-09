# Training design and readiness

This is a supervised imitation-learning baseline for airborne approaches to a
moving dock. The model and data path have executable correctness checks; no
trained policy has yet established held-out landing reliability. A fast
benchmark does not establish whether the task is learned.

## Model and deployment contract

The actor receives the recorded 640×360 drone RGB image and the 32-value contract
in `recording.numeric_observation`: PX4 body-frame velocity, attitude/rates,
gimbal angles, coarse boat-beacon relative position/velocity, validity/age/readiness,
image age, previous executed action and decision timing. Privileged simulation
pose, deck normal, exact clearance, wave state and expert phase are excluded.
The synthetic observation interface still requires hardware verification.

MobileNetV3 Small supplies per-channel spatial x/y expectations and mean
activation, retaining marker location rather than only a classification vector.
A trainable 1,728→256 projection joins a 32→64 telemetry MLP. A causal GRU with
128 hidden units predicts six bounded commands: forward/right/down velocity,
yaw rate and two gimbal rates. PX4 handles attitude/motor control. This avoids
asking a small visual policy to learn fast motor stabilization from scratch.
The model has **1,550,768 parameters**, of which **623,760** are trainable with
the encoder frozen. Auxiliary heads predict visibility, marker centre, current
relative position/velocity and stable-contact confidence. Contact confidence
is advisory; the physical contact/PX4 supervisor owns confirmation and disarming.

ImageNet transfer and a small recurrent head are reasonable first experiments,
not proof that the frozen features resolve the marker at 60 m or in partial
touchdown views. The pilot must compare distance/search/weather performance.
Fine-tuning is available if frozen features prove inadequate. Gimbal feedback,
ALLXF camera FOV/zoom/latency, SX1262 payload/timing/noise and Khadas Edge2
runtime latency/NPU compatibility are not verified by the simulation benchmark.

## Optimization without changing the task

The default encoder is fixed in evaluation mode. Computing its spatial features
once is equivalent to recomputing them every epoch. Cache FP32 features before
the trainable projection, preserving image resolution and feature precision.
The cache uses approximately 7,108 bytes/frame for features and labels, plus
metadata. A 60 s mean episode gives roughly 11.5 GB for 960 training and 120
validation episodes. Keep the original RGB recordings for audit, DAgger and
possible fine-tuning; the cache is not a substitute for the original dataset.

Spawned readers decode independent chunks with bounded queues and no shared
HDF5/CUDA handles. Reader counts are capped by CPU, RAM and shared memory;
benchmark 0/4/8/16 readers rather than equating vCPUs with a good setting. Cache
files are content/encoder/preprocessing/supervision keyed, checksummed and
atomically published. Interrupted partial files are removed; completed caches
can be reused. Production preparation reserves 32 GB free space.

Cached epochs use in-process feature reads with a bounded 512 MiB LRU and batch
equal-length recurrent lanes. Each episode has a distinct hidden-state token;
short final chunks are kept without padding, with the same per-lane loss weight.
Frozen cache training has no fresh per-epoch image augmentation. Current visual
variation is recorded at collection time; adding new augmentation requires the
RGB path or a separately tested cache method. A trainable encoder always uses
the RGB path, with fixed BatchNorm statistics for temporal causality.

## Labels, epochs and evaluation

The expert is an oracle using privileged scene state. Its bounded action is the
teacher label, separately from the action actually executed. DAgger retains
teacher corrections on student-visited states. Terminal and invalid/intervened
actions are masked. Expert flights ending in `water_strike` or
`collision_failure` do not provide action-imitation targets: without a reviewed
failure-onset label, retaining their earlier commands as safe would be
unjustified. Their auxiliary targets remain available. Failed student DAgger
flights keep valid oracle action labels; all recordings are retained for audit.

RGB and marker visibility/pixel labels pass through the same image-delay queue.
The relative pose/velocity targets describe the current decision state, which
combines delayed vision with current telemetry; they are not camera-time pose
labels. Simulated pose is only a teacher/auxiliary target. It never enters the
actor input.

One epoch visits every training recording once. Episode order is shuffled;
frame order is preserved. Eight lanes contribute up to 64 frames each per Adam
update (2.56 s of decisions per lane at 25 Hz). State carries between chunks,
but gradients stop at their boundaries. Learning rate is 1e-4, gradient norm is
clipped to 1, and actions use normalized Huber loss. Auxiliary loss weights are
0.1 visibility, 0.05 stable contact and 0.05 visible regression. These are
declared baseline hyperparameters requiring pilot evidence, not tuned optima.

Telemetry normalization uses training worlds only. Forward/reverse variants of
one world stay in one split. The 1,200-episode plan has 960/120/120
training/validation/test episodes and now balances configured initial camera aim
50/50 inside every split. Camera aim is not a guarantee of actual marker
visibility. “70% nominal” describes scenario faults, not successful landings.

Validation uses dataset-wide denominators per loss component, avoiding excess
weight on short terminal chunks. It reports action/auxiliary losses, supervised
step count, visible/contact fractions and an action-persistence baseline.
Because previous executed action is an input, simply repeating it can achieve
small one-step error; low imitation loss alone is insufficient evidence of
visual control. The default ten epochs are a budget, with early stopping after
three unimproved validation epochs. Test worlds never select weights.

Atomic latest/best checkpoints include optimizer, RNG, normalization, history
and dataset/review hashes. Resume requires the same approved data and encoder
training mode. It resumes from the last complete epoch, replaying an interrupted
epoch. Existing training outputs require resume or a fresh directory, preventing
accidental checkpoint replacement. CPU checks verify that resumed and uninterrupted weights match exactly;
CUDA numerical determinism across machines is not promised.

Closed-loop evaluation uses the checkpoint's matching approved dataset/review,
and reports landings, water strikes, collisions, abort/timeouts, touchdown
velocity and map/distance/weather/camera-aim strata. Paired directions share a
world and are not independent trials. A small prefix can omit difficult strata;
qualification needs the full held-out coverage. Use validation worlds during
iteration and reserve test worlds for the final assessment.

## Evidence and remaining work before a long run

Executable tests cover outputs/loss/gradients/state against the serial path,
unequal chunks, temporal ordering, cache reuse/corruption, source preservation,
worker cleanup after cancellation, training-only normalization, atomic
checkpoints, optimizer/RNG resume, early stopping, split balance and evaluation
provenance. The benchmark compares RGB/cached throughput, charges one-time
preparation separately and verifies loss improvement on a repeated fragment.
That fit is a wiring diagnostic; its temporary weights are discarded.

Before automatic collection→training:

1. Broaden and qualify boat starting progress. `Navigation.spawn` starts at
   `route.points[0]` and resets progress to zero; `Environment` also uses the
   first coastal coordinate for launch placement. Generated maps, reversed
   routes and world rotation already vary the scene, but later route sections
   are not guaranteed to appear during short flights. Random progress needs
   consistent placement, clear-water checks and flight review.
2. Inspect the initial 60 expert pilot flights for actual visibility, outcome,
   distance/weather/fault coverage, duration and compressed size. These first
   60 are training-role flights; add held-out validation coverage before fitting
   a pilot policy. Do not infer coverage from ten near-boat review videos.
3. Audit scenario-dependent expert decisions. Search uses the scenario's target
   height and abort uses its deadline, neither of which is an explicit actor
   input. Measure agreement on search/abort states; mission deadlines should be
   handled explicitly by the deployment supervisor rather than assuming the GRU
   will reconstruct them. The current benchmark does not resolve this contract.
4. Run a short frozen-encoder pilot and closed-loop validation before spending
   the full epoch budget. Compare against action persistence, inspect recovery
   from off-expert states, then use DAgger or fine-tuning according to the
   observed failures. No arbitrary success threshold is claimed as qualified.
5. The future orchestrator must require compatible approval, collection
   completion, valid train/validation coverage and space for caches/checkpoints.
   A disk-limit or crash stop must not silently launch training on an incomplete
   dataset. Persist stage reports and resume checkpoints independently of SSH.

Training/plan changes refresh the full-source review fingerprint. Existing
videos can be reused by review export only when its simulation-runtime hash
still matches; refreshed metadata still requires the user's verification.
