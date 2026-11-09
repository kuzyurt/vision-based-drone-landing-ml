"""Time each per-frame stage of the still-frame generator at several ranges.

Rendering was measured at ~0.05 s/frame, so a 40-frame scene should take a few
seconds. This separates pose, RGB render, segmentation render, label build and
PNG/NPZ write to show which stage actually dominates.
"""
from __future__ import annotations

import dataclasses
import statistics
import sys
import tempfile
import time
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from landing_training.expert import camera_projection, pad_visibility  # noqa: E402
from training_data_generation.core.geometry import pad_projected_extent  # noqa: E402
from training_data_generation.core.labels import search_labels  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, _set_drone_pose, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR, apply_camera_weather  # noqa: E402
from training_runs.search_frames_20261108.generate import _keep_decoys  # noqa: E402

REPEATS = 4
DISTANCES = (2.0, 4.0, 8.0, 12.0, 30.0)
LABEL_PARAMS = dict(min_extent_px=16, min_visible_fraction=0.50, max_clipped_fraction=0.25)


def main() -> None:
    base_spec = SceneSpec(
        seed=20261108 + 771, map_kind="island", distance_m=7.0, height_m=3.5,
        bearing_deg=18.0, decoy_layout=(), camera_pan_deg=0.0,
        camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR,
    )
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="profile_cost_") as temporary:
        env, model, groups = build_scene(base_spec, Path(temporary) / "variant")
        groups = _keep_decoys(env, model, groups, 0, np.random.default_rng(77))
        build_s = time.perf_counter() - started
        renderer = AnnotatableRenderer(env)
        work = Path(temporary) / "out"
        work.mkdir()
        try:
            print(f"scene build: {build_s:.2f} s\n")
            print(f"{'dist':>6} {'pose':>7} {'rgb':>7} {'seg':>7} {'labels':>8} {'write':>7} {'total':>8} {'mask px':>8}")
            for distance in DISTANCES:
                spec = dataclasses.replace(base_spec, distance_m=distance)
                stages = {k: [] for k in ("pose", "rgb", "seg", "labels", "write")}
                mask_px = 0
                for i in range(REPEATS):
                    t0 = time.perf_counter()
                    _set_drone_pose(env, spec)
                    mujoco.mj_forward(env.model, env.data)
                    t1 = time.perf_counter()
                    rgb = np.asarray(renderer.onboard_image()).copy()
                    t2 = time.perf_counter()
                    renderer.onboard.enable_segmentation_rendering()
                    try:
                        seg = np.asarray(renderer.onboard_image()).copy()
                    finally:
                        renderer.onboard.disable_segmentation_rendering()
                    t3 = time.perf_counter()
                    rgb = apply_camera_weather(rgb, env, spec.weather)
                    pad_pixels, pad_depth = camera_projection(env, env.pad_position)
                    pad_pixel = pad_pixels[0] if len(pad_pixels) else np.array([np.nan, np.nan])
                    pad_depth_value = float(pad_depth[0]) if len(pad_depth) else float("nan")
                    pad_visible, _ = pad_visibility(env)
                    pad_extent = pad_projected_extent(env, pad_depth_value) if np.isfinite(pad_depth_value) else 0.0
                    labels = search_labels(env, seg, groups, pad_pixel, bool(pad_visible),
                                           pad_extent_px=pad_extent, **LABEL_PARAMS)
                    t4 = time.perf_counter()
                    mask_px = int(np.isin(seg[..., 0], np.asarray(groups["target"])).sum())
                    Image.fromarray(rgb, mode="RGB").save(work / f"{distance}_{i}.png",
                                                          format="PNG", compress_level=1)
                    np.savez_compressed(work / f"{distance}_{i}.npz",
                                        heat=labels["heat"].astype(np.float32),
                                        offset=labels["offset"].astype(np.float32),
                                        evidence=labels["evidence"].astype(np.int16),
                                        identity=labels["identity"].astype(np.int16),
                                        identity_valid=labels["identity_valid"].astype(bool),
                                        ignore=labels["ignore"].astype(bool))
                    t5 = time.perf_counter()
                    for key, value in zip(stages, (t1 - t0, t2 - t1, t3 - t2, t4 - t3, t5 - t4)):
                        stages[key].append(value * 1000)
                med = {k: statistics.median(v) for k, v in stages.items()}
                total = sum(med.values())
                print(f"{distance:6.0f} {med['pose']:7.1f} {med['rgb']:7.1f} {med['seg']:7.1f} "
                      f"{med['labels']:8.1f} {med['write']:7.1f} {total:8.1f} {mask_px:8d}")
        finally:
            renderer.close()
    print("\nAll values are milliseconds per frame, median of "
          f"{REPEATS}. 'write' is PNG + NPZ.")


if __name__ == "__main__":
    main()
