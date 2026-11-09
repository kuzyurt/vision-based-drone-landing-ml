from .nearfield_visibility import final_view_plan
from .physical_pose_context import fit_height_context
from .persistent_target import VisualTargetState
from .visibility_recovery import VisibilityRecovery
from .visual_acquisition import acquire_visual, visual_motion
'Learned pad orientation plus metric RGB registration and bounded touchdown.'
import copy, math
from collections import deque
import numpy as np
from scipy.optimize import least_squares
from .hybrid_policy import HybridPosePolicy, LandingController, heading_rotation, body_to_heading
from .marker_geometry import marker_pose
from .camera_geometry import compensate_capture, camera_body_transform, relative_from_pixel
from .recording import numeric_observation
from .action_guard import wrap, beacon_camera_target

class MarkerLandingController(LandingController):

    def __init__(self, calibration, slew_limits):
        self.calibration = calibration
        super().__init__(calibration['foot_local_flu'], slew_limits)
        self.visual_boat_sample = None
        self.visual_velocity_enu = None

    def reset(self):
        super().reset()
        self.contact_started = None
        self.nearfield_visibility_hold_started = None
        self.commit_visual_reference = None
        self.camera_branch = None
        self.current_estimate = None
        self.visual_boat_sample = None
        self.visual_velocity_enu = None

    def act(self, estimate, observation):
        self.current_estimate = estimate
        now = float(observation['image_delivery_time_s'])
        px4 = observation['px4']
        if px4.get('landed') or not px4.get('armed'):
            return super().act(estimate, observation)
        if self.contact_started is not None:
            # The marker can fill/leave the image once the feet reach the pad.
            # A recurrent network velocity after that occlusion must not replace
            # the motion observed immediately before contact.
            reference=self.commit_visual_reference
            yaw=math.pi/2-px4['attitude_ned_rad'][2]
            R=heading_rotation(yaw);D=np.diag([1.,-1.,-1.])
            own=np.asarray(px4['position_enu_m'],dtype=float)
            own_velocity=np.asarray(px4['velocity_enu_m_s'],dtype=float)
            predicted=reference['pad_world']+reference['velocity_world']*(now-reference['time'])
            observed=own+R@D@np.asarray(estimate['relative_position'])
            observed_velocity=own_velocity+R@D@np.asarray(estimate['relative_velocity'])
            if (estimate.get('metric_age_s',99)<.08 and estimate.get('motion_ready',False)
                and np.linalg.norm(observed[:2]-predicted[:2])<.08
                and np.linalg.norm(observed_velocity-reference['velocity_world'])<.1):
                reference.update(pad_world=observed.copy(),velocity_world=observed_velocity.copy(),time=now)
                predicted=observed
            roll,pitch,_=px4['attitude_ned_rad']
            speed=np.linalg.norm(own_velocity[:2]-reference['velocity_world'][:2])
            error=predicted[:2]-own[:2]
            height_change=abs((own[2]-predicted[2])-reference['initial_relative_height'])
            fresh=observation['beacon'].get('valid',False) and observation['beacon']['age_s']<3.
            bounded=(now-self.contact_started<=8. and (fresh or not observation['beacon'].get('valid',False))
                     and speed<.15 and max(abs(roll),abs(pitch))<math.radians(8)
                     and np.linalg.norm(error)<.18 and height_change<.25 and px4.get('valid')
                     and px4.get('position_age_s',99)<.5 and px4.get('attitude_age_s',99)<.5)
            if bounded:
                target_velocity=reference['velocity_world'].copy()
                correction=.8*error;length=np.linalg.norm(correction)
                if length>.10:correction*=.10/length
                target_velocity[:2]+=correction
                action=np.zeros(6);action[:3]=D@R.T@target_velocity
                action[2]=max(action[2]+.32,.3)
                return self.finish(action,observation,dict(control_phase='touchdown_commit',pose_valid=False,
                    pad_visibility_probability=estimate['visibility'],contact_commit_s=now-self.contact_started,
                    contact_motion_source='last accepted visual motion plus own odometry',
                    contact_visual_reference_age_s=now-reference['time'],contact_predicted_xy_error_m=float(np.linalg.norm(error)),
                    contact_observed_relative_speed_m_s=float(speed)))
            self.contact_started=None;self.commit_visual_reference=None;self.stable_elapsed=0.
        action, diagnostics = self._tracked_act(estimate, observation)
        if diagnostics['control_phase'] == 'touchdown' and diagnostics.get('stable_tracking_s', 0) >= 0.24 and (diagnostics['estimated_lateral_error_m'] < 0.08) and (np.linalg.norm(estimate['relative_velocity'][:2]) < 0.1) and (abs(diagnostics['estimated_heading_error_deg']) < 5.0) and (diagnostics['estimated_deck_tilt_deg'] < 5.0) and (estimate.get('metric_age_s', 99) < 2.0):
            self.contact_started = now
            yaw=math.pi/2-px4['attitude_ned_rad'][2];R=heading_rotation(yaw);D=np.diag([1.,-1.,-1.])
            own=np.asarray(px4['position_enu_m'],dtype=float)
            pad=own+R@D@np.asarray(estimate['relative_position'])
            velocity=np.asarray(px4['velocity_enu_m_s'])+R@D@np.asarray(estimate['relative_velocity'])
            self.commit_visual_reference=dict(time=now,pad_world=pad.copy(),velocity_world=velocity.copy(),
                                               initial_relative_height=float(own[2]-pad[2]))
        return (action, diagnostics)

    def _tracked_act(self, estimate, observation):
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
                action[3] = -wrap(candidate - yaw) if np.linalg.norm(relative[:2]) > 1.0 else 0.0
                target = beacon_camera_target(observation)
                if target is not None:
                    action[4] = 3 * wrap(target[0] - observation['gimbal_rad'][0]) + float(px4['angular_rate_frd_rad_s'][2])
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
        ready = estimate.get('motion_ready', True) and lateral + estimate.get('metric_uncertainty_m', 0.0) < 0.12 and speed < 0.18 and (abs(heading_error) < math.radians(8)) and (deck_tilt < math.radians(8)) and (not b.get('valid', False) or b.get('dock_ready', False))
        self.stable_elapsed = self.stable_elapsed + dt if ready else 0.0
        phase = 'align' if lateral > 0.15 else 'match'
        boat_velocity = numeric[:3] + velocity
        offset = r[:2] + normal[:2] * (r[2] / max(-normal[2], 0.5))
        view_plan=None;view_pause=False
        if clearance < .65:
            view_plan=final_view_plan(self.calibration,observation,r,velocity,normal,self.feet,self.camera_branch)
            if view_plan['valid']:offset=r[:2]-np.asarray(view_plan['desired_relative_xy_m'])
            view_pause=view_plan['pause_descent'] or not estimate.get('_fresh_metric_fit',False)
        action = np.zeros(6)
        action[:2] = boat_velocity[:2] + 1.1 * offset + 0.8 * velocity[:2]
        closure=action[:2]-boat_velocity[:2]
        # Allow braking/alignment time before reaching the pad. This is a
        # velocity-command limit, not weaker touchdown/readiness criteria.
        closure_limit=.7 if not estimate.get('motion_ready',False) or abs(heading_error)>math.radians(15) else 1.5
        length=np.linalg.norm(closure)
        if length>closure_limit:action[:2]=boat_velocity[:2]+closure*closure_limit/length
        action[2] = boat_velocity[2] - 0.8 * (max(1.2, clearance) - clearance)
        if self.stable_elapsed >= 0.24:
            phase = 'descend'
            action[2] = boat_velocity[2] + (0.22 if clearance > 0.65 else 0.1)
        elif clearance < 1.2:
            phase = 'recover'
            action[2] = boat_velocity[2] - 0.4 * (1.2 - clearance)
        if view_pause:
            # Hold relative altitude while geometry remains visible; never
            # use this planning layer to grant touchdown or missing-image descent.
            action[2]=min(action[2],boat_velocity[2]);self.stable_elapsed=0.
            if self.nearfield_visibility_hold_started is None:self.nearfield_visibility_hold_started=float(observation['image_delivery_time_s'])
            if ready:phase='visibility_align'
        else:self.nearfield_visibility_hold_started=None
        if ready and clearance < 0.03 and not view_pause:
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
            action[4] = 3 * wrap(target[0] - observation['gimbal_rad'][0]) + float(px4['angular_rate_frd_rad_s'][2])
            action[5] = 3 * (target[1] - observation['gimbal_rad'][1])
        info = {'control_phase': phase, 'pose_valid': True, 'estimated_relative_position': r.tolist(), 'estimated_relative_velocity': velocity.tolist(), 'estimated_lateral_error_m': lateral, 'estimated_clearance_m': clearance, 'estimated_heading_error_deg': math.degrees(heading_error), 'estimated_deck_tilt_deg': math.degrees(deck_tilt), 'stable_tracking_s': self.stable_elapsed, 'pad_visibility_probability': probability}
        if view_plan is not None:info.update(nearfield_visibility_plan=view_plan,nearfield_descent_paused=view_pause,nearfield_visibility_hold_started=self.nearfield_visibility_hold_started,nearfield_max_descent_command=float(boat_velocity[2]) if estimate.get('_fresh_metric_fit',False) else min(0.,float(boat_velocity[2])))
        return self.finish(action, observation, info)

    def recover_metric(self, estimate, observation):
        self.current_estimate = estimate
        self.stable_elapsed = 0.0
        self.relative = None
        numeric = numeric_observation({'observation': observation})
        r = np.asarray(estimate['relative_position'])
        normal = np.asarray(estimate['normal'])
        normal /= max(np.linalg.norm(normal), 1e-06)
        velocity = np.asarray(estimate['relative_velocity'])
        boat = numeric[:3] + velocity
        offset = r[:2] + normal[:2] * (r[2] / max(-normal[2], 0.5))
        correction = 0.4 * offset
        norm = np.linalg.norm(correction)
        if norm > 0.2:
            correction *= 0.2 / norm
        action = np.zeros(6)
        action[:3] = boat
        action[:2] += correction
        feet = (body_to_heading(*observation['px4']['attitude_ned_rad'][:2]) @ self.feet.T).T
        clearance = float(np.min((feet - r) @ normal))
        action[2] -= 0.4 * np.clip(1.2 - clearance, 0, 0.75)
        yaw = math.pi / 2 - observation['px4']['attitude_ned_rad'][2]
        if self.heading_target is not None:
            action[3] = -wrap(self.heading_target - yaw)
        aim = dict(observation)
        aim['beacon'] = {'valid': True, 'age_s': 0.0, 'relative_heading_m': r.tolist()}
        target = beacon_camera_target(aim)
        if target is not None:
            action[4] = 3 * wrap(target[0] - observation['gimbal_rad'][0])
            action[5] = 3 * (target[1] - observation['gimbal_rad'][1])
        return self.finish(action, observation, {'control_phase': 'metric_recovery', 'pose_valid': False, 'pad_visibility_probability': 0.0, 'estimated_clearance_m': clearance})

    def finish(self, action, observation, diagnostics):
        e = self.current_estimate
        if diagnostics.get('pose_valid') and diagnostics.get('estimated_clearance_m', 99) < 0.65 and (diagnostics.get('estimated_lateral_error_m', 99) < 0.1) and (self.camera_branch is None):
            self.camera_branch = round(observation['gimbal_rad'][0] / math.pi) * math.pi
        if self.camera_branch is not None and diagnostics['control_phase'] not in ('acquire', 'disarmed'):
            action[4] = 3 * wrap(self.camera_branch - observation['gimbal_rad'][0])
            target = np.diag([1.0, -1.0, -1.0]) @ body_to_heading(*observation['px4']['attitude_ned_rad'][:2]).T @ np.asarray(e['relative_position'])

            def residual(tilt):
                T = camera_body_transform(self.calibration, [self.camera_branch, tilt[0]])
                ray = T[:3, :3].T @ (target - T[:3, 3])
                norm = np.linalg.norm(ray)
                return ray / max(norm, 1e-06) - [0.0, 0.0, -1.0]
            fit = least_squares(residual, [np.clip(observation['gimbal_rad'][1], -math.radians(10) + 1e-06, math.pi / 2 - 1e-06)], bounds=([-math.radians(10)], [math.pi / 2]), max_nfev=10)
            action[5] = 3 * (fit.x[0] - observation['gimbal_rad'][1])
            diagnostics['camera_corridor_pan_rad'] = self.camera_branch
        action,diagnostics=super().finish(action, observation, diagnostics)
        if diagnostics.get('nearfield_descent_paused'):
            cap=float(diagnostics['nearfield_max_descent_command'])
            if action[2]>cap:action[2]=cap;diagnostics['nearfield_descent_brake_override']=True
        return action,diagnostics

