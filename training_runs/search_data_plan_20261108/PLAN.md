# Search-head data plan — corrected 8 November 2026

Status: **plan only; no generation or training launched.**

This supersedes the earlier 100-episode plan. That plan incorrectly treated a
per-frame detector as if it needed flight episodes.

## What was wrong

- The search head has **45,674 parameters** and takes only the current frame.
  It has no recurrent or temporal input. A 250k-frame episode corpus was not
  justified by the model.
- `train.py` reads independent `(image, labels)` rows. It does not need PX4,
  flight dynamics, a 25 Hz recorder, or temporal sequences.
- Validation/test should be held-out **scene worlds and frames**, not ten
  episodes each.
- PX4 is only needed for the closed-loop policy benchmark, not for generating
  training images.

The runtime `SearchRuntime` has track memory and a state machine. That is
evaluation/runtime behaviour; it is not an input to the network being trained.

## Model

- Backbone: frozen R15 encoder.
- Head: `SearchHead` with `45,674` parameters:
  - spatial heatmap, offset, presence: 45,380
  - evidence: 196
  - identity: 98
- Input: one 640×360 RGB frame.
- No previous frame, no GRU, no tracker state in the head.
- Existing checkpoint: `training_runs/search_revision_20261025/output_optimized/search_best.pt`.

## Correct data unit: still frames

Use the existing `training_data_generation` renderer:

- `SceneSpec` sets map, target range, altitude, bearing, decoy layout, camera
  pan/tilt, and weather.
- `build_scene` creates a real MuJoCo scene.
- `render_rgb_seg` returns the exact 640×360 onboard RGB and segmentation.
- `search_labels` produces heat, offset, evidence, identity, ignore, presence.
- `core/weather.py` applies sun glare, haze, exposure, contrast and saturation.
- No PX4 process, no flight controller, no episode rollouts, no 25 Hz timing.

The current generator still rebuilds a scene for every image. It needs a
randomized still-frame loop that reuses a scene for many camera poses. That code
change is not made yet.

## 3,000-frame pilot

Use **3,000 independent frames** as the first test of whether this head learns
from synthetic stills:

| Split | Frames | Source |
|---|---:|---|
| Train | 2,400 | Held-in scene worlds |
| Validation | 300 | Disjoint world seeds |
| Test | 300 | Disjoint world seeds and maps |

This is a pilot/ablation, not a production dataset. It is enough to see whether
the loss and held-out detection move in the right direction. It is not enough to
claim robust search across all maps, glare and decoy conditions.

### Coverage for the pilot

Sample these as marginal quotas, not a full factorial:

- 5 maps: island, beach, city, gravel, rock
- 9 screen bins: center, four corners, four edges
- target range: 10–60 m, with a resolvable target (≥16 px)
- altitude: 3–10 m
- relative heading: 0–360°
- target visibility: full, truncated, presence-only, and deliberately rejected
- weather/glare: clear, sunlit, hazy, overcast
- decoys: 0, 2, 4, 6; similar and dissimilar
- other clutter: buoys, debris, rocks, docks
- partial target rule: never turn a present, classifiable target into background

The pilot should over-sample the hard cases: edge positions, truncated targets,
sun glare, and similar decoys. A useful starting allocation is 60% nominal,
40% edge/glare/decoy/partial cases.

## Label rule

- Positive centre and identity only when the target centre is in frame, visible
  fraction is at least 0.50, clipping is at most 0.25, hull extent is at least
  16 px, and identity is resolvable.
- Presence/evidence with no centre when the target is visible but the centre is
  outside the frame or only 0.25–0.50 visible.
- Reject frames below 0.25 visible, or too small/degraded to label.
- Never use a visible target as a negative. Reject the frame instead.
- Do not require a target in every frame; empty-water and non-target frames are
  valid negatives only when the target is genuinely absent.

## Measured cost

### Image generation

Current generator, rebuilding a scene for each image:

- 3 images in **22.6 s** = **7.5 s/image**
- 3,000 images ≈ **6.3 h**, before any speedup

With one scene built once and the camera moved:

- scene build: **3.2 s**
- render RGB + segmentation: **1.9 s/frame** (median 1.86 s)
- 3,000 frames ≈ **1.6 h** of rendering, plus scene builds
- 100 scenes × 30 poses: ~5 min builds + 1.6 h rendering

The 1.9 s/frame figure is without label computation and disk overhead; measure
the randomized generator before committing to a large run. It is already much
faster than flight collection.

### Training

Measured effective training throughput is about **106 frames/s**.

- 3,000 frames × 18 epochs ≈ **8.5 min**
- 3,000 frames × 12 epochs ≈ **5.7 min**
- 10,000 frames × 18 epochs ≈ **28 min**
- 20,000 frames × 18 epochs ≈ **57 min**
- 50,000 frames × 18 epochs ≈ **2.4 h**

### Storage

At the measured lossless RGB size of ~142 KB/frame:

- 3,000 frames ≈ **0.41 GB**
- 10,000 frames ≈ **1.35 GB**
- 20,000 frames ≈ **2.7 GB**
- 50,000 frames ≈ **6.8 GB**

Training images, not review overlays, are what matter. Do not store the
annotated/overlay copies for the full training set.

## Scale-up only after the pilot

If 3,000 frames show real held-out learning:

- 20,000 frames is a reasonable next step: ~1 h training, ~2.7 GB, and about
  10–11 h of rendering at the measured 1.9 s/frame before optimization.
- 50,000 frames is the upper useful range for this head: ~2.4 h training,
  ~6.8 GB, but ~26 h of rendering at the current rate.
- Do not jump to 250,000 frames. That was an episode-coverage number, not a
  model-capacity requirement.

## Validation and benchmark

- Per-frame validation: held-out scene worlds, all screen bins, glare and decoy
  strata. Report heat, offset, presence, evidence and identity separately.
- Do not call a 3,000-frame training loss a result. Evaluate on held-out frames
  first.
- Closed-loop benchmark still needs the simulator/PX4 path; that is the only
  place PX4 belongs. Budget roughly 3 h for the existing 60-flight comparison.
- Compare against R15's **59.3/100** and **4/10 acquisitions**; the older
  15 October policy's 63.4 is a different bundle.

No generation or training is started by this document.
