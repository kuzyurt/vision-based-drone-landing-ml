"""Browser radio-first/pre360 layer over the frozen student search runtime."""
from __future__ import annotations

import math
import numpy as np

from .student_runtime import SearchRuntime, MIN_SEARCH_HEIGHT_M
from . import tidewater_guidance as guidance

# The approach speed now follows tidewater_guidance.approach_velocity (intercept
# in the boat's frame, braking by distance). The old flat 2 m/s / 1 m/s schedule
# is kept only as documentation of what it replaced.
FAST_RANGE_M = 30.0
FAST_MPS = 2.0
CLOSE_MPS = 1.0
STOP_RANGE_M = 3.0
HOLD_REACHED_M = 1.0
DEAD_RECKONING_S = 6.0
DEAD_RECKONING_MPS = 1.5
HANDOFF_FRAMES = 4
HANDOFF_CONFIDENCE = 0.50
# Pre-check (2026-11-14): climb to the search height with the camera straight
# down, then hand over to the radio approach / normal horizon scan. The former
# 75 deg-down 360 deg turn is gone: it mostly looked at nearby water (and the
# sun glare on it); the normal scan already looks around at the horizon.
PRE360_TILT_DEG = 90.0
PRE360_NADIR_S = 2.0          # look down at least this long, even if already high
PRE360_CLIMB_TOL_M = 0.3      # "at search height" tolerance
PRE360_CLIMB_TIMEOUT_S = 15.0 # never hold the search longer (ceiling, wind)
MAX_PACKET_AGE_S = 3.0
MAX_POSITION_SIGMA_M = 1.5
MAX_VELOCITY_SIGMA_MPS = 0.20

