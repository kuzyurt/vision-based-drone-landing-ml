"""Re-render the recorded fast-boat flight with the policy's own overlays.

Uses the flight's own step log: the drone pose, gimbal and observation are the
recorded ones, so the geometry is the benchmark's, not a synthetic approach.
Each re-rendered frame is fed back through the policy, and the search head's
proposals plus the pad finder's diagnostics are burned into the video.

The pad position comes from ``scoring_only`` truth and is used only to place the
boat for rendering; it is never put in the observation the policy receives.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[3]
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
for entry in (REPO, SEARCH_RUN):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import cv2  # noqa: E402
import mujoco  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from runtime import SearchRuntime  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR  # noqa: E402
from usv.boat_sim import quaternion  # noqa: E402

BUNDLE = SEARCH_RUN / "output_optimized"
OUT = REPO / "training_runs/search_frames_20261108/output/fastboat"

PAD_KEYS = ("control_phase", "metric_confirmed", "metric_distance_m", "metric_range_m",
            "spatial_distance_m", "pad_distance_m", "clearance_m", "acquisition_state",
            "visual_pixel", "pad_pixel", "target_pixel", "metric_pixel", "selected_pixel",
            "range_m", "intervention", "gate_reason", "handoff_latched")


PX4_ALLOWED = ("valid", "position_enu_m", "velocity_enu_m_s", "attitude_ned_rad",
               "angular_rate_frd_rad_s", "position_age_s", "attitude_age_s",
               "position_source_boot_ms", "attitude_source_boot_ms", "armed", "landed",
               "gimbal_commanded_rad", "gimbal_command_source")


def sanitize(obs, elapsed):
    """Rebuild the actor input by allowlist, exactly as the benchmark does.

    The recorded row also carries the boat beacon and mission priors; the policy
    is forbidden to see either, so they are dropped rather than passed through.
    """
    mission = obs.get("mission") or {}
    return dict(
        px4={k: obs["px4"][k] for k in PX4_ALLOWED if k in obs["px4"]},
        gimbal_rad=list(obs["gimbal_rad"]),
        gimbal_source="synthetic own encoder",
        previous_executed_action=list(obs["previous_executed_action"]),
        image_capture_time_s=float(obs["image_capture_time_s"]),
        image_delivery_time_s=float(obs["image_delivery_time_s"]),
        image_age_s=float(obs.get("image_age_s", 0.0)),
        image_valid=True,
        decision_dt_s=float(obs.get("decision_dt_s", 0.04)),
        mission=dict(elapsed_s=float(mission.get("elapsed_s", elapsed)),
                     budget_s=float(mission.get("budget_s", 240.0))),
    )


def plain(value):
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, int, str, bool)) or value is None:
        return value
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="benchmark/revisions/bounded_search_20261026/runs/"
                                        "handoff_fastboat_20261108")
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--tag", default="fastboat")
    args = parser.parse_args()
    device = args.device if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(2)
    OUT.mkdir(parents=True, exist_ok=True)

    episode = Path(glob.glob(str(REPO / args.run / "**" / "steps.jsonl"), recursive=True)[0]).parent
    case = json.loads((episode / "case.json").read_text(encoding="utf-8"))
    scenario = case["scenario"]
    steps = [json.loads(line) for line in (episode / "steps.jsonl").read_text(encoding="utf-8").splitlines()]
    print(f"episode {case['id']} frames={len(steps)} stride={args.stride}", flush=True)

    policy = SearchRuntime(BUNDLE, device)
    captured: dict = {}
    original_act = policy.base.act

    def recording_act(rgb, observation):
        action, diag = original_act(rgb, observation)
        captured.clear()
        captured.update(diag or {})
        return action, diag

    policy.base.act = recording_act

    spec = SceneSpec(seed=int(scenario["seed"]), map_kind=scenario["kind"],
                     distance_m=float(scenario["distance"]), height_m=float(scenario["height"]),
                     bearing_deg=float(scenario["bearing_deg"]), decoy_layout=(),
                     camera_pan_deg=0.0, camera_tilt_offset_deg=0.0,
                     yaw_offset_deg=0.0, weather=CLEAR)
    rows: list[dict] = []
    frames: list[np.ndarray] = []
    with tempfile.TemporaryDirectory(prefix="fastboat_") as temporary:
        try:
            env, model, groups = build_scene(spec, Path(temporary) / "variant")
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            raise SystemExit(f"scene build failed for kind={scenario['kind']}: {exc}")
        renderer = AnnotatableRenderer(env)
        q, cq, bq = env.drone.free_qadr, env.drone.camera_qpos, env.boat.free_qadr
        try:
            for index in range(0, len(steps), args.stride):
                step = steps[index]
                obs = sanitize(step["observation"], float(step["task_s"]))
                pos = np.asarray(obs["px4"]["position_enu_m"], dtype=float)
                yaw_ned = float(obs["px4"]["attitude_ned_rad"][2])
                yaw = math.pi / 2.0 - yaw_ned
                gimbal = np.asarray(obs["gimbal_rad"], dtype=float)
                pad = np.asarray(step["scoring_only"]["pad_position_enu_m"], dtype=float)

                env.data.qpos[q:q + 3] = pos
                env.data.qpos[q + 3:q + 7] = quaternion(0.0, 0.0, yaw)
                env.data.qpos[cq] = gimbal
                env.data.qpos[bq:bq + 3] = pad
                env.data.qpos[bq + 3:bq + 7] = [1.0, 0.0, 0.0, 0.0]
                env.data.qvel[:] = 0.0
                mujoco.mj_forward(env.model, env.data)

                rgb = np.asarray(renderer.onboard_image()).copy()
                policy.last_proposals = None
                action, diag = policy.act(rgb, obs)
                proposals = policy.last_proposals or []
                top = [dict(pixel=[round(float(v), 1) for v in item["pixel"]],
                            evidence=item["evidence"],
                            confidence=round(float(item["confidence"]), 3),
                            identity=round(float(item["identity_target_probability"]), 3))
                       for item in sorted(proposals, key=lambda p: -p["confidence"])[:3]]

                distance = float(np.linalg.norm(pos[:2] - pad[:2]))
                pad_info = {key: plain(diag[key]) for key in PAD_KEYS if key in (diag or {})}
                truth_pixel = None
                rows.append(dict(t=round(float(step["task_s"]), 2), frame=index,
                                 range_m=round(distance, 2),
                                 height_m=round(float(pos[2] - pad[2]), 2),
                                 phase=diag.get("phase"), mode=diag.get("mode"),
                                 selected=diag.get("selected"),
                                 confirmed=bool(diag.get("confirmed")),
                                 latched=bool(diag.get("handoff_latched")),
                                 coverage=diag.get("coverage_deg"),
                                 head=top, pad=pad_info))
                frames.append(rgb)
                if index % 250 == 0:
                    print(f"  {index}/{len(steps)} range={distance:.1f}m "
                          f"confirmed={rows[-1]['confirmed']} top={top[0]['evidence'] if top else 'none'}",
                          flush=True)
        finally:
            renderer.close()

    (OUT / f"replay_{args.tag}.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")

    try:
        font = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
    video = OUT / f"replay_{args.tag}.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (640, 360))
    confirmed_ever = False
    for row, frame in zip(rows, frames):
        canvas = Image.fromarray(frame).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        for item in row["head"]:
            px, py = item["pixel"]
            colour = (231, 76, 60) if item["evidence"] == "target_boat" else (230, 126, 34)
            draw.line([px - 8, py, px + 8, py], fill=colour, width=2)
            draw.line([px, py - 8, px, py + 8], fill=colour, width=2)
            draw.text((px + 9, py - 6), f"{item['evidence'][:9]} {item['confidence']:.2f}",
                      fill=colour, font=font)
        pixel = row["pad"].get("pad_pixel") or row["pad"].get("visual_pixel")
        if pixel:
            px, py = float(pixel[0]), float(pixel[1])
            draw.ellipse([px - 10, py - 10, px + 10, py + 10], outline=(0, 220, 220), width=2)
        confirmed_ever = confirmed_ever or row["confirmed"]
        lines = [f"t={row['t']:.2f}s range={row['range_m']:.2f}m height={row['height_m']:.2f}m",
                 f"mode={row['mode']} phase={row['phase']} selected={row['selected']}",
                 f"search confirmed={row['confirmed']} handoff={row['latched']}",
                 f"head_top={row['head'][0]['evidence'] if row['head'] else 'none'}  "
                 f"pad_finder={row['pad'].get('control_phase', 'idle') if row['pad'] else 'not called'}"]
        for offset, line in enumerate(lines):
            draw.text((6, 6 + 13 * offset), line, fill=(255, 255, 255), font=font)
        writer.write(cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR))
    writer.release()
    print(json.dumps(dict(frames=len(rows), video=str(video),
                          confirmed_ever=confirmed_ever,
                          pad_calls=sum(1 for row in rows if row["pad"]),
                          min_range=min(row["range_m"] for row in rows)), indent=2))


if __name__ == "__main__":
    main()
