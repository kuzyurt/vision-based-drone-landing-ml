# Handoff — city80 search / find / land review scene

**24 Oct update:** the current simulator-assisted, visibility-gated no-radio
teacher is `landing_training/privileged_teacher.py`. Its experiment entry is
`artifacts/teacher_scan_modes_20261024/run_privileged_review.py`; see
`artifacts/teacher_scan_modes_20261024/PRIVILEGED_TEACHER.md` for the rules.
It uses the same physical decoy scene, 85m target and random yaw/pan/tilt,
with no neural detector. The original `SearchDirector` flight and the notes
below are historical; they are not the current search implementation.

State as of 24 Oct 2026. Everything lives in
`artifacts/city80_decoys_20261023/` unless stated otherwise. Nothing in
`landing_training/` was edited for this work.

## Deliverable

`episode_search_v2/review.mp4` — 119 s, 960x420, 25 fps, 2975 frames, 8.9 MB.

80 m target, six static false boats. Frame 0 has the target 89.7 deg off-axis
and outside the camera; no position beacon. Two search legs (55.7 m, 51.4 s),
turn-in, visual lock at 54.72 m, approach, descent, touchdown, PX4 disarm.
Outcome `landed`.

## Important files (created)

| path | role |
|---|---|
| `README.md` | the main explainer: what changed vs the old clip, geometry, timing |
| `HANDOFF.md` | this file |
| `scene_spec.py` | scenario (`Scenario80`), 6 decoys, search legs, start heading fields |
| `search_geometry.py` | shared pad frame (u/v), start heading, segment distance |
| `build_scene.py` | rebuilds `scene.xml`/`scene.mjb`, validates decoy clearances, writes `decoys.json`, asserts the target is not visible in frame 0 |
| `decoys.json` | scene manifest: scenario, decoy table, lane clearances, search plan, first-frame geometry, SHA256 |
| `scene.xml`, `scene.mjb` | built model, 52 bodies. **`.mjb` is 522 MB — do not commit** |
| `plot_search_plan.py`, `search_plan_topdown.png` | top-down plan drawn from the built scene |
| `run_search_land.py` | Windows flight harness: PX4 WASM, GPU onboard renderer, `SearchDirector`, stock `Expert` |
| `video_overlay.py` | single review canvas (960x420) + `SearchVideo` H.264 writer |
| `render_video.py` | offline re-encode from `steps.jsonl` + `observations.h5`, no re-flight |
| `run_search.log`, `run_search_v2.log` | raw flight logs incl. `target_locked` event |

## Recorded episode

`episode_search_v2/`

- `review.mp4` — the deliverable; `review.receipt.json` has frame count and byte size.
- `steps.jsonl` — one row per frame: observation, executed action, diagnostics
  (`control_phase`, `actual_command_owner`, `search_flown_m`, `pad_visible`), privileged block.
- `observations.h5` — 640x360 RGB per frame (~880 MB) plus the serialized rows.
- `summary.json` — outcome, phase counts, lock record, initial-view record, wall time, fps.
- `initial_view_actual.jpg` — the actual first frame, no overlay (target absent).
- `stills/search_{0,20,40,52,75,100}s.jpg` — frames pulled for review.
- `terminal.jpg`, `px4/` (PX4 runtime dir and parameters/logs).

`episode_80m/` is the **superseded** straight-in clip. It is kept only for
comparison; it is not the deliverable and its behaviour is the thing being fixed.

## Changed / removed

- `scene_spec.py` and `build_scene.py` were rewritten: broadside start heading,
  two new search legs, confirm gate, first-frame visibility assertion, lane checks.
- `run_expert.py` was deleted (it flew the old straight-in behaviour).
- Regenerated build cache: `landing_training/build/combined_1000us.{xml,mjb}`
  (gitignored via `landing_training/.gitignore: build/`).
- `decoys_topdown.png` (old layout) was deleted and replaced by
  `search_plan_topdown.png`.

