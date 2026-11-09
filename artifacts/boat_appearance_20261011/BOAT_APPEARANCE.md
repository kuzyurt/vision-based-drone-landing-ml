# Boat finish generalization

Four frozen-policy flights compare two worn finishes and two palette changes. No model training or tuning is performed. Boat CAD, mass, collision geometry, motion, wind, waves, camera geometry, PX4 and landing criteria remain unchanged. All original on-disk textures and approved assets remain unchanged; evaluation modifies only each process's material and texture buffers.

| Appearance | Scenario | Change |
|---|---|---|
| used_light | test_0489_forward | Original palette and texture pixels under moderate dust/grime, scuffs and salt runoff; some marker weathering |
| used_heavy | test_0239_reverse | Stronger grime and scratches, including partial marker degradation |
| recolor_warm | test_0489_forward | Muted brown hull, tan deck and warmer structural finishes; cyan marker unchanged |
| recolor_cool | test_0239_reverse | Blue hull, green-gray deck and cooler structural finishes; cyan marker unchanged |

The two scenario configurations exactly match the successful original-appearance controls from the previous visual-weather experiment. The near case starts 1.63 m from the boat in calm conditions. The reverse case starts 37.95 m away with 3.21 m/s mean wind and 8.95 cm waves. Four workers execute the four requested tests, with a policy-controlled MP4 for each. There is one flight per finish, so this is an exploratory screen rather than a reliability estimate.

Procedural grime is blended over existing boat texture pixels. Plain CAD surfaces get object-space texture coordinates so wear is visible there too. Wear preserves base material RGBA values, while reducing gloss. Palette changes affect selected hull/deck/platform/frame materials and preserve the cyan marker's RGBA. Wear deliberately dirties the marker as well. Physics/camera arrays, non-boat colors and non-boat textures are checked; weights and policy source remain bound to the selected bundle's hashes.

Run on the VM with a fresh output directory:

```bash
export MUJOCO_GL=egl
export LANDING_REUSE_APPROVED_RUNTIME=1
landing_training/.venv/bin/python -B -m landing_training.evaluate_boat_appearance \\
  --bundle landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json \\
  --review landing_training/outputs/diverse_review_20261010T010226Z_93857/bundle \\
  --manifest landing_training/datasets/expert/manifest.json \\
  --baseline landing_training/outputs/generalization_20261011/matrix_v1 \\
  --output landing_training/outputs/new_boat_finish_evaluation \\
  --workers 4 --instance-base 210
```

Plan, reports, native traces, input RGB snapshots and videos are retained in outputs/boat_appearance_20261011/flights_v1. The appearance extensions are separate from the original environment qualification and are not training data.

## Completed results

All four flights landed with zero unsafe outcomes: both worn finishes and both palette changes. Three material-invariance checks pass. The completion audit verifies frozen policy weights and source, unchanged base runtime/assets/checkpoints/approvals and exact matched scenario settings. No retraining was performed.

| Appearance | Outcome | First metric track, seconds | Terminal task time, seconds | Matched baseline terminal time |
|---|---|---:|---:|---:|
| used_light | landed | 0.96 | 43.24 | 42.20 |
| recolor_warm | landed | 1.00 | 41.40 | 42.20 |
| used_heavy | landed | 23.64 | 66.68 | 65.12 |
| recolor_cool | landed | 28.64 | 65.08 | 65.12 |

The cooler palette acquired metric tracking at 28.64 s versus 23.72 s for its control, but still landed at 65.08 s versus 65.12 s. A single run cannot establish whether this acquisition delay is systematic. The dirt tests include marker weathering; palette tests preserve the original cyan marker.

All four H.264 MP4s (1280x720, 25 fps) were downloaded to the Windows PC in a combined 22.724 seconds with exact SHA-256 matches. Native traces, videos, camera snapshots and comparison/preservation evidence remain in the experiment directory. Original recordings were preserved.
