"""Plumbing check without MuJoCo/PX4: the real policy, real game frames, simulated electronics.

The "world" here is only a kinematic stand-in: the drone integrates the
velocities the hardware executes and the camera shows saved frames from the
realistic game. It proves that every byte path works (camera queue, MAVLink,
GCU packets, LoRa + ESP32 firmware, SPICE power model, compute timing) with the
production policy in the loop. It is not a flight and produces no score.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
FRAMES = [REPO / 'tidewater-game/history/tidewater_20261011' / name for name in
          ('mapped_onboard_preview.png', 'moving_daylight_rgb_0100.png', 'mapped_boat_preview.png')]


def _frames():
    from PIL import Image
    return [np.asarray(Image.open(path).convert('RGB')) for path in FRAMES if path.exists()]


def smoke(config, steps=150, radio=True):
    import sys
    sys.path.insert(0, str(REPO))
    from benchmark.harness import student_tidewater
    from adapter import HardwareInTheLoopActor

    sys.path.insert(0, str(student_tidewater.STUDENT_DIR))
    actor = HardwareInTheLoopActor(student_tidewater.TidewaterActor('cpu'), config)
    frames = _frames() or [np.zeros((360, 640, 3), np.uint8)]
    position, velocity, yaw = np.array([0., 0., 6.]), np.zeros(3), 0.3
    pan, tilt = 0.0, math.pi / 2
    previous = [0.0] * 6
    boat = np.array([18., 6., .45])
    phases = {}
    for k in range(steps):
        t = k * 0.04
        own = dict(valid=True, position_enu_m=position.tolist(), velocity_enu_m_s=velocity.tolist(),
                   attitude_ned_rad=[0., 0., yaw], angular_rate_frd_rad_s=[0., 0., 0.], position_age_s=.01,
                   attitude_age_s=.004, position_source_boot_ms=int(t * 1000), attitude_source_boot_ms=int(t * 1000),
                   armed=True, landed=False, gimbal_commanded_rad=[pan, tilt],
                   gimbal_command_source='own_last_issued_setpoint')
        observation = dict(px4=own, gimbal_rad=[pan, tilt], gimbal_source='synthetic own encoder',
                           image_capture_time_s=t, image_delivery_time_s=t, image_age_s=0., image_valid=True,
                           decision_dt_s=.04, previous_executed_action=previous,
                           mission=dict(elapsed_s=t, budget_s=240.))
        if radio:
            send = math.floor(t)
            rotation_yaw = math.pi / 2 - yaw
            c, s = math.cos(rotation_yaw), math.sin(rotation_yaw)
            rotation = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])
            observation['beacon'] = dict(valid=True, age_s=t - send, dock_ready=True, dock_status_valid=True,
                                         position_sigma_m=.25, velocity_sigma_m_s=.025,
                                         relative_heading_m=((rotation.T @ (boat - position)) * [1, -1, -1]).tolist(),
                                         velocity_heading_m_s=[0., 0., 0.])
        action, diagnostics = actor.act(frames[(k // 25) % len(frames)], observation)
        phase = diagnostics.get('control_phase') or diagnostics.get('phase') or 'unknown'
        phases[phase] = phases.get(phase, 0) + 1
        forward, right, down, yaw_rate, pan_rate, tilt_rate = action
        c, s = math.cos(yaw), math.sin(yaw)
        velocity = np.array([forward * s + right * c, forward * c - right * s, -down])  # ENU
        position = position + velocity * .04
        yaw += yaw_rate * .04
        pan += pan_rate * .04
        tilt = float(np.clip(tilt + tilt_rate * .04, math.radians(-61), math.radians(140)))
        previous = list(map(float, action))
    summary = actor.hardware.summary()
    summary['policy_phases'] = phases
    actor.hardware.close()
    return summary
