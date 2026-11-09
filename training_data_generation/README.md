# Training-data generation

New, isolated generation code for the search head and the R15 pad finder.
It reuses the existing MuJoCo scene, target boat, water/world rendering, and
label helpers. It does not modify historical generators, datasets, weights, or
the canonical scene build.

## What it produces

Each sample is one real onboard camera frame at **640x360 RGB**:

- `input.png` — exactly what the camera renders
- `overlay.png` — the network target overlaid on that input
- `annotated.png` — side-by-side input and output for visual review
- `labels.npz` — training arrays
- `metadata.json` — scene seed, range, altitude, projected centers, rule checks

### Search

- `heat`: `(45, 80)` boat-center presence
- `offset`: `(2, 45, 80)` sub-cell x/y correction
- `evidence`: `(45, 80)` class index:
  `unknown_boat`, `target_or_similar`, `different_boat`, `target_boat`
- `identity`: `(45, 80)` target-vs-different for valid cells
- `identity_valid`: `(45, 80)` valid-identity mask
- `ignore`: `(45, 80)` clipped/ambiguous-cell mask
- `presence`: scalar

Each boat also carries `label_class` (`full`, `truncated`, `presence_only`,
`overlap`, `occluded`, `ignore`), `visible_fraction`, `center_in_frame`, and
`full_bbox`. `presence_only` keeps evidence on the visible hull but emits no
heat cell; `truncated` keeps the heat at the true projected centre.

### Pad finder

- `pad_heat`: `(45, 80)` pad-center presence
- `pad_offset`: `(2, 45, 80)` sub-cell x/y correction
- `pad_presence`: scalar
- `pad_center_valid`: scalar presence label kept separate from centre validity
- `pad_ignore`: `(45, 80)` visible pad footprint when presence is true but the centre is not inferable

Presence and centre validity are independent. A centre label requires at least
60% of the projected pad pattern to be visible, in addition to an in-frame,
ray-visible centre and a resolvable extent; a corner-clipped pad keeps
presence true and masks its visible footprint instead.

Weather presets are in `core/weather.py`: `clear`, `sunlit`, `hazy`, and
`overcast`. The overlay shows the weather name and a `REVIEW ONLY` badge when
the frame is outside the training envelope. It draws the actual heat,
per-cell evidence, and ignore cells, not only boxes, so a visual review is a
review of the supervision.

The grid is the existing 8-pixel search grid. Boat labels come from the exact
MuJoCo segmentation buffer; pad labels come from the verified camera
projection and ray-visible pad probe. The RGB frame is not a screenshot of the
review view: it is the same `drone_onboard` camera used by the runtime.

## Run

From the repository root on Windows:

```powershell
python -m training_data_generation.generate_samples `
  --output datasets/training_data_generation_samples `
  --samples 2 `
  --overwrite
```

Near-range / weather set (three cases per task: very close, close,
and a half-visible boat):

```powershell
python -m training_data_generation.generate_samples `
  --output datasets/training_data_generation_near_weather `
  --profile near `
  --samples 3 `
  --overwrite
```

`--profile near` changes the wave field, wind profile, fog, light direction,
and sun-glare strength. Glare is a deterministic camera/sensor pass on the RGB
input; segmentation and label geometry are computed from the unmodified render.
Close pad views are admitted when the pad centre is visible and at least 60%
of the pattern is in frame; the pad-finder far limit is 20 m. A pad centre
with less than 60% of the pad visible is review-only (R013). A search target
is review-only when its projected bounds cover more than 75% of the frame,
not simply because the camera is near. A half-visible search target is a
measured truncated positive when at least 40% of its projected bbox is
visible and its true centre is in frame; otherwise it is presence/evidence
only or ignored. A frame that actually overfills keeps presence and masks the
whole visible hull, so it never becomes background. Eligible and review frames are written
to separate `eligible/` and `review/` directories, so a glob loader cannot
train on review-only frames.

Separate entry points:

```powershell
python -m training_data_generation.search.generate --output datasets/search_samples --samples 2
python -m training_data_generation.pad_finder.generate --output datasets/pad_finder_samples --samples 2
```

Use a fresh output directory unless `--overwrite` is explicitly intended.

## Rules

`rules/data_collection_rules.json` is the policy artifact. The still-frame
generators enforce the per-frame subset in `core/rules.py`: clearance,
search visibility/resolvability, and pad range/center validity. The JSON
remains the source of truth for dataset-level and sequence-level admission.

## Deliberate limits

- Static boat/deck placement, no moving sea state sample yet.
- The segmentation labels are offline labels, never policy inputs.
- `core/scene.py` points the existing `Environment` at a per-sample variant;
  it does not edit the canonical scene or any historical artifact.
- The overlay is review-only and is not fed to the network.
