"""Interactive Tidewater runtime: original AERODOCK/PX4 MuJoCo vehicles."""
from __future__ import annotations

import asyncio
import json
import math
import os
import shlex
import select
import socket
import struct
import subprocess
import sys
import threading
import time
import traceback
import orjson
from pathlib import Path

import cv2
import mujoco
import numpy as np
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

SIM_DIR = Path(__file__).resolve().parent
GAME_DIR = SIM_DIR.parent
REPO = SIM_DIR.parents[1]
RUNTIME = SIM_DIR / "runtime"
RUNTIME.mkdir(parents=True, exist_ok=True)
sys.dont_write_bytecode = True
sys.setswitchinterval(.001)
sys.path.insert(0, str(REPO))
from landing_training import paths as _paths  # noqa: E402
from landing_training.config import Scenario  # noqa: E402
from landing_training.environment import DronePhysics, object_velocity  # noqa: E402
from landing_training.px4 import NativePX4  # noqa: E402
from landing_training.scene import compile_scene, DRONE, FEET  # noqa: E402
from landing_training.environment import Wind, directional_drag  # noqa: E402
from usv.boat_sim import BoatSim, quaternion  # noqa: E402
from sim.propulsion import THRUST, TORQUE, THRUST_MODEL_FACTOR  # noqa: E402

MAV = __import__("pymavlink.dialects.v20.common", fromlist=["MAVLink"])
PX4_TO_CAD = np.array([0, 2, 1, 3])
SPIN = np.array([-1., 1., -1., 1.])
C = np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0.]])


class ClosedRoute:
    def __init__(self, points: np.ndarray):
        self.points = np.asarray(points, dtype=np.float64)
        self.points = np.vstack((self.points, self.points[0]))
        self.arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(self.points, axis=0), axis=1))]
        self.length = float(self.arc[-1])
        self.direction = 1
        self.seed = 1
        self.speeds = np.full(len(self.points), 2.8)
        self.offsets = np.zeros(len(self.points))
        self.coast_s = np.zeros(len(self.points))
        self.segments = ["front beach loop"] * len(self.points)

    def at(self, distance: float):
        s = float(distance) % self.length
        point = np.array([np.interp(s, self.arc, self.points[:, axis]) for axis in range(2)])
        speed = float(np.interp(s, self.arc, self.speeds))
        return point, speed, "front beach loop"

    def export(self):
        return {"path_seed": self.seed, "direction": 1, "length_m": self.length,
                "waypoints": self.points.tolist(), "closed": True}


