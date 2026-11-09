"""One closed-loop approach from 15 m in search mode, real policy in the loop.

The drone is integrated kinematically from the policy's own velocity and gimbal
rate commands, so this is the actual controller behaviour on real frames, not a
re-implementation of the camera law.  Starts in search mode, 15 m out, a few
seconds before a landing handoff would be attempted.
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

REPO = Path(__file__).resolve().parents[3]
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
for entry in (REPO, SEARCH_RUN):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import mujoco  # noqa: E402

from landing_training.expert import camera_projection  # noqa: E402
from runtime import SearchRuntime  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR, apply_camera_weather  # noqa: E402
from usv.boat_sim import quaternion  # noqa: E402

BUNDLE = SEARCH_RUN / "output_optimized"
OUT = REPO / "training_runs/search_frames_20261108/output/close_approach"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-range", type=float, default=15.0)
    parser.add_argument("--height", type=float, default=4.0)
    parser.add_argument("--seconds", type=float, default=45.0)
    parser.add_argument("--seed", type=int, default=20261108 + 4049)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--tag", default="fixed")
    args = parser.parse_args()
    device = args.device if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(2)
    OUT.mkdir(parents=True, exist_ok=True)

    policy = SearchRuntime(BUNDLE, device)
    spec = SceneSpec(seed=args.seed, map_kind="island", distance_m=12.0,
                     height_m=4.0, bearing_deg=0.0, decoy_layout=(),
                     camera_pan_deg=0.0, camera_tilt_offset_deg=0.0,
                     yaw_offset_deg=0.0, weather=CLEAR)
    rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="close_") as temporary:
        env, model, groups = build_scene(spec, Path(temporary) / "variant")
        renderer = AnnotatableRenderer(env)
        pad = env.pad_position.copy()
        boat_z = float(env.data.qpos[env.boat.free_qadr + 2])
        boat_quat = np.array(env.data.qpos[env.boat.free_qadr + 3: env.boat.free_qadr + 7])
        q = env.drone.free_qadr
        cq = env.drone.camera_qpos
        start = pad + np.array([args.start_range, 0.0, 0.0])
        pos = np.array([start[0], start[1], pad[2] + args.height])
        yaw = math.atan2(pad[1] - pos[1], pad[0] - pos[0])
        gimbal = np.array([0.0, math.radians(6.0)])
        previous = np.zeros(6)
        dt = 0.04
        latched = False
        outcome = "timeout"
        dt_last = dt
        try:
            index = 0
            while index * dt < args.seconds:
                t = round(index * dt, 3)
                qpos = env.data.qpos
                qpos[q:q + 3] = pos
                qpos[q + 3:q + 7] = quaternion(0.0, 0.0, yaw)
                qpos[cq] = gimbal
                bq = env.boat.free_qadr
                qpos[bq] = pad[0]
                qpos[bq + 1] = pad[1]
                qpos[bq + 2] = boat_z
                qpos[bq + 3:bq + 7] = boat_quat
                env.data.qvel[:] = 0.0
                mujoco.mj_forward(env.model, env.data)

                rgb = np.asarray(renderer.onboard_image()).copy()
                rgb = apply_camera_weather(rgb, env, CLEAR)
                pixels, depth = camera_projection(env, env.pad_position)
                pad_pixel = pixels[0] if len(pixels) else np.array([np.nan, np.nan])
                in_frame = bool(len(pixels) and -1 <= pad_pixel[0] <= 641 and -1 <= pad_pixel[1] <= 361)

                observation = {
                    "px4": {
                        "valid": True,
                        "position_enu_m": pos.tolist(),
                        "velocity_enu_m_s": np.zeros(3).tolist(),
                        "attitude_ned_rad": [0.0, 0.0, math.pi / 2 - yaw],
                        "angular_rate_frd_rad_s": [0.0, 0.0, 0.0],
                        "position_age_s": 0.0,
                        "attitude_age_s": 0.0,
                        "armed": True,
                        "landed": False,
                    },
                    "gimbal_rad": gimbal.tolist(),
                    "gimbal_source": "synthetic_encoder",
                    "image_capture_time_s": t,
                    "image_delivery_time_s": t,
                    "image_age_s": 0.0,
                    "image_valid": True,
                    "decision_dt_s": dt_last,
                    "previous_executed_action": previous.tolist(),
                    "mission": {"elapsed_s": t, "budget_s": 240.0},
                }
                action, diag = policy.act(rgb, observation)
                action = np.asarray(action, dtype=float)

                co, si = math.cos(yaw), math.sin(yaw)
                rotation = np.array([[co, -si, 0.0], [si, co, 0.0], [0.0, 0.0, 1.0]])
                velocity = rotation @ np.diag([1.0, -1.0, -1.0]) @ action[:3]
                pos = pos + velocity * dt
                yaw = yaw - float(action[3]) * dt
                gimbal = gimbal + action[4:] * dt
                gimbal[1] = min(max(gimbal[1], 0.0), math.radians(85.0))
                previous = action.copy()
                dt_last = dt

                distance = float(np.linalg.norm(pos[:2] - pad[:2]))
                rows.append(dict(
                    t=t, range_m=round(distance, 2), height_m=round(float(pos[2] - pad[2]), 2),
                    tilt_deg=round(math.degrees(float(gimbal[1])), 1),
                    pan_deg=round(math.degrees(float(gimbal[0])), 1),
                    in_frame=in_frame, phase=diag.get("control_phase"),
                    selected=diag.get("selected_visual_track"),
                    confirmed=bool(diag.get("search_identity_confirmed")),
                    latched=bool(diag.get("handoff_latched")),
                    intervention=diag.get("intervention"),
                    action=[round(float(v), 3) for v in action],
                ))
                if diag.get("handoff_latched"):
                    latched = True
                    outcome = "handoff_latched"
                    break
                if distance < 1.2 and float(pos[2] - pad[2]) < 1.0:
                    outcome = "arrived_low_without_handoff"
                    break
                index += 1
        finally:
            renderer.close()

    summary = dict(
        tag=args.tag, bundle=str(BUNDLE), device=device,
        start_range_m=args.start_range, outcome=outcome, latched=latched,
        latched_at_s=next((row["t"] for row in rows if row["latched"]), None),
        final_range_m=rows[-1]["range_m"] if rows else None,
        first_frame_missing_at_s=next((row["t"] for row in rows if not row["in_frame"]), None),
        frames_missing=sum(1 for row in rows if not row["in_frame"]),
        phases=sorted({row["phase"] for row in rows}),
        rows=rows,
    )
    (OUT / f"close_{args.tag}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print("t     range  height tilt  inframe phase")
    for row in rows[::max(1, len(rows) // 40)]:
        print(f"{row['t']:5.1f} {row['range_m']:6.1f} {row['height_m']:6.1f} "
              f"{row['tilt_deg']:5.1f} {str(row['in_frame']):5s} {row['phase']}")


if __name__ == "__main__":
    main()
