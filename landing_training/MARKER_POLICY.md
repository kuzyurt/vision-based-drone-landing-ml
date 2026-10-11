# Learned marker policy

The original three-epoch action policy aborted all twelve validation flights. Feeding its own previous actions also amplified camera and descent errors. Limiting camera tilt alone did not produce a landing.

This branch adds a hybrid policy: a supervised RGB/telemetry tracker estimates visibility and deck normal; calibrated RGB marker registration supplies metric position and visual orientation; explicit observable control aligns, matches boat velocity, descends, commits briefly to contact, and gives native PX4 landed/disarmed state priority. The frozen encoder and existing 960 training / 120 validation feature caches are reused. No RL or new training collection is required. The held-out test split is not used for training.

The trained pose model uses physically scaled losses and preserves every epoch checkpoint. Metric registration uses the reviewed painted marker dimensions (outer half-width 0.130 m, inner half-width 0.123 m, cross arm half-length 0.085 m and half-width 0.005 m). Camera transforms use static CAD calibration and public encoder/attitude history at image capture time. A narrow RGB search and ink-density initialization retain distant fragmented paint without accepting unrelated deck graphics. Filled-paint agreement, observable fit geometry, range checks and source checksums reject ambiguous results.

Public boat motion selects the visual marker's rotational quadrant; its direction is not substituted for precise visual heading. The original twelve recorded comparison scenarios were audited: fresh, smoothed motion above 0.10 m/s selected the correct quadrant in every eligible recorded frame. Once acquired, the visual heading remains continuous. No simulator state or teacher output enters the policy.

Camera targets stay between -10 and +90 degrees, with recovery from measured excursions; physical servo overshoot can briefly exceed a target bound. Command slew limits come from the training recordings. Close approach selects a front/back camera corridor. Descent uses the original 0.12 m lateral, 0.18 m/s speed, 8 degree heading/deck limits with an additional uncertainty margin and tracking dwell. Contact commitment has stricter checks, an eight-second limit, and breaks on stale motion, excessive relative speed or attitude. Ordinary PX4 disarm and the unchanged evaluator determine success; contact is never faked or made sticky.

The early camera/velocity-slew-only variant and the first pose controller were rejected after collisions. Their traces, code and checkpoints remain in the experiment outputs. The independent heading-head experiment is preserved but not selected because aggregate validation improvements did not fix its high-altitude focus frames.

## Reproduce evaluation on the VM

A bundle contains pose.pt, policy.json, calibration, command limits, source hashes and the selected validation names. The loader refuses altered weights, changed source or a checkpoint path escaping the bundle. Evaluation reuses bounded native PX4 slots and refuses to replace an existing output directory.

```bash
export MUJOCO_GL=egl
export LANDING_REUSE_APPROVED_RUNTIME=1
landing_training/.venv/bin/python -m landing_training.evaluate_marker \
  --bundle landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json \
  --review landing_training/outputs/diverse_review_20261010T010226Z_93857/bundle \
  --manifest landing_training/datasets/expert/manifest.json \
  --output landing_training/outputs/new_marker_evaluation \
  --workers 2
```

Use a fresh output path. The bundle defaults to the same original twelve validation scenarios; explicit names can select other approved validation scenarios. Held-out test evaluation requires an explicit test split and test names. Video requires one named scenario and renders on the VM. The original pipeline state remains needs_model_iteration because it refers to the preserved legacy action checkpoint; do not resume its former 64-worker configuration on the 8-vCPU VM.

## Evidence

The final three-case focus pilot landed all three flights, including both previously blocked high-altitude cases, with no unsafe outcomes. Thirty-one focused checks pass. The completed twelve-case comparison landed 12/12 flights with zero unsafe outcomes, versus 12 aborts and zero landings from the original three-epoch action policy. All twelve scenario configurations match the original comparison exactly. The unchanged physical evaluator confirmed contact and disarm; the separate policy-controlled video flight also landed.

Median roll/pitch RMS over the first 20 task seconds decreased from 5.682/3.940 degrees to 2.136/1.887 degrees across the twelve matched scenarios. These numbers use observed PX4 attitude and the same window for both policies.

Evidence is stored in outputs/marker_iteration_20261010T233621Z/full_validation_v5/report.json, paired_comparison_v5.json and completion_receipt_v5.json. The selected bundle is policy_bundle_v5/policy.json; the final video is video_v5/validation_0008_forward/review.mp4. Its SHA-256 is f4ac0600a16268faa28cc3c29526bbc1222aeaff14b88470ca0dc8e1e43f1994. It was downloaded to the Windows PC in 4.871 seconds with an exact checksum match.

These twelve validation scenarios guided model and controller iteration. The held-out test split remains unevaluated by the selected policy, so these results establish progress on the comparison scenarios and do not establish general landing reliability or hardware qualification.

Original recordings, manifest, production checkpoints, review approvals and pipeline state are preserved. The VM verification receipt and preservation hashes are stored with the experiment. All source and policy variants, interrupted flights and failed launches are retained.
