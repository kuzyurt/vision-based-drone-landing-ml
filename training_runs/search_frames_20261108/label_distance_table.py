"""Tabulate the boat label a frame gets, by range, under both labelling rules.

Two independent rules produced the training labels:

* October 20261025 -- ``landing_training/privileged_teacher.py::BoatView``.
  Hard ``range_m > 35`` cutoff, ``pixels >= 80``, ``extent_px >= 24``, and a
  visible pad of at least 6 px before ``target_boat`` is allowed.
* 3k stills 20261108 -- ``training_data_generation/core/labels.py::search_labels``.
  No range cutoff. ``extent_px >= 16`` for a heat cell, ``extent_px >= 24`` plus
  a visible pad of at least 10 px for ``target_boat``, and a frame-coverage cap.

Both are evaluated on the same rendered frame at each range, so the table is a
direct like-for-like comparison rather than a restatement of the constants.
"""
from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
from pathlib import Path

import mujoco
import numpy as np

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

OUT = REPO / "training_runs/search_frames_20261108/output/3k"
TABLE_MD = OUT / "label_distance_table.md"
TABLE_JSON = OUT / "label_distance_table.json"

DISTANCES = (2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 15, 18, 20, 25, 30, 33, 35, 36, 40, 45, 48)
CURRENT_PARAMS = dict(min_extent_px=16, min_visible_fraction=0.50, max_clipped_fraction=0.25)


def october_rule(range_m, pixels, extent_px, pad_visible, pad_extent_px, truth="target"):
    """Mirror of BoatView.evidence, blocker included for the table."""
    if not (pixels >= 24 and extent_px >= 8):
        return "not_resolved", "pixels<24 or extent<8"
    if range_m > 35:
        return "unknown_boat", "range > 35 m"
    if pixels < 80:
        return "unknown_boat", "pixels < 80"
    if extent_px < 24:
        return "unknown_boat", "extent < 24 px"
    if truth == "target":
        if pad_visible and pad_extent_px >= 6:
            return "target_boat", "ok"
        return "target_or_similar", "pad missing or < 6 px"
    return "different_boat", "ok"


