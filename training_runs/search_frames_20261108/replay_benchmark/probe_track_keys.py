"""Why does R15 go idle after ~10 m? Log the runtime's own track keys per frame."""
from __future__ import annotations

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

from runtime import SearchRuntime  # noqa: E402
from training_data_generation.core.render import AnnotatableRenderer  # noqa: E402
from training_data_generation.core.scene import SceneSpec, build_scene  # noqa: E402
from training_data_generation.core.weather import CLEAR, apply_camera_weather  # noqa: E402
from usv.boat_sim import quaternion  # noqa: E402

BUNDLE = SEARCH_RUN / "output_optimized"
OUT = REPO / "training_runs/search_frames_20261108/output/close_approach"


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(2)
    policy = SearchRuntime(BUNDLE, device)
    called = {"n": 0}
    original = policy.base.act

    def counted(rgb, observation):
        called["n"] += 1
        return original(rgb, observation)

    policy.base.act = counted

    spec = SceneSpec(seed=20261108 + 4049, map_kind="island", distance_m=12.0, height_m=4.0,
                     bearing_deg=0.0, decoy_layout=(), camera_pan_deg=0.0,
                     camera_tilt_offset_deg=0.0, yaw_offset_deg=0.0, weather=CLEAR)
    rows = []
    dt = 0.04
    with tempfile.TemporaryDirectory(prefix="keys_") as temporary:
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
            for index in range(int(round(10.0 / dt))):
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
                called["n"] = 0
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
                    "mission": {"elapsed_s": t, "budget_s": 240.0},
                }
                action, diag = policy.act(rgb, observation)
                action = np.asarray(action, dtype=float)
                seen = sorted(k for k, v in policy.tracks.items() if abs(v["time"] - t) < 1e-9)
                rows.append(dict(t=t, selected=policy.selected, seen=seen,
                                 live=policy.selected in seen, confirmed=bool(policy.search.confirmed),
                                 pad_called=called["n"] > 0, phase=diag.get("control_phase"),
                                 range_m=round(float(np.linalg.norm(pos[:2] - pad[:2])), 2)))
                co, si = math.cos(yaw), math.sin(yaw)
                rotation = np.array([[co, -si, 0.0], [si, co, 0.0], [0.0, 0.0, 1.0]])
                pos = pos + (rotation @ np.diag([1.0, -1.0, -1.0]) @ action[:3]) * dt
                yaw = yaw - float(action[3]) * dt
                gimbal = gimbal + action[4:] * dt
                gimbal[1] = min(max(gimbal[1], 0.0), math.radians(85.0))
                previous = action.copy()
        finally:
            renderer.close()

    (OUT / "track_keys.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    for row in rows:
        if 4.6 <= row["t"] <= 8.6 and abs(row["t"] * 10 - round(row["t"] * 10)) < 0.06:
            print(f"{row['t']:5.2f} r={row['range_m']:5.2f} sel={str(row['selected']):10s} "
                  f"seen={','.join(row['seen']):28s} live={str(row['live']):5s} "
                  f"conf={str(row['confirmed']):5s} r15={str(row['pad_called']):5s} {row['phase']}")
    keys = [row["selected"] for row in rows if row["selected"]]
    print("selected key history:", sorted(set(keys)))
    print("frames with r15 called:", sum(1 for row in rows if row["pad_called"]))
    print("first idle-with-selection:", next((r["t"] for r in rows if r["selected"] and not r["live"]), None))


if __name__ == "__main__":
    main()
