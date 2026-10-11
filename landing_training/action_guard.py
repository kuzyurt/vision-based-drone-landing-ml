"""Observable camera protection and measured command-slew experiments.

This wrapper never reads simulator state. The caller must still apply the
existing mission/readiness/estimator supervisor after act().
"""
from dataclasses import dataclass, asdict
import math
import numpy as np


def wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


@dataclass(frozen=True)
class GuardConfig:
    tilt_min_deg: float = -10.
    tilt_max_deg: float = 90.
    recovery: bool = False
    lost_seconds: float = .25
    # Optional measured 99th-percentile expert command derivatives, per second.
    slew_limits: tuple | None = None

    def __post_init__(self):
        if not -61 <= self.tilt_min_deg < self.tilt_max_deg <= 140:
            raise ValueError('Tilt guard must stay inside the existing travel range')
        if not math.isfinite(self.lost_seconds) or self.lost_seconds < 0:
            raise ValueError('Invalid visibility grace interval')
        if self.slew_limits is not None and (
                len(self.slew_limits) != 6 or not all(math.isfinite(v) and v > 0 for v in self.slew_limits)):
            raise ValueError('Six positive finite command derivatives required')


def beacon_camera_target(observation):
    beacon = observation['beacon']
    if not beacon.get('valid') or beacon.get('age_s', math.inf) >= 3:
        return None
    relative = np.asarray(beacon.get('relative_heading_m', []), dtype=float)
    if relative.shape != (3,) or not np.isfinite(relative).all() or np.linalg.norm(relative) < 1e-6:
        return None
    roll, pitch, _ = observation['px4'].get('attitude_ned_rad', [0., 0., 0.])
    cr, sr, cp, sp = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    # The public packet is heading FRD. Remove roll/pitch to get aircraft FRD.
    body = (ry @ rx).T @ relative
    return np.array([math.atan2(-body[1], body[0]),
                     math.atan2(body[2], np.linalg.norm(body[:2]))])


class ActionGuard:
    def __init__(self, config=GuardConfig()):
        self.config = config
        self.reset()

    def reset(self):
        self.tilt_target = None
        self.lost_elapsed = 0.

    def apply(self, action, observation, diagnostics):
        value = np.asarray(action, dtype=float).copy()
        if value.shape != (6,) or not np.isfinite(value).all():
            return np.zeros(6), {'guard_reasons': ['nonfinite_action']}
        dt = float(observation['decision_dt_s'])
        if not math.isfinite(dt) or not 0 < dt <= .2:
            raise ValueError('Guard requires a valid decision interval')
        pan, tilt = np.asarray(observation['gimbal_rad'], dtype=float)
        if not math.isfinite(pan) or not math.isfinite(tilt):
            value[4:] = 0
            return value, {'guard_reasons': ['invalid_gimbal']}
        minimum, maximum = np.radians([self.config.tilt_min_deg, self.config.tilt_max_deg])
        if self.tilt_target is None:
            # Settled preparation provides the initial encoder angle. This is
            # an observable target estimate, not a simulator actuator read.
            self.tilt_target = float(tilt)
        visible = observation.get('image_valid', False) and diagnostics.get('pad_visibility_probability', 0.) >= .5
        self.lost_elapsed = 0. if visible else self.lost_elapsed + dt
        reasons = []
        if self.config.recovery and self.lost_elapsed >= self.config.lost_seconds:
            target = beacon_camera_target(observation)
            if target is not None:
                value[4] = 3 * wrap(target[0] - pan)
                value[5] = 3 * (np.clip(target[1], minimum, maximum) - tilt)
                reasons.append('beacon_camera_recovery')
        value[4] = np.clip(value[4], -math.radians(50), math.radians(50))
        value[5] = np.clip(value[5], -math.radians(40), math.radians(40))
        if self.config.slew_limits is not None:
            previous = np.asarray(observation['previous_executed_action'], dtype=float)
            if previous.shape != (6,) or not np.isfinite(previous).all():
                raise ValueError('Invalid previous executed action')
            delta = np.asarray(self.config.slew_limits) * dt
            smooth = np.clip(value, previous - delta, previous + delta)
            if not np.array_equal(smooth, value):
                reasons.append('measured_command_slew')
            value = smooth
        # Project the integrated target as well as checking the measured joint.
        # Boundary protection has priority over command smoothing.
        target = np.clip(self.tilt_target + value[5] * dt, minimum, maximum)
        projected = (target - self.tilt_target) / dt
        projected = np.clip(projected, -math.radians(40), math.radians(40))
        if tilt <= minimum and projected < 0:
            projected = 0.
        if tilt >= maximum and projected > 0:
            projected = 0.
        if tilt < minimum:
            projected = max(projected, min(3 * (minimum - tilt), math.radians(40)))
        elif tilt > maximum:
            projected = min(projected, max(3 * (maximum - tilt), -math.radians(40)))
        if abs(projected - value[5]) > 1e-12:
            reasons.append('tilt_target_boundary')
        value[5] = projected
        self.tilt_target += value[5] * dt
        return value, {'guard_reasons': reasons, 'guard_tilt_target_rad': self.tilt_target,
                       'guard_lost_elapsed_s': self.lost_elapsed}


class GuardedPolicy:
    def __init__(self, policy, config=GuardConfig()):
        self.policy = policy
        self.guard = ActionGuard(config)
        self.metadata = dict(policy.metadata, guard=asdict(config))

    def reset(self):
        self.policy.reset()
        self.guard.reset()

    def act(self, rgb, observation):
        raw, diagnostics = self.policy.act(rgb, observation)
        action, extra = self.guard.apply(raw, observation, diagnostics)
        return action, dict(diagnostics, raw_policy_action=np.asarray(raw).tolist(), **extra)
