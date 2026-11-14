"""Radio-first boat search layered over the frozen visual search student.

The canonical student is sensor-only and must stay that way.  This variant is a
working policy: a valid boat packet supplies a metrically meaningful target and
the aircraft flies toward it with the camera looking at the boat.  The learned
search head is still the authority for identity: control is handed to the frozen
R15 landing policy only after the head reports ``target_boat`` for several
consecutive frames.  Without a usable packet the inherited visual search runs
unchanged.  At initialization, before either search mode starts, a one-time
pre360 sweep looks near-nadir around the aircraft so a boat already underneath
is found and handed directly to the frozen lander.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import torch

_HERE = Path(__file__).resolve().parent
_STUDENT = _HERE.parent / 'student'
if str(_STUDENT) not in sys.path:
    sys.path.insert(0, str(_STUDENT))

_spec = importlib.util.spec_from_file_location('student_runtime', _STUDENT / 'runtime.py')
if _spec is None or _spec.loader is None:
    raise ImportError('cannot load the frozen student runtime')
student_runtime = importlib.util.module_from_spec(_spec)
sys.modules['student_runtime'] = student_runtime
_spec.loader.exec_module(student_runtime)

# The canonical student code was relocated from benchmark/student to
# benchmark/policies/student; its common.py still derives REPO as
# benchmark/.  Correct the module globals here so the frozen source stays
# byte-identical while this variant resolves the real repository paths.
import common as student_common
_REPO = _HERE.parents[2]
student_common.REPO = _REPO
student_common.LOCAL = _REPO / 'artifacts/local_curriculum_20261020'
student_common.R15 = (_REPO / 'artifacts/approved_curriculum_20261020/'
                      'candidate_exports/experimental_v39/package/base_r15')
student_runtime.R15 = student_common.R15
for _name in list(sys.modules):
    if _name == student_common.PACKAGE or _name.startswith(student_common.PACKAGE + '.'):
        del sys.modules[_name]
SearchRuntime = student_runtime.SearchRuntime

FAST_RANGE_M = 30.0
FAST_MPS = 2.0
CLOSE_MPS = 1.0
STOP_RANGE_M = 3.0
HANDOFF_FRAMES = 4
HANDOFF_CONFIDENCE = 0.50
# pre360 geometry: the camera first looks straight down, then tilts 15 degrees
# back up to 75 degrees below horizontal.  With the 36.1 degree vertical lens,
# the point directly below the aircraft at 10 m is about 0.53 m inside the
# bottom edge of the image (18.05 deg half-FOV; 15 deg leaves 3.05 deg margin).
PRE360_TILT_DEG = 75.0
PRE360_NADIR_S = 2.5
PRE360_YAW_RATE = 0.5          # rad/s, about 12.6 s for one revolution
PRE360_SETTLE_YAW_RATE = 0.10  # rad/s, handoff gate
PRE360_STOP_SETTLE_S = 0.40
PRE360_LOST_S = 0.60
MAX_PACKET_AGE_S = 3.0
MAX_POSITION_SIGMA_M = 1.5
MAX_VELOCITY_SIGMA_MPS = 0.20


class RadioSearchRuntime(SearchRuntime):
    """The frozen visual student plus a bounded radio-first approach mode."""

    def __init__(self, bundle, device='cpu'):
        self.radio_target = None
        self.radio_velocity = np.zeros(2)
        self.radio_age = 0.0
        self.radio_active = False
        self.radio_handoff_frames = 0
        self.radio_dock_ready = False
        self.pre360_done = False
        self.pre360_skipped = False
        self.pre360_phase = 'check'
        self.pre360_nadir_start = None
        self.pre360_sweep_start = None
        self.pre360_last_yaw = None
        self.pre360_yaw_accum = 0.0
        self.pre360_candidate_frames = 0
        self.pre360_stop_start = None
        self.pre360_settle_s = 0.0
        super().__init__(bundle, device=device)

    def reset(self):
        super().reset()
        self.radio_target = None
        self.radio_velocity = np.zeros(2)
        self.radio_age = 0.0
        self.radio_active = False
        self.radio_handoff_frames = 0
        self.radio_dock_ready = False
        self.pre360_done = False
        self.pre360_skipped = False
        self.pre360_phase = 'check'
        self.pre360_nadir_start = None
        self.pre360_sweep_start = None
        self.pre360_last_yaw = None
        self.pre360_yaw_accum = 0.0
        self.pre360_candidate_frames = 0
        self.pre360_stop_start = None
        self.pre360_settle_s = 0.0

    @staticmethod
    def radio_free(observation):
        return {key: value for key, value in observation.items() if key != 'beacon'}

    def usable_beacon(self, observation):
        """Only a fresh, metrically plausible packet may steer the aircraft."""
        packet = observation.get('beacon')
        if not isinstance(packet, dict) or packet.get('valid') is not True:
            return None
        try:
            age = float(packet['age_s'])
            position_sigma = float(packet['position_sigma_m'])
            velocity_sigma = float(packet['velocity_sigma_m_s'])
            relative = np.asarray(packet['relative_heading_m'], dtype=float)
            velocity = np.asarray(packet['velocity_heading_m_s'], dtype=float)
        except (KeyError, TypeError, ValueError):
            return None
        if not all(math.isfinite(value) for value in
                   (age, position_sigma, velocity_sigma)):
            return None
        if age < 0.0 or age > MAX_PACKET_AGE_S:
            return None
        if position_sigma > MAX_POSITION_SIGMA_M or velocity_sigma > MAX_VELOCITY_SIGMA_MPS:
            return None
        if relative.shape != (3,) or velocity.shape != (3,):
            return None
        if not np.isfinite(relative).all() or not np.isfinite(velocity).all():
            return None
        return dict(age=age, relative=relative, velocity=velocity,
                    dock_ready=packet.get('dock_ready') is True)

    def _proposals(self, rgb, observation):
        rotation, _, focal, _ = self.visual.camera_geometry(observation, self.calibration)
        image = torch.from_numpy(np.asarray(rgb).copy()).permute(2, 0, 1)[None].to(self.device)
        fine, context = student_runtime.encode_maps(self.base.model, image)
        proposals = student_runtime.decode(self.head(fine, context))[0]
        self.last_maps = (fine, context)
        self.last_proposals = proposals
        return proposals

    def _target_boat_visible(self, proposals):
        return any(item.get('evidence') == 'target_boat'
                   and float(item.get('confidence', 0.0)) >= HANDOFF_CONFIDENCE
                   for item in proposals)

    def _handoff(self, rgb, observation, point, velocity, t, key):
        self.selected = key
        self.last_point = np.asarray(point, dtype=float).copy()
        self.boat_velocity = np.asarray(velocity, dtype=float).copy()
        self.landing_latched = True
        self.latched_since = t
        self.base.reset()
        self._harden_base_recovery()
        self.base.decode_spatial = self.native_decode_spatial
        return super().act(rgb, self.radio_free(observation))

    def _pre360_point(self, proposals, position, observation, yaw):
        flip = np.diag([1., -1., -1.])
        for item in sorted(proposals, key=lambda p: -float(p.get('confidence', 0.0))):
            if item.get('evidence') != 'target_boat':
                continue
            if float(item.get('confidence', 0.0)) < HANDOFF_CONFIDENCE:
                continue
            relative = self.geometry.relative_from_pixel(
                item['pixel'], position[2] - .45, observation, self.calibration)
            if relative is None:
                continue
            return position + self._rotation(yaw) @ flip @ relative
        return None

    def _pre360_action(self, observation, position, pan, tilt, yaw_rate=0.0,
                       tilt_target=PRE360_TILT_DEG):
        action = np.zeros(6)
        action[2] = -float(np.clip(.8 * (self.height - position[2]), -.5, .5))
        action[3] = float(np.clip(yaw_rate, -.5, .5))
        action[4] = float(np.clip(3.0 * (0.0 - pan), -math.radians(50), math.radians(50)))
        action[5] = float(np.clip(3.0 * (math.radians(tilt_target) - tilt),
                                  -math.radians(40), math.radians(40)))
        return self.guard.apply(action, observation, dict(pad_visibility_probability=0.))

    def _pre360_diag(self, phase, extra):
        return dict(control_phase=phase, boat_radio=False, radio_mode=False,
                    pre360=True, pre360_done=self.pre360_done,
                    pre360_skipped=self.pre360_skipped,
                    pre360_phase=self.pre360_phase,
                    pre360_yaw_accum_rad=self.pre360_yaw_accum,
                    pre360_candidate_frames=self.pre360_candidate_frames,
                    pre360_camera_tilt_deg=PRE360_TILT_DEG,
                    pre360_reference_height_m=10.0,
                    search_identity_confirmed=False, radio_handoff_frames=0, **extra)

    def _pre360(self, rgb, observation, t, position, yaw, pan, tilt, dt):
        """One-time initialization check: look down, tilt up, yaw 360 degrees.

        This is intentionally independent of radio availability and is not part
        of scan 1.  It runs once per policy reset.  If the learned head confirms
        ``target_boat``, the turn is stopped and the frozen R15 lander is given
        control only after the yaw rate has settled and identity is reconfirmed.
        """
        own = observation['px4']
        if self.pre360_phase == 'check':
            proposals = self._proposals(rgb, observation)
            if self._target_boat_visible(proposals):
                self.pre360_done = True
                self.pre360_skipped = True
                self.pre360_phase = 'done'
                return None
            self.pre360_phase = 'nadir'
            self.pre360_nadir_start = t
            self.pre360_last_yaw = yaw
            self.pre360_yaw_accum = 0.0
            self.pre360_candidate_frames = 0

        if self.pre360_phase == 'nadir':
            proposals = self._proposals(rgb, observation)
            if self._target_boat_visible(proposals):
                self.pre360_candidate_frames += 1
            else:
                self.pre360_candidate_frames = 0
            if self.pre360_candidate_frames >= HANDOFF_FRAMES:
                point = self._pre360_point(proposals, position, observation, yaw)
                if point is not None:
                    return self._handoff(rgb, observation, point, np.zeros(2), t,
                                         'pre360_target')
            if t - self.pre360_nadir_start < PRE360_NADIR_S:
                action, extra = self._pre360_action(observation, position, pan, tilt,
                                                    yaw_rate=0.0, tilt_target=90.0)
                return action, self._pre360_diag('pre360_nadir', extra)
            self.pre360_phase = 'sweep'
            self.pre360_sweep_start = t
            self.pre360_last_yaw = yaw
            self.pre360_candidate_frames = 0

        if self.pre360_phase == 'sweep':
            proposals = self._proposals(rgb, observation)
            if self._target_boat_visible(proposals):
                self.pre360_candidate_frames += 1
            else:
                self.pre360_candidate_frames = 0
            if self.pre360_candidate_frames >= HANDOFF_FRAMES:
                self.pre360_phase = 'stopping'
                self.pre360_stop_start = t
                self.pre360_settle_s = 0.0
                self.pre360_candidate_frames = 0
                action, extra = self._pre360_action(observation, position, pan, tilt,
                                                    yaw_rate=0.0)
                return action, self._pre360_diag('pre360_stopping', extra)
            delta_yaw = float(self.wrap(yaw - self.pre360_last_yaw))
            self.pre360_last_yaw = yaw
            self.pre360_yaw_accum += max(0.0, delta_yaw)
            if self.pre360_yaw_accum >= 2.0 * math.pi:
                self.pre360_done = True
                self.pre360_phase = 'done'
                return None
            action, extra = self._pre360_action(observation, position, pan, tilt,
                                                yaw_rate=PRE360_YAW_RATE)
            return action, self._pre360_diag('pre360_sweep', extra)

        if self.pre360_phase == 'stopping':
            yaw_rate = abs(float(own['angular_rate_frd_rad_s'][2]))
            if yaw_rate < PRE360_SETTLE_YAW_RATE:
                self.pre360_settle_s += dt
            else:
                self.pre360_settle_s = 0.0
            proposals = self._proposals(rgb, observation)
            if self._target_boat_visible(proposals):
                self.pre360_candidate_frames += 1
            else:
                self.pre360_candidate_frames = 0
            if (self.pre360_candidate_frames >= HANDOFF_FRAMES
                    and self.pre360_settle_s >= PRE360_STOP_SETTLE_S):
                point = self._pre360_point(proposals, position, observation, yaw)
                if point is not None:
                    return self._handoff(rgb, observation, point, np.zeros(2), t,
                                         'pre360_target')
            if (self.pre360_candidate_frames == 0
                    and t - self.pre360_stop_start >= PRE360_LOST_S):
                # The boat left the frame while braking; resume the sweep from
                # the current heading rather than handing off blind.
                self.pre360_phase = 'sweep'
                self.pre360_last_yaw = yaw
                self.pre360_candidate_frames = 0
                action, extra = self._pre360_action(observation, position, pan, tilt,
                                                    yaw_rate=PRE360_YAW_RATE)
                return action, self._pre360_diag('pre360_sweep', extra)
            action, extra = self._pre360_action(observation, position, pan, tilt,
                                                yaw_rate=0.0)
            return action, self._pre360_diag('pre360_stopping', extra)

        return None

    @staticmethod
    def _rotation(yaw):
        c, s = math.cos(yaw), math.sin(yaw)
        return np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])

    @torch.inference_mode()
    def act(self, rgb, observation):
        beacon = self.usable_beacon(observation)
        radio_free = self.radio_free(observation)
        own = observation['px4']
        t = float(observation['mission']['elapsed_s'])

        # Landing, contact, estimation holds and image holds stay the frozen
        # student/R15 behaviour and never see radio after handoff.
        if self.landing_latched or self.base.controller.controller.contact_started is not None:
            return super().act(rgb, radio_free)
        if (not own.get('valid')
                or max(own.get('position_age_s', 100), own.get('attitude_age_s', 100)) > .25
                or not observation.get('image_valid')
                or observation.get('image_age_s', 100) > .25):
            return super().act(rgb, radio_free)

        position = np.asarray(own['position_enu_m'], dtype=float)
        if self.height is None:
            self.height = float(position[2])
        yaw = math.pi / 2 - own['attitude_ned_rad'][2]
        pan, tilt = (float(observation['gimbal_rad'][0]),
                     float(observation['gimbal_rad'][1]))
        dt = float(observation.get('decision_dt_s', .04))

        # One-time initialization stage, before radio or visual search.  It is
        # conditional on the target not already being visible and never repeats
        # when the inherited scan 1 starts or restarts.
        if not self.pre360_done:
            pre360 = self._pre360(rgb, radio_free, t, position, yaw, pan, tilt, dt)
            if pre360 is not None:
                return pre360

        if beacon is None:
            self.radio_active = False
            self.radio_handoff_frames = 0
            self.radio_target = None
            self.radio_velocity = np.zeros(2)
            return super().act(rgb, radio_free)

        rotation = self._rotation(yaw)
        flip = np.diag([1., -1., -1.])
        predicted_relative = beacon['relative'] + beacon['velocity'] * beacon['age']
        self.radio_target = position + rotation @ flip @ predicted_relative
        self.radio_velocity = (rotation @ flip @ beacon['velocity'])[:2]
        self.radio_age = beacon['age']
        self.radio_dock_ready = beacon['dock_ready']
        self.radio_active = True

        proposals = self._proposals(rgb, observation)
        if self._target_boat_visible(proposals):
            self.radio_handoff_frames += 1
        else:
            self.radio_handoff_frames = 0
        if self.radio_handoff_frames >= HANDOFF_FRAMES:
            return self._handoff(rgb, observation, self.radio_target,
                                 self.radio_velocity, t, 'radio_target')

        delta = self.radio_target - position
        range_xy = float(np.linalg.norm(delta[:2]))
        body = flip @ rotation.T @ delta
        prev = np.asarray(observation['previous_executed_action'], dtype=float)
        action = np.zeros(6)
        action[2] = -float(np.clip(.8 * (self.height - position[2]), -.5, .5))

        if range_xy > STOP_RANGE_M:
            speed = FAST_MPS if range_xy > FAST_RANGE_M else CLOSE_MPS
            # A 1 m/s closing command cannot catch a faster boat.  Preserve the
            # requested 1 m/s close schedule for normal boats, but keep a real
            # closing margin when the packet says the boat is faster.
            boat_speed = float(np.linalg.norm(self.radio_velocity))
            if range_xy <= FAST_RANGE_M and boat_speed > 0.8:
                speed = min(FAST_MPS, max(speed, boat_speed + 0.5))
            unit = delta[:2] / max(range_xy, 1e-6)
            desired_world = unit * speed
            body_velocity = (flip @ rotation.T @ np.r_[desired_world, 0.0])[:2]
            limit = self.slew_limits * dt
            action[0] = float(np.clip(body_velocity[0],
                                      prev[0] - limit[0], prev[0] + limit[0]))
            action[1] = float(np.clip(body_velocity[1],
                                      prev[1] - limit[1], prev[1] + limit[1]))
            norm = float(np.linalg.norm(action[:2]))
            if norm > FAST_MPS:
                action[:2] *= FAST_MPS / norm

        heading = math.atan2(delta[1], delta[0])
        action[3] = float(np.clip(-self.wrap(heading - yaw), -.5, .5))
        action[4] = float(np.clip(3.0 * (math.atan2(-body[1], body[0]) - pan),
                                  -math.radians(50), math.radians(50)))
        action[5] = float(np.clip(
            3.0 * (math.atan2(body[2], np.linalg.norm(body[:2])) - tilt),
            -math.radians(40), math.radians(40)))
        action, extra = self.guard.apply(action, observation,
                                         dict(pad_visibility_probability=0.))
        phase = 'radio_hold' if range_xy <= STOP_RANGE_M else 'radio_approach'
        return action, dict(control_phase=phase, boat_radio=True, radio_mode=True,
                            radio_range_m=range_xy, radio_age_s=self.radio_age,
                            radio_dock_ready=self.radio_dock_ready,
                            radio_handoff_frames=self.radio_handoff_frames,
                            pre360_done=True, pre360_skipped=self.pre360_skipped,
                            search_identity_confirmed=False,
                            **extra)
