"""Search, find and land on the 80 m city scene with six false boats.

The aircraft starts broadside to the boat with the camera on the first search
leg, so the target is not in the first frame (asserted on the actual render).
It flies two declared search legs with a sweeping camera, then turns in toward
the searched sector; the stock teacher's own pad-visibility gate decides when
the boat has been found, after which the stock teacher lands it.

Control authority is the existing ``landing_training.expert.Expert``.  The
search sweep is a review-only pattern over the declared sector; it carries no
target position.  This is a geometry/behaviour review flight, not a trained
perception result.

Runs natively on Windows so the onboard camera renders on the GPU: the earlier
software-rendered WSL attempt took ~90 minutes for the same footage.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CURRICULUM = ROOT / "artifacts/local_curriculum_20261020"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CURRICULUM))
sys.path.insert(0, str(CURRICULUM / "sources"))

import local_paths  # noqa: E402,F401  (installs the sim/usv import paths)

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

from windows_kernels import install as install_kernels  # noqa: E402

install_kernels()

import fast_physics_windows  # noqa: E402
import landing_training.environment as environment  # noqa: E402
from landing_training.expert import Expert, pad_visibility, wrap  # noqa: E402
from landing_training.recording import Recorder  # noqa: E402
from landing_training.run_episode import camera_image  # noqa: E402
from scene_spec import MAP, SEARCH_LEGS, SEARCH_START, Scenario80  # noqa: E402
from search_geometry import apply_start_heading, frame, point, start_heading  # noqa: E402
from windows_px4_v2 import WindowsPX4  # noqa: E402
from video_overlay import SearchVideo, compose  # noqa: E402
from windows_renderer import OnboardRenderer  # noqa: E402

# Dock readiness is a one-bit status flag.  No position fix is available during
# the search, so every metre flown before the visual lock is a real search.
STATUS_ONLY_BEACON = dict(valid=False, age_s=3.1, sequence=0, dock_ready=True,
                          dock_status_valid=True)


class SearchDirector:
    """Two search legs, then a turn-in.  The target is found by looking."""

    def __init__(self, env, expert, *, search_height, pan_amplitude_deg=30.0,
                 sweep_period_s=9.0):
        self.env = env
        self.expert = expert
        pad, u, v = frame(env)
        self.pad = pad
        self.waypoints = [np.array([*(pad[:2] + leg["along"] * u + leg["lateral"] * v), 0.0])
                          for leg in SEARCH_LEGS]
        self.names = [leg["name"] for leg in SEARCH_LEGS]
        self.start = point(env, SEARCH_START["along"], SEARCH_START["lateral"])
        self.index = 0
        self.locked = False
        self.seen = 0
        self.phase = self.names[0]
        self.altitude = float(env.pad_position[2]) + search_height - env.drone.bottom
        self.pan_amplitude = math.radians(pan_amplitude_deg)
        self.sweep_period = float(sweep_period_s)
        self.t0 = None
        self.lock = None
        self.confirm_range_m = 55.0

    def _confirmed(self, visible, pixels, position):
        """A near, centred sighting is an identification; an edge speck is not.

        The pad-visibility gate is the stock teacher sensor.  A contact grazing
        the frame edge at 80 m is still just a candidate, so the search keeps
        going until the boat is centred and close enough to identify.
        """
        if not visible or not pixels:
            return False
        px, py = pixels[0]
        centred = abs(px - 320.0) / 320.0 <= 0.35 and abs(py - 180.0) / 180.0 <= 0.55
        distance = float(np.linalg.norm(self.pad[:2] - np.asarray(position, float)[:2]))
        return bool(centred and distance <= self.confirm_range_m)

    def act(self, px4, visible, t, pixels=None):
        env = self.env
        if self.t0 is None:
            self.t0 = t
        if self.locked:
            raw, executed, reason = self.expert.act(px4, STATUS_ONLY_BEACON, visible)
            return raw, executed, reason
        # A find must be stable, centred and within identification range.
        self.seen = self.seen + 1 if self._confirmed(visible, pixels,
                                                     self.env.drone.position) else 0
        if self.seen >= 6:
            self.locked = True
            self.phase = "target_found"
            velocity = np.asarray(env.drone.velocity, float)
            vector = self.pad - env.drone.position
            yaw_enu = math.pi / 2.0 - px4.attitude.yaw if px4.attitude else 0.0
            self.lock = dict(
                task_time_s=float(t),
                range_m=round(float(np.linalg.norm(vector[:2])), 2),
                leg=self.names[min(self.index, len(self.names) - 1)],
                heading_error_deg=round(math.degrees(abs(wrap(
                    math.atan2(vector[1], vector[0]) - yaw_enu))), 1),
                flown_search_m=round(float(np.linalg.norm(env.drone.position[:2]
                                                          - self.start[:2])), 1),
            )
            print(json.dumps(dict(event="target_locked", **self.lock)), flush=True)
            raw, executed, reason = self.expert.act(px4, STATUS_ONLY_BEACON, visible)
            return raw, executed, reason

        position = np.asarray(env.drone.position, float)
        yaw_enu = math.pi / 2.0 - px4.attitude.yaw if px4.attitude else 0.0
        turning_in = self.index >= len(self.waypoints)
        if not turning_in:
            target = self.waypoints[self.index]
            error = target[:2] - position[:2]
            if float(np.linalg.norm(error)) < 1.2:
                self.index += 1
                if self.index >= len(self.waypoints):
                    turning_in = True
                    self.phase = "turn_in_to_boat"
                    print(json.dumps(dict(event="search_legs_complete")), flush=True)
                else:
                    self.phase = self.names[self.index]
                return self.act(px4, visible, t, pixels)
        if turning_in:
            error = self.pad[:2] - position[:2]
        else:
            error = self.waypoints[self.index][:2] - position[:2]
        distance = float(np.linalg.norm(error))
        direction = error / max(distance, 1e-9)
        if turning_in:
            desired_heading = math.atan2(error[1], error[0])
            aligned = abs(wrap(desired_heading - yaw_enu)) < math.radians(10.0)
            speed = 1.2 if aligned else 0.0
        else:
            speed = min(2.0, max(0.55, 0.7 * distance))
            desired_heading = math.atan2(error[1], error[0])
        velocity = np.array([speed * direction[0], speed * direction[1], 0.0])
        velocity[2] = float(np.clip(0.7 * (self.altitude - position[2])
                                    - 0.25 * env.drone.velocity[2], -0.4, 0.4))
        yaw_rate = float(np.clip(-wrap(desired_heading - yaw_enu), -0.5, 0.5))
        elapsed = t - self.t0
        if turning_in:
            desired_pan = 0.0
            desired_tilt = math.radians(10.0)
        else:
            desired_pan = float(self.pan_amplitude
                                * math.sin(2.0 * math.pi * elapsed / self.sweep_period))
            desired_tilt = math.radians(18.0)
        pan, tilt = env.data.qpos[env.drone.camera_qpos]
        camera = np.array([3.0 * (desired_pan - pan), 3.0 * (desired_tilt - tilt)])
        raw = self.expert.heading_action(velocity, px4, yaw_rate, camera)
        return raw, self.expert.bounded(raw), None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--probe-seconds", type=float, default=0.0)
    parser.add_argument("--out", default="episode_search")
    parser.add_argument("--instance", type=int, default=0)
    parser.add_argument("--no-video", action="store_true")
    args = parser.parse_args()

    model = mujoco.MjModel.from_binary_path(str(HERE / "scene.mjb"))
    scenario = Scenario80(**{**MAP, "duration": args.duration or MAP["duration"],
                             "name": f"city80_search_{int(args.duration or MAP['duration'])}s"})
    out = HERE / args.out
    if out.exists():
        raise FileExistsError(f"refusing to replace {out}")
    out.mkdir(parents=True)

    environment.compile_scene = lambda *a, **k: model
    fast_physics_windows.install()
    env = environment.Environment(scenario)
    env.boat.navigation.manual()
    apply_start_heading(env)

    expert = Expert(env)
    px4 = WindowsPX4(env, out / "px4", instance=args.instance)
    renderer = recorder = video = None
    started = time.perf_counter()
    rows = 0
    phase_counts = {}
    lock = None
    failure = None
    try:
        px4.start()
        for tick in range(int(np.ceil(env.preparation_budget_s * 25))):
            if tick > 125 and tick % 50 == 0 and not px4.armed:
                px4.arm_offboard()
            px4.send_action(expert.prepare(px4))
            px4.advance()
            if (px4.was_airborne and px4.armed
                    and abs(env.vertical_clearance - scenario.height) < .15
                    and np.linalg.norm(env.drone.velocity) < .3
                    and np.linalg.norm(env.drone.position[:2] - env.task_start_xy) < .15):
                break
        else:
            raise RuntimeError("PX4 preparation did not establish the requested airborne state")

        renderer = OnboardRenderer(env)
        recorder = Recorder(out, json.loads(json.dumps(MAP)), "review")
        if not args.no_video:
            video = SearchVideo(out / "review.mp4")
        director = SearchDirector(env, expert, search_height=scenario.height)

        task_start = float(env.data.time)
        env.task_start_time = task_start
        env.recording = True
        env.boat.navigation.mode = "automatic"
        rng = np.random.default_rng(scenario.seed + 50)
        previous = np.zeros(6)
        initial_view = None
        for index in range(round(scenario.duration * 25)):
            capture = float(env.data.time)
            rgb = renderer.onboard_image()
            rgb = camera_image(rgb, scenario)
            visible, pixels = pad_visibility(env)
            if initial_view is None:
                initial_view = dict(
                    pad_visible=bool(visible),
                    horizontal_range_m=round(float(np.linalg.norm(
                        env.pad_position[:2] - env.drone.position[:2])), 2),
                    task_time_s=0.0,
                )
                from PIL import Image
                Image.fromarray(rgb).save(out / "initial_view_actual.jpg", quality=92)
                if visible:
                    raise RuntimeError("target is visible in the first frame; not a search")
            packet = dict(STATUS_ONLY_BEACON)
            packet.update(age_s=float(env.data.time))
            task_s = capture - task_start
            raw, action, reason = director.act(px4, visible, task_s, pixels)
            phase = expert.phase if director.locked else director.phase
            observation = dict(
                px4=px4.observation(), beacon=packet,
                gimbal_rad=(env.data.qpos[env.drone.camera_qpos]
                            + rng.normal(0, math.radians(.1), 2)).tolist(),
                gimbal_source="synthetic encoder",
                image_capture_time_s=capture, image_delivery_time_s=capture,
                image_age_s=0.0, image_valid=True, decision_dt_s=.04,
                previous_executed_action=previous.tolist(),
            )
            diag = dict(
                actual_command_owner="search_director" if not director.locked else "expert",
                control_phase=phase,
                expert_observable_target_confirmed=bool(director.locked),
                metric_confirmed=bool(director.locked),
                evaluation_fault_active=False,
                search_leg=director.names[min(director.index, len(director.names) - 1)],
                search_flown_m=round(float(np.linalg.norm(
                    env.drone.position[:2] - director.start[:2])), 2),
                pad_visible=bool(visible),
            )
            if director.lock is not None:
                lock = dict(director.lock)
                diag.update(lock_range_m=director.lock["range_m"],
                            lock_time_s=director.lock["task_time_s"])
            row = dict(
                schema="aerodock.landing.step.v1", role="review", frame_index=index,
                time_s=capture, task_time_s=task_s, phase=phase,
                outcome=env.outcome, observation=observation,
                output=dict(expert_raw_action=raw.tolist(), executed_action=action.tolist(),
                            intervention=reason, learner_action=None,
                            learner_diagnostics=diag),
                privileged=dict(
                    drone_position_enu_m=env.drone.position.tolist(),
                    drone_velocity_enu_m_s=env.drone.velocity.tolist(),
                    pad_position_enu_m=env.pad_position.tolist(),
                    pad_velocity_enu_m_s=env.pad_velocity.tolist(),
                    pad_rotation=env.pad_rotation.tolist(), clearance_m=env.clearance,
                    vertical_clearance_m=env.vertical_clearance,
                    pad_visible=bool(visible), pad_keypoints_px=pixels,
                    annotation_and_scoring_only=True,
                ),
            )
            recorder.append(rgb, row)
            frame_rgb = compose(rgb, row)
            if video:
                video.write(frame_rgb)
            if index in (0, 100):
                from PIL import Image
                Image.fromarray(frame_rgb).save(out / f"frame_{index:04d}.jpg", quality=92)
            rows += 1
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            if index % 100 == 0:
                print(json.dumps(dict(
                    task_s=round(task_s, 2), phase=phase, rows=rows,
                    clearance=round(env.clearance, 3), outcome=env.outcome,
                    wall_s=round(time.perf_counter() - started, 1),
                    fps=round(rows / (time.perf_counter() - started), 2),
                )), flush=True)
                (out / "state.json").write_text(json.dumps(dict(
                    status="search_flight", task_s=task_s, phase=phase,
                    rows=rows, outcome=env.outcome, locked=director.locked,
                    wall_s=time.perf_counter() - started), indent=2))

            terminal = env.outcome in ("landed", "water_strike", "collision_failure")
            if terminal:
                rgb = camera_image(renderer.onboard_image(), scenario)
                row["frame_index"] = index + 1
                row["time_s"] = float(env.data.time)
                row["task_time_s"] = float(env.data.time) - task_start
                row["observation"]["px4"] = px4.observation()
                row["observation"]["previous_executed_action"] = action.tolist()
                row["privileged"]["pad_visible"] = bool(pad_visibility(env)[0])
                row["terminal"] = True
                row["output"]["executed_action"] = [0.0] * 6
                recorder.append(rgb, row)
                frame_rgb = compose(rgb, row)
                if video:
                    video.write(frame_rgb)
                from PIL import Image
                Image.fromarray(frame_rgb).save(out / "terminal.jpg", quality=92)
                rows += 1
                break

            px4.send_action(action)
            px4.advance()
            previous = action
            if args.probe_seconds and task_s >= args.probe_seconds:
                print(json.dumps({"event": "probe_stop", "task_s": task_s}), flush=True)
                break
        else:
            env.outcome = "contact_only" if env.first_contact is not None else "timeout"
            env.event(env.outcome)
    except BaseException as exc:
        failure = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        try:
            if recorder:
                recorder.close()
            if video:
                video.close()
        finally:
            try:
                if renderer:
                    renderer.close()
            finally:
                px4.close()
        summary = dict(
            scenario=dict(MAP), outcome=env.outcome, failure=failure, rows=rows,
            phase_counts=phase_counts, lock=lock, initial_view=initial_view,
            events=env.events, wall_s=time.perf_counter() - started,
            fps=rows / max(time.perf_counter() - started, 1e-9),
            video=str(out / "review.mp4"), search_legs=[dict(leg) for leg in SEARCH_LEGS],
            control="stock landing_training.expert.Expert after visual lock",
            note=("Search sweep is a review-only pattern over the declared sector. "
                  "Target lock needs a centred pad-visibility sighting within 55 m "
                  "(identification), not a frame-edge speck. No target position is "
                  "supplied during the search."),
        )
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps({k: summary[k] for k in
                          ("outcome", "rows", "wall_s", "fps", "lock")}, indent=2))


if __name__ == "__main__":
    main()
