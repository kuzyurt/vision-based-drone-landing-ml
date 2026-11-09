"""Learned pad tracking with explicit, observable landing phases."""
import math
import copy
from collections import deque
import numpy as np
from .camera_geometry import relative_from_pixel, compensate_capture
from .recording import numeric_observation
from .action_guard import ActionGuard, GuardConfig, beacon_camera_target, wrap

def heading_rotation(yaw):
    c, s = (math.cos(yaw), math.sin(yaw))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])

def body_to_heading(roll, pitch):
    cr, sr, cp, sp = (math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch))
    return np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]]) @ np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])

class LandingController:

    def __init__(self, foot_local_flu, slew_limits):
        self.feet = np.asarray(foot_local_flu, dtype=float) * [1, -1, -1]
        if self.feet.shape != (4, 3) or not np.isfinite(self.feet).all():
            raise ValueError('Four calibrated feet required')
        self.guard = ActionGuard(GuardConfig(slew_limits=tuple(slew_limits)))
        self.reset()

    def reset(self):
        self.relative = None
        self.relative_velocity = None
        self.previous_yaw = None
        self.heading_target = None
        self.stable_elapsed = 0.0
        self.last_phase = 'acquire'
        self.guard.reset()

    def act(self, estimate, observation):
        dt = float(observation['decision_dt_s'])
        numeric = numeric_observation({'observation': observation})
        px4 = observation['px4']
        b = observation['beacon']
        roll, pitch, yaw_ned = px4.get('attitude_ned_rad', [0.0, 0.0, 0.0])
        yaw = math.pi / 2 - yaw_ned
        probability = float(estimate['visibility'])
        if px4.get('landed', False) or not px4.get('armed', False):
            action = np.zeros(6)
            if px4.get('armed', False):
                action[:3] = np.asarray(b.get('velocity_heading_m_s', [0.0, 0.0, 0.0]))
                action[2] = max(action[2] + 0.32, 0.3)
            phase = 'confirm' if px4.get('armed', False) else 'disarmed'
            return self.finish(action, observation, {'control_phase': phase, 'pose_valid': False, 'pad_visibility_probability': probability})
        r = np.asarray(estimate['relative_position'], dtype=float)
        velocity = np.asarray(estimate['relative_velocity'], dtype=float)
        normal = np.asarray(estimate['normal'], dtype=float)
        heading = np.asarray(estimate['heading_pair'], dtype=float)
        valid = r.shape == (3,) and velocity.shape == (3,) and (normal.shape == (3,)) and (heading.shape == (2,)) and all((np.isfinite(x).all() for x in [r, velocity, normal, heading])) and (probability >= 0.8) and observation['image_valid'] and (observation['image_age_s'] <= 0.25) and (np.linalg.norm(normal) > 0.5) and (normal[2] < -0.5) and (np.linalg.norm(heading) > 0.5)
        fresh = b.get('valid', False) and b.get('age_s', math.inf) < 3
        if not valid:
            self.stable_elapsed = 0.0
            self.relative = None
            action = np.zeros(6)
            phase = 'acquire'
            if fresh:
                relative = np.asarray(b['relative_heading_m'], dtype=float)
                vboat = np.asarray(b['velocity_heading_m_s'], dtype=float)
                action[:2] = 0.4 * relative[:2] + vboat[:2]
                action[2] = -np.clip(1.5 - relative[2], 0, 0.5)
                candidate = yaw + math.atan2(-relative[1], relative[0])
                action[3] = -wrap(candidate - yaw)
                target = beacon_camera_target(observation)
                if target is not None:
                    action[4] = 3 * wrap(target[0] - observation['gimbal_rad'][0])
                    action[5] = 3 * (target[1] - observation['gimbal_rad'][1])
            else:
                action[2] = -0.3
            return self.finish(action, observation, {'control_phase': phase, 'pose_valid': False, 'pad_visibility_probability': probability})
        if self.relative is not None:
            previous_enu = heading_rotation(self.previous_yaw) @ (self.relative * [1, -1, -1]) + heading_rotation(self.previous_yaw) @ (self.relative_velocity * [1, -1, -1]) * dt
            predicted = heading_rotation(yaw).T @ previous_enu * [1, -1, -1]
            alpha = min(1.0, dt / 0.12)
            r = predicted + alpha * (r - predicted)
        self.relative = r.copy()
        self.relative_velocity = velocity.copy()
        self.previous_yaw = yaw
        normal = normal / np.linalg.norm(normal)
        relative_tangent = r - normal * np.dot(r, normal)
        lateral = float(np.linalg.norm(relative_tangent))
        speed = float(np.linalg.norm(velocity[:2]))
        deck_tilt = math.acos(np.clip(-normal[2], -1, 1))
        delta = 0.5 * math.atan2(heading[0], heading[1])
        candidate = yaw + delta
        if self.heading_target is None:
            self.heading_target = candidate
        else:
            self.heading_target += min(1.0, dt / 0.25) * 0.5 * wrap(2 * (candidate - self.heading_target))
        heading_error = wrap(self.heading_target - yaw)
        feet_heading = (body_to_heading(roll, pitch) @ self.feet.T).T
        clearance = float(np.min((feet_heading - r) @ normal))
        ready = lateral < 0.12 and speed < 0.18 and (abs(heading_error) < math.radians(8)) and (deck_tilt < math.radians(8)) and (not b.get('valid', False) or b.get('dock_ready', False))
        self.stable_elapsed = self.stable_elapsed + dt if ready else 0.0
        phase = 'align' if lateral > 0.15 else 'match'
        boat_velocity = numeric[:3] + velocity
        offset = r[:2] + normal[:2] * (r[2] / max(-normal[2], 0.5))
        action = np.zeros(6)
        action[:2] = boat_velocity[:2] + 1.1 * offset + 0.45 * velocity[:2]
        action[2] = boat_velocity[2] - 0.8 * (max(1.2, clearance) - clearance)
        if self.stable_elapsed >= 0.24:
            phase = 'descend'
            action[2] = boat_velocity[2] + (0.22 if clearance > 0.65 else 0.1)
        elif clearance < 1.2:
            phase = 'recover'
            action[2] = boat_velocity[2] - 0.4 * (1.2 - clearance)
        if ready and clearance < 0.03:
            phase = 'touchdown'
            action[:3] = boat_velocity
            action[2] = max(boat_velocity[2] + 0.32, 0.3)
        if px4.get('landed', False):
            phase = 'confirm'
            action[:3] = boat_velocity
            action[2] = max(boat_velocity[2] + 0.32, 0.3)
        if not px4.get('armed', False):
            action[:4] = 0.0
            phase = 'disarmed'
        action[3] = 0.0 if phase in ('touchdown', 'confirm', 'disarmed') else -heading_error
        camera_observation = dict(observation)
        camera_observation['beacon'] = {'valid': True, 'age_s': 0.0, 'relative_heading_m': r.tolist()}
        target = beacon_camera_target(camera_observation)
        if target is not None:
            action[4] = 3 * wrap(target[0] - observation['gimbal_rad'][0])
            action[5] = 3 * (target[1] - observation['gimbal_rad'][1])
        info = {'control_phase': phase, 'pose_valid': True, 'estimated_relative_position': r.tolist(), 'estimated_relative_velocity': velocity.tolist(), 'estimated_lateral_error_m': lateral, 'estimated_clearance_m': clearance, 'estimated_heading_error_deg': math.degrees(heading_error), 'estimated_deck_tilt_deg': math.degrees(deck_tilt), 'stable_tracking_s': self.stable_elapsed, 'pad_visibility_probability': probability}
        return self.finish(action, observation, info)

    def finish(self, action, observation, diagnostics):
        norm = np.linalg.norm(action[:2])
        if norm > 2:
            action[:2] *= 2 / norm
        action[2] = np.clip(action[2], -1.0, 0.7)
        action[3] = np.clip(action[3], -0.5, 0.5)
        action, extra = self.guard.apply(action, observation, diagnostics)
        if diagnostics['control_phase'] == 'disarmed':
            action[:4] = 0.0
        diagnostics.update(extra)
        self.last_phase = diagnostics['control_phase']
        return (action, diagnostics)

class HybridPosePolicy:

    def __init__(self, checkpoint, calibration, slew_limits, device='cuda'):
        self.calibration = calibration
        self.controller = LandingController(calibration['foot_local_flu'], slew_limits)
        self.metadata = {}
        self.history = deque(maxlen=16)
        self.height = None
        self.last_valid = None
        self.last_valid_time = None
        self.hidden = None

    def reset(self):
        self.hidden = None
        self.controller.reset()
        self.history.clear()
        self.height = None
        self.last_valid = None
        self.last_valid_time = None

    def remember_projection(self, estimate, observation, projected, time):
        if projected is not None and np.isfinite(projected).all() and (estimate['visibility'] >= 0.8) and observation['image_valid'] and (observation['image_age_s'] <= 0.25):
            self.last_valid = copy.deepcopy(estimate)
            self.last_valid_time = time