class TidewaterMap:
    """Signed coast and bathymetry in the MuJoCo ENU horizontal frame."""
    kind = "island"
    seed = 714

    def __init__(self, meta: dict, heights: np.ndarray):
        self.origin = float(meta["origin"])
        self.size = float(meta["size"])
        self.res = int(meta["res"])
        self.texel = self.size / self.res
        self.heights = heights.reshape(self.res, self.res)
        self.boxes = meta["colliders"].get("boxes", [])
        self.cylinders = meta["colliders"].get("cylinders", [])
        contours, _ = cv2.findContours((self.heights > 0).astype(np.uint8),
                                        cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ValueError("Tidewater terrain did not contain a coastline")
        contour = max(contours, key=cv2.contourArea)
        contour = cv2.approxPolyDP(contour, 1.5, True)[:, 0, :].astype(np.float64)
        # Terrain rows increase toward Tidewater +Z. MuJoCo uses +Y north.
        self.coast = np.column_stack((self.origin + (contour[:, 0] + .5) * self.texel,
                                      -(self.origin + (contour[:, 1] + .5) * self.texel)))
        area = np.sum(self.coast[:, 0] * np.roll(self.coast[:, 1], -1) -
                      np.roll(self.coast[:, 0], -1) * self.coast[:, 1])
        if area < 0:
            self.coast = self.coast[::-1].copy()
        self.coast = np.vstack((self.coast, self.coast[0]))
        self.contour = self.coast[:-1].astype(np.float32).reshape(-1, 1, 2)
        self.arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(self.coast, axis=0), axis=1))]
        self.coast_length = float(self.arc[-1])
        self.route = ClosedRoute(self._choose_route())

    def height_at(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        # Horizontal MuJoCo Y is the negative of Tidewater's Z.
        col = np.clip(((np.asarray(x) - self.origin) / self.texel).astype(int), 0, self.res - 1)
        row = np.clip(((-np.asarray(y) - self.origin) / self.texel).astype(int), 0, self.res - 1)
        return self.heights[row, col]

    def distance(self, xy):
        points = np.atleast_2d(np.asarray(xy, dtype=np.float64))
        return np.array([-cv2.pointPolygonTest(self.contour, tuple(map(float, p)), True)
                         for p in points])

    def sample(self, s):
        s = float(s) % self.coast_length
        p = np.array([np.interp(s, self.arc, self.coast[:, i]) for i in range(2)])
        a = (s - 2.) % self.coast_length
        b = (s + 2.) % self.coast_length
        tangent = np.array([np.interp(b, self.arc, self.coast[:, i]) -
                            np.interp(a, self.arc, self.coast[:, i]) for i in range(2)])
        tangent /= max(float(np.linalg.norm(tangent)), 1e-9)
        return p, np.array([tangent[1], -tangent[0]]), tangent

    def _collider_clear(self, point: np.ndarray, radius=8.):
        x, y = point
        for box in self.boxes:
            center, half = box["center"], box["half"]
            # Skip structures well above the waterline and objects outside the
            # route's radius-expanded bounding square.
            if center[1] - half[1] > 1.8 or center[1] + half[1] < -2.0:
                continue
            if abs(x - center[0]) > radius + math.hypot(half[0], half[2]):
                continue
            if abs(y + center[2]) > radius + math.hypot(half[0], half[2]):
                continue
            a = float(box.get("rotY", 0.))
            dx, dy = x - center[0], y + center[2]
            lx, ly = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
            if abs(lx) < half[0] + radius and abs(ly) < half[2] + radius:
                return False
        for cyl in self.cylinders:
            if cyl["yMin"] > 1.8 or cyl["yMax"] < -2.0:
                continue
            if math.hypot(x - cyl["x"], y + cyl["z"]) < radius + cyl["radius"]:
                return False
        return True

    def _choose_route(self):
        # The loop stays seaward of the complete pier, follows the central bay,
        # and searches only through the actual Tidewater heightfield/colliders.
        angles = np.linspace(math.pi, 3 * math.pi, 721, endpoint=False)
        # An eight-metre swept envelope covers the hull in every heading,
        # steering error and the coarser physics heightfield.
        offsets = np.array([[0, 0], [8, 0], [-8, 0], [0, 8], [0, -8],
                            [5.7, 5.7], [5.7, -5.7], [-5.7, 5.7], [-5.7, -5.7]])
        candidates = []
        for cx, cz, rx, rz in ((40, 170, 100, 65), (20, 190, 110, 65),
                                (40, 190, 100, 65), (20, 210, 110, 75),
                                (0, 230, 120, 75), (0, 260, 120, 75)):
            # Polar ellipse starts at its western end and moves smoothly offshore.
            x = cx + rx * np.cos(angles)
            z = cz + rz * np.sin(angles)
            route = np.column_stack((x, -z))
            samples = route[:, None, :] + offsets[None, :, :]
            depths = self.height_at(samples[:, :, 0], samples[:, :, 1])
            if np.any(depths > -2.2):
                continue
            if any(not self._collider_clear(p, radius=9.) for p in route):
                continue
            coast_gap = self.distance(route[::4])
            if np.min(coast_gap) < 14.:
                continue
            length = float(np.sum(np.linalg.norm(np.diff(np.vstack((route, route[0])), axis=0), axis=1)))
            if length < 480:
                continue
            # Prefer a broad, long route near the front beach, with full depth.
            score = abs(cz - 150.) + abs(cx - 135.) * .25 - length * .012
            candidates.append((score, route))
        if not candidates:
            raise ValueError("No closed boat route cleared the beach, pier, terrain and obstacles")
        return min(candidates, key=lambda candidate: candidate[0])[1]


def _matrix(position, rotation):
    transform = np.eye(4)
    transform[:3, :3] = C @ np.asarray(rotation).reshape(3, 3)
    transform[:3, 3] = C @ np.asarray(position)
    return transform.reshape(-1).tolist()


def visual_layout_from(model):
    roots = (model.body("boat").id, model.body("drone_base_link").id)
    layout = []
    for gid in range(model.ngeom):
        root = int(model.geom_bodyid[gid])
        while root not in (0, *roots):
            root = int(model.body_parentid[root])
        if (root in roots and model.geom_group[gid] < 3 and model.geom_rgba[gid, 3] > 0
                and model.geom_type[gid] == mujoco.mjtGeom.mjGEOM_MESH):
            local = np.eye(4)
            rotation = np.empty(9)
            mujoco.mju_quat2Mat(rotation, model.geom_quat[gid])
            local[:3, :3] = rotation.reshape(3, 3)
            local[:3, 3] = model.geom_pos[gid]
            layout.append([model.geom(gid).name, local.reshape(-1).tolist(),
                           model.body(int(model.geom_bodyid[gid])).name])
    return layout


class GameEnvironment:
    """Interactive form of the existing 1 ms combined training physics."""
    def __init__(self, model, meta, heights, use_native=True, visual_layout=None):
        self.model = model
        self.data = mujoco.MjData(model)
        self.scenario = Scenario(seed=714, world_seed=714, path_seed=714,
                                 wave_height=.05, wave_period=3.0,
                                 wave_direction_deg=35., boat_speed=0.)
        self.boat = BoatSim(model=model, data=self.data)
        self.world = TidewaterMap(meta, heights)
        self.boat.navigation.world = self.world
        self.boat.navigation.spawn()
        self.boat.navigation.mode = "manual"
        self.boat.navigation.next_update = 0.
        self.boat.navigation.progress = 0.
        self.boat.set_environment(wave_height=.05, wave_period=3., wave_direction=35.)
        self.boat.wave_phases = np.array([0., 1.3, 2.1, .7])
        self.drone = DronePhysics(model, self.data)
        self.wind = Wind(profile="calm", seed=714)
        self.tick = 0
        self.boat_auto = True
        self.launch_complete = False
        self.course_progress = 0.
        self.course_error = 0.
        self.target_speed = 2.8
        self.pan = 0.
        self.tilt = 0.
        self.target_altitude = 0.
        self.takeoff_requested = False
        self.home_height = 0.216
        self.last_arm = -10.
        self.radio = RadioModel()
        self.realtime_factor = 1.
        self.meta = meta

        for index in range(model.neq):
            name = model.eq(index).name or ""
            if name.startswith("prepared_"):
                self.data.eq_active[index] = 0

        boat_q = self.boat.free_qadr
        self.data.qpos[boat_q:boat_q + 2] = self.world.route.points[0]
        dxy = self.world.route.points[1] - self.world.route.points[0]
        boat_yaw = math.atan2(dxy[1], dxy[0])
        self.data.qpos[boat_q + 3:boat_q + 7] = quaternion(0., 0., boat_yaw)
        self._set_mechanisms((.4, .46, .46))

        pad = model.body("launch_pad").id
        self.launch_mid = int(model.body_mocapid[pad])
        # The training scene also has a world-fixed launch pad. A moving mocap
        # pad does not transfer the boat's velocity through contact friction.
        # Use the original articulated boat platform for physical support.
        launch_geom = model.geom("launch_contact").id
        model.geom_contype[launch_geom] = 0
        model.geom_conaffinity[launch_geom] = 0
        self.pad_site = model.site("landing_center").id
        self.pad_geom = model.geom("landing_contact").id
        platform = model.body("platform").id
        self.platform_body = platform
        self._sync_screws()
        mujoco.mj_forward(model, self.data)
        self._follow_launch_pad()
        drone_q = self.drone.free_qadr
        self.data.qpos[drone_q:drone_q + 3] = self.data.site_xpos[self.pad_site] + [0., 0., .012 - self.drone.bottom]
        self.data.qpos[drone_q + 3:drone_q + 7] = quaternion(0., 0., boat_yaw)
        self.data.qvel[self.drone.free_vadr:self.drone.free_vadr + 6] = 0.
        mujoco.mj_forward(model, self.data)
        self._follow_launch_pad()
        self.wind_on_boat(self.wind.velocity)

        self.static_ids = {i for i in range(model.ngeom)
                           if model.geom(i).name.startswith("tidewater_")}
        self.visual_layout = visual_layout if visual_layout is not None else visual_layout_from(model)
        self.visual_bodies = sorted({model.body(part[2]).id for part in self.visual_layout})
        self.native = None
        self.exact_flight = model.opt.timestep == .001
        self.force_stride = max(1, round(.004/model.opt.timestep))
        self.cached_qfrc = np.zeros(model.nv)
        self.cached_xfrc = np.zeros((model.nbody, 6))
        if use_native:
            from native_forces import NativeForces
            self.native = NativeForces(self)
            # Compile and cache the kernels before PX4 begins lockstep.
            self.native.apply(self.wind.velocity)
            self.native.controls()
            self.native.after_step(self.wind.velocity)
            self.data.qfrc_applied[:] = 0.
            self.data.xfrc_applied[:] = 0.

    def _sync_screws(self):
        for index in range(self.model.neq):
            if self.model.eq_type[index] != mujoco.mjtEq.mjEQ_JOINT:
                continue
            j1, j2 = int(self.model.eq_obj1id[index]), int(self.model.eq_obj2id[index])
            if j1 < 0 or j2 < 0:
                continue
            q1 = self.model.jnt_qposadr[j1]
            q2 = self.model.jnt_qposadr[j2]
            self.data.qpos[q1] = np.polynomial.polynomial.polyval(
                self.data.qpos[q2], self.model.eq_data[index, :5])

    def _set_mechanisms(self, positions):
        positions = np.asarray(positions, dtype=float)
        names = ("platform_slide", "aft_lid_slide", "fore_lid_slide")
        for i, name in enumerate(names):
            self.data.qpos[self.boat.qadr[name]] = positions[i]
        self.boat.targets[:] = positions
        self.boat.servos[:] = positions

    def _follow_launch_pad(self):
        self.data.mocap_pos[self.launch_mid] = self.data.site_xpos[self.pad_site] + [0., 0., .055]
        self.data.mocap_quat[self.launch_mid] = self.data.xquat[self.platform_body]

    def wind_on_boat(self, wind):
        R = self.data.xmat[self.boat.boat].reshape(3, 3)
        center = self.data.xpos[self.boat.boat] + R @ np.array([0., 0., .55])
        velocity = object_velocity(self.model, self.data, mujoco.mjtObj.mjOBJ_BODY, self.boat.boat)
        relative = R.T @ (velocity[3:] + np.cross(velocity[:3], center - self.data.xipos[self.boat.boat]) - wind)
        force = R @ np.array([directional_drag(relative[i], (.22, .6, 0.)[i]) for i in range(3)])
        mujoco.mj_applyFT(self.model, self.data, force, np.zeros(3), center,
                          self.boat.boat, self.data.qfrc_applied)

    def step(self, armed):
        if self.native is not None and self.exact_flight:
            return self.step_exact_flight(armed)
        if self.native is None:
            return self.step_reference(armed)
        m, d, n = self.model, self.data, self.native
        if d.time + 1e-8 >= self.boat.navigation.next_update:
            self.boat.navigation.update()
            for gid in self.boat.navigation.contact_ids:
                if m.geom_contype[gid]:
                    m.geom_contype[gid] = 4
                    m.geom_conaffinity[gid] = 1
        n.before_step()
        mujoco.mj_step1(m, d)
        wind = self.wind.velocity if self.wind.profile == "calm" else self.wind.step(d.time, m.opt.timestep)
        # External fluid/electrical forces at 250 Hz; every engine step uses
        # the original implicitfast solver and unmodified collision shapes.
        if self.tick % self.force_stride == 0:
            d.qfrc_applied[:] = 0.
            d.xfrc_applied[:] = 0.
            n.apply(wind)
            self.cached_qfrc[:] = d.qfrc_applied
            self.cached_xfrc[:] = d.xfrc_applied
        else:
            d.qfrc_applied[:] = self.cached_qfrc
            d.xfrc_applied[:] = self.cached_xfrc
        # Motor, gimbal and mechanism feedback runs every engine step.
        n.controls()
        mujoco.mj_step2(m, d)
        if self.tick % self.force_stride == self.force_stride-1:
            self.boat.refresh_transforms()
            n.after_step(wind, m.opt.timestep*self.force_stride)
        if self.boat.drainage:
            self.boat.drainage.step(m.opt.timestep)
        self.boat.busy = bool(np.max(np.abs(self.boat.targets-self.boat._positions())) > .004 or
                              np.max(np.abs(self.boat.servos-self.boat.targets)) > .0005)
        if not np.isfinite(d.qpos).all():
            raise RuntimeError("Non-finite MuJoCo state")
        self.tick += 1

    def step_exact_flight(self, armed):
        """Original flight.physics ordering: four 1 ms steps per PX4 output.

        Drone targets are held across that 4 ms actuator cycle; forces and
        electrical load are recalculated on every original engine step.
        Boat water forces keep their separate 250 Hz cadence.
        """
        m, d, n, u = self.model, self.data, self.native, self.drone
        self.armed = armed
        if d.time+1e-8 >= self.boat.navigation.next_update:
            self.boat.navigation.update()
            for gid in self.boat.navigation.contact_ids:
                if m.geom_contype[gid]:
                    m.geom_contype[gid], m.geom_conaffinity[gid] = 4, 1
        n.before_step()
        wind = self.wind.velocity if self.wind.profile == 'calm' else self.wind.step(d.time, .001)
        if self.tick % 4 == 0:
            d.qfrc_applied[:] = 0.
            d.xfrc_applied[:] = 0.
            n.apply_boat(wind)
            self.cached_qfrc[:] = d.qfrc_applied
            self.cached_xfrc[:] = d.xfrc_applied
            u.targets = u.power.targets(np.where(u.failed, 0., u.commands))
            n.electrical[:] = [u.power.charge_Ah, u.power.voltage, u.power.current, float(u.power.limited)]
        else:
            d.qfrc_applied[:] = self.cached_qfrc
            d.xfrc_applied[:] = self.cached_xfrc
        n.apply_drone(wind, update_targets=False)
        n.project_drone_forces()
        mujoco.mj_step(m, d)
        n.after_step(wind)
        if self.boat.drainage:
            self.boat.drainage.step(.001)
        if self.tick % 4 == 3:
            self.boat.busy = bool(np.max(np.abs(self.boat.targets-self.boat._positions())) > .004 or np.max(np.abs(self.boat.servos-self.boat.targets)) > .0005)
            if not np.isfinite(d.qpos).all():
                raise RuntimeError('Non-finite MuJoCo state')
        self.tick += 1

    def step_reference(self, armed):
        m, d = self.model, self.data
        dt = m.opt.timestep
        self.boat.navigation.update()
        for gid in self.boat.navigation.contact_ids:
            if m.geom_contype[gid]:
                m.geom_contype[gid] = 4
                m.geom_conaffinity[gid] = 1
        speeds = np.array([self.boat.config["lift_speed_mps"],
                           self.boat.config["lid_speed_mps"], self.boat.config["lid_speed_mps"]])
        self.boat.servos += np.clip(self.boat.targets - self.boat.servos, -speeds * dt, speeds * dt)
        denominator = (2 * math.pi * self.boat.config["water_density"] *
                       self.boat.config["propeller_diameter_m"] ** 5 * self.boat.config["propeller_KQ"])
        desired = np.minimum(self.boat.config["max_propeller_rps"],
                             np.cbrt(self.boat.power / 100 * self.boat.config["max_shaft_power_w"] / denominator))
        self.boat.rps += (desired - self.boat.rps) * (1 - math.exp(-dt / self.boat.config["motor_response_seconds"]))
        self._follow_launch_pad()
        mujoco.mj_step1(m, d)
        d.qfrc_applied[:] = 0.
        d.xfrc_applied[:] = 0.
        self.boat._set_actuators()
        self.boat.apply_water(clear_forces=False)
        wind = self.wind.step(d.time, dt)
        self.wind_on_boat(wind)
        self.drone.apply(wind)
        mujoco.mj_step2(m, d)
        self.boat.refresh_transforms()
        self.drone.after_step(wind)
        if self.boat.drainage:
            self.boat.drainage.step(dt)
        if not np.isfinite(d.qpos).all():
            raise RuntimeError("Non-finite MuJoCo state")
        self.tick += 1
        self.boat.busy = bool(np.max(np.abs(self.boat.targets-self.boat._positions())) > .004 or
                              np.max(np.abs(self.boat.servos-self.boat.targets)) > .0005)

    def drone_state(self):
        d, m = self.data, self.model
        pos = d.xpos[self.drone.base].copy()
        vel = object_velocity(m, d, mujoco.mjtObj.mjOBJ_BODY, self.drone.base)[3:]
        R = d.xmat[self.drone.base].reshape(3, 3)
        roll = math.atan2(R[2, 1], R[2, 2])
        pitch = math.asin(float(np.clip(-R[2, 0], -1., 1.)))
        yaw = math.atan2(R[1, 0], R[0, 0])
        return {"position": [float(pos[0]), float(pos[2]), float(-pos[1])],
                "velocity": [float(vel[0]), float(vel[2]), float(-vel[1])],
                "roll": roll, "pitch": pitch, "yaw": yaw,
                "heading": (math.pi / 2 - yaw) % (2 * math.pi),
                "speed": float(np.linalg.norm(vel)), "pan": float(d.qpos[self.drone.camera_qpos[0]]),
                "tilt": float(d.qpos[self.drone.camera_qpos[1]]),
                "altitude": float(pos[2]), "battery_v": float(self.drone.power.voltage),
                "battery_pct": float(self.drone.power.charge_Ah / 12. * 100),
                "armed": bool(getattr(self, "armed", False)),
                "failed_rotors": self.drone.failed.astype(bool).tolist()}

    def boat_state(self):
        d, m = self.data, self.model
        R = d.xmat[self.boat.boat].reshape(3, 3)
        vel = object_velocity(m, d, mujoco.mjtObj.mjOBJ_BODY, self.boat.boat)[3:]
        pos = d.xpos[self.boat.boat]
        return {"position": [float(pos[0]), float(pos[2]), float(-pos[1])],
                "velocity": [float(vel[0]), float(vel[2]), float(-vel[1])],
                "speed": float(self.boat.get_speed("m/s")),
                "heading": (math.pi / 2 - math.atan2(R[1, 0], R[0, 0])) % (2 * math.pi),
                "pitch": float(math.atan2(R[2, 0], R[2, 2])),
                "roll": float(math.atan2(R[2, 1], R[2, 2])),
                "port_power": float(self.boat.power[0]), "starboard_power": float(self.boat.power[1]),
                "platform": float(np.clip(self.boat._positions()[0] / .4, 0, 1)),
                "aft_lid": float(np.clip(self.boat._positions()[1] / .46, 0, 1)),
                "fore_lid": float(np.clip(self.boat._positions()[2] / .46, 0, 1)),
                "mechanism_busy": bool(self.boat.busy),
                "platform_target": float(self.boat.targets[0] / .4),
                "aft_lid_target": float(self.boat.targets[1] / .46),
                "fore_lid_target": float(self.boat.targets[2] / .46)}

    def _route_control(self, dt):
        route = self.world.route
        pos = self.data.xpos[self.boat.boat, :2]
        lo = int(np.searchsorted(route.arc, self.course_progress, side="right") - 4)
        lo = max(0, min(lo, len(route.points) - 3))
        hi = min(len(route.points) - 1, lo + 30)
        a = route.points[lo:hi]
        delta = route.points[lo + 1:hi + 1] - a
        frac = np.clip(((pos - a) * delta).sum(axis=1) / np.maximum((delta * delta).sum(axis=1), 1e-9), 0., 1.)
        nearest_points = a + delta * frac[:, None]
        nearest = int(np.argmin(np.linalg.norm(nearest_points - pos, axis=1)))
        projected = route.arc[lo + nearest] + frac[nearest] * (route.arc[lo + nearest + 1] - route.arc[lo + nearest])
        self.course_progress = max(self.course_progress, float(projected)) % route.length
        self.course_error = float(np.linalg.norm(nearest_points[nearest] - pos))
        goal, speed_target, _ = route.at(self.course_progress + max(12., 5. * self.boat.get_speed("m/s")))
        R = self.data.xmat[self.boat.boat].reshape(3, 3)
        yaw = math.atan2(R[1, 0], R[0, 0])
        desired = math.atan2(goal[1] - pos[1], goal[0] - pos[0])
        error = math.atan2(math.sin(desired - yaw), math.cos(desired - yaw))
        speed_target *= max(.35, math.cos(error))
        base = float(np.clip(2.8 * speed_target ** 3 + 4 * speed_target +
                             12 * (speed_target - self.boat.get_speed("m/s")), 0., 78.))
        yaw_rate = float(self.data.qvel[self.boat.free_vadr + 5])
        turn = float(np.clip(60 * error - 85 * yaw_rate, -base, base))
        self.boat.power[:] = np.clip([base + turn, base - turn], 0., 100.)
        self.target_speed = speed_target

    def control_boat(self, command, dt):
        if self.boat_auto:
            self._route_control(dt)
        else:
            self.boat.power[:] = np.clip(command.get("motors", self.boat.power), 0., 100.)
            self.boat.navigation.mode = "manual"

    def views(self):
        d, m = self.data, self.model
        views = {}
        for name, camera_name in (("drone", "drone_onboard"),
                                  ("boat_dock", "DockCamera"),
                                  ("boat_nav", "NavigationCamera")):
            camera = m.camera(camera_name).id
            views[name] = {"matrix": _matrix(d.cam_xpos[camera], d.cam_xmat[camera]),
                           "fovy": float(m.cam_fovy[camera])}
        return views

    def geom_transforms(self):
        return self.visual_layout

    def body_transforms(self):
        return [[self.model.body(i).name, _matrix(self.data.xpos[i], self.data.xmat[i])]
                for i in self.visual_bodies]

    def wave_coefficients(self):
        angles = math.radians(self.boat.wave_direction) + np.array([0., .38, -.52, .9])
        omega = 2 * math.pi / (self.boat.wave_period * np.array([1., .72, 1.31, .52]))
        k = omega**2 / self.boat.gravity
        amplitude = self.boat.wave_height * .5 * np.array([.55, .23, .15, .07])
        return np.column_stack((k*np.cos(angles), -k*np.sin(angles), amplitude,
                                self.boat.wave_phases-self.data.time*omega)).tolist()


def make_controller(env):
    if os.environ.get("TIDEWATER_CONTROLLER", "px4") == "px4":
        return GamePX4(env)
    from native_controller import NativeController
    return NativeController(env)


class RadioModel:
    """Clearly labelled packet-level SX1262 link estimate; no radio hardware."""
    def __init__(self):
        self.rng = np.random.default_rng(0x1262)
        self.elapsed = 0.
        self.tx = self.rx = self.dropped = 0
        self.samples = []
        self.connected = True
        self.retry_pending = False
        self.quality = 100
        self.reconnect = 0.
        self.last_remote = None
        self.last_rx_time = 0.
        self.state = {}

    def request(self):
        self.reconnect = 1.2
        self.retry_pending = True

    def update(self, dt, env, obstacles, now):
        boat = env.boat_state()
        drone = env.drone_state()
        a = np.array([*boat["position"][:1], boat["position"][1] + 2.5, boat["position"][2]])
        b = np.array([drone["position"][0], drone["position"][1], drone["position"][2]])
        distance = float(np.linalg.norm(b - a))
        steps = max(4, min(80, int(distance / 4)))
        blocked = False
        for t in np.linspace(.08, .92, steps):
            p = a + (b - a) * t
            if env.world.height_at(p[0], -p[2]) > p[1] - .35:
                blocked = True
                break
        if not blocked:
            for box in obstacles["boxes"]:
                c, h = box["center"], box["half"]
                if c[1] - h[1] > max(a[1], b[1]) or c[1] + h[1] < min(a[1], b[1]):
                    continue
                mid = (a + b) * .5
                if abs(mid[0] - c[0]) < h[0] + distance * .5 and abs(mid[2] - c[2]) < h[2] + distance * .5:
                    # Sample the segment through the obstacle footprint.
                    ang = float(box.get("rotY", 0.))
                    dx, dz = mid[0] - c[0], mid[2] - c[2]
                    if abs(dx * math.cos(ang) - dz * math.sin(ang)) < h[0] + .5 and abs(dx * math.sin(ang) + dz * math.cos(ang)) < h[2] + .5:
                        blocked = True
                        break
        attenuation = 1. if blocked else 0.
        self.quality = int(np.clip(100 - distance * .26 - attenuation * 82, 0, 100))
        self.rssi = -42. - 20 * math.log10(max(distance, 1.)) - attenuation * 38.
        self.snr = float(np.clip(10.5 - (100 - self.quality) * .38, -20, 10.5))
        self.elapsed += dt
        if self.reconnect > 0:
            self.reconnect = max(0., self.reconnect - dt)
        while self.elapsed >= .25:
            self.elapsed -= .25
            self.tx += 1
            receive_chance = float(np.clip((self.quality - 5.) / 95., 0., 1.))
            if self.rng.random() < receive_chance:
                self.rx += 1
                self.samples.append(0)
                self.last_remote = {"boat": boat, "drone": drone}
                self.last_rx_time = now
            else:
                self.dropped += 1
                self.samples.append(1)
            self.samples = self.samples[-40:]
        loss = 100. * sum(self.samples) / max(1, len(self.samples))
        if self.reconnect <= 0. and (self.quality < 8 or (len(self.samples) >= 4 and loss > 78)):
            self.connected = False
        elif (self.retry_pending and self.reconnect <= 0. and not self.connected and
              self.quality > 24 and (not self.samples or loss < 62)):
            self.connected = True
            self.retry_pending = False
        self.state = {"status": "handshake" if self.reconnect > 0 else
                      ("lost" if not self.connected else "critical" if self.quality < 30 else
                       "degraded" if self.quality < 62 else "stable"),
                      "connected": self.connected, "quality": self.quality,
                      "rssi": round(self.rssi, 1), "snr": round(self.snr, 1),
                      "latency": int(36 + (100 - self.quality) * 1.2),
                      "packet_loss": round(loss, 1), "distance": round(distance, 1),
                      "tx": self.tx, "rx": self.rx, "dropped": self.dropped,
                      "simulated": True, "frequency_mhz": 868, "spreading_factor": 7,
                      "telemetry_age_s": round(max(0., now - self.last_rx_time), 2)}


class GamePX4(NativePX4):
    source = "PX4 v1.16 SITL + MuJoCo"
    """Native PX4 bridge using the already installed WSL SITL build."""
    def __init__(self, env):
        self.distro = os.environ.get("PX4_WSL_DISTRO", "Ubuntu-22.04")
        self.gateway = self._gateway() if os.name == "nt" else "127.0.0.1"
        self.px4_dir = self._px4_dir()
        super().__init__(env, RUNTIME, instance=0)
        self.listener.close()
        self.listener = socket.socket()
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("0.0.0.0", 4560))
        self.listener.listen(1)
        self.listener.setblocking(False)
        self.offboard.close()
        self.offboard = __import__("pymavlink.mavutil", fromlist=["mavlink_connection"]).mavlink_connection(
            "udpin:0.0.0.0:14541", source_system=255, source_component=190, dialect="common")
        self.power_mav = MAV.MAVLink(self.offboard, srcSystem=1, srcComponent=180)
        rc = (RUNTIME / "rcS").read_text(encoding="utf-8")
        old = "mavlink start -u 18000 -o 19000 -t 127.0.0.1 -m onboard -r 150000"
        new = f"mavlink start -u 14581 -o 14541 -t {self.gateway} -m onboard -r 150000"
        if old not in rc:
            raise RuntimeError("Unexpected native PX4 startup script; transport config was not changed")
        (RUNTIME / "rcS").write_text(rc.replace(old, new), encoding="utf-8")
        self.flight_requested = False
        self.takeoff_pending = False
        self.target_height = 0.
        self.home_height = .216
        self.last_setpoint = 0.
        self.operator_time = 0.
        self.last_arm = -10.
        self.log = (RUNTIME / "px4.log").open("w", encoding="utf-8")
        self.launcher = None
        parameters = json.loads((DRONE / 'build/px4_configuration.json').read_text(encoding='utf-8'))['parameters']
        parameter_lines = [f"param set {key} {value}" for key, value in parameters.items()]
        (RUNTIME / "px4_parameters.sh").write_text("\n".join(parameter_lines) + "\n",
                                                    encoding="utf-8")
        self.rng = np.random.default_rng(714)
        from px4_pilot import OriginalPilot
        self.pilot = OriginalPilot(self)

    def _wsl(self, *args, timeout=20):
        script = "exec " + " ".join(shlex.quote(str(arg)) for arg in args) + "\n"
        runner = ["wsl.exe", "-d", self.distro, "--", "bash", "-s"] if os.name == "nt" else ["bash", "-s"]
        result = subprocess.run(runner,
                                input=script.encode("utf-8"), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            raise RuntimeError("PX4 WSL command failed: " + result.stdout.decode("utf-8", errors="replace").strip())
        return result.stdout.decode("utf-8").strip()

    def _gateway(self):
        route = self._wsl("ip", "-4", "route", "show", "default")
        fields = route.split()
        if len(fields) < 3 or fields[0] != "default":
            raise RuntimeError("WSL did not report a Windows gateway for PX4 SITL")
        socket.inet_aton(fields[2])
        return fields[2]

    def _px4_dir(self):
        script = ("for d in \"${PX4_AUTOPILOT_DIR:-}\" "
                  "$HOME/.cache/px4-mujoco-drone-simulation/PX4-Autopilot "
                  "$HOME/.cache/smartdrone2/PX4-Autopilot; do "
                  "[ -n \"$d\" ] && [ -x \"$d/build/px4_sitl_default/bin/px4\" ] && "
                  "[ \"$(git -C \"$d\" rev-parse HEAD 2>/dev/null)\" = "
                  "6ea3539157ca358c70a515878b77077af7d4611d ] && { printf '%s' \"$d\"; exit 0; }; "
                  "done; exit 1")
        # WSL's Windows argument parser removes nested quotes from bash -lc.
        # Send shell source through stdin as LF bytes instead.
        runner = ["wsl.exe", "-d", self.distro, "--", "bash", "-s"] if os.name == "nt" else ["bash", "-s"]
        result = subprocess.run(runner,
                                input=(script + "\n").encode("utf-8"),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        if result.returncode:
            raise RuntimeError("The pinned PX4 SITL executable was not found in WSL")
        return result.stdout.decode("utf-8").strip()

    def start(self):
        runtime_wsl = self._wsl("wslpath", "-u", str(RUNTIME)) if os.name == "nt" else str(RUNTIME)
        project_wsl = self._wsl("wslpath", "-u", str(REPO)) if os.name == "nt" else str(REPO)
        px4_script = self._wsl("wslpath", "-u", str(SIM_DIR / "px4_start.sh")) if os.name == "nt" else str(SIM_DIR / "px4_start.sh")
        self.launcher = subprocess.Popen(
            (["wsl.exe", "-d", self.distro, "--"] if os.name == "nt" else []) + ["bash", px4_script,
             self.px4_dir, project_wsl, runtime_wsl, self.gateway],
            stdout=self.log, stderr=subprocess.STDOUT)
        self.process = self.launcher

    def setpoints(self, keys, pan_rate, tilt_rate, dt):
        # The caller already schedules the original 25 Hz pilot cadence using
        # the host clock; a second Linux-time throttle would drop alternate
        # inputs on hosts where the two clock rates differ.
        self.operator_time += dt
        self.pilot.update(keys, pan_rate, tilt_rate, self.operator_time)

    def observation(self):
        result = super().observation()
        if self.data.time < 8.:
            result['valid'] = False
        return result

    def advance(self, steps=4):
        if steps % 4:
            raise ValueError("PX4 advance requires complete 4 ms sensor cycles")
        for _ in range(steps // 4):
            deadline = time.monotonic()+15.
            while True:
                self.poll()
                if self.sim_mav is not None and (not self.first_actuator or self.actuator_time_usec >= self.last_sensor_time_usec):
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("PX4 lockstep timeout; inspect simulation/runtime/px4.log")
                select.select([self.sock or self.listener, self.offboard.port], [], [], .01)
            for _ in range(round(.004/self.model.opt.timestep)):
                self.env.step(self.armed)
            self.send_sensors()
        self.poll()

    def poll(self):
        if self.process and self.process.poll() is not None:
            raise RuntimeError("PX4 exited; inspect simulation/runtime/px4.log")
        if self.sock is None:
            try:
                self.sock, _ = self.listener.accept()
                self.sock.setblocking(False)
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                from sim.server import SocketWriter
                self.sim_mav = MAV.MAVLink(SocketWriter(self.sock), srcSystem=1, srcComponent=200)
                self.sim_mav.robust_parsing = True
            except BlockingIOError:
                pass
        if self.sock:
            try:
                blob = self.sock.recv(65536)
                if not blob:
                    raise RuntimeError("PX4 simulator link disconnected")
                for message in self.sim_mav.parse_buffer(blob) or []:
                    if message.get_type() == 'HIL_ACTUATOR_CONTROLS':
                        self.armed = bool(message.mode & MAV.MAV_MODE_FLAG_SAFETY_ARMED)
                        self.env.drone.commands[:] = 0.
                        if self.armed:
                            self.env.drone.commands[:] = np.clip(np.asarray(message.controls)[PX4_TO_CAD], 0., 1.)
                        self.first_actuator = True
                        self.actuator_time_usec = int(message.time_usec)
                        self.last_controls_wall = time.monotonic()
            except BlockingIOError:
                pass
        for message in self._offboard_messages():
            if message.get_srcSystem() != 1:
                continue
            kind = message.get_type()
            if kind == 'LOCAL_POSITION_NED':
                self.local, self.local_time, self.estimator_ready = message, float(self.data.time), True
            elif kind == 'ATTITUDE':
                self.attitude, self.attitude_time = message, float(self.data.time)
            elif kind == 'EXTENDED_SYS_STATE':
                self.landed = message.landed_state == MAV.MAV_LANDED_STATE_ON_GROUND
                if message.landed_state == MAV.MAV_LANDED_STATE_IN_AIR:
                    self.was_airborne = True
            elif kind == 'COMMAND_ACK':
                self.ack.append({'command': message.command, 'result': message.result, 't': float(self.data.time)})
            elif kind == 'STATUSTEXT':
                self.messages.append(message.text)
                self.messages = self.messages[-30:]

    def _offboard_messages(self):
        """Drain UDP packets once and decode each complete buffer in a batch."""
        connection = self.offboard
        connection.pre_message()
        while True:
            blob = connection.recv()
            if not blob:
                return
            if connection.first_byte:
                connection.auto_mavlink_version(blob)
            for message in connection.mav.parse_buffer(blob) or []:
                connection.post_message(message)
                yield message

    def close(self):
        try:
            if self.launcher:
                runtime_wsl = self._wsl("wslpath", "-u", str(RUNTIME)) if os.name == "nt" else str(RUNTIME)
                px4_script = self._wsl("wslpath", "-u", str(SIM_DIR / "px4_start.sh")) if os.name == "nt" else str(SIM_DIR / "px4_start.sh")
                subprocess.run((["wsl.exe", "-d", self.distro, "--"] if os.name == "nt" else []) + ["bash", px4_script,
                                self.px4_dir, runtime_wsl, "stop"], timeout=12,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    self.launcher.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    self.launcher.terminate()
            if self.sock:
                self.sock.close()
            self.listener.close()
            self.offboard.close()
            self.log.close()
        except Exception:
            pass


class Backend:
    def __init__(self):
        self.clock_ratio = 1.
        self.host_clock_samples = []
        self.lock = threading.RLock()
        self.status = {"status": "Waiting for Tidewater terrain", "ready": False,
                       "source": "PX4 SITL + MuJoCo", "error": None}
        self.heights = None
        self.meta = None
        self.model = None
        self.visual_layout = None
        self.env = None
        self.px4 = None
        self.command = {"keys": [], "motors": [0., 0.], "look_x": 0., "look_y": 0.}
        self.actions = []
        self.mode = "drone"
        self.boat_auto = True
        self.boat_camera = "boat_dock"
        self.reset_requested = False
        self.reconnect_requested = False
        self.started = False
        self.simulation_time = 0.
        self.publish_time = 0.
        self.runtime_thread = None
        self.realtime_factor = 1.
        self.initializing = False
        self.paused = False
        self.radio = RadioModel()

    def accept_map(self, meta, heights):
        with self.lock:
            if self.initializing or self.env is not None:
                return
            self.initializing = True
            self.meta = meta
            self.heights = np.asarray(heights, dtype=np.float32).copy()
            self.status = {"status": "Building Tidewater collision world", "ready": False,
                           "source": "PX4 SITL + MuJoCo", "error": None}
        threading.Thread(target=self._initialize, daemon=True, name="tidewater-init").start()

    def _compile_map(self):
        with self.lock:
            self.status = {**self.status, "status": "Loading original MuJoCo CAD model · first Linux compilation can take a few minutes"}
        prepared = os.name != "nt" and (RUNTIME / "physics-base-linux.xml").exists()
        source = mujoco.MjModel.from_binary_path(str(RUNTIME / "physics-base.mjb")) if prepared else compile_scene(.001)
        base_xml = RUNTIME / "physics-base-linux.xml" if prepared else REPO / "landing_training" / "build" / "combined_1000us.xml"
        if not base_xml.exists():
            raise FileNotFoundError("Combined MuJoCo source scene was not created")
        spec = mujoco.MjSpec.from_file(str(base_xml))
        with self.lock:
            self.status = {**self.status, "status": "Compiling water terrain and obstacle collisions"}
        self.visual_layout = json.loads((RUNTIME / "visual-layout.json").read_text()) if prepared else visual_layout_from(source)
        # Browser rendering already owns these exact CAD meshes. Keep every
        # collision shape, body inertia, joint, sensor and actuator in MuJoCo.
        for geom in list(spec.geoms):
            gid = mujoco.mj_name2id(source, mujoco.mjtObj.mjOBJ_GEOM, geom.name)
            if (gid >= 0 and geom.name != "water_surface" and not geom.name.startswith("shore_contact_") and source.geom_contype[gid] == 0
                    and source.geom_conaffinity[gid] == 0):
                spec.delete(geom)
        n = 1024
        h = self.heights.reshape(int(self.meta["res"]), int(self.meta["res"]))[::-2, ::2]
        h = h[:n, :n]
        resolution = self.size / int(self.meta["res"]) * 2
        # A single island-sized heightfield has a mountain-sized vertical AABB.
        # It triggers expensive mesh/terrain tests even far offshore. Overlapping
        # boundary nodes keep exactly the same sampled surface in 128 m tiles.
        start = -(n - 1) * resolution * .5 - .5
        for row in range(0, n-1, 64):
            for col in range(0, n-1, 64):
                tile = h[row:min(row+65, n), col:min(col+65, n)]
                nr, nc = tile.shape
                low, high = float(np.min(tile)), float(np.max(tile))
                span = max(high-low, .01)
                name = f"tidewater_terrain_{row}_{col}"
                hx, hy = (nc-1)*resolution*.5, (nr-1)*resolution*.5
                spec.add_hfield(name=name, nrow=nr, ncol=nc, size=[hx, hy, span, .1],
                                userdata=((tile-low)/span).astype(np.float32).ravel().tolist())
                spec.worldbody.add_geom(name=name+"_collision", type=mujoco.mjtGeom.mjGEOM_HFIELD,
                                        hfieldname=name, pos=[start+col*resolution+hx,
                                                             start+row*resolution+hy, low],
                                        contype=12, conaffinity=3, group=5)
        for i, box in enumerate(self.meta["colliders"].get("boxes", [])):
            if not box.get("solid", True):
                continue
            c, half, angle = box["center"], box["half"], float(box.get("rotY", 0.))
            spec.worldbody.add_geom(name=f"tidewater_box_{i}", type=mujoco.mjtGeom.mjGEOM_BOX,
                                    pos=[c[0], -c[2], c[1]], size=[half[0], half[2], half[1]],
                                    quat=[math.cos(angle / 2), 0, 0, math.sin(angle / 2)],
                                    contype=12, conaffinity=3, group=5)
        for i, cylinder in enumerate(self.meta["colliders"].get("cylinders", [])):
            spec.worldbody.add_geom(name=f"tidewater_cylinder_{i}", type=mujoco.mjtGeom.mjGEOM_CYLINDER,
                                    pos=[cylinder["x"], -cylinder["z"],
                                         (cylinder["yMin"] + cylinder["yMax"]) / 2],
                                    size=[cylinder["radius"],
                                          (cylinder["yMax"] - cylinder["yMin"]) / 2, 0],
                                    contype=12, conaffinity=3, group=5)
        model = spec.compile()
        for attribute in ("body_mass", "body_inertia", "body_ipos", "body_iquat", "jnt_axis"):
            if not np.array_equal(getattr(source, attribute), getattr(model, attribute)):
                raise RuntimeError(f"Physics compilation changed original {attribute}")
        model.opt.timestep = float(os.environ.get("TIDEWATER_TIMESTEP", ".001"))
        if model.opt.timestep not in (.001, .002, .004):
            raise ValueError("Tidewater supports 1, 2 or 4 ms MuJoCo integration")
        if os.environ.get("TIDEWATER_CONTROLLER", "px4") == "px4" and model.opt.timestep != .001:
            raise ValueError("Original PX4 flight requires TIDEWATER_TIMESTEP=.001 for physics parity")
        model.vis.map.znear = .001 / model.stat.extent
        model.vis.map.zfar = 6000. / model.stat.extent
        del source
        return model

    @property
    def size(self):
        return float(self.meta["size"])

    def _initialize(self):
        px4 = None
        try:
            model = self._compile_map()
            with self.lock:
                self.status = {**self.status, "status": "Compiling native force equations · cached after first start"}
            env = GameEnvironment(model, self.meta, self.heights, visual_layout=self.visual_layout)
            with self.lock:
                self.status = {**self.status, "status": "Starting PX4 and calibrating sensors",
                               "views": env.views(), "geoms": env.geom_transforms(), "bodies": env.body_transforms(),
                               "mode": self.mode, "boat_camera": self.boat_camera}
            px4 = make_controller(env)
            px4.start()
            with self.lock:
                self.model, self.env, self.px4 = model, env, px4
                self.radio = env.radio
                self.status = {"status": f"Starting {px4.source}",
                               "ready": False, "source": px4.source,
                               "views": env.views(), "geoms": env.geom_transforms(), "bodies": env.body_transforms(),
                               "mode": self.mode, "boat_camera": self.boat_camera,
                               "model": "Holybro X500 V2 CAD", "physics_hz": round(1/model.opt.timestep),
                               "sensor_hz": 250, "error": None,
                               "route": {"valid": True, "length_m": round(env.world.route.length, 1),
                                         "points": self._map_points(env.world.route.points), "error_m": 0.}}
            if not self.runtime_thread or not self.runtime_thread.is_alive():
                self.runtime_thread = threading.Thread(target=self._run, daemon=True,
                                                       name="tidewater-mujoco")
                self.runtime_thread.start()
        except Exception as error:
            traceback.print_exc()
            if px4 is not None:
                px4.close()
            with self.lock:
                self.status = {**self.status, "status": "Simulation startup failed", "ready": False,
                               "source": "PX4 SITL + MuJoCo", "error": str(error)}
        finally:
            with self.lock:
                self.initializing = False

    def retry(self):
        with self.lock:
            if self.initializing:
                return
            if self.env is not None:
                self.reset_requested = True
            elif self.meta is not None and self.heights is not None:
                self.accept_map(self.meta, self.heights)


    @staticmethod
    def _map_points(points):
        return [[float(p[0]), float(-p[1])] for p in points[::2]]

    def input(self, payload):
        with self.lock:
            if "keys" in payload:
                self.command["keys"] = [str(k) for k in payload["keys"] if isinstance(k, str)]
            if payload.get("mode") in ("drone", "boat"):
                self.mode = payload["mode"]
            if "motors" in payload and len(payload["motors"]) == 2:
                self.command["motors"] = [float(np.clip(v, 0., 100.)) for v in payload["motors"]]
            for axis in ("look_x", "look_y"):
                if axis in payload:
                    self.command[axis] = float(np.clip(self.command[axis] + payload[axis], -1200., 1200.))
            if payload.get("action") == "reset":
                self.reset_requested = True
            elif payload.get("action") == "takeoff" and not self.status.get("ready"):
                self.status["message"] = "Wait for the simulator camera and PX4 sensors to be ready"
            elif payload.get("action") in ("reconnect", "takeoff", "land", "hover", "lid", "platform"):
                self.actions.append(dict(payload))
            elif payload.get("action") == "autopilot":
                self.boat_auto = bool(payload.get("enabled"))
            elif payload.get("action") == "camera":
                if payload.get("name") in ("boat_dock", "boat_nav"):
                    self.boat_camera = payload["name"]

    def _apply_actions(self, env, px4, actions):
        for action in actions:
            kind = action.get("action")
            if kind == "reconnect":
                env.radio.request()
            elif kind == "takeoff":
                self.mode = "drone"
                env.launch_complete = False
                px4.takeoff_pending = True
            elif kind == "land":
                if isinstance(px4, GamePX4):
                    px4.pilot.sim.action = 'land'
                else:
                    px4.target_height = 0.
                px4.flight_requested = True
                with self.lock:
                    self.command["keys"] = []
            elif kind == "hover":
                with self.lock:
                    self.command["keys"] = []
            elif kind == "lid":
                self._mechanism("lid", bool(action.get("open")))
            elif kind == "platform":
                self._mechanism("platform", bool(action.get("raised")))

    def _mechanism(self, kind, enabled):
        boat = self.env.boat
        if boat.busy:
            self.status["message"] = "Wait for the current mechanism movement to finish"
            return
        positions = boat._positions()
        if kind == "lid":
            if not enabled and positions[0] > .008:
                self.status["message"] = "Lower the launch platform before closing both lids"
                return
            boat.targets[1:] = .46 if enabled else 0.
        else:
            if enabled and min(positions[1:]) < .45:
                self.status["message"] = "Open both lids before raising the launch platform"
                return
            boat.targets[0] = .4 if enabled else 0.
        boat.busy = True

    def _reset(self):
        old = self.px4
        self.px4 = None
        if old:
            old.close()
        self.env = None
        self.status = {"status": "Resetting both vehicles", "ready": False,
                       "source": "MuJoCo", "error": None}
        env = GameEnvironment(self.model, self.meta, self.heights, visual_layout=self.visual_layout)
        px4 = make_controller(env)
        px4.start()
        self.env, self.px4 = env, px4
        self.paused = False
        self.radio = env.radio
        self.boat_auto = True
        self.mode = "drone"
        self.boat_camera = "boat_dock"
        self.command = {"keys": [], "motors": [0., 0.], "look_x": 0., "look_y": 0.}
        self.actions.clear()
        self.status = {"status": f"Starting {px4.source}", "ready": False,
                       "views": env.views(), "geoms": env.geom_transforms(), "bodies": env.body_transforms(),
                       "mode": self.mode, "boat_camera": self.boat_camera,
                       "source": px4.source, "model": "Holybro X500 V2 CAD",
                       "physics_hz": round(1/self.model.opt.timestep), "sensor_hz": 250, "error": None,
                       "route": {"valid": True, "length_m": round(env.world.route.length, 1),
                                 "points": self._map_points(env.world.route.points), "error_m": 0.}}

    def _run(self):
        profile = None
        if os.environ.get("TIDEWATER_PROFILE"):
            import cProfile
            profile = cProfile.Profile()
            profile.enable()
        profile_start = time.monotonic()
        next_tick = time.monotonic()
        last_control = 0.
        last_radio = 0.
        rate_wall, rate_sim = next_tick, 0.
        while True:
            with self.lock:
                if self.reset_requested:
                    self.reset_requested = False
                    try:
                        self._reset()
                        next_tick = time.monotonic()
                        rate_wall, rate_sim = next_tick, 0.
                    except Exception as error:
                        self.status = {"status": "Reset failed", "ready": False,
                                       "source": "PX4 SITL + MuJoCo", "error": str(error)}
                    continue
                env, px4 = self.env, self.px4
                command = {"keys": list(self.command["keys"]),
                           "motors": list(self.command["motors"]),
                           "look_x": self.command["look_x"],
                           "look_y": self.command["look_y"]}
                actions, self.actions = self.actions, []
            if env is None or px4 is None or self.paused:
                time.sleep(.05)
                continue
            try:
                if actions:
                    self._apply_actions(env, px4, actions)
                now = time.monotonic()
                if now >= next_tick:
                    if now - last_control >= .04*self.clock_ratio:
                        dt = max(.04, (now - last_control)/self.clock_ratio) if last_control else .04
                        if self.mode == "boat":
                            self.boat_auto = bool(self.boat_auto)
                        # Calibrate the PX4 estimator on a stationary launch
                        # platform before beginning the continuous boat loop.
                        if px4.takeoff_pending and abs(env.boat.get_speed("m/s")) < .15:
                            px4.takeoff_pending = False
                            px4.flight_requested = True
                            px4.target_height = 1.5 if isinstance(px4, GamePX4) else max(3., px4.target_height)
                        if px4.armed and env.drone.position[2] > env.data.site_xpos[env.pad_site, 2] + 1.0:
                            env.launch_complete = True
                        launch_hold = px4.takeoff_pending or (not env.launch_complete and self.mode == "drone")
                        env.boat_auto = self.boat_auto and px4.observation()["valid"] and not launch_hold
                        if launch_hold:
                            env.boat.power[:] = 0.
                        else:
                            env.control_boat(command, min(dt, .1))
                        keys = command["keys"] if self.mode == "drone" else []
                        with self.lock:
                            look_x = float(self.command["look_x"])
                            look_y = float(self.command["look_y"])
                            self.command["look_x"] = 0.
                            self.command["look_y"] = 0.
                        if self.mode == "drone":
                            pan_rate = (float("ArrowLeft" in keys) - float("ArrowRight" in keys)) * math.radians(50) + look_x * .0022 / .04
                            tilt_rate = (float("ArrowDown" in keys) - float("ArrowUp" in keys)) * math.radians(40) - look_y * .0022 / .04
                        else:
                            pan_rate = tilt_rate = 0.
                        px4.setpoints(keys, pan_rate, tilt_rate, min(dt, .1))
                        last_control = now
                    px4.advance(4)
                    next_tick += .004*self.clock_ratio
                    if now - next_tick > .25:
                        next_tick = now + .004*self.clock_ratio
                    self.simulation_time = env.data.time
                    if profile is not None and time.monotonic()-profile_start > 8:
                        profile.disable()
                        profile.dump_stats(str(RUNTIME / "live-profile.pstats"))
                        profile = None
                    if now-rate_wall >= 1.:
                        self.realtime_factor = (env.data.time-rate_sim)/(now-rate_wall)*self.clock_ratio
                        rate_wall, rate_sim = now, env.data.time
                    if now - last_radio >= .25*self.clock_ratio:
                        env.radio.update(.25, env, self.meta["colliders"], now)
                        last_radio = now
                    if now - self.publish_time >= .05*self.clock_ratio:
                        self.publish_time = now
                        self._publish(env, px4)
                else:
                    time.sleep(min(.001, max(0., next_tick - now)))
            except Exception as error:
                traceback.print_exc()
                with self.lock:
                    self.paused = True
                    self.status = {**self.status, "status": "Simulation paused", "ready": False,
                                   "source": "PX4 SITL + MuJoCo", "error": str(error)}
                time.sleep(.1)

    def _publish(self, env, px4):
        drone = env.drone_state()
        boat = env.boat_state()
        observation = px4.observation()
        drone["armed"] = bool(px4.armed)
        drone["px4_ready"] = bool(observation["valid"])
        drone["px4_mode"] = int(px4.attitude is not None)
        drone["flight_requested"] = bool(px4.flight_requested)
        drone["takeoff_pending"] = bool(px4.takeoff_pending)
        drone["px4_position"] = observation
        route = env.world.route
        hull_id = env.model.geom("hull_contact").id
        label = "PX4" if isinstance(px4, GamePX4) else "Native flight controller"
        self.status = {"status": f"Flying · {label}" if px4.armed else
                       f"{label} ready · press Take off" if observation["valid"] else
                       f"{label} warming sensors", "ready": bool(observation["valid"]),
                       "source": px4.source,
                       "physics_hz": round(1/env.model.opt.timestep), "sensor_hz": 250,
                       "controller_lag_ms": max(0., (px4.last_sensor_time_usec-px4.actuator_time_usec)/1000),
                       "time_s": float(env.data.time), "tick": env.tick,
                       "drone": drone, "boat": boat,
                       "views": env.views(), "geoms": env.geom_transforms(), "bodies": env.body_transforms(),
                       "coastline": [[float(p[0]), float(-p[1])] for p in env.world.coast[:-1:8]],
                       "hull_pose": _matrix(env.data.geom_xpos[hull_id], env.data.geom_xmat[hull_id]),
                       "mode": self.mode, "boat_camera": self.boat_camera,
                       "boat_autopilot": bool(self.boat_auto),
                       "radio": dict(env.radio.state),
                       "remote": env.radio.last_remote,
                       "route": {"valid": True, "length_m": float(route.length),
                                 "progress_m": float(env.course_progress),
                                 "error_m": float(env.course_error),
                                 "target_speed_m_s": float(env.target_speed),
                                 "points": self._map_points(route.points)},
                       "message": self.status.get("message"),
                       "messages": px4.messages[-6:],
                       "wind": env.wind.velocity.tolist()}
        self.status["waves"] = env.wave_coefficients()
        self.status["wave_height_m"] = .05
        self.status["realtime_factor"] = round(self.realtime_factor, 3)


backend = Backend()
app = FastAPI(title="Tidewater PX4 / MuJoCo runtime")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5189", "http://localhost:5189"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.on_event("shutdown")
def shutdown_runtime():
    if backend.px4 is not None:
        backend.px4.close()


@app.get("/api/status")
def get_status():
    return backend.status


@app.post("/api/clock")
async def host_clock(request: Request):
    payload = await request.json()
    elapsed = float(payload['elapsed_s'])
    if not math.isfinite(elapsed) or elapsed < 0:
        return JSONResponse({'error': 'Invalid host clock'}, status_code=400)
    samples = backend.host_clock_samples
    if samples and elapsed <= samples[-1][1]:
        samples.clear()
    samples.append((time.monotonic(), elapsed))
    samples[:] = samples[-13:]
    if len(samples) >= 4:
        linux_delta = samples[-1][0]-samples[0][0]
        host_delta = samples[-1][1]-samples[0][1]
        backend.clock_ratio = float(np.clip(linux_delta/host_delta, .5, 1.5))
    return {'accepted': True}


@app.post("/api/map")
async def upload_map(request: Request):
    body = await request.body()
    if len(body) < 4:
        return JSONResponse({"error": "Map packet is incomplete"}, status_code=400)
    header_size = struct.unpack_from("<I", body)[0]
    if header_size > 2_000_000 or len(body) < 4 + header_size:
        return JSONResponse({"error": "Map header is invalid"}, status_code=400)
    meta = json.loads(body[4:4 + header_size])
    res = int(meta.get("res", 0))
    pixels = res * res
    raw = body[4 + header_size:]
    if res < 256 or res > 4096 or len(raw) != pixels * 4:
        return JSONResponse({"error": "Terrain dimensions do not match height data"}, status_code=400)
    if backend.env is not None or backend.status.get("status") == "Building Tidewater collision world":
        return {"accepted": True, "status": backend.status.get("status")}
    backend.accept_map(meta, np.frombuffer(raw, dtype="<f4"))
    return {"accepted": True, "status": "Building Tidewater collision world"}


@app.post("/api/retry")
def retry_simulation():
    backend.retry()
    return {"accepted": True}


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    async def read_commands():
        try:
            while True:
                backend.input(await ws.receive_json())
        except WebSocketDisconnect:
            backend.input({"keys": [], "look_x": 0., "look_y": 0.})
        except Exception:
            backend.input({"keys": [], "look_x": 0., "look_y": 0.})
    task = asyncio.create_task(read_commands())
    layout_sent = False
    map_sent = False
    last_packet = None
    try:
        while not task.done():
            current = backend.status
            if current is last_packet:
                await asyncio.sleep(.004)
                continue
            last_packet = current
            packet = dict(current)
            if layout_sent:
                packet.pop("geoms", None)
            elif packet.get("geoms"):
                layout_sent = True
            if map_sent:
                packet.pop("coastline", None)
                if "route" in packet:
                    packet["route"] = {k: v for k, v in packet["route"].items() if k != "points"}
            elif packet.get("coastline") and packet.get("route", {}).get("points"):
                map_sent = True
            await ws.send_text(orjson.dumps(packet).decode("utf-8"))
            await asyncio.sleep(.004)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        task.cancel()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("TIDEWATER_LISTEN_HOST", "127.0.0.1"), port=5195, log_level="warning", ws_per_message_deflate=False)