## Reused read-only (do not edit for this task)

- `landing_training/expert.py` — stock teacher: search/reacquire/approach/descend/touchdown.
- `landing_training/environment.py`, `scene.py`, `recording.py`, `run_episode.py`, `rendering.py`.
- `artifacts/local_curriculum_20261020/windows_px4_v2.py` — pinned PX4 in Node/WebAssembly.
- `artifacts/local_curriculum_20261020/px4_windows_bridge_v2.mjs` — Node bridge (requires
  `tidewater-game/app/public/landing/wasm/px4.{mjs,wasm}`).
- `artifacts/local_curriculum_20261020/windows_renderer.py`, `fast_physics_windows.py`,
  `windows_kernels.py`, `physics_math.dll`, `review_helpers.py`, `local_paths.py`.
- `artifacts/local_curriculum_20261020/sources/target_learning/scenes.py` — `add_boat`
  and `annotation_groups`.

## Environment

Windows-native, **not WSL** (WSL has no GPU: llvmpipe rendered two 1280x720 views
at ~1.4 s/frame and made a 120 s clip take ~24 min, with earlier attempts over an hour).

- `C:\Users\gamee\AppData\Local\Programs\Python\Python312\python.exe` — Python 3.12.9,
  mujoco 3.14.0, numpy 2.2.6, torch 2.6.0+cu124 (CUDA available), matplotlib 3.10.6, h5py.
- Node v22.23.2 on PATH; the PX4 bridge opens ports 4560/18000/19000 + `--instance`.
  **Run one flight at a time.**
- Measured: 2975 frames in 669 s wall = 4.45 fps, including ~80 s PX4 startup and
  preparation. Rendering is one 640x360 onboard view on the RTX 2060.

## Reproduce

From `artifacts/city80_decoys_20261023/`, on Windows Python:

```
python build_scene.py
python run_search_land.py --out episode_search_v3      # ~11 min, writes review.mp4 live
python render_video.py episode_search_v3               # optional re-encode, ~40 s
```

`run_search_land.py` refuses to overwrite an existing output directory.
`--probe-seconds N` stops early (used for 12 s smoke tests); `--no-video` skips encoding.

## Verified

- `summary.json`: `outcome=landed`, 2975 rows, `initial_view.pad_visible=false` at 79.99 m.
- Lock event: `task_time_s=51.44`, `range_m=54.72`, `heading_error_deg=0.0`,
  `flown_search_m=55.7`.
- Phase counts: sweep1 489, sweep2 391, turn-in 406, approach 743, match 33,
  descend 763, touchdown 97, confirm 52.
- `ffprobe`: 2975 frames, 119.0 s, 960x420, 25 fps.
- Live overlay path (`SearchVideo`) smoke-tested for 12 s after the fix; the shipped
  v2 video was re-encoded offline from its own recorded rows (same pixels, corrected overlay).

## Known limits / open items

- `Scenario80` extends only the production 60 m distance cap to 80 m for review;
  all other `Scenario.validate()` rules still apply.
- Target boat is stationary (`boat_speed=0`) so the 80 m geometry and static decoys
  stay valid. Decoys are static mocap props, not policy inputs.
- The search pattern and the "centred sighting within 55 m" identification rule are
  **declared mission logic**. Target lock uses the teacher's pad-visibility raycast,
  not a trained RGB detector: this is not evidence about recognition performance.
- `pad_visibility` is a ground-truth geometric gate; the overlay marks range as `(eval)`.
- Only the onboard camera is recorded; there is no external chase view in the video.
- The trained v61 observable actor (`artifacts/local_curriculum_20261020/run_windows_review_v61.py`)
  was not run on this scene. Doing so, without the declared sweep, is the natural next test.
- Nothing here is committed. `scene.mjb` (522 MB) and `observations.h5` (880 MB) should
  stay out of git; the scripts and `decoys.json` are small enough to add if wanted.
