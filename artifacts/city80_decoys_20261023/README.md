# 80 m search, find and land with six false boats

The clip in `episode_80m/` was not a search: the takeoff preparation aimed the
gimbal at the boat and the 1 Hz position beacon told the teacher exactly where
it was, so frame 0 already contained the target and the aircraft flew straight
in. This directory now holds a flight where neither is true.

**Clip:** `episode_search_v2/review.mp4` (119 s, 960x420, 25 fps).

## What makes this a search

| | previous clip | this clip |
|---|---|---|
| First frame | target centred, 80 m out | **target 89.7 deg off-axis, not in frame** (asserted on the render) |
| Position of the boat | 1 Hz beacon fix | **no position fix at all**; only a one-bit dock-ready flag |
| Path before the boat is known | straight in | 2 search legs, 55.7 m flown, 51.4 s |
| Find criterion | first visibility | centred sighting inside 55 m (identification, not a frame-edge speck) |
| What it sees first | the target | a false boat 26 deg off the nose at launch |

The flight is still flown by the stock `landing_training.expert.Expert`. A
review-only `SearchDirector` owns the aircraft only while the boat is unknown;
it follows a declared search sector and hands over the moment the teacher's own
pad-visibility gate confirms a centred, close sighting. The teacher then flies
its unchanged approach, match, descent and touchdown.

## Geometry

Frame: `u` runs from the target pad towards the 80 m start, `v` is 90 deg left.

- Start `(80, 0)`, nose along `+v` (broadside), camera forward, 18 deg down.
- Search leg 1: `(80, 0) -> (80, 40)`, camera sweeping +/-30 deg, t = 0-19.6 s.
- Search leg 2: `(80, 40) -> (50, 50)`, t = 19.6-35.2 s.
- Turn-in: yaw onto the boat, close at 1.2 m/s, t = 35.2-51.4 s.
- Lock: **t = 51.44 s, 54.72 m, heading error 0.0 deg, 55.7 m searched**.
- Approach 29.7 s, descend 30.5 s, touchdown, disarm. Outcome `landed`.

Six static decoys (`decoys.json`) sit on and beside the search legs and the
turn-in corridor: three similar white hulls (two with masts) and three
dissimilar red/navy/orange hulls. Each is checked to be >= 6 m from the final
corridor, >= 6 m from every search lane, >= 8 m from the pad, >= 5 m from land,
>= 6 m from every other decoy, and all are >= 1.8 m tall at most, so the 6 m
search altitude clears them.

The scene is rebuilt from the current `landing_training.scene` by
`build_scene.py`, which also evaluates the first-frame camera geometry on the
built model and refuses to write a scene in which the target is already visible.

## Why the earlier clip took so long

That run was in WSL, which has no GPU (`/dev/dri` absent), so MuJoCo rendered
two 1280x720 views per frame with llvmpipe at about 1.4 s/frame. A 120 s episode
is 3000 frames, and the aborted 180 s attempt alone was heading past an hour.

This run is Windows-native: the repo's existing Windows PX4 (the same pinned
PX4 build in Node/WebAssembly) drives the physics, and the single 640x360
onboard view renders on the RTX 2060. Measured: **2975 frames in 669 s wall,
4.45 fps**, including 80 s of PX4 startup and preparation. Re-encoding a
corrected overlay from the recording took 40 s and did not re-fly anything.

## Files

- `HANDOFF.md` - state, paths and open items for the next agent.
- `scene_spec.py` - scenario, decoy table, search legs.
- `search_geometry.py` - shared pad frame and start heading.
- `build_scene.py` - builds and validates `scene.xml` / `scene.mjb`, writes `decoys.json`.
- `run_search_land.py` - Windows flight: PX4 WASM, GPU renderer, search director, teacher.
- `render_video.py` / `video_overlay.py` - offline re-encode of a recorded episode.
- `plot_search_plan.py` / `search_plan_topdown.png` - top-down plan of the built scene.
- `episode_search_v2/` - `review.mp4`, `steps.jsonl`, `observations.h5`, `summary.json`,
  `initial_view_actual.jpg`, `stills/`.
- `episode_80m/` - the superseded straight-in clip, kept for comparison.

Re-run (Windows Python 3.12, from this directory):

```
python build_scene.py
python run_search_land.py --out episode_search_v3
python render_video.py episode_search_v3
```

## Scope

The search pattern and the find criterion are declared mission logic, reviewed
here for behaviour and geometry. Target lock uses the teacher's pad-visibility
sensor, not a trained RGB detector, so this is not evidence about recognition
performance. The trained observable actor from `review_v61` is a separate
pipeline; nothing here changes it.
