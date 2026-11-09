"""Render a distance ladder (2-8 m, then 10-48 m) with the dataset output view.

The labels use the same parameters as the 3k still-frame dataset
(``min_extent_px=16``, ``min_visible_fraction=0.50``,
``max_clipped_fraction=0.25``) so what is drawn is exactly what a training
sample at that range would contain. Nothing is trained here.
"""
from __future__ import annotations

import dataclasses
import json
import statistics
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from landing_training.expert import camera_projection, pad_visibility  # noqa: E402
from training_data_generation.core.geometry import pad_projected_extent  # noqa: E402
from training_data_generation.core.labels import search_labels  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, _set_drone_pose, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR, apply_camera_weather  # noqa: E402
from training_runs.search_frames_20261108 import visualize_comparison as vis  # noqa: E402
from training_runs.search_frames_20261108.generate import _keep_decoys  # noqa: E402

OUT = REPO / "training_runs/search_frames_20261108/output/3k"
SHEET = OUT / "distance_ladder_2_8m.png"
DATA = OUT / "distance_ladder.json"

NEAR = (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
FAR = (10.0, 12.0, 15.0, 18.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 48.0)

PANEL_W, PANEL_H = vis.PANEL_W, vis.PANEL_H
LABEL_W, GAP = 250, 8
HEADER_H = 62
ROW_H = PANEL_H + 30
COLS = 2
WIDTH = LABEL_W + COLS * PANEL_W + (COLS + 1) * GAP
HEIGHT = HEADER_H + len(NEAR) * ROW_H + 150

# The 3k dataset's label parameters, mirrored from generate.py::_render_labels.
LABEL_PARAMS = dict(min_extent_px=16, min_visible_fraction=0.50, max_clipped_fraction=0.25)


def render_at(env, renderer, base_spec: SceneSpec, groups: dict, distance: float):
    spec = dataclasses.replace(base_spec, distance_m=float(distance))
    _set_drone_pose(env, spec)
    import mujoco

    mujoco.mj_forward(env.model, env.data)
    rgb = np.asarray(renderer.onboard_image()).copy()
    renderer.onboard.enable_segmentation_rendering()
    try:
        seg = np.asarray(renderer.onboard_image()).copy()
    finally:
        renderer.onboard.disable_segmentation_rendering()
    rgb = apply_camera_weather(rgb, env, spec.weather)
    pad_pixels, pad_depth = camera_projection(env, env.pad_position)
    pad_pixel = pad_pixels[0] if len(pad_pixels) else np.array([np.nan, np.nan])
    pad_depth_value = float(pad_depth[0]) if len(pad_depth) else float("nan")
    pad_visible, _ = pad_visibility(env)
    pad_extent = pad_projected_extent(env, pad_depth_value) if np.isfinite(pad_depth_value) else 0.0
    labels = search_labels(
        env,
        seg,
        groups,
        pad_pixel,
        bool(pad_visible),
        pad_extent_px=pad_extent,
        **LABEL_PARAMS,
    )
    return rgb, labels


def record(distance: float, labels: dict) -> dict:
    target = labels.get("target")
    if target is None:
        return dict(distance_m=distance, present=False, label_class="absent", evidence="absent")
    return dict(
        distance_m=distance,
        present=True,
        extent_px=int(target["extent_px"]),
        full_extent_px=int(target["full_extent_px"]),
        visible_fraction=round(float(target["visible_fraction"]), 4),
        frame_coverage=round(float(target["frame_coverage"]), 4),
        clipped=bool(target["clipped"]),
        center_in_frame=bool(target["center_in_frame"]),
        too_close=bool(target["too_close"]),
        too_close_reason=target.get("too_close_reason"),
        label_class=target["label_class"],
        evidence=target["evidence"],
        identity_valid=bool(target["identity_valid"]),
        pad_visible=target.get("pad_visible"),
        pad_extent_px=None if target.get("pad_extent_px") is None else round(float(target["pad_extent_px"]), 2),
        heat=round(float(np.max(labels["heat"])), 3),
        presence=round(float(labels["presence"]), 3),
        center_px=[round(float(v), 1) for v in target["center_px"]],
        visible_bbox=[int(v) for v in target["bbox"]],
    )


def panel_with_bbox(rgb, labels, color):
    panel = vis.render_panel(
        rgb, labels["heat"], [], color,
        target_px=(labels.get("target") or {}).get("center_px"), teacher=True,
    )
    target = labels.get("target")
    if target is not None:
        sx, sy = PANEL_W / 640.0, PANEL_H / 360.0
        x0, y0, x1, y1 = target["bbox"]
        draw = ImageDraw.Draw(panel)
        draw.rectangle(
            [int(x0 * sx), int(y0 * sy), max(int(x0 * sx) + 1, int(x1 * sx)), max(int(y0 * sy) + 1, int(y1 * sy))],
            outline=color, width=2,
        )
    return panel


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
    near_rows = []
    with tempfile.TemporaryDirectory(prefix="distance_ladder_") as temporary:
        env, model, groups = build_scene(base_spec, Path(temporary) / "variant")
        groups = _keep_decoys(env, model, groups, 0, np.random.default_rng(77))
        renderer = AnnotatableRenderer(env)
        try:
            for distance in NEAR:
                rgb, labels = render_at(env, renderer, base_spec, groups, distance)
                near_rows.append((rgb, labels, record(distance, labels)))
            far_rows = []
            for distance in FAR:
                rgb, labels = render_at(env, renderer, base_spec, groups, distance)
                far_rows.append(record(distance, labels))
        finally:
            renderer.close()

    figure = Image.new("RGB", (WIDTH, HEIGHT), vis.BG)
    draw = ImageDraw.Draw(figure)
    draw.text((16, 18), "Distance ladder 2-8 m: what the dataset view would look like", font=vis.FONT_TITLE, fill=vis.TEXT)
    for col, header in enumerate(("INPUT FRAME", "DATASET VIEW (teacher heat + hull box)")):
        x = LABEL_W + GAP + col * (PANEL_W + GAP)
        draw.text((x + 4, HEADER_H - 22), header, font=vis.FONT_HEADER, fill=vis.MUTED)

    for row, (rgb, labels, info) in enumerate(near_rows):
        top = HEADER_H + row * ROW_H
        y = top + 16
        into = bool(info.get("too_close"))
        color = vis.GREEN if info["label_class"] in ("full", "truncated") else (vis.ORANGE if into else vis.MUTED)
        draw.text((14, y), f"{info['distance_m']:.0f} m", font=vis.FONT_CASE, fill=color)
        draw.text((14, y + 28), f"{info['label_class']} / {info['evidence']}", font=vis.FONT_SMALL, fill=vis.TEXT)
        draw.text((14, y + 45), f"{info['extent_px']} px extent", font=vis.FONT_SMALL, fill=vis.MUTED)
        draw.text((14, y + 62), f"{info['visible_fraction']:.0%} visible", font=vis.FONT_SMALL, fill=vis.MUTED)
        draw.text((14, y + 79), f"{info['frame_coverage']:.0%} of frame", font=vis.FONT_SMALL, fill=vis.MUTED)
        if info.get("too_close_reason"):
            reason = info["too_close_reason"].split(",")[0]
            draw.text((14, y + 96), reason[:34], font=vis.FONT_PANEL_SMALL, fill=vis.ORANGE)

        panels = (
            Image.fromarray(rgb).resize((PANEL_W, PANEL_H), Image.Resampling.BILINEAR),
            panel_with_bbox(rgb, labels, vis.GREEN),
        )
        for col, panel in enumerate(panels):
            x = LABEL_W + GAP + col * (PANEL_W + GAP)
            figure.paste(panel, (x, top))
            draw.rectangle([x, top, x + PANEL_W - 1, top + PANEL_H - 1], outline=(65, 70, 82), width=1)

    legend_y = HEADER_H + len(NEAR) * ROW_H + 10
    draw.text((16, legend_y), "Label parameters are the 3k dataset's: min extent 16 px, identity extent 24 px, min visible 50%, max clipped 25%, max frame coverage 75%.",
              font=vis.FONT_SMALL, fill=vis.MUTED)
    draw.text((16, legend_y + 18), "full/truncated own a heat cell. target_boat additionally needs extent >= 24 px and a visible pad (>= 10 px).",
              font=vis.FONT_SMALL, fill=vis.MUTED)
    draw.text((16, legend_y + 36), "A frame is rejected as ignore once the hull covers more than 75% of the image, regardless of range.",
              font=vis.FONT_SMALL, fill=vis.MUTED)

    measured = [(r["distance_m"], r["extent_px"]) for r in far_rows if r.get("present") and r.get("extent_px")]
    measured += [(r[2]["distance_m"], r[2]["extent_px"]) for r in near_rows if r[2].get("present") and r[2].get("extent_px")]
    crossing = {}
    if measured:
        k = statistics.median(d * e for d, e in measured)
        crossing = {
            "extent_px_times_distance": round(k, 1),
            "distance_at_16px_heat_gate_m": round(k / 16.0, 1),
            "distance_at_24px_identity_gate_m": round(k / 24.0, 1),
            "distance_at_48px_decoy_identity_gate_m": round(k / 48.0, 1),
        }
        draw.text((16, legend_y + 62),
                  f"Measured size law: extent ~= {k:.0f} / distance. 16 px at {k/16:.1f} m, 24 px at {k/24:.1f} m, 48 px at {k/48:.1f} m.",
                  font=vis.FONT_SMALL, fill=vis.TEXT)

    figure.save(SHEET, format="PNG", compress_level=6)
    payload = dict(
        sheet=str(SHEET),
        scene=dict(seed=base_spec.seed, map_kind=base_spec.map_kind, height_m=base_spec.height_m,
                   bearing_deg=base_spec.bearing_deg, weather="clear", decoys=0),
        label_params=LABEL_PARAMS,
        near=near_rows and [r[2] for r in near_rows],
        far=far_rows,
        crossing=crossing,
        note="Rows are one scene at one camera aim (pan 0); labels use the 3k still-frame dataset parameters.",
    )
    DATA.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
