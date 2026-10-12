"""Reuse the original simulator's pilot code without changing that project."""
import math
import time
from sim.server import Simulation

class OriginalPilot:
    def __init__(self, bridge):
        self.bridge = bridge
        self.sim = Simulation(launch=False)
        s, e = self.sim, bridge.env
        s.model, s.data, s.base = e.model, e.data, e.drone.base
        s.power, s.offboard, s.power_mav = e.drone.power, bridge.offboard, bridge.power_mav
        s.last_power_report = -1e9
        s.last_arm_try = 0.
        s.arm_request_time = time.monotonic()
        self.was_requested = False

    def update(self, keys, pan_rate, tilt_rate, now=None):
        b, s, u = self.bridge, self.sim, self.bridge.env.drone
        now = time.monotonic() if now is None else now
        s.armed, s.landed, s.estimator_ready = b.armed, b.landed, b.estimator_ready
        if b.flight_requested and not self.was_requested:
            s.arm_request_time, s.last_arm_try = now, 0.
        self.was_requested = b.flight_requested
        s.flight_requested = b.flight_requested
        s.target_height = b.target_height
        s.pan, s.tilt = u.pan, u.tilt
        s.keys, s.last_browser_wall = set(keys), now
        # Arrow keys are processed by the original method; only mouse motion
        # is added here, preventing doubled pan/tilt rates.
        arrow_pan = (('ArrowLeft' in keys)-('ArrowRight' in keys))*math.radians(50)
        arrow_tilt = (('ArrowDown' in keys)-('ArrowUp' in keys))*math.radians(40)
        s.camera_steps[:] = [(pan_rate-arrow_pan)*.04, (tilt_rate-arrow_tilt)*.04]
        Simulation.setpoints(s, now)
        u.pan, u.tilt = s.pan, s.tilt
        b.flight_requested, b.target_height = s.flight_requested, s.target_height
