# Current policy reference

Verified local snapshot: **17 October 2026**. This page identifies the current
candidate; it does not select a new checkpoint or launch training.

## Which implementation is current?

The active candidate uses **learned vision, geometric marker registration,
explicit control and PX4**. Its independent visual memory receives no boat-radio
coordinates or quality flags. Learned fusion can add a bounded radio contribution;
raw radio cannot steer the acquisition/controller directly. Missing radio has an
explicit validity/uncertainty representation. This is not end-to-end neural motor
control or reinforcement learning.

The root `policy.py` and `train.py` are the original baseline implementation.
They remain available for reproduction; they are not the latest deployed runtime.

| Item | Verified reference |
|---|---|
| Candidate metadata | [Frozen policy manifest](../../artifacts/vision_first_fusion_20261017/vision_first_fusion_delivery/candidate/policy.json) |
| Native runtime | [Candidate runtime](../../artifacts/vision_first_fusion_20261017/vision_first_fusion_delivery/candidate/code/landing_training/radio_robust_20261015/runtime.py) |
| Learned fusion | [Candidate model](../../artifacts/vision_first_fusion_20261017/vision_first_fusion_delivery/candidate/code/landing_training/radio_robust_20261015/model.py) |
| Scored native results | [Experiment results](../../artifacts/vision_first_fusion_20261017/vision_first_fusion_delivery/RESULTS.md) |
| Browser deployment | [Tidewater policy manifest](../../tidewater-game/app/public/policy/manifest.json) |
| Browser integration evidence | [Port report](../../tidewater-game/benchmarks/flight-parity/vision-first-browser-20261017.md) |

Candidate checkpoint SHA-256:
`2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4`.

Its spatial acquisition checkpoint is
`b432c1584b778d1959e950e855fcdf78c468d7f5ec7e86b71641f5052a6ce14b`.
Tidewater's manifest identifies the same candidate. Original weights and frozen
experiment sources stay in their preserved bundles rather than being copied over
the older environment package.

## What the evidence supports

- **Latest fusion candidate:** 4/4 targeted boat landings in one beach scenario,
  including falsely confident constant 5 m and 20 m radio offsets, accurate radio
  and no radio. This is not a broad reliability qualification.
- **Earlier R8 parent:** 58/60 fresh no-radio boat landings across five maps, with
  zero collisions/water strikes; separately 6/6 physical home fallbacks when the
  target was unavailable. Those results do not automatically qualify the newer
  fusion candidate.
- **Browser port:** neural/controller parity and integration checks passed. A new
  closed-loop Tidewater flight success rate has not been measured.

Current no-radio qualification used starts through 60 m, moving boats, varied
appearance/wind and configured wave heights up to 5 cm. The historical baseline
guide contains different, earlier stress settings; do not treat all of its
settings as the current qualified envelope.

## Deployment boundaries

Tidewater retains independent boat controls and normal 2.8 m/s cruise. The policy's
horizontal command cap is 2 m/s, so stop or slow the boat for an initial landing
trial. The game has no authorized stationary home: at the mission deadline
reserve it restores manual hold rather than copying the native evaluation
harness's static-home landing. Native evaluation fallback required an explicitly
declared home reference.

Actual recordings and the large dataset remain on the VM. These links describe
the verified Windows bundle; they do not imply that the VM source tree or its
storage layout has been reorganized.
