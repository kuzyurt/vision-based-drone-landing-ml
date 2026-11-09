# Landing without the boat radio

This candidate continues the previously trained radio-robust model. Its weights
are unchanged (SHA256 `20709cee9c6ac66e15614e1162a7180aa0efb5f126996473c227484406df2749`).
The original 1,200-episode dataset, approvals, previous bundles and every training
checkpoint are preserved. This iteration corrects runtime perception and tracking.

The four development scenarios previously aborted. All four now finish with
native PX4 disarmed and stable physical support on the moving deck. A broader
attempt exposed remaining limitations: of four actual flights, one landed and
three aborted. Four other scheduled cases never entered flight because a reused
start barrier timed out. The harness now synchronizes only the first cohort.
Those four worker errors are excluded from policy success/failure counts.
This candidate is not established as reliable across the operating envelope.
The user's additional 60 m water/inland pair is recorded separately.
Final results are recorded in `RESULTS.md` and `results.json` when complete.

## Changes

- Separate cyan paint objects before estimating the size of the 0.26 m marker.
  Previously, the convex hull could include rails and cabin accents; this made
  an elevated drone appear approximately one metre from the deck and prevented
  registration. A component only seeds the existing full geometric paint fit.
- Estimate boat velocity by robust regression over up to 1.2 seconds of accepted
  visual poses, using image capture times and the drone's own PX4 odometry.
  The old frame difference amplified position noise and fed an already
  latency-compensated estimate back into its velocity measurement.
- Require at least 0.6 seconds of motion observations before descent. Preserve
  the existing alignment, speed, attitude, marker acceptance and contact gates.

## Input and control contract

The policy receives onboard RGB, camera encoders and the drone's own PX4 state.
The evaluation removes the entire `beacon` input before inference. No boat
position, boat velocity, route, simulator state or expert command enters policy
control. The radio sensor does not generate spatial packets. Unknown radio input
is masked explicitly by the trained model; zero coordinates are not treated as a
target location.

The trained neural network estimates visual features/pose. Marker geometry and
the existing explicit landing controller turn estimates into bounded human-like
velocity/yaw/camera commands; native PX4 controls the motors. These are evaluations
of that hybrid runtime. Standard airborne setup happens before evaluated policy
control. Search starts include cases with the boat initially outside the camera.

`allow_visual_landing=True` explicitly authorizes the mission to land with unknown
radio dock status. It does not fabricate a dock-ready message. The simulated dock
is open for these scenarios. The simulator's original physical landing criteria
require stable support and two seconds of disarmed contact.

## Reproduce on the VM

The scripts contain the verified VM repository and bundle paths. Use the original
repository's `landing_training/.venv/bin/python` and run `evaluate_four.py` for the
development cases or `evaluate_native.py --cases heldout_plan.json` for the eight
test cases. Both require a fresh `--output` directory and run four workers. Do not
overwrite any existing run. Rendering is limited to the onboard policy input;
these scripts do not export videos or collect new training data.

Full episode traces and native PX4 logs remain under the VM experiment directory
`/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/radio_free_20261016T124008Z`.
