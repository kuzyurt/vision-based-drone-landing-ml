"""Adapter: Tidewater world  <->  flight_electronics hardware simulation  <->  Tidewater policy.

flight_electronics knows nothing about Tidewater. This file is the only place
that translates between the two:

* the runner's per-tick (rgb, observation) becomes a ``WorldSample``
  (rendered frame, PX4 estimate, true gimbal angles, boat radio packet);
* the companion view (late camera frame, MAVLink telemetry, GCU encoder angles,
  radio fix decoded by the ESP32 firmware) becomes the observation the
  Tidewater policy expects (same keys, beacon in the heading frame);
* the policy action goes through the compute timing, MAVLink and the GCU, and
  what the hardware actually executes is returned to the runner.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np

from flight_electronics.simulation.hil import FlightElectronics, HilConfig, WorldSample


def _heading_rotation(attitude_yaw_ned):
    yaw = math.pi / 2 - attitude_yaw_ned
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])


def beacon_to_world(beacon, own):
    """Invert the runner's packet -> heading-frame transform (benchmark/harness/runner.py)."""
    rotation = _heading_rotation(own['attitude_ned_rad'][2])
    flip = np.array([1, -1, -1.])
    position = np.asarray(own['position_enu_m']) + rotation @ (np.asarray(beacon['relative_heading_m']) * flip)
    velocity = rotation @ (np.asarray(beacon['velocity_heading_m_s']) * flip)
    return position, velocity


def world_to_beacon(fix, own):
    rotation = _heading_rotation(own['attitude_ned_rad'][2])
    flip = np.array([1, -1, -1.])
    relative = (rotation.T @ (np.asarray(fix['position_enu_m']) - np.asarray(own['position_enu_m']))) * flip
    velocity = (rotation.T @ np.asarray(fix['velocity_enu_m_s'])) * flip
    return dict(valid=bool(fix['valid']), age_s=float(fix['age_s']), dock_ready=bool(fix['dock_ready']),
                dock_status_valid=bool(fix['dock_status_valid']), position_sigma_m=float(fix['position_sigma_m']),
                velocity_sigma_m_s=.025, relative_heading_m=relative.tolist(), velocity_heading_m_s=velocity.tolist())


def marker_mode(diagnostics):
    if 'metric_valid' not in diagnostics:
        return 'none'
    return 'tracked' if diagnostics.get('metric_valid') else 'cold'


class HardwareInTheLoopActor:
    """Drop-in replacement for the runner's actor: same act(rgb, observation) interface."""

    def __init__(self, inner, config: HilConfig = HilConfig(), summary_path: Path | None = None):
        self.inner = inner
        self.config = config
        self.summary_path = summary_path
        self.hardware = FlightElectronics(config)
        self._last_frame = np.zeros((360, 640, 3), np.uint8)
        self._last_beacon_capture = None
        self._sequence = 0

    @property
    def controller(self):
        return self.inner.controller

    def reset(self):
        self.inner.reset()
        self.hardware.close()
        self.hardware = FlightElectronics(self.config)

    def _boat_packet(self, observation, t):
        beacon = observation.get('beacon')
        if not beacon or not beacon.get('valid'):
            return None
        capture = t - float(beacon['age_s'])
        if self._last_beacon_capture is not None and abs(capture - self._last_beacon_capture) < 1e-6:
            return None
        self._last_beacon_capture = capture
        self._sequence += 1
        position, velocity = beacon_to_world(beacon, observation['px4'])
        distance = float(np.linalg.norm(position - np.asarray(observation['px4']['position_enu_m'])))
        return dict(sequence=self._sequence, send_time_s=capture, position_enu_m=position.tolist(),
                    velocity_enu_m_s=velocity.tolist(), distance_m=distance,
                    dock_ready=bool(beacon.get('dock_ready', True)),
                    dock_status_valid=bool(beacon.get('dock_status_valid', True)),
                    position_sigma_m=float(beacon.get('position_sigma_m', .25)))

    def act(self, rgb, observation):
        t = float(observation['mission']['elapsed_s'])
        world = WorldSample(time_s=t, camera_rgb=np.asarray(rgb, np.uint8).reshape(360, 640, 3),
                            vehicle=observation['px4'], gimbal_true_rad=tuple(observation['gimbal_rad']),
                            boat_packet=self._boat_packet(observation, t))
        view = self.hardware.sense(world)
        hw = dict(view.diagnostics)
        if not view.soc_running:
            actuation = self.hardware.actuate(np.zeros(6), 'none')
            return actuation.action, dict(hardware=hw, hardware_state='companion_brownout')
        seen = copy.deepcopy(observation)
        px4 = dict(seen['px4'])
        px4.update({k: v for k, v in view.observation['px4'].items() if k in px4 or k.endswith('_age_s')})
        seen['px4'] = px4
        for key in ('gimbal_rad', 'image_capture_time_s', 'image_delivery_time_s', 'image_age_s', 'image_valid',
                    'previous_executed_action'):
            seen[key] = view.observation[key]
        seen.pop('beacon', None)
        if 'beacon' in view.observation and 'beacon' in observation:
            seen['beacon'] = world_to_beacon(view.observation['beacon'], px4)
        if view.frame is not None:
            self._last_frame = view.frame
        action, diagnostics = self.inner.act(self._last_frame, seen)
        actuation = self.hardware.actuate(action, marker_mode(diagnostics))
        diagnostics = dict(diagnostics)
        diagnostics['hardware'] = dict(hw, latency_ms=actuation.latency_s * 1000,
                                       applied_this_tick=actuation.applied_from_this_tick)
        return actuation.action, diagnostics

    def write_summary(self):
        if self.summary_path is not None:
            import json
            self.summary_path.write_text(json.dumps(self.hardware.summary(), indent=2, default=str), encoding='utf-8')
