"""Real MuJoCo scene construction for synthetic search/pad samples."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from .runtime import BASE_XML, configure
from .weather import CLEAR, Weather, apply_scene_weather

configure()

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

from landing_training import environment  # noqa: E402
from landing_training.config import Scenario  # noqa: E402
from target_learning.scenes import annotation_groups, compile_variant  # noqa: E402
from usv.boat_sim import quaternion  # noqa: E402


@dataclass(frozen=True)
class SceneSpec:
    seed: int
    map_kind: str
    distance_m: float
    height_m: float
    bearing_deg: float
    # (distance from target, angular offset from the target-to-drone line)
    decoy_layout: tuple[tuple[float, float], ...] = field(default_factory=tuple)
    camera_pan_deg: float = 0.0
    camera_tilt_offset_deg: float = 0.0
    yaw_offset_deg: float = 0.0
    weather: Weather = CLEAR


def _place_decoys(env, model, groups, spec: SceneSpec) -> None:
    """Move the authored static distractors around the target for this shot."""
    rng = np.random.default_rng(spec.seed + 77)
    target = env.pad_position
    bearing = math.radians(spec.bearing_deg)
    names = sorted(k for k in groups if k.startswith("decoy_") and k != "target")
    if not spec.decoy_layout:
        return
    for index, name in enumerate(names):
        radius, offset_deg = spec.decoy_layout[index % len(spec.decoy_layout)]
        angle = bearing + math.radians(offset_deg)
        mid = int(model.body_mocapid[model.body(name).id])
        if mid < 0:
            continue
        env.data.mocap_pos[mid] = [
            target[0] + radius * math.cos(angle),
            target[1] + radius * math.sin(angle),
            0.03,
        ]
        yaw = float(rng.uniform(-math.pi, math.pi))
        env.data.mocap_quat[mid] = quaternion(0.0, 0.0, yaw)


def _set_drone_pose(env, spec: SceneSpec) -> None:
    """Place the drone at a requested bearing/range/height and look at the pad."""
    pad = env.pad_position.copy()
    bearing = math.radians(spec.bearing_deg)
    xy = pad[:2] + spec.distance_m * np.array([math.cos(bearing), math.sin(bearing)])
    q = env.drone.free_qadr
    env.data.qpos[q : q + 3] = [xy[0], xy[1], pad[2] + spec.height_m]
    yaw = math.atan2(pad[1] - xy[1], pad[0] - xy[0]) + math.radians(spec.yaw_offset_deg)
    env.data.qpos[q + 3 : q + 7] = quaternion(0.0, 0.0, yaw)
    tilt = math.atan2(spec.height_m, spec.distance_m) + math.radians(spec.camera_tilt_offset_deg)
    tilt = float(np.clip(tilt, 0.0, math.pi / 2))
    env.data.qpos[env.drone.camera_qpos] = [math.radians(spec.camera_pan_deg), tilt]
    env.data.qvel[:] = 0.0
    mujoco.mj_forward(env.model, env.data)


def build_scene(spec: SceneSpec, workdir: Path):
    """Compile a fresh variant and return (env, model, annotation groups).

    The source XML, materials, boat CAD, and canonical build cache are reused.
    The variant is written only under the caller's temporary work directory.
    """
    workdir = Path(workdir)
    workdir.parent.mkdir(parents=True, exist_ok=True)
    # compile_variant owns creation of the variant directory.
    model = compile_variant(BASE_XML, workdir, seed=spec.seed, sun=True, distractors=True)

    # Environment normally compiles the canonical cache. Point it at this
    # variant for the duration of this one render only.
    environment.compile_scene = lambda *args, **kwargs: model
    scenario = Scenario(
        name=f"synthetic_{spec.map_kind}_{spec.seed}",
        kind=spec.map_kind,
        world_seed=spec.seed + 1,
        path_seed=spec.seed + 2,
        seed=spec.seed,
        distance=float(np.clip(spec.distance_m, 2.0, 60.0)),
        height=float(np.clip(spec.height_m, 1.2, 8.0)),
        boat_speed=0.0,
        wave_height=spec.weather.wave_height,
        wave_period=spec.weather.wave_period,
        wind_profile=spec.weather.wind_profile,
        wind_direction_deg=spec.weather.wind_direction_deg,
        duration=60.0,
    )
    env = environment.Environment(scenario)
    env.boat.navigation.manual()
    groups = annotation_groups(model)
    _place_decoys(env, model, groups, spec)
    _set_drone_pose(env, spec)
    camera_forward = spec.bearing_deg + 180.0 + spec.yaw_offset_deg + spec.camera_pan_deg
    apply_scene_weather(env, spec.weather, camera_forward)
    return env, model, groups
