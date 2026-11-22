# README media

| Asset | What it shows |
|---|---|
| [Hero film](../../website/assets/hero.mp4) | 45 s from one recorded flight in the realistic simulator: launch from the moving AERODOCK, manual approach, handover with **L**, policy landing. Rendered headlessly; see [how it is made](../../tidewater-game/app/tools/hero/README.md) |
| [Boat under way](tidewater-boat-1080p.mp4) | 5 s of the AERODOCK under way, seen from off its port bow, 1920 × 1080, 30 fps. Rendered from a recorded simulation run with the [hero-film tools](../../tidewater-game/app/tools/hero/README.md) (`boatFront` shot) |
| [Animated preview](tidewater-boat-preview.gif) | The same 5 s, 640 × 360 at 12 fps |
| [Poster](tidewater-boat-poster.jpg) | Frame from that clip |
| [Landing flow](landing-flow.png) | The flight in five steps, split into the search-head phase and precision landing; [SVG](landing-flow.svg) |
| [Training story](training-story.png) | Four design steps with their benchmark results; [SVG](training-story.svg) |
| [Policy flow](policy-flow.png) | Camera, learned perception, pad geometry, controller and PX4; [SVG](policy-flow.svg) |
| [Benchmark comparison](benchmark-comparison.png) | Five policies, including the final version, on the 20-mission benchmark; [SVG](benchmark-comparison.svg) |
| [Final system](final-system.png) | Final version: camera, encoder, search head, main network, control code, PX4; [SVG](final-system.svg) |
| [Final networks](final-networks.png) | Inside the two networks of the final version; [SVG](final-networks.svg) |
| [Architecture](policy-architecture.png) | R15 perception, localization and flight-command flow; [SVG](policy-architecture.svg) |
| [System data flow](policy-architecture-detailed.png) | R15 (history): camera, PX4 telemetry, radio, perception, geometry, flight/gimbal commands and feedback; [SVG](policy-architecture-detailed.svg) |
| [Neural architecture](policy-neural-architecture.png) | R15 (history): shared encoder, spatial acquisition, recurrent pose and bounded radio fusion; [SVG](policy-neural-architecture.svg) |
| [Five-map montage](drone-policy-landing.gif) | October 2026 policy (before R15) landing in scenarios absent from its training data |

## Training and visual transfer

Models are trained only in the MuJoCo training environment. The montage uses
fresh review scenarios excluded from the training manifest. The pilot in the
realistic simulator uses the same frozen policy bundle, without training on its
images.

The preserved evidence is in the
[montage report](../../artifacts/cinematic_20261011/CINEMATIC_MONTAGE.md),
[montage audit](../../artifacts/cinematic_20261011/completion_audit_v2.json), and
[realistic-simulator pilot results](../../tidewater-game/history/tidewater_20261011/pilot_results.json).

## Provenance of the earlier landing recording

Source: `tidewater-game/history/tidewater_20261011/policy_tidewater_windy_reef.mp4`.
The preserved `pilot_results.json` records **landed**, about 0.658 m/s median boat
speed, 3.657 m/s median wind and 41.04 s of video. Its source SHA-256 is verified
before export. The full pilot report retains its failed flight as well.

This is the historical frozen `policy_bundle_v5`, **not R15 or the new search
head**. The realistic simulator's actual onboard render drove the original
closed-loop flight.
The spectator view was originally rendered at 640 × 360 and archived at
1280 × 720. The README MP4 uses Lanczos upscale to 1920 × 1080; it is not a native
1080p render. No new flight or generated/interpolated motion was used.

[Export receipt and hashes](tidewater-landing-provenance.json).

## Regenerate

Current figures (policy flow and benchmark comparison), from `benchmark/benchmark.json`
and `benchmark/evidence/final/summary.json`:

```sh
python -B docs/tools/build_current_figures.py
node docs/tools/rasterize_svg.mjs
```

Earlier R15 figures and the landing video:

From the repository root, with Python 3, Pillow and FFmpeg installed:

```sh
python -B docs/tools/build_readme_assets.py
python -B docs/tools/export_landing_demo.py
```

Both scripts use CPU only; FFmpeg is limited to one thread. The benchmark image
reads the completed `summary.json` in `benchmark/reports/2026-10-25/`.
It does not rerun, rescore or modify the original benchmark. Original media,
experiment bundles, data and checkpoints remain unchanged.

Architecture and benchmark figures have matching PNG and SVG exports. Their
source references are the R15 runtime in
`artifacts/landing_hardening_20261018/candidate_r15/` and the preserved benchmark
summary. Detailed model dimensions and score definitions live in the training
and benchmark guides.

To regenerate only the two detailed training figures, preserving the root
figures, run `python -B docs/tools/build_readme_assets.py --detail-only`.

Use `python -B docs/tools/export_landing_demo.py --preview-only` to refresh the
preview and receipt while retaining the completed MP4. The preview starts at
16 seconds; the MP4 retains all 41.04 seconds of the source flight.
