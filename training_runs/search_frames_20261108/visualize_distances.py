"""Render 6 m and 14 m target-range cases for teacher/new/before comparison."""
from __future__ import annotations

import dataclasses
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

from landing_training.expert import camera_projection, pad_visibility  # noqa: E402
from model import SearchHead, decode, encode_maps, load_backbone  # noqa: E402
from training_data_generation.core.geometry import pad_projected_extent  # noqa: E402
from training_data_generation.core.labels import search_labels  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, _set_drone_pose, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR, apply_camera_weather  # noqa: E402
from training_runs.search_frames_20261108 import visualize_comparison as vis  # noqa: E402
from training_runs.search_frames_20261108.generate import _keep_decoys  # noqa: E402

ROOT = REPO / "training_runs/search_frames_20261108/output/3k"
OUT_IMAGE = ROOT / "comparison_6m_14m.png"
OUT_JSON = ROOT / "comparison_6m_14m.json"
IMAGE_6 = ROOT / "distance_6m_input.png"
IMAGE_14 = ROOT / "distance_14m_60pct_input.png"

PANEL_W, PANEL_H = vis.PANEL_W, vis.PANEL_H
LABEL_W, GAP = 235, 8
HEADER_H, ROW_H, FOOTER_H = 60, PANEL_H + 25, 92
COLS = 4
WIDTH = LABEL_W + COLS * PANEL_W + (COLS + 1) * GAP
HEIGHT = HEADER_H + 2 * ROW_H + FOOTER_H
BG, TEXT, MUTED = vis.BG, vis.TEXT, vis.MUTED
CYAN, ORANGE, GREEN = vis.CYAN, vis.ORANGE, vis.GREEN
FONT_TITLE, FONT_HEADER = vis.FONT_TITLE, vis.FONT_HEADER
FONT_CASE, FONT_SMALL = vis.FONT_CASE, vis.FONT_SMALL
FONT_PANEL_SMALL = vis.FONT_PANEL_SMALL