class RadioSearchRuntime(SearchRuntime):
    """The frozen visual student plus a bounded radio-first approach mode."""

    def __init__(self, config, policy):
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
        self.pre360_search_handover = False
        self.radio_last = None
        super().__init__(config, policy)

    def reset(self):
        super().reset()
        self.radio_last = None
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
        self.pre360_search_handover = False

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

    def _spot(self, observation, position, yaw, pixel):
        """World ray and sea-plane point of an image pixel (same geometry as
        the normal search)."""
        rotation, _, focal, _ = self.visual.camera_geometry(observation, self.calibration)
        ray = rotation @ np.array([(pixel[0] - 320) / focal, -(pixel[1] - 180) / focal, -1.])
        ray /= np.linalg.norm(ray)
        R = self._rotation(yaw)
        D = np.diag([1., -1., -1.])
        world = R @ D @ ray
        if ray[2] <= .02:
            return world, None
        relative = self.geometry.relative_from_pixel(pixel, position[2] - .45,
                                                     observation, self.calibration)
        point = None if relative is None else position + R @ D @ relative
        return world, point

    def _agrees(self, position, world, point):
        ctx = self._radio_ctx
        if ctx is None:
            return True
        return guidance.agrees_with_radio(position[:2], ctx['target'][:2], world,
                                          None if point is None else point[:2],
                                          ctx['sigma'], ctx['speed'], ctx['age'])

    def _target_boat_visible(self, proposals, observation=None, position=None, yaw=None):
        for item in proposals:
            if (item.get('evidence') != 'target_boat'
                    or float(item.get('confidence', 0.0)) < HANDOFF_CONFIDENCE):
                continue
            if observation is None or self._radio_ctx is None:
                return True
            # The radio hand-off needs the confirmed boat to be where the radio
            # says it is (direction tight, distance loose).
            world, point = self._spot(observation, position, yaw, item['pixel'])
            if self._agrees(position, world, point):
                return True
        return False

    def _selection_agrees(self, position):
        track = self.tracks.get(self.selected)
        if track is None:
            return False
        point = track.get('position')
        return self._agrees(position, track['ray'], point)

    def _handoff(self, rgb, observation, point, velocity, t, key):
        self.selected = key
        self.last_point = np.asarray(point, dtype=float).copy()
        self.boat_velocity = np.asarray(velocity, dtype=float).copy()
        self.landing_latched = True
        self.latched_since = t
        self.latch_samples = []
        self.latch_metric_seen = False
        self.base.reset()
        self._harden_base_recovery()
        return super().act(rgb, self.radio_free(observation))

    def _pre360_search(self, observation, position, yaw, t):
        """Run the normal search's evidence rules on the current pre360 view.

        Returns True when the normal search would act on what it sees now:
        a boat it would inspect (for example ``target_or_similar``) or the
        confirmed ``target_boat``.  The pre360 look-around then ends and the
        normal search continues from this view, so a boat seen during pre360
        is treated exactly as it would be right after pre360.
        """
        rotation, _, focal, _ = self.visual.camera_geometry(observation, self.calibration)
        selected, _ = self._update_search(observation, position, yaw,
                                          self._rotation(yaw), np.diag([1., -1., -1.]),
                                          rotation, focal, t)
        return selected is not None or bool(self.search.confirmed)

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
                    pre360_last_yaw_rad=self.pre360_last_yaw,
                    pre360_sweep_start_s=self.pre360_sweep_start,
                    pre360_camera_tilt_deg=PRE360_TILT_DEG,
                    pre360_reference_height_m=10.0,
                    pre360_rule='normal_search_evidence',
                    pre360_search_handover=self.pre360_search_handover,
                    search_height_m=self.height,
                    search_identity_confirmed=bool(self.search.confirmed),
                    search_selected=self.selected, radio_handoff_frames=0, **extra)

    def _pre360_handover(self, observation, position, pan, tilt, skipped):
        """End pre360 because the normal search found something to act on.

        This frame only stops the turn and holds the camera; the normal search
        (which already holds the selection) steers from the next frame.
        """
        self.pre360_done = True
        self.pre360_skipped = skipped
        self.pre360_phase = 'done'
        self.pre360_search_handover = True
        action, extra = self._pre360_action(observation, position, pan, tilt,
                                            yaw_rate=0.0,
                                            tilt_target=math.degrees(tilt))
        return action, self._pre360_diag('pre360_handover', extra)

    def _pre360(self, rgb, observation, t, position, yaw, pan, tilt, dt):
        """One-time initialization check: climb to the search height with the
        camera straight down (is the boat right underneath?), then continue.

        Independent of radio availability, not part of scan 1, once per policy
        reset. Every frame is judged with the same evidence rules as the normal
        search; as soon as the normal search would inspect or confirm a boat,
        the check ends and the normal search continues from this view. There is
        no look-around turn any more: the radio approach or the normal horizon
        scan follows directly.
        """
        if self.pre360_phase == 'check':
            if self._pre360_search(observation, position, yaw, t):
                return self._pre360_handover(observation, position, pan, tilt, True)
            self.pre360_phase = 'nadir'
            self.pre360_nadir_start = t
            self.pre360_last_yaw = yaw
            self.pre360_yaw_accum = 0.0
            self.pre360_candidate_frames = 0

        if self.pre360_phase == 'nadir':
            if self._pre360_search(observation, position, yaw, t):
                return self._pre360_handover(observation, position, pan, tilt, False)
            elapsed = t - self.pre360_nadir_start
            at_height = abs(float(position[2]) - self.height) <= PRE360_CLIMB_TOL_M
            if (elapsed < PRE360_NADIR_S or not at_height) and elapsed < PRE360_CLIMB_TIMEOUT_S:
                action, extra = self._pre360_action(observation, position, pan, tilt,
                                                    yaw_rate=0.0, tilt_target=90.0)
                return action, self._pre360_diag('pre360_nadir', extra)
            self.pre360_done = True
            self.pre360_phase = 'done'
            return None

        return None

    @staticmethod
    def _rotation(yaw):
        c, s = math.cos(yaw), math.sin(yaw)
        return np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])

    def act(self, rgb, observation):
        beacon = self.usable_beacon(observation)
        radio_free = self.radio_free(observation)
        own = observation['px4']
        t = float(observation['mission']['elapsed_s'])
        self._radio_ctx = None
        own_ok = (own.get('valid')
                  and max(own.get('position_age_s', 100), own.get('attitude_age_s', 100)) <= .25)
        flip = np.diag([1., -1., -1.])
        if beacon is not None and own_ok:
            # Boat velocity from the radio, kept for the near-deck finish
            # (the landing controller itself never sees the radio).
            yaw_now = math.pi / 2 - own['attitude_ned_rad'][2]
            self.radio_hint = dict(t=t, velocity=(self._rotation(yaw_now) @ flip @ beacon['velocity'])[:2])

        # Landing, contact, estimation holds and image holds stay the frozen
        # student/R15 behaviour and never see radio after handoff.
        if self.landing_latched or self.base.controller.controller.contact_started is not None:
            if not self.pre360_done:
                self.pre360_done = True
                self.pre360_phase = 'done'
            return super().act(rgb, radio_free)
        if (not own_ok
                or not observation.get('image_valid')
                or observation.get('image_age_s', 100) > .25):
            return super().act(rgb, radio_free)

        position = np.asarray(own['position_enu_m'], dtype=float)
        if self.height is None:
            self.height = max(float(position[2]), MIN_SEARCH_HEIGHT_M)
        yaw = math.pi / 2 - own['attitude_ned_rad'][2]
        pan, tilt = (float(observation['gimbal_rad'][0]),
                     float(observation['gimbal_rad'][1]))
        dt = float(observation.get('decision_dt_s', .04))
        rotation = self._rotation(yaw)

        # Where the radio says the boat is. While this exists, camera spots
        # that disagree with it cannot steer the search (glare, other boats).
        dead_reckoning = False
        if beacon is not None:
            predicted_relative = beacon['relative'] + beacon['velocity'] * beacon['age']
            self.radio_target = position + rotation @ flip @ predicted_relative
            self.radio_velocity = (rotation @ flip @ beacon['velocity'])[:2]
            self.radio_age = beacon['age']
            self.radio_dock_ready = beacon['dock_ready']
            sigma = float(observation['beacon'].get('position_sigma_m', 1.5))
            self.radio_last = dict(t=t, target=self.radio_target.copy(),
                                   velocity=self.radio_velocity.copy(), sigma=sigma,
                                   age=beacon['age'])
            self._radio_ctx = dict(target=self.radio_target, sigma=sigma,
                                   speed=float(np.linalg.norm(self.radio_velocity)),
                                   age=beacon['age'])
        elif (self.radio_last is not None and t - self.radio_last['t'] <= DEAD_RECKONING_S
              and not self.pre360_search_handover):
            # Radio just dropped out: keep flying to where it said the boat is
            # going for a few seconds (camera hand-off stays possible), then
            # fall back to the normal visual search.
            last = self.radio_last
            elapsed = t - last['t']
            self.radio_target = last['target'] + np.r_[last['velocity'] * elapsed, 0.]
            self.radio_velocity = last['velocity'].copy()
            self.radio_age = last['age'] + elapsed
            self._radio_ctx = dict(target=self.radio_target, sigma=last['sigma'],
                                   speed=float(np.linalg.norm(self.radio_velocity)),
                                   age=self.radio_age)
            dead_reckoning = True

        # One-time initialization stage, before radio or visual search.  It is
        # conditional on the target not already being visible and never repeats
        # when the inherited scan 1 starts or restarts.
        if not self.pre360_done:
            pre360 = self._pre360(rgb, radio_free, t, position, yaw, pan, tilt, dt)
            if pre360 is not None:
                return pre360

        if self.pre360_search_handover:
            if self.selected is not None or self.search.confirmed:
                if self._radio_ctx is not None and not self._selection_agrees(position):
                    # The camera picked something the radio disagrees with
                    # (for example sun glare): the radio keeps authority.
                    self.search.restart(t, 'radio_disagrees_with_camera')
                    self.selected = None
                    self.last_point = None
                    self.pre360_search_handover = False
                else:
                    # The camera already found the boat during pre360: the normal
                    # visual search keeps authority, exactly as without radio.
                    self.radio_active = False
                    return super().act(rgb, radio_free)
            else:
                # The search lost that boat again; radio-first guidance resumes.
                self.pre360_search_handover = False

        if beacon is None and not dead_reckoning:
            self.radio_active = False
            self.radio_handoff_frames = 0
            self.radio_target = None
            self.radio_velocity = np.zeros(2)
            return super().act(rgb, radio_free)

        self.radio_active = True
        proposals = self._proposals(rgb, observation)
        if self._target_boat_visible(proposals, radio_free, position, yaw):
            self.radio_handoff_frames += 1
        else:
            self.radio_handoff_frames = 0
        if self.radio_handoff_frames >= HANDOFF_FRAMES:
            self._radio_ctx = None
            return self._handoff(rgb, observation, self.radio_target,
                                 self.radio_velocity, t, 'radio_target')

        delta = self.radio_target - position
        range_xy = float(np.linalg.norm(delta[:2]))
        body = flip @ rotation.T @ delta
        prev = np.asarray(observation['previous_executed_action'], dtype=float)
        action = np.zeros(6)
        action[2] = -float(np.clip(.8 * (self.height - position[2]), -.5, .5))

        # Intercept in the boat's frame with distance-based braking (see
        # tidewater_guidance.approach_velocity). Matches the boat's velocity at
        # the waiting point instead of stopping dead next to a moving boat.
        max_speed = DEAD_RECKONING_MPS if dead_reckoning else guidance.APPROACH_MAX_SPEED_MPS
        desired_world, approach = guidance.approach_velocity(
            position[:2], self.radio_target[:2], self.radio_velocity, max_speed=max_speed)
        body_velocity = (flip @ rotation.T @ np.r_[desired_world, 0.0])[:2]
        limit = self.slew_limits * dt
        action[0] = float(np.clip(body_velocity[0], prev[0] - limit[0], prev[0] + limit[0]))
        action[1] = float(np.clip(body_velocity[1], prev[1] - limit[1], prev[1] + limit[1]))
        norm = float(np.linalg.norm(action[:2]))
        if norm > FAST_MPS:
            action[:2] *= FAST_MPS / norm

        heading = math.atan2(delta[1], delta[0])
        action[3] = float(np.clip(-self.wrap(heading - yaw), -.5, .5)) if range_xy > 1.0 else 0.0
        action[4] = float(np.clip(3.0 * (math.atan2(-body[1], body[0]) - pan),
                                  -math.radians(50), math.radians(50)))
        action[5] = float(np.clip(
            3.0 * (math.atan2(body[2], np.linalg.norm(body[:2])) - tilt),
            -math.radians(40), math.radians(40)))
        action, extra = self.guard.apply(action, observation,
                                         dict(pad_visibility_probability=0.))
        if dead_reckoning:
            phase = 'radio_dead_reckoning'
        else:
            phase = 'radio_hold' if approach['hold_distance_m'] <= HOLD_REACHED_M else 'radio_approach'
        return action, dict(control_phase=phase, boat_radio=True, radio_mode=True,
                            radio_range_m=range_xy, radio_age_s=self.radio_age,
                            radio_dock_ready=self.radio_dock_ready,
                            radio_handoff_frames=self.radio_handoff_frames,
                            pre360_done=True, pre360_skipped=self.pre360_skipped,
                            search_identity_confirmed=False,
                            approach_hold_distance_m=approach['hold_distance_m'],
                            approach_closing_m_s=approach['closing_m_s'],
                            approach_closing_limit_m_s=approach['closing_limit_m_s'],
                            approach_boat_speed_m_s=approach['boat_speed_m_s'],
                            approach_feasible=approach['feasible'],
                            approach_warning=approach['warning'],
                            **extra)
