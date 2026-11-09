# Drone-landing diagnosis and VM sizing

Remote identity verified: hxhshsh7gyg on instance-20261009-152306.
Repository: /home/hxhshsh7gyg/vision-based-drone-landing-ml.
Branch: codex/landing-training.

## Outcome

The original production pipeline remains needs_model_iteration. Its state,
recordings, manifests, approvals, feature caches and original best/latest
checkpoints were preserved. The stopped pipeline was not resumed past its
minimum-control gate.

The isolated ten-epoch periodic_no_action_v1 experiment selected epoch 9.
Its validation action Huber loss was 0.00319540, compared with the original
epoch-3 loss of 0.00189716 and persistence baseline of 0.000906620.
All twelve original validation pilot scenarios were reevaluated:
12 aborts, zero landings and zero unsafe outcomes. Mean pad visibility
improved from 17.0684% to 78.9745%, but this did not solve landing.
There is no justification for promoting the new weights or running final
qualification as though the minimum pilot check passed.

## Verified causes and remaining behavior

A fixed-recording feedback probe on twelve validation recordings kept visual
features and sensor states fixed. Feeding predicted actions back into the
previous-action inputs increased normalized pan-command MSE from 0.0207323
to 1.05547 (50.9 times) and descent-command MSE from 0.00365026 to 0.220503
(60.4 times). This isolates instability in action feedback; it is not a
counterfactual flight success measurement.

All training feature rows were checked for camera-angle coverage:
pan -12.4207 to +12.6102 radians; tilt -9.8128 to +90.1947 degrees.
Only 6,064 of 1,146,916 supervised training rows (0.5287%) have negative
(upward) tilt. Planned initial tilt is sampled from 0 to 90 degrees.
The recorded policy video instead reaches approximately -61 and +140 degrees,
the simulation's tilt travel limits. It has 963 recorded rows near the upward
stop while commanding further upward motion, and 2,166 rows near the opposite
stop while commanding further motion in that direction. Those states lie far
outside expert training coverage.

The compiled MuJoCo camera transform was inspected with a level aircraft.
Tilt 0 degrees looks at the horizon; tilt -10 points 10 degrees above it;
tilt -61 points 61 degrees above it; tilt +90 looks straight down.
Thus a sky-filled image indicates camera/aircraft viewing orientation.
It does not determine altitude. Height must be checked from recorded state.

Over the first twenty seconds of the same scenario, the original policy's
roll/pitch RMS is 4.3818/4.0208 degrees, versus the expert's 1.1136/1.5945.
The 95th percentile successive forward/right velocity-command changes are
0.14290/0.15474 m/s per 40 ms for the policy, versus 0.03497/0.03958 for
the expert. This confirms wobble and command variability; an arbitrary
smoothing constant has not been substituted for a verified control solution.

Cached/recomputed visual features and batched/single-step recurrence differed
slightly numerically. The maximum normalized action difference in that probe
was about 0.00108. Large action error is already present on expert inputs.
The probe did not identify a large cache/runtime preprocessing mismatch.

## Changes and validation

Versioned periodic inputs remove the six previous-action inputs and reuse
their model slots for sine/cosine yaw/pan/tilt pairs. Old checkpoints keep the
legacy representation. Recorded observations are unchanged. Normalization is
fitted on training rows only, with explicit floors for constant validity/timing
fields. The frozen encoder and checksummed feature recordings are reused;
raw RGB and test recordings are not consumed by the experimental trainer.

Fifteen regression tests passed, covering legacy checkpoint behavior, periodic
input invariance, feature integrity/masking, and existing training pipeline
equivalence. Simulation/runtime fingerprint remains
5ef2dd6e6b1853286fd2bbda52167100eb16e69cd3594969023e684f0333f403.

Code was committed on the VM branch. No GitHub push was performed.
The first code commit is 2ab41091d908d04188b8a10dd618b67c125a2ef7.

## VM recommendation

The current pipeline performs supervised imitation learning, not RL.
Bulk collection of the original 1,200 episodes is finished. Targeted supervised
recovery collection is likely needed because sky-facing/travel-stop states
are missing from training coverage and the new policy still cannot land.
Additional bulk recollection is not currently justified, and switching to RL
is not part of the current implementation or proposed immediate next step.

Recommend g2-standard-8: 8 vCPUs, 32 GB RAM, one NVIDIA L4 (24 GB VRAM).
A lower-cost option is g2-standard-4: 4 vCPUs, 16 GB RAM, the same L4.
The smaller option should run fewer simulation workers and do training/video
work serially. Eight vCPUs offers more room for simultaneous debugging,
limited collection and evaluation.

Measured evaluation-worker peak RSS was about 1.88-1.91 GiB for eleven workers,
with one reaching 3.78 GiB. This is worker RAM, not GPU VRAM, and not a bound
on raw-image training or a full VM peak. The large filesystem cache on the
128 GB machine is reclaimable; it is not application memory demand.
These observations support downsizing; no benchmark on the smaller VM has
been claimed.

Even without RL, MuJoCo/PX4 evaluations and supervised collection require CPU.
The present production configuration still specifies 64 collection workers,
8 evaluation workers and 4 image readers. It must not be launched unchanged
on the smaller machine. Use fewer workers for a new compatible iteration;
do not rewrite the frozen original state to force a configuration change.
Keep the existing data disk and all recordings/checkpoints during migration.

Google's current documented machine specifications:
https://docs.cloud.google.com/compute/docs/accelerator-optimized-machines#g2_machine_types

Google documents changing within the G2 series after stopping the instance:
https://docs.cloud.google.com/compute/docs/gpus/add-remove-gpus#accelerator-optimized_instances

## Requested video

Rendered entirely on the VM using the preserved epoch-3 policy, in a fresh
validation_0008_forward simulation. The overlay distinguishes learned policy
control from the teacher's diagnostic phase. The observed outcome is abort.

MP4: 1280x720, 25 fps, 175.08 seconds, 4,377 frames, 30,532,536 bytes.
There are 4,376 command rows, including 4,375 policy commands without supervisor
intervention and one mission-deadline intervention; the last row is terminal.

SHA256: c099f81733f50ad2afd806bb3689d26718d0e11ce9efb55360923bb97fe26168
Download to Windows took 13.153 seconds; the checksum matches the VM.
The five-minute transfer deadline was enforced.

Local video:
D:/Dokumente/CODE_PROJEKTE/SMARTSYSTEMS/schiebel-drone-landing/artifacts/model_iteration_20261010/policy_epoch3_validation_0008_forward.mp4