def render_frame(env, renderer, spec: SceneSpec, groups: dict):
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
        min_extent_px=16,
        min_visible_fraction=0.50,
        max_clipped_fraction=0.50,
    )
    return rgb, labels


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path,
                        default=REPO / "training_runs/search_frames_20261108/output/3k/search_best.pt")
    parser.add_argument("--tag", default="NEW HEAD (3k)", help="column header for the checkpoint under test")
    parser.add_argument("--output", type=Path, default=OUT_IMAGE)
    parser.add_argument("--json", type=Path, default=OUT_JSON)
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
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
    with tempfile.TemporaryDirectory(prefix="distance_cases_") as temporary:
        env, model, groups = build_scene(base_spec, Path(temporary) / "variant")
        groups = _keep_decoys(env, model, groups, 0, np.random.default_rng(77))
        renderer = AnnotatableRenderer(env)
        try:
            spec6 = dataclasses.replace(base_spec, distance_m=6.0)
            rgb6, labels6 = render_frame(env, renderer, spec6, groups)
            target6 = labels6.get("target")
            if target6 is None:
                raise RuntimeError("6 m target is not visible")

            def evaluate_14(pan):
                spec14 = dataclasses.replace(base_spec, distance_m=14.0, camera_pan_deg=float(pan))
                rgb14, labels14 = render_frame(env, renderer, spec14, groups)
                target14 = labels14.get("target")
                if target14 is None:
                    return None
                if target14["label_class"] not in ("full", "truncated", "presence_only"):
                    return None
                return (abs(float(target14["visible_fraction"]) - 0.60),
                        float(pan), rgb14, labels14, spec14)

            best14 = None
            for pan in np.linspace(0.0, 35.0, 71):
                candidate = evaluate_14(pan)
                if candidate is not None and (best14 is None or candidate[0] < best14[0]):
                    best14 = candidate
            if best14 is None:
                raise RuntimeError("could not find a visible 14 m target pose")
            # Refine around the coarse minimum. The projected-bbox fraction
            # changes in small steps, so a 0.05 degree sweep gets the requested
            # 60% visibility much closer than the 0.5 degree coarse grid.
            center = best14[1]
            for pan in np.linspace(max(0.0, center - 1.0), min(35.0, center + 1.0), 41):
                candidate = evaluate_14(pan)
                if candidate is not None and candidate[0] < best14[0]:
                    best14 = candidate
            _, pan14, rgb14, labels14, spec14 = best14
            target14 = labels14["target"]
        finally:
            renderer.close()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    base = load_backbone(device)
    current = SearchHead().to(device)
    current.load_state_dict(torch.load(args.checkpoint.resolve(), map_location="cpu",
                                       weights_only=False)["model"], strict=True)
    current.eval()
    before = SearchHead().to(device)
    before.load_state_dict(torch.load(SEARCH_RUN / "output_optimized/search_best.pt",
                                      map_location="cpu", weights_only=False)["model"], strict=True)
    before.eval()

    def infer(rgb):
        with torch.inference_mode():
            image = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to(device)
            fine, context = encode_maps(base, image)
            new_output = current(fine, context)
            old_output = before(fine, context)
            return (
                new_output["heat"].sigmoid()[0].cpu().numpy(),
                old_output["heat"].sigmoid()[0].cpu().numpy(),
                decode(new_output, threshold=0.50)[0],
                decode(old_output, threshold=0.50)[0],
            )

    figure = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(figure)
    draw.text((LABEL_W + GAP, 16), "Two distance cases: 6 m and 14 m, target 60% visible at 14 m",
              font=FONT_TITLE, fill=TEXT)
    headers = ("INPUT FRAME", "TEACHER LABELS", args.tag, "BEFORE (OCT 25)")
    for col, header in enumerate(headers):
        x = LABEL_W + GAP + col * (PANEL_W + GAP)
        draw.text((x + 4, HEADER_H - 22), header, font=FONT_HEADER, fill=MUTED)

    cases = []
    for row, (distance, rgb, labels, target, tag) in enumerate((
        (6.0, rgb6, labels6, target6, "6 m"),
        (14.0, rgb14, labels14, target14, "14 m"),
    )):
        top = HEADER_H + row * ROW_H
        y = top + 18
        label_x = 14
        draw.text((label_x, y), tag, font=FONT_CASE, fill=GREEN if row == 0 else ORANGE)
        draw.text((label_x, y + 27), f"{labels['target']['label_class']} target", font=FONT_SMALL, fill=TEXT)
        if row == 0:
            draw.text((label_x, y + 44), "clear / no decoys", font=FONT_SMALL, fill=MUTED)
            draw.text((label_x, y + 61), f"{float(target['visible_fraction']):.1%} visible", font=FONT_SMALL, fill=MUTED)
        else:
            draw.text((label_x, y + 44), f"{float(target['visible_fraction']):.1%} visible / clipped", font=FONT_SMALL, fill=MUTED)
            draw.text((label_x, y + 61), f"camera pan {pan14:.1f} deg", font=FONT_SMALL, fill=MUTED)

        new_heat, old_heat, new_props, old_props = infer(rgb)
        target_px = target["center_px"]
        panels = [
            Image.fromarray(rgb).resize((PANEL_W, PANEL_H), Image.Resampling.BILINEAR),
            vis.render_panel(rgb, labels["heat"], [], GREEN, target_px=target_px, teacher=True),
            vis.render_panel(rgb, new_heat, new_props, CYAN),
            vis.render_panel(rgb, old_heat, old_props, ORANGE),
        ]
        for col, panel in enumerate(panels):
            x = LABEL_W + GAP + col * (PANEL_W + GAP)
            figure.paste(panel, (x, top))
            draw.rectangle([x, top, x + PANEL_W - 1, top + PANEL_H - 1], outline=(65, 70, 82), width=1)

        draw.text((label_x, y + 92), "teacher", font=FONT_PANEL_SMALL, fill=GREEN)
        draw.text((label_x + 57, y + 92), f"{labels['target']['label_class']} / p={float(labels['presence']):.2f}",
                  font=FONT_PANEL_SMALL, fill=TEXT)
        draw.text((label_x, y + 110), "new", font=FONT_PANEL_SMALL, fill=CYAN)
        draw.text((label_x + 57, y + 110), vis._proposal_text(new_props), font=FONT_PANEL_SMALL, fill=TEXT)
        draw.text((label_x, y + 128), "before", font=FONT_PANEL_SMALL, fill=ORANGE)
        draw.text((label_x + 57, y + 128), vis._proposal_text(old_props), font=FONT_PANEL_SMALL, fill=TEXT)

        cases.append(dict(
            distance_m=distance,
            distance_source="SceneSpec.distance_m (horizontal camera-to-target range)",
            image=str((IMAGE_6 if row == 0 else IMAGE_14)),
            teacher=dict(label_class=labels["target"]["label_class"],
                         evidence=labels["target"]["evidence"],
                         visible_fraction=float(labels["target"]["visible_fraction"]),
                         presence=float(labels["presence"]),
                         center_px=target["center_px"]),
            new=dict(max_heat=float(np.max(new_heat)), proposals=new_props),
            before=dict(max_heat=float(np.max(old_heat)), proposals=old_props),
        ))

    Image.fromarray(rgb6).save(IMAGE_6, format="PNG", compress_level=1)
    Image.fromarray(rgb14).save(IMAGE_14, format="PNG", compress_level=1)
    legend_y = HEADER_H + 2 * ROW_H + 12
    draw.text((LABEL_W + GAP, legend_y), "Green: teacher target centre and teacher heat.  Cyan: new head.  Orange: pre-pilot head.",
              font=FONT_SMALL, fill=MUTED)
    draw.text((LABEL_W + GAP, legend_y + 18), "Heat is the 45x80 teacher label or network sigmoid upsampled to 640x360. Circles are network proposals at threshold 0.50.",
              font=FONT_SMALL, fill=MUTED)
    draw.text((LABEL_W + GAP, legend_y + 36), "The 14 m pose was selected to make the teacher visible fraction closest to 60%; the target is clipped at the right edge.",
              font=FONT_SMALL, fill=MUTED)
    figure.save(args.output, format="PNG", compress_level=6)
    args.json.write_text(json.dumps(dict(image=str(args.output), tag=args.tag,
                                         checkpoint=str(args.checkpoint), cases=cases), indent=2) + "\n",
                          encoding="utf-8")
    print(json.dumps(dict(image=str(args.output), tag=args.tag, cases=cases), indent=2))
    print("WROTE", args.output)


if __name__ == "__main__":
    main()
