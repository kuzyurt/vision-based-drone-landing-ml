# Current policy reference

Verified local snapshot: **18 October 2026, R15 hardening**. This page identifies the current
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
| Candidate metadata | [Frozen policy manifest](../../artifacts/landing_hardening_20261018/candidate_r15/policy.json) |
| Native runtime | [Candidate runtime](../../artifacts/landing_hardening_20261018/candidate_r15/code/landing_training/radio_robust_20261015/runtime.py) |
| Learned fusion | [Candidate model](../../artifacts/landing_hardening_20261018/candidate_r15/code/landing_training/radio_robust_20261015/model.py) |
| Scored native results | [Fresh-suite audit](../../artifacts/landing_hardening_20261018/r15_native_completion_verified/r15_fresh_E60/hardening_audit.json) |
| Browser deployment | [Tidewater policy manifest](../../tidewater-game/app/public/policy/manifest.json) |
| Browser integration evidence | [Hardening report](../../tidewater-game/benchmarks/flight-parity/landing-hardening-20261018.md) |
| Qualification | [Separate certificate](../../tidewater-game/app/public/policy/qualification/r15_simulation_qualification_certificate.json) |

Frozen controller policy SHA-256:
`5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35`.

Unchanged neural checkpoint SHA-256:
`2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4`.

Its spatial acquisition checkpoint is
`b432c1584b778d1959e950e855fcdf78c468d7f5ec7e86b71641f5052a6ce14b`.
Tidewater's manifest identifies the same candidate. Original weights and frozen
experiment sources stay in their preserved bundles rather than being copied over
the older environment package.

## What the evidence supports

- **R15 hardening:** 5/5 targeted development landings, then 58/60 boat landings
  in a frozen fresh suite of 60 independent worlds. Two home landings count as
  failed boat missions. Zero collisions/water strikes; all 15 camera-fault cases
  exercised. Separate unavailable-target/camera-fault checks passed 10/10
  physical home landings. Successful fresh flights took 35–143 s, median 71.6 s.
- **Actual Tidewater stack:** unpowered boat landed in 40.4 s; independent moving
  boat averaging 0.63 m/s landed in 47.7 s, both without boat radio input. These
  use production components with headless Node scheduling, not a new UI-worker
  success-rate or performance measurement. Controller parity passed on 1,810
  recorded-input frames.
- **Preserved history:** the prior fusion candidate's four targeted radio checks
  and the earlier R8 qualification remain lineage evidence. They are separate
  from this new R15 suite. No new neural training or teacher collection occurred.

R15 adds persistent visual tracking, stopping-distance approach control,
geometry-based terminal motion limits and bounded clearance-gated recovery.
The exact tested browser manifest retains freeze-time staging flags; the separate
certificate above records the subsequent qualification without rewriting the
frozen experiment. A finite 58/60 result does not establish hardware reliability
or a guaranteed population success rate.

Current no-radio qualification used starts through 60 m, moving boats, varied
appearance/wind and configured wave heights up to 5 cm. The historical baseline
guide contains different, earlier stress settings; do not treat all of its
settings as the current qualified envelope.

## Deployment boundaries

Tidewater retains independent boat controls and normal 2.8 m/s cruise. The policy's
horizontal command cap is 2 m/s, so stop or slow the boat for an initial landing
trial. The game has no authorized stationary home: bounded recovery exhaustion
or the mission deadline reserve restores manual hold rather than copying the native evaluation
harness's static-home landing. Native evaluation fallback required an explicitly
declared home reference. Recovery-to-manual handoff retains the measured height
instead of commanding a drop to the normal 8 m manual ceiling. Static corridor
checks are upward-recovery vetoes, not full dynamic obstacle avoidance.

Actual recordings and the large dataset remain on the VM. These links describe
the verified Windows bundle; they do not imply that the VM source tree or its
storage layout has been reorganized.
