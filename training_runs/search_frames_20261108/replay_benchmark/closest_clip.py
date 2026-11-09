"""Render the +/- window around the closest approach in the benchmark's own scene.

The earlier fast-boat clip rebuilt a training scene and dropped the recorded boat
position into it, which put the boat on land. This script instead reconstructs the
environment exactly as ``benchmark/runner.py`` does (same compiled scene, same
scenario, same ``setup_scene``) and then places the drone, gimbal and boat at the
positions recorded in ``steps.jsonl``. Only the *rendering* is new; the policy is
not re-run, so the HUD shows the diagnostics that flight actually produced.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
for entry in (REPO, REPO / "artifacts/local_curriculum_20261020"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import cv2  # noqa: E402
import mujoco  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from benchmark.common import ROOT, REPO as BENCH, read  # noqa: E402
from benchmark.runner import make_renderer, make_scenario, setup_scene  # noqa: E402


def yaw_quaternion(yaw: float) -> list[float]:
    return [math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0)]


def build_environment(case: dict, output: Path):
    import local_paths  # noqa: F401  (installs the benchmark's source paths)
    from landing_training import environment
    from mission_setup import VerticalLaunchEnvironment

    runtime = read(ROOT / "environments/runtime.json")
    environment.compile_scene = lambda *a, **k: mujoco.MjModel.from_binary_path(
        str(BENCH / runtime["scene"]))
    scenario = make_scenario(case)
    VerticalLaunchEnvironment.audit_directory = output
    env = VerticalLaunchEnvironment(scenario)
    env.boat.navigation.manual()
    setup_scene(env, case, output)
    return env


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True, help="directory holding steps.jsonl")
    parser.add_argument("--window", type=float, default=15.0, help="seconds either side")
    parser.add_argument("--out", required=True, help="output mp4 path")
    parser.add_argument("--work", default="training_runs/search_frames_20261108/output/clips")
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--max-frames", type=int, default=0, help="smoke limit")
    args = parser.parse_args()

    episode = Path(args.episode)
    case = json.loads((episode / "case.json").read_text(encoding="utf-8"))
    steps = [json.loads(line) for line in
             (episode / "steps.jsonl").read_text(encoding="utf-8").splitlines()]
    pad = np.asarray(steps[0]["scoring_only"]["pad_position_enu_m"], dtype=float)
    deck = float(steps[0]["observation"]["mission"].get("nominal_deck_height_above_water_m", 0.45))

    def drone(step):
        px4 = step["observation"]["px4"]
        return (np.asarray(px4["position_enu_m"], dtype=float),
                float(px4["attitude_ned_rad"][2]),
                np.asarray(step["observation"]["gimbal_rad"], dtype=float))

    horizontal = np.array([float(np.linalg.norm(drone(s)[0][:2] - pad[:2])) for s in steps])
    ranges = np.array([float(np.linalg.norm(drone(s)[0] - pad)) for s in steps])
    closest = int(np.argmin(ranges))
    t_star = float(steps[closest]["task_s"])
    times = np.array([float(s["task_s"]) for s in steps])
    selected = [i for i in range(len(steps)) if abs(times[i] - t_star) <= args.window]
    if args.max_frames:
        selected = selected[: args.max_frames]
    print(f"{case['id']}: closest {ranges[closest]:.2f} m (3D to deck, "
          f"{horizontal[closest]:.2f} m horizontal) at t={t_star:.2f}s "
          f"({closest}/{len(steps)}), rendering {len(selected)} frames", flush=True)
    pads = [np.asarray(s["scoring_only"]["pad_position_enu_m"], dtype=float) for s in steps]
    for i in range(0, len(steps), max(1, len(steps) // 12)):
        print(f"   profile t={times[i]:6.1f}s horiz={horizontal[i]:6.2f}m "
              f"range3d={ranges[i]:6.2f}m boat_moved={np.linalg.norm(pads[i][:2]-pads[0][:2]):6.2f}m "
              f"mode={(steps[i].get('diagnostics') or {}).get('mode')}",
              flush=True)

    work = Path(args.work) / case["id"]
    work.mkdir(parents=True, exist_ok=True)
    env = build_environment(case, work)
    renderer = make_renderer(env)
    q = env.drone.free_qadr
    cq = env.drone.camera_qpos
    bq = env.boat.free_qadr
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (640, 360))
    try:
        font = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
    hud = []
    try:
        for count, index in enumerate(selected):
            step = steps[index]
            pos, yaw_ned, gimbal = drone(step)
            env.data.qpos[q:q + 3] = pos
            env.data.qpos[q + 3:q + 7] = yaw_quaternion(math.pi / 2.0 - yaw_ned)
            env.data.qpos[cq] = gimbal
            where = np.asarray(step["scoring_only"]["pad_position_enu_m"], dtype=float)
            env.data.qpos[bq:bq + 3] = [where[0], where[1], where[2] - deck]
            env.data.qpos[bq + 3:bq + 7] = [1.0, 0.0, 0.0, 0.0]
            env.data.qvel[:] = 0.0
            mujoco.mj_forward(env.model, env.data)
            rgb = np.asarray(renderer.onboard_image()).copy()

            diag = step.get("diagnostics") or {}
            rel = float(ranges[index])
            height = float(pos[2] - pad[2])
            canvas = Image.fromarray(rgb).convert("RGB")
            draw = ImageDraw.Draw(canvas)
            lines = [f"t={times[index]:6.2f}s   range={rel:4.2f} m   height={height:4.2f} m",
                     f"phase={diag.get('phase')}  mode={diag.get('mode')}  "
                     f"selected={diag.get('selected')}",
                     f"search confirmed={diag.get('confirmed')}  handoff={diag.get('handoff_latched')}",
                     f"fallback={diag.get('mission_fallback_active')}  "
                     f"closest={ranges[closest]:.2f} m at {t_star:.1f}s"]
            for offset, text in enumerate(lines):
                draw.text((6, 6 + 13 * offset), text, fill=(255, 255, 255), font=font)
            if abs(times[index] - t_star) < 0.5:
                draw.rectangle([0, 0, 639, 359], outline=(255, 220, 0), width=2)
            writer.write(cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR))
            hud.append(dict(t=round(float(times[index]), 2), range_m=round(rel, 2),
                            height_m=round(height, 2), phase=diag.get("phase"),
                            mode=diag.get("mode"), confirmed=diag.get("confirmed"),
                            handoff=diag.get("handoff_latched")))
            if count % 150 == 0:
                print(f"  {count}/{len(selected)} t={times[index]:.1f}s range={rel:.2f}m", flush=True)
    finally:
        writer.release()
        renderer.close()

    summary = dict(case=case["id"], video=str(out), frames=len(selected),
                   closest_range_m=round(float(ranges[closest]), 2),
                   closest_t=round(t_star, 2), window_s=args.window,
                   t0=hud[0]["t"] if hud else None, t1=hud[-1]["t"] if hud else None)
    Path(str(out) + ".json").write_text(json.dumps(dict(summary=summary, hud=hud), indent=1))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
