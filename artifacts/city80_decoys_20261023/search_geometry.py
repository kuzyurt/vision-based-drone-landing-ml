"""Shared search-frame geometry so the builder and the flight agree exactly."""
import math

import mujoco
import numpy as np
from usv.boat_sim import quaternion


def frame(env):
    """(pad, u, v): u runs from the pad toward the 80 m start, v is 90 deg left."""
    pad = np.asarray(env.pad_position, float)
    axis = np.asarray(env.task_start_xy, float) - pad[:2]
    u = axis / np.linalg.norm(axis)
    return pad, u, np.array([-u[1], u[0]])


def point(env, along, lateral):
    pad, u, v = frame(env)
    return np.array([*(pad[:2] + float(along) * u + float(lateral) * v), 0.0])


def start_heading(env):
    """Heading along the first search leg: broadside to the target."""
    _, _, v = frame(env)
    return math.atan2(v[1], v[0])


def apply_start_heading(env):
    """Review-only start pose: nose along the first leg, target 90 deg off-axis."""
    q = env.drone.free_qadr
    env.data.qpos[q + 3:q + 7] = quaternion(0.0, 0.0, start_heading(env))
    env.data.qvel[env.drone.free_vadr:env.drone.free_vadr + 6] = 0.0
    mujoco.mj_forward(env.model, env.data)


def segment_distance(xy, a, b):
    """Horizontal distance from a point to a segment."""
    xy = np.asarray(xy, float)[:2]
    a = np.asarray(a, float)[:2]
    b = np.asarray(b, float)[:2]
    d = b - a
    t = np.clip(np.dot(xy - a, d) / max(np.dot(d, d), 1e-12), 0.0, 1.0)
    return float(np.linalg.norm(xy - (a + t * d)))
