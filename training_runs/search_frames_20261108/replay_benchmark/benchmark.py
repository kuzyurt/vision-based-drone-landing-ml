"""Replay benchmark across several search heads on identical frames.

Each situation is rendered once per time step. The frame is then given to the
privileged teacher search decision and to every listed search head, so a
difference between heads is a weights difference, never a scene difference.

Per situation the summary reports a success rate per head:

* ``confirm_target`` situations: fraction of the teacher-confirmed frames in
  which that head also confirms, and does so on the target boat itself,
* ``reject_all`` situations: fraction of all frames in which that head does not
  confirm anything.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
if str(SEARCH_RUN) not in sys.path:
    sys.path.insert(0, str(SEARCH_RUN))

import mujoco  # noqa: E402

from landing_training.expert import camera_projection, pad_visibility  # noqa: E402
from landing_training.privileged_teacher import SearchDecision, VisibleBoatOracle  # noqa: E402
from model import SearchHead, decode, encode_maps, load_backbone  # noqa: E402
from training_data_generation.core.geometry import pad_projected_extent  # noqa: E402
from training_data_generation.core.labels import search_labels  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR, apply_camera_weather  # noqa: E402
from training_runs.search_frames_20261108.generate import _keep_decoys  # noqa: E402
from training_runs.search_frames_20261108.replay_benchmark.situations import (  # noqa: E402
    SITUATIONS, Situation, target_scale, yaw_offset_rad,
)
from usv.boat_sim import quaternion  # noqa: E402

OUT = REPO / "training_runs/search_frames_20261108/output/replay_benchmark"
HEAD_PATHS = {
    "old_oct25": SEARCH_RUN / "output_optimized/search_best.pt",
    "frozen_ft": REPO / "training_runs/search_frames_20261108/output/finetune_frozen/search_best.pt",
    "balanced": REPO / "training_runs/search_frames_20261108/output/evidence_balanced/search_best.pt",
}
PRIMARY = "balanced"
ABANDON_NO_PROGRESS_S = 12.0


def _basis(final_xy: np.ndarray, drone_xy: np.ndarray):
    forward = (final_xy - drone_xy)
    forward = forward / max(float(np.linalg.norm(forward)), 1e-9)
    right = np.array([forward[1], -forward[0]])
    return forward, right


def _place_boat(env, xy, boat_z: float, boat_quat) -> None:
    q = env.boat.free_qadr
    env.data.qpos[q] = xy[0]
    env.data.qpos[q + 1] = xy[1]
    env.data.qpos[q + 2] = boat_z
    env.data.qpos[q + 3 : q + 7] = boat_quat
    env.data.qvel[:] = 0.0


def _place_drone(env, xy, height_m: float, aim_xy, pad_z: float, yaw_offset: float) -> float:
    q = env.drone.free_qadr
    env.data.qpos[q : q + 3] = [xy[0], xy[1], pad_z + height_m]
    yaw = math.atan2(aim_xy[1] - xy[1], aim_xy[0] - xy[0]) + yaw_offset
    env.data.qpos[q + 3 : q + 7] = quaternion(0.0, 0.0, yaw)
    distance = float(np.linalg.norm(aim_xy - xy))
    tilt = float(np.clip(math.atan2(height_m, max(distance, 1e-6)), 0.0, math.pi / 2))
    env.data.qpos[env.drone.camera_qpos] = [0.0, tilt]
    return yaw


def _heads_on_frame(heads, fine, context):
    """Run every head on one encoded frame and return the proposal summary."""
    results = {}
    for name, head in heads.items():
        output = head(fine, context)
        proposals = decode(output, 0.50)[0]
        heat = float(output["heat"].sigmoid().max())
        top = max(proposals, key=lambda p: p["confidence"]) if proposals else None
        results[name] = dict(
            heat=round(heat, 4),
            proposals=len(proposals),
            pixel=None if top is None else [round(float(v), 1) for v in top["pixel"]],
            evidence=None if top is None else top["evidence"],
            identity=None if top is None else round(top["identity_target_probability"], 4),
            confirmed=bool(top and top["evidence"] == "target_boat"),
        )
    return results


def _attribute(pixel, views, limit=80.0):
    if pixel is None:
        return None
    best, best_distance = None, limit
    for view in views:
        cx = (view.bbox[0] + view.bbox[2]) * 0.5
        cy = (view.bbox[1] + view.bbox[3]) * 0.5
        distance = math.hypot(pixel[0] - cx, pixel[1] - cy)
        if distance < best_distance:
            best, best_distance = view.key, distance
    return best


def _success(situation: Situation, rows, head) -> dict:
    valid = True
    if situation.expectation == "reject_all":
        total = len(rows)
        good = sum(1 for row in rows if not row["students"][head]["confirmed"])
    else:
        window = [row for row in rows if row["teacher_confirmed"]]
        total = len(window)
        good = sum(1 for row in window
                   if row["students"][head]["confirmed"] and row["student_objects"][head] == "target")
        # Without a teacher-confirmed window the situation cannot test the
        # landing gate, so it is reported as n/a instead of a fake zero.
        valid = total > 0
    return dict(
        success=round(good / total, 4) if total else 0.0,
        valid=valid,
        good_frames=good,
        counted_frames=total,
        confirmed_at_s=next((row["t"] for row in rows if row["students"][head]["confirmed"]), None),
        confirmed_on={key: sum(1 for row in rows
                               if row["students"][head]["confirmed"] and row["student_objects"][head] == key)
                      for key in {row["student_objects"][head] for row in rows}
                      if key is not None},
    )


def run(situation: Situation, heads: dict, base, device, save_frames: bool = False) -> dict:
    spec = SceneSpec(
        seed=situation.seed, map_kind=situation.map_kind,
        distance_m=situation.drone_final_distance_m, height_m=situation.drone_height_m,
        bearing_deg=situation.bearing_deg, decoy_layout=(), camera_pan_deg=0.0,
        camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR,
    )
    rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix=f"replay_{situation.key}_") as temporary:
        env, model, groups = build_scene(spec, Path(temporary) / "variant")
        groups = _keep_decoys(env, model, groups, len(situation.decoy_offsets_m),
                              np.random.default_rng(situation.seed + 5))
        final_xy = env.pad_position[:2].copy()
        pad_z = float(env.pad_position[2])
        boat_z = float(env.data.qpos[env.boat.free_qadr + 2])
        boat_quat = np.array(env.data.qpos[env.boat.free_qadr + 3 : env.boat.free_qadr + 7])
        bearing = math.radians(situation.bearing_deg)
        drone_xy = final_xy + situation.drone_final_distance_m * np.array(
            [math.cos(bearing), math.sin(bearing)])
        forward, right = _basis(final_xy, drone_xy)

        decoy_keys = sorted(key for key in groups if key.startswith("decoy_"))
        for index, key in enumerate(decoy_keys):
            lateral, along = situation.decoy_offsets_m[index % len(situation.decoy_offsets_m)]
            decoy_xy = final_xy + right * lateral + forward * along
            mid = int(model.body_mocapid[model.body(key).id])
            if mid >= 0:
                env.data.mocap_pos[mid] = [decoy_xy[0], decoy_xy[1], 0.03]

        oracle = VisibleBoatOracle(env, groups)
        decision = SearchDecision()
        renderer = AnnotatableRenderer(env)
        selected_since = last_progress = 0.0
        best_range = math.inf
        last_selected = None
        try:
            steps = int(round(situation.duration_s / situation.dt_s))
            save = {int(round(f * steps)) for f in (0.0, 0.15, 0.3, 0.45, 0.6, 0.8, 1.0)}
            for index in range(steps + 1):
                t = round(index * situation.dt_s, 3)
                fraction = target_scale(situation, t)
                lateral, along = situation.target_start_offset_m
                target_xy = final_xy + right * lateral * fraction + forward * along * fraction
                _place_boat(env, target_xy, boat_z, boat_quat)
                yaw = _place_drone(env, drone_xy, situation.drone_height_m, final_xy, pad_z,
                                   yaw_offset_rad(situation, t))
                mujoco.mj_forward(env.model, env.data)

                rgb = np.asarray(renderer.onboard_image()).copy()
                renderer.onboard.enable_segmentation_rendering()
                try:
                    seg = np.asarray(renderer.onboard_image()).copy()
                finally:
                    renderer.onboard.disable_segmentation_rendering()
                rgb = apply_camera_weather(rgb, env, CLEAR)

                pad_pixels, pad_depth = camera_projection(env, env.pad_position)
                pad_pixel = pad_pixels[0] if len(pad_pixels) else np.array([np.nan, np.nan])
                pad_depth_value = float(pad_depth[0]) if len(pad_depth) else float("nan")
                visible, _ = pad_visibility(env)
                pad_extent = (pad_projected_extent(env, pad_depth_value)
                              if np.isfinite(pad_depth_value) else 0.0)
                labels = search_labels(
                    env, seg, groups, pad_pixel, bool(visible), pad_extent_px=pad_extent,
                    min_extent_px=16, min_visible_fraction=0.50, max_clipped_fraction=0.25,
                )

                views = oracle.observe(seg)
                decision.decide(t, views, yaw, True)
                selected = decision.selected
                if selected != last_selected:
                    last_selected = selected
                    selected_since = t
                    best_range = math.inf
                    last_progress = t
                live = next((v for v in views if v.key == selected and v.detectable), None)
                if live is not None and live.range_m < best_range - 0.5:
                    best_range = live.range_m
                    last_progress = t
                if (selected is not None and not decision.confirmed
                        and t - last_progress > ABANDON_NO_PROGRESS_S):
                    decision.restart(t, "unresolved_inspection_restart_scan_1")
                    selected_since = t
                    best_range = math.inf
                    last_progress = t
                    last_selected = None

                image = torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).to(device)
                with torch.inference_mode():
                    fine, context = encode_maps(base, image)
                    students = _heads_on_frame(heads, fine, context)
                student_objects = {name: _attribute(result["pixel"], views)
                                   for name, result in students.items()}

                if save_frames and index in save:
                    canvas = Image.fromarray(rgb).convert("RGB")
                    painter = ImageDraw.Draw(canvas)
                    if live is not None:
                        x0, y0, x1, y1 = (int(v) for v in live.bbox)
                        colour = ((46, 204, 113) if live.evidence == "target_boat"
                                  else (241, 196, 15))
                        painter.rectangle([x0, y0, x1, y1], outline=colour, width=2)
                    primary = students.get(PRIMARY) or next(iter(students.values()))
                    if primary["pixel"] is not None:
                        px, py = primary["pixel"]
                        colour = ((231, 76, 60) if primary["confirmed"] else (230, 126, 34))
                        painter.line([px - 9, py, px + 9, py], fill=colour, width=2)
                        painter.line([px, py - 9, px, py + 9], fill=colour, width=2)
                    (OUT / "frames_annotated").mkdir(parents=True, exist_ok=True)
                    canvas.save(OUT / "frames_annotated" / f"{situation.key}_{index:04d}.png")

                target = labels.get("target")
                rows.append(dict(
                    t=t,
                    target_range_m=None if target is None else round(
                        float(np.linalg.norm(target_xy - drone_xy)), 2),
                    target_extent_px=None if target is None else int(target["extent_px"]),
                    target_present=target is not None,
                    pad_visible=bool(visible),
                    pad_extent_px=round(float(pad_extent), 2),
                    teacher_views=[dict(key=v.key, evidence=v.evidence,
                                        range_m=round(float(v.range_m), 1)) for v in views],
                    teacher_rejected=sorted(decision.rejected),
                    teacher_selected=decision.selected,
                    teacher_evidence=None if live is None else live.evidence,
                    teacher_confirmed=decision.confirmed,
                    teacher_pad_extent_px=None if live is None else round(float(live.pad_extent_px), 2),
                    students=students,
                    student_objects=student_objects,
                ))
        finally:
            renderer.close()

    summary = dict(
        key=situation.key,
        title=situation.title,
        expectation=situation.expectation,
        other_boats=len(situation.decoy_offsets_m),
        frames=len(rows),
        teacher_confirmed_at_s=next((row["t"] for row in rows if row["teacher_confirmed"]), None),
        heads={name: _success(situation, rows, name) for name in heads},
        rows=rows,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--situations", nargs="+", default=["all"])
    parser.add_argument("--heads", nargs="+", default=list(HEAD_PATHS))
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--no-frames", action="store_true")
    args = parser.parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    keys = list(SITUATIONS) if args.situations == ["all"] else args.situations
    torch.set_num_threads(2)
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_backbone(args.device)
    heads = {}
    for name in args.heads:
        head = SearchHead().to(args.device)
        head.load_state_dict(torch.load(HEAD_PATHS[name], map_location="cpu",
                                        weights_only=False)["model"], strict=True)
        head.eval()
        heads[name] = head

    summaries = []
    for key in keys:
        summary = run(SITUATIONS[key], heads, base, args.device, save_frames=not args.no_frames)
        summaries.append(summary)
        (OUT / f"{key}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        rates = " ".join(f"{name}={100 * part['success']:.0f}%" for name, part in summary["heads"].items())
        print(f"{key:24s} teacher={summary['teacher_confirmed_at_s']}  {rates}", flush=True)

    (OUT / "summary.json").write_text(json.dumps(
        [{k: v for k, v in item.items() if k != "rows"} for item in summaries], indent=2) + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
