# SX1262 dropout: visual acquisition

## Observed failure

The user's `browser-performance-2026-10-15T17-11-51-750Z-ml.json`
already had all radio fields zero. The network was active, but its decoded pose
was a correction to a missing radio base: estimated depth 0.2218 m. No marker
registration was accepted. The original acquisition fallback commanded
`[0, 0, -0.3, 0, 0, 0]` (climb), rather than following the boat.
This recording rules out stale website code as the cause of that flight.

## Implementation

- SX1262 numeric fields remain zero and invalid during disabled/lost connection.
- With no trusted metric pose, confident learned image bearing drives bounded
  horizontal approach and camera aiming. Vertical velocity target is zero;
  existing command slew limits transition any preceding climb to that target.
- If the target is not visible, the gimbal searches; the acquisition fallback
  no longer continually climbs during radio loss.
- Calibrated camera rays and the known 0.26 m painted square initialize marker
  scale independently of the network's missing radio-relative range.
- The existing full marker fit must still pass RMS, paint precision/recall,
  conditioning, visibility and frame-boundary checks. No bearing-only descent.
- Successive accepted marker poses combined with PX4 odometry provide boat
  velocity. These are internal visual estimates, not substituted radio inputs.
- Network weights, FP32 inference, 640×360 input, 25 Hz decisions, original
  command bounds and boat control remain unchanged.

## Focused checks

- Actual GPU inference on the user's failing image: 16 decisions per replay,
  with zero radio inputs. Horizontal commands reach PX4 MAVLink transport;
  final command approximately `[0.885, -0.108, 0, 0, -0.043, 0.047]`.
  The preceding climb settles to zero by decision 13 under the original slew
  limits. Phase is `visual_acquire`, with no fabricated valid metric pose.
- Actual GPU inference on a close recorded image: starting with radio disabled,
  phase transitions from `visual_search` to accepted metric acquisition and
  tracking on decisions 2 and 3.
- Calibrated synthetic marker: deliberately wrong 0.001 m neural range prior,
  zero radio inputs, accepted image-based range and descent after stable
  alignment. Fit RMS approximately 0.81 px. Blank and clipped paint rejected.
- Visual velocity reconstruction checked against known 0.8 m/s motion.
- Connected-radio numeric inputs and eight original controller action fixtures
  still match. Manual boat throttles, stop and route speed checks pass.

Commands (from `app/`):

```
node test/ml-boat-radio.mjs
node test/visual-acquisition.mjs
node test/radio-dropout.mjs --live-neural --record browser-performance-2026-10-15T17-11-51-750Z-ml.json --steps 16 --expect-acquire
node test/radio-dropout.mjs --live-neural
node test/policy-inference.mjs --external
node test/policy-pipeline.mjs
node test/flight-request-lifecycle.mjs
```

These are component, recorded-image and calibrated-image checks. They do not
establish a complete moving-boat touchdown or full-scene browser performance.
No browser was opened. The original 2 m/s policy command bound still prevents
catching a boat moving faster than that bound in the same direction.
