# Landing hardening: keeping the target in view

18 October 2026. The revised controller passed the predeclared simulation gates:
**58 boat landings in 60 fresh flights, two home fallbacks and zero collisions or
water strikes**. It also passed all ten separate safe-home cases and landed in
both actual Tidewater runtime checks. The revision is integrated into Tidewater.

## The problem we set out to solve

Near the boat, a small movement changes the camera view dramatically. The drone
could see the pad, approach it, lose it below or behind the airframe, then repeat
the same acquisition attempt. Some flights followed the boat without reaching a
safe landing position. Merely increasing confidence or allowing more descent
would have hidden the uncertainty and increased collision risk.

The investigation separated three problems: losing the target estimate between
images, approaching faster than the aircraft could brake, and drifting across
the tiny camera footprint during the final centimetres. Recorded onboard RGB,
capture timestamps, own-motion estimates and executed commands supplied the
evidence. Simulator truth was used for assessment, not to guide the drone.

## What changed

The neural checkpoints stayed unchanged. This round hardened the tracking and
control architecture around the learned vision:

1. **Persistent tracking with uncertainty.** Accepted visual measurements update
   a target-motion estimate. Own odometry carries it between images. Its age and
   uncertainty limit how long it can guide camera aim or recovery; remembered
   geometry does not become a new visual measurement.
2. **An approach that leaves room to stop.** Observed bearing changes and own
   motion constrain closing speed before the pad becomes untrackably close. The
   constraint remains active through the first, still-unsettled metric estimate.
   Aircraft yaw and gimbal motion retain their airframe-obstruction limits.
3. **Better motion information near the deck.** The established visual tracker
   supplies a current velocity estimate instead of a slower smoothed regression.
   This reduces lag while matching a moving landing pad.
4. **A visibility-based final descent budget.** Calibrated camera geometry and
   image age determine how much lateral motion the final view can tolerate.
   Descent pauses when that budget is exceeded. This adds a stricter veto; the
   original geometry, touchdown and disarm requirements remain unchanged.
5. **Bounded recovery.** Loss of a usable measurement triggers braking and local
   reacquisition. A roughly 2.5 m climb is available only with a declared clear
   upward corridor and altitude limit. Retries are finite. Exhaustion leads to
   authorized home landing in the native harness or manual hold in Tidewater.

Failed revisions were retained rather than promoted. Five targeted development
flights then passed before the frozen fresh suite began. The fresh suite was not
used to tune this revision.

## Measured results

All flights below had **no boat radio position or velocity input**. Flight time
is simulated mission time after policy handoff, separate from computation time.

| Evaluation | Result | Flight time |
|---|---|---|
| Five targeted development cases | 5/5 boat landings | 44.1–122.1 s |
| Frozen fresh suite: 60 independent worlds | 58/60 boat landings; 2 home landings | Successful median 71.6 s; range 35–143 s |
| Separate unavailable-target/camera-fault suite | 10/10 physical home landings | All five injected camera-fault cases exercised |
| Actual Tidewater stack, unpowered boat | Boat landed, stable and disarmed | 40.4 s |
| Actual Tidewater stack, independently moving boat | Boat landed, stable and disarmed | 47.7 s |

The fresh suite covered all five maps, 3–60 m starts including airborne starts
over land, moving boats through 0.9 m/s, varied appearance and lighting, wind,
camera faults and configured wave heights up to 5 cm. All 12 island, beach and
gravel cases landed; city and rock each landed in 11 of 12. Fifteen camera-fault
cases actually triggered. Source, input, physical-outcome and visibility audits
passed, with zero collisions or water strikes across both native final suites.

The two unsuccessful boat missions were 60 m, 8 m-high over-land starts in city
and rock scenes. They physically landed at their authorized home after 114.6 s
and 121.7 s. They count as boat-landing failures.

The moving Tidewater boat averaged 0.630 m/s and travelled 29.8 m. Each game
landing had four supporting feet and more than two seconds of stable, disarmed
contact. These checks used the production ONNX WebGPU, WASM registration,
Pyodide controller and MuJoCo/PX4 components on the VM, with headless Node
scheduling. They took about 109 and 126 wall-clock seconds after runtime setup;
they are not browser-worker UI performance measurements.

## Integration and limits

The browser controller matched native decisions over 1,810 fixed recorded-input
frames. Camera-optimizer differences were about 10⁻⁹ rad/s within a documented
10⁻⁸ tolerance; physical scoring was unchanged. A separate handoff fix prevents
a recovery at 10 m from suddenly requesting the manual controller's normal 8 m
ceiling. Normal manual limits and independent boat controls are preserved.

The result is **96.7% on this sample**, not a promise of that rate elsewhere or
on hardware. Its approximate 95% Wilson interval is 88.6–99.1%. Static corridor
checks are not comprehensive dynamic obstacle avoidance. The bounded terminal
contact phase may use a recent visual-motion estimate and own odometry; fresh
vision is not guaranteed on every final-centimetre step.

Tidewater has no authorized stationary home and therefore restores manual hold
when recovery is exhausted. Its normal boat cruise remains 2.8 m/s while policy
horizontal commands cap at 2 m/s: arbitrary pursuit at default cruise is not
established. Stop or slow the boat for an initial trial.

This remains hybrid learned vision, geometric tracking, explicit control and
PX4. There was no new neural training, reinforcement learning or teacher-data
collection in this hardening round. Original weights, recordings, approvals,
failed revisions and the previous local build were preserved.

The [qualification certificate](../../app/public/policy/qualification/r15_simulation_qualification_certificate.json)
ties the results to frozen controller policy
`5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35`.
The exact tested browser manifest retains its freeze-time staging metadata;
this separate certificate records the subsequent measured qualification.