class MarkerPosePolicy(HybridPosePolicy):

    def __init__(self, checkpoint, calibration, slew_limits, device='cuda'):
        super().__init__(checkpoint, calibration, slew_limits, device)
        self.controller = MarkerLandingController(calibration, slew_limits)
        self.track = None
        self.track_time = None
        self.track_yaw = None
        self.track_own_position = None
        self.metric_support = deque()
        self.metric_time = None
        self.boat_velocity_enu = None
        self.metric_heading_world = None
        self.heading_quadrant_from_motion = False
        self.learned_heading_world = None
        self.visual_boat_sample = None
        self.visual_velocity_enu = None
        self.visual_memory = VisualTargetState()
        self.visibility_recovery = VisibilityRecovery()

    def reset(self):
        super().reset()
        self.track = None
        self.track_time = None
        self.track_yaw = None
        self.track_own_position = None
        self.metric_support = deque()
        self.metric_time = None
        self.boat_velocity_enu = None
        self.metric_heading_world = None
        self.heading_quadrant_from_motion = False
        self.learned_heading_world = None
        self.visual_boat_sample = None
        self.visual_velocity_enu = None
        self.visual_memory = VisualTargetState()
        self.visibility_recovery = VisibilityRecovery()
        self.visual_motion_samples = deque()
        self.visual_motion_time = None

    def resolve_marker_heading(self, observed_world_heading, yaw):
        moving = self.boat_velocity_enu is not None and np.linalg.norm(self.boat_velocity_enu[:2]) > 0.1
        if moving and (not self.heading_quadrant_from_motion):
            course = math.atan2(self.boat_velocity_enu[1], self.boat_velocity_enu[0])
            reference = course + round((yaw - course) / math.pi) * math.pi
            self.heading_quadrant_from_motion = True
        elif self.metric_heading_world is not None:
            reference = self.metric_heading_world
        elif self.learned_heading_world is not None:
            reference = self.learned_heading_world + round((yaw - self.learned_heading_world) / math.pi) * math.pi
        else:
            reference = yaw
        return observed_world_heading + round((reference - observed_world_heading) / (math.pi / 2)) * (math.pi / 2)

    def accept_metric(self, measured, prior, observation, now):
        cold = self.track is None
        reacquiring = not cold and self.metric_time is not None and (now - self.metric_time > 2.0)
        if cold or reacquiring:
            beacon = observation['beacon']
            if not beacon.get('valid', False):
                return (True, 'reacquired' if reacquiring else 'acquired')
            if not beacon.get('valid', False) or beacon['age_s'] >= 3.0:
                return (False, 'radio_reference_stale')
            coarse = np.asarray(beacon['relative_heading_m']) + np.asarray(beacon['velocity_heading_m_s']) * beacon['age_s']
            if abs(measured[2] - coarse[2]) > 0.9 or np.linalg.norm(measured[:2] - coarse[:2]) > 0.9:
                return (False, 'outside_radio_context')
            return (True, 'reacquired' if reacquiring else 'acquired')
        if np.linalg.norm(measured - prior) > max(0.08, 0.1 * prior[2]):
            return (False, 'tracking_innovation')
        return (True, 'tracked')

    def act(self, rgb, observation, prediction):
        p = np.asarray(prediction, dtype=np.float32)
        probability = float(1 / (1 + np.exp(-np.clip(p[0], -40, 40))))
        now = float(observation['image_delivery_time_s'])
        dt = float(observation['decision_dt_s'])
        yaw = math.pi / 2 - observation['px4']['attitude_ned_rad'][2]
        if probability >= .8 and np.linalg.norm(p[7:9]) > .5:
            self.learned_heading_world = yaw + .5 * math.atan2(p[7], p[8])
        R = heading_rotation(yaw)
        D = np.diag([1.0, -1.0, -1.0])
        own_position=np.asarray(observation["px4"]["position_enu_m"])+np.asarray(observation["px4"]["velocity_enu_m_s"])*float(observation["px4"].get("position_age_s",0.))
        fresh = observation['beacon'].get('valid', False) and observation['beacon']['age_s'] < 3.0
        if fresh:
            boat = R @ D @ np.asarray(observation['beacon']['velocity_heading_m_s'])
            if self.boat_velocity_enu is None:
                self.boat_velocity_enu = boat
            else:
                self.boat_velocity_enu += min(1.0, dt / 0.3) * (boat - self.boat_velocity_enu)
        else:
            self.boat_velocity_enu = self.visual_velocity_enu if self.visual_boat_sample is not None and now - self.visual_boat_sample[0] < 0.5 else None
        remembered=self.visual_memory.estimate(observation)
        if self.boat_velocity_enu is None and remembered is not None and remembered['motion_hold_valid']:
            self.boat_velocity_enu=remembered['velocity_world'].copy()
        velocity = p[4:7]
        if self.boat_velocity_enu is not None:
            velocity = D @ R.T @ (self.boat_velocity_enu - np.asarray(observation['px4']['velocity_enu_m_s']))
        prior = p[1:4].copy()
        if self.track is None and fresh:
            prior[2] = observation['beacon']['relative_heading_m'][2]
        if self.track is not None:
            previous_own=self.track_own_position
            if previous_own is None:
                prior = D @ R.T @ (heading_rotation(self.track_yaw) @ D @ self.track) + velocity * dt
            else:
                boat_velocity=np.zeros(3) if self.boat_velocity_enu is None else self.boat_velocity_enu
                previous_world=previous_own+heading_rotation(self.track_yaw)@D@self.track
                prior=D@R.T@(previous_world+boat_velocity*dt-own_position)
                velocity=D@R.T@(boat_velocity-np.asarray(observation['px4']['velocity_enu_m_s']))
        memory_seed=remembered is not None and (remembered['tracking_prior_valid'] or remembered['provisional_fit_seed_valid'])
        if memory_seed:
            prior=remembered['relative_position'].copy()
            if remembered['motion_hold_valid']:velocity=remembered['relative_velocity'].copy()
        self.history.append((now, copy.deepcopy(observation)))
        capture_time = observation['image_capture_time_s']
        capture = min(self.history, key=lambda t: abs(t[0] - capture_time))[1]
        history_error = min((abs(t - capture_time) for t, _ in self.history))
        age = float(observation['image_age_s'])
        current = {'relative_position': prior, 'relative_velocity': velocity, 'normal': p[9:12], 'heading_pair': p[7:9], 'visibility': probability, 'contact_probability': float(1 / (1 + np.exp(-np.clip(p[14], -40, 40))))}
        if memory_seed and self.metric_time is not None and now-self.metric_time>.12:
            current['normal']=remembered['normal'].copy()
        capture_yaw = math.pi / 2 - capture['px4']['attitude_ned_rad'][2]
        Rc = heading_rotation(capture_yaw)
        current_to_capture = D @ Rc.T @ R @ D
        pose_at_capture = copy.deepcopy(current)
        pose_at_capture['relative_position'] = current_to_capture @ (prior - velocity * age)
        pose_at_capture['normal'] = current_to_capture @ current['normal']
        angle = 0.5 * math.atan2(p[7], p[8]) + yaw - capture_yaw
        if self.metric_heading_world is not None:
            angle = self.metric_heading_world - capture_yaw
        elif self.boat_velocity_enu is not None and np.linalg.norm(self.boat_velocity_enu[:2]) > 0.1:
            angle = math.atan2(self.boat_velocity_enu[1], self.boat_velocity_enu[0]) - capture_yaw
        else:
            angle = .5 * math.atan2(p[7], p[8]) + yaw - capture_yaw
        pose_at_capture['heading_pair'] = [math.sin(2 * angle), math.cos(2 * angle)]
        metric_recent = self.metric_time is not None and now - self.metric_time < 0.5
        pose_at_capture['_tracked'] = metric_recent
        if not metric_recent and not memory_seed:
            pixel = (p[12:14] + 1) * [320.0, 180.0]
            if 0 < pixel[0] < 640 and 0 < pixel[1] < 360:
                ray_prior = relative_from_pixel(pixel, pose_at_capture['relative_position'][2], capture, self.calibration)
                if ray_prior is not None:
                    pose_at_capture['relative_position'] = ray_prior
        pose_at_capture['_image_pixel'] = (p[12:14] + 1) * [320.0, 180.0]
        memory_roi=False
        if memory_seed:
            T=camera_body_transform(self.calibration,capture['gimbal_rad'])
            level=body_to_heading(*capture['px4']['attitude_ned_rad'][:2])
            camera_rotation=level@D@T[:3,:3];camera_origin=level@D@T[:3,3]
            ray=camera_rotation.T@(pose_at_capture['relative_position']-camera_origin)
            if ray[2]<-.035:
                f=180/math.tan(math.radians(self.calibration['camera_fovy_deg'])/2)
                roi=np.array([320+f*ray[0]/-ray[2],180-f*ray[1]/-ray[2]])
                memory_roi=bool(np.isfinite(roi).all() and 10<roi[0]<630 and 10<roi[1]<350)
                if memory_roi:pose_at_capture['_image_pixel']=roi;pose_at_capture['_tracked']=True
        fit = None
        if history_error <= 0.021 and observation['image_valid'] and (age <= 0.25) and ((probability >= 0.8) or memory_roi):
            fit = marker_pose(rgb, capture, self.calibration, pose_at_capture)
        fit_candidate_valid = fit is not None
        acceptance = 'no_registration'
        innovation = None
        height_context=fit_height_context(fit,capture)
        if fit is not None and not height_context['compatible']:
            fit=None;acceptance=height_context['reason']
        if fit is not None:
            measured = compensate_capture(fit['relative_position'], capture, observation, velocity, age)
            innovation = float(np.linalg.norm(measured - prior))
            accepted, acceptance = self.accept_metric(measured, prior, observation, now)
            if not accepted:
                fit = None
            else:
                current['relative_position'] = measured if acceptance in ('acquired', 'reacquired') else prior + 0.6 * (measured - prior)
                self.metric_time = now
                observed_heading = capture_yaw + fit['heading_angle_heading_rad']
                self.metric_heading_world = self.resolve_marker_heading(observed_heading, yaw)
                self.visual_memory.observe(fit['relative_position'],capture,capture_time,fit_rms_px=fit['fit_rms_px'],normal_heading=pose_at_capture['normal'],heading_world=self.metric_heading_world)
                if acceptance == 'reacquired':
                    self.controller.relative = None
                    self.controller.stable_elapsed = 0.0
        if fit is None:
            current['relative_position'] = prior
        if self.metric_heading_world is not None:
            angle = self.metric_heading_world - yaw
            current['heading_pair'] = [math.sin(2 * angle), math.cos(2 * angle)]
        current = visual_motion(self, current, observation, now, fit, capture=capture)
        current['_fresh_metric_fit']=fit is not None
        metric_age = math.inf if self.metric_time is None else now - self.metric_time
        uncertainty = 0.012 + 0.035 * metric_age
        if metric_age>.6:self.metric_support.clear()
        if fit is not None:
            self.metric_support.append(now)
            while self.metric_support and now-self.metric_support[0]>.4:self.metric_support.popleft()
            if self.track is None:
                self.track=np.array(current['relative_position']);self.track_yaw=yaw;self.track_own_position=own_position.copy()
        confirmed=len(self.metric_support)>=3 and self.metric_support[-1]-self.metric_support[0]>=.079
        trusted = confirmed and metric_age <= .6 and (fresh or not observation['beacon'].get('valid', False)) and observation['image_valid'] and (age <= 0.25)
        current['visibility'] = max(0.9, probability) if trusted else 0.0
        current['metric_age_s'] = metric_age
        if trusted:
            r = np.asarray(current['relative_position'])
            n = current['normal'] / np.linalg.norm(current['normal'])
            tangent = r - n * np.dot(r, n)
            lateral = np.linalg.norm(tangent)
            current['metric_uncertainty_m'] = uncertainty
            self.track = np.array(current['relative_position'])
            self.track_time = now
            self.track_yaw = yaw
            self.track_own_position=own_position.copy()
        elif self.track is not None:
            self.track = np.array(current['relative_position'])
            self.track_time = now
            self.track_yaw = yaw
            self.track_own_position=own_position.copy()
        self.controller.bearing_capture_observation=capture
        recovery=self.visibility_recovery.decide(self,current,observation,p,probability,fit,trusted)
        if recovery is not None:
            raw,diag=recovery;self.controller.camera_branch=None;self.controller.current_estimate=current;self.controller.nearfield_visibility_hold_started=None
            self.controller.stable_elapsed=0.;self.controller.relative=None
            action,diag=self.controller.finish(raw,observation,diag)
            if action[2]>0.:action[2]=0.;diag['recovery_descent_brake_override']=True
        elif not observation['beacon'].get('valid', False) and (not trusted) and (self.controller.contact_started is None) and observation['px4'].get('armed', False) and (not observation['px4'].get('landed', False)):
            action, diag = acquire_visual(self.controller, dict(current, visibility=probability), observation, p)
        elif not trusted and self.track is not None and (self.controller.contact_started is None) and observation['px4'].get('armed', False) and (not observation['px4'].get('landed', False)):
            action, diag = self.controller.recover_metric(current, observation)
        else:
            action, diag = self.controller.act(current, observation)
        memory_now=self.visual_memory.estimate(observation)
        diag.update(recovery_active=bool(recovery is not None),recovery_attempts=self.visibility_recovery.attempts,recovery_exhausted=self.visibility_recovery.exhausted,geometric_fit_requested_from_memory=memory_roi,predicted_measurement_roi_px=roi.tolist() if memory_roi else None,visual_memory_established=bool(memory_now and memory_now['established']),visual_memory_position_sigma_m=memory_now['position_sigma_m'] if memory_now is not None else None,visual_memory_age_s=memory_now['measurement_age_s'] if memory_now is not None else None)
        diag.update(metric_physical_height_context=height_context,metric_valid=fit is not None, fit_candidate_valid=fit_candidate_valid, metric_acceptance=acceptance, metric_innovation_m=innovation, metric_age_s=metric_age if math.isfinite(metric_age) else None, metric_uncertainty_m=uncertainty if math.isfinite(uncertainty) else None, raw_model_visibility_probability=probability, capture_history_error_s=history_error, stable_contact_probability=current['contact_probability'])
        diag.update(visual_motion_ready=current.get('motion_ready', False), visual_motion_window_s=current.get('visual_motion_window_s', 0.))
        diag.update(metric_confirmed=confirmed,metric_support_count=len(self.metric_support),learned_center_px=((p[12:14]+1)*[320.,180.]).tolist(),odometry_track_prediction=True)
        if fit is not None:
            diag.update(marker_orientation_correction_deg=math.degrees(fit['orientation_correction_rad']), marker_fit_rms_px=fit['fit_rms_px'], marker_center_px=fit['center_px'], marker_paint_precision=fit['paint_precision'], marker_paint_recall=fit['paint_recall'])
        return (action, diag)