def current_blocker(target, extent_px, pixels):
    if target is None:
        return "no target record"
    if target["too_close"]:
        return target["too_close_reason"] or "too close"
    if target["label_class"] == "presence_only":
        return "centre off-frame"
    if target["label_class"] not in ("full", "truncated"):
        if extent_px < 16:
            return "extent < 16 px"
        if float(target["visible_fraction"]) < 0.50:
            return "visible < 50%"
        if float(target["clipped_fraction"]) > 0.25:
            return "clipped > 25%"
        if not target["center_in_frame"]:
            return "centre off-frame"
        return "unlabelled"
    if target["evidence"] == "target_boat":
        return "ok"
    if extent_px < 24:
        return "identity extent < 24 px"
    if not target.get("pad_visible"):
        return "pad not visible"
    if float(target.get("pad_extent_px") or 0.0) < 10.0:
        return "pad < 10 px"
    return "ok"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base_spec = SceneSpec(
        seed=20261108 + 771,
        map_kind="island",
        distance_m=14.0,
        height_m=3.5,
        bearing_deg=18.0,
        decoy_layout=(),
        camera_pan_deg=0.0,
        camera_tilt_offset_deg=0.0,
        yaw_offset_deg=0.0,
        weather=CLEAR,
    )
    rows = []
    with tempfile.TemporaryDirectory(prefix="label_table_") as temporary:
        env, model, groups = build_scene(base_spec, Path(temporary) / "variant")
        groups = _keep_decoys(env, model, groups, 0, np.random.default_rng(77))
        renderer = AnnotatableRenderer(env)
        try:
            for distance in DISTANCES:
                spec = dataclasses.replace(base_spec, distance_m=float(distance))
                _set_drone_pose(env, spec)
                mujoco.mj_forward(env.model, env.data)
                renderer.onboard.enable_segmentation_rendering()
                try:
                    seg = np.asarray(renderer.onboard_image()).copy()
                finally:
                    renderer.onboard.disable_segmentation_rendering()

                ids = groups["target"]
                mask = np.isin(seg[..., 0], np.asarray(ids, dtype=np.int64)) & (
                    seg[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM)
                )
                pixels = int(mask.sum())
                ys, xs = np.nonzero(mask)
                if len(xs):
                    extent_px = int(max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))
                else:
                    extent_px = 0

                pad_pixels, _ = camera_projection(env, env.pad_position)
                pad_pixel = pad_pixels[0] if len(pad_pixels) else np.array([np.nan, np.nan])
                pad_visible, projected = pad_visibility(env)
                p = np.asarray(projected, dtype=float)
                october_pad_extent = (
                    float(min(np.ptp(p[:, 0]), np.ptp(p[:, 1]))) if len(p) else 0.0
                )
                depth = float(np.linalg.norm(env.data.cam_xpos[env.model.camera("drone_onboard").id]
                                             - env.pad_position))
                current_pad_extent = pad_projected_extent(env, depth) if np.isfinite(depth) else 0.0
                range_m = float(np.linalg.norm(env.drone.position[:2] - env.pad_position[:2]))

                labels = search_labels(
                    env, seg, groups, pad_pixel, bool(pad_visible),
                    pad_extent_px=current_pad_extent, **CURRENT_PARAMS,
                )
                target = labels.get("target")

                oct_class, oct_why = october_rule(
                    range_m, pixels, extent_px, bool(pad_visible), october_pad_extent
                )
                cur_class = target["evidence"] if target else "absent"
                cur_label = (target or {}).get("label_class", "absent")
                cur_why = current_blocker(target, extent_px, pixels)

                rows.append(dict(
                    distance_m=int(distance),
                    range_m=round(range_m, 2),
                    boat_pixels=pixels,
                    boat_extent_px=extent_px,
                    pad_visible=bool(pad_visible),
                    october_pad_extent_px=round(october_pad_extent, 1),
                    current_pad_extent_px=round(float(current_pad_extent), 1),
                    october=dict(evidence=oct_class, blocker=oct_why),
                    current=dict(label_class=cur_label, evidence=cur_class, blocker=cur_why),
                ))
        finally:
            renderer.close()

    header = (
        "| range | boat px | extent px | pad px (oct/cur) | Oct 25 teacher | why | 3k stills | why |\n"
        "|---:|---:|---:|---:|---|---|---|---|\n"
    )
    body = "".join(
        f"| {r['distance_m']} m | {r['boat_pixels']} | {r['boat_extent_px']} | "
        f"{r['october_pad_extent_px']:.1f} / {r['current_pad_extent_px']:.1f} | "
        f"**{r['october']['evidence']}** | {r['october']['blocker']} | "
        f"**{r['current']['evidence']}** | {r['current']['blocker']} |\n"
        for r in rows
    )
    notes = (
        "\n## Why the October head answers `target_or_similar`\n\n"
        "* Its teacher refused every identity claim beyond **35 m** (`unknown_boat`).\n"
        "* Between ~20 m and 35 m the pad drops under **6 px**, so the teacher emitted\n"
        "  `target_or_similar` while the boat itself was still easy to see and owned a heat cell.\n"
        "* `identity_supervision_valid` is true only for `target_boat` / `different_boat`,\n"
        "  so those mid-range frames contributed no identity gradient at all.\n"
        "* At inference `decode()` additionally demotes `target_boat` to `target_or_similar`\n"
        "  unless `identity_threshold` 0.98 is met, which is a very high bar.\n\n"
        "The 3k rule has no range cutoff and a lower pad bar (10 px), so it keeps teaching\n"
        "`target_boat` closer in, where the October rule had already given up.\n"
    )
    TABLE_MD.write_text(header + body + notes, encoding="utf-8")
    TABLE_JSON.write_text(json.dumps(dict(rows=rows), indent=2) + "\n", encoding="utf-8")
    print(header + body)
    print(notes)


if __name__ == "__main__":
    main()
