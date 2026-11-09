"""R15 alone on the same 15 m approach: its own pad finder, called every frame."""
from __future__ import annotations
import json, math, sys, tempfile
from pathlib import Path
import numpy as np
import torch

REPO = Path(__file__).resolve().parents[3]
SEARCH_RUN = REPO / "training_runs/search_revision_20261025"
for entry in (REPO, SEARCH_RUN):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import mujoco
from landing_training.expert import camera_projection
from runtime import SearchRuntime
from training_data_generation.core.render import AnnotatableRenderer
from training_data_generation.core.scene import SceneSpec, build_scene
from training_data_generation.core.weather import CLEAR, apply_camera_weather
from usv.boat_sim import quaternion

BUNDLE = SEARCH_RUN / "output_optimized"
OUT = REPO / "training_runs/search_frames_20261108/output/close_approach"

device = "cuda" if torch.cuda.is_available() else "cpu"
torch.set_num_threads(2)
policy = SearchRuntime(BUNDLE, device)
base = policy.base

spec = SceneSpec(seed=20261108 + 4049, map_kind="island", distance_m=12.0, height_m=4.0,
                 bearing_deg=0.0, decoy_layout=(), camera_pan_deg=0.0,
                 camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR)
rows = []
dt = 0.04
with tempfile.TemporaryDirectory(prefix="r15only_") as temporary:
    env, model, groups = build_scene(spec, Path(temporary) / "variant")
    renderer = AnnotatableRenderer(env)
    pad = env.pad_position.copy()
    boat_z = float(env.data.qpos[env.boat.free_qadr + 2])
    boat_quat = np.array(env.data.qpos[env.boat.free_qadr + 3: env.boat.free_qadr + 7])
    q, cq = env.drone.free_qadr, env.drone.camera_qpos
    pos = pad + np.array([15.0, 0.0, 4.0])
    yaw = math.atan2(pad[1] - pos[1], pad[0] - pos[0])
    gimbal = np.array([0.0, math.radians(6.0)])
    previous = np.zeros(6)
    try:
        for index in range(int(40.0 / dt)):
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
            rgb = apply_camera_weather(np.asarray(renderer.onboard_image()).copy(), env, CLEAR)
            observation = {
                "px4": {"valid": True, "position_enu_m": pos.tolist(),
                        "velocity_enu_m_s": np.zeros(3).tolist(),
                        "attitude_ned_rad": [0.0, 0.0, math.pi / 2 - yaw],
                        "angular_rate_frd_rad_s": [0.0, 0.0, 0.0],
                        "position_age_s": 0.0, "attitude_age_s": 0.0,
                        "armed": True, "landed": False},
                "gimbal_rad": gimbal.tolist(), "gimbal_source": "synthetic_encoder",
                "image_capture_time_s": t, "image_delivery_time_s": t,
                "image_age_s": 0.0, "image_valid": True, "decision_dt_s": dt,
                "previous_executed_action": previous.tolist(),
                "beacon": {"valid": False},
                "mission": {"elapsed_s": t, "budget_s": 240.0},
            }
            action, diag = base.act(rgb, observation)
            action = np.asarray(action, dtype=float)
            pixels, _ = camera_projection(env, env.pad_position)
            in_frame = bool(len(pixels) and -1 <= pixels[0][0] <= 641 and -1 <= pixels[0][1] <= 361)
            rows.append(dict(t=t, range_m=round(float(np.linalg.norm(pos[:2] - pad[:2])), 2),
                             alt_m=round(float(pos[2] - pad[2]), 2), in_frame=in_frame,
                             phase=diag.get("control_phase"),
                             metric=bool(diag.get("metric_confirmed")),
                             vis=round(float(diag.get("pad_visibility_probability", -1)), 3),
                             clearance=round(float(diag.get("estimated_clearance_m", -1)), 2),
                             intervention=diag.get("intervention"),
                             act=[round(float(v), 3) for v in action]))
            if diag.get("control_phase") in ("touchdown", "confirm") or float(pos[2] - pad[2]) < 0.12:
                break
            co, si = math.cos(yaw), math.sin(yaw)
            rotation = np.array([[co, -si, 0.0], [si, co, 0.0], [0.0, 0.0, 1.0]])
            pos = pos + (rotation @ np.diag([1.0, -1.0, -1.0]) @ action[:3]) * dt
            yaw = yaw - float(action[3]) * dt
            gimbal = gimbal + action[4:] * dt
            gimbal[1] = min(max(gimbal[1], 0.0), math.radians(85.0))
            previous = action.copy()
    finally:
        renderer.close()

(OUT / "r15_only.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
print("frames", len(rows), "final phase", rows[-1]["phase"], "range", rows[-1]["range_m"],
      "alt", rows[-1]["alt_m"], "metric_any", any(r["metric"] for r in rows),
      "touchdown_any", any(r["phase"] in ("touchdown", "confirm") for r in rows))
for row in rows[::max(1, len(rows) // 30)]:
    print(f"{row['t']:5.1f} r={row['range_m']:6.2f} alt={row['alt_m']:5.2f} vis={row['vis']:5.2f} "
          f"clr={row['clearance']:6.2f} metric={str(row['metric']):5s} {row['phase']}")
