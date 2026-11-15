# README media

| Asset | What it shows |
|---|---|
| [Hero film](../../website/assets/hero.mp4) | 45 s from one recorded Tidewater flight: launch from the moving AERODOCK, manual approach, handover with **L**, policy landing. Rendered headlessly; see [how it is made](../../tidewater-game/app/tools/hero/README.md) |
| [Tidewater landing](tidewater-landing-1080p.mp4) | Complete successful third-person landing, 1920 × 1080, 25 fps, real-time playback |
| [Animated preview](tidewater-landing-preview.gif) | Final approach and landing, 640 × 360 at 8 fps and 2× playback |
| [Poster](tidewater-landing-poster.jpg) | Frame from that flight |
| [Policy flow](policy-flow.png) | Camera, learned perception, pad geometry, controller and PX4; [SVG](policy-flow.svg) |
| [Benchmark comparison](benchmark-comparison.png) | Four policies on the current 20-mission benchmark; [SVG](benchmark-comparison.svg) |
| [Architecture](policy-architecture.png) | R15 perception, localization and flight-command flow; [SVG](policy-architecture.svg) |
| [System data flow](policy-architecture-detailed.png) | Camera, PX4 telemetry, radio, perception, geometry, flight/gimbal commands and feedback; [SVG](policy-architecture-detailed.svg) |
| [Neural architecture](policy-neural-architecture.png) | Shared encoder, spatial acquisition, recurrent pose and bounded radio fusion; [SVG](policy-neural-architecture.svg) |
| [Five-map montage](drone-policy-landing.gif) | Frozen policy landing in scenarios absent from its training data |

## Training and visual transfer

Models are trained only in the MuJoCo training environment. The montage uses
fresh review scenarios excluded from the training manifest. The Tidewater
pilot uses the same frozen policy bundle, without training on Tidewater images.

The preserved evidence is in the
[montage report](../../artifacts/cinematic_20261011/CINEMATIC_MONTAGE.md),
[montage audit](../../artifacts/cinematic_20261011/completion_audit_v2.json), and
[Tidewater pilot results](../../tidewater-game/history/tidewater_20261011/pilot_results.json).

## Tidewater recording provenance

Source: `tidewater-game/history/tidewater_20261011/policy_tidewater_windy_reef.mp4`.
The preserved `pilot_results.json` records **landed**, about 0.658 m/s median boat
speed, 3.657 m/s median wind and 41.04 s of video. Its source SHA-256 is verified
before export. The full pilot report retains its failed flight as well.

This is the historical frozen `policy_bundle_v5`, **not R15 or the new search
head**. Tidewater's actual onboard render drove the original closed-loop flight.
The spectator view was originally rendered at 640 × 360 and archived at
1280 × 720. The README MP4 uses Lanczos upscale to 1920 × 1080; it is not a native
1080p render. No new flight or generated/interpolated motion was used.

[Export receipt and hashes](tidewater-landing-provenance.json).

## Regenerate

Current figures (policy flow and benchmark comparison), from `benchmark/benchmark.json`:

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
