from .observable_acquisition import acquire_visual as observable_acquire
"""Bounded local recovery/view setup; memory guides the camera, not descent."""
from collections import deque
import math
import numpy as np
from .persistent_target import own_state,D
from .visual_acquisition import camera_geometry
from .hybrid_policy import body_to_heading
from .camera_feedback import bearing_rates
from .action_guard import wrap

class VisibilityRecovery:
    def __init__(self):self.reset()
    def reset(self):
        self.start=None;self.phase=None;self.phase_start=None;self.deadline=None;self.goal_z=None
        self.attempts=0;self.ever_confirmed=False;self.last_strong=None;self.strong_count=0
        self.last_bearing=None;self.seen_latch=False;self.loss_events=deque();self.cooldown=-math.inf
        self.local_started=None;self.exhausted=False;self.trigger=None;self.scan_started=None
        self.climb_start_z=None;self.settled=0.
        self.blocked_since=None;self.local_cycles=0
    def _observe_bearing(self,policy,observation,p,probability):
        now=float(observation['image_delivery_time_s']);pixel=(np.asarray(p[12:14])+1.)*[320.,180.]
        valid=observation['image_valid'] and observation['image_age_s']<=.25 and probability>=.8 and np.isfinite(pixel).all() and 8<pixel[0]<632 and 8<pixel[1]<352
        capture=policy.controller.bearing_capture_observation
        own=own_state(capture)
        if valid and own is not None:
            rotation,origin,focal,_=camera_geometry(capture,policy.calibration)
            ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.]);ray/=np.linalg.norm(ray)
            ray_world=own[2]@D@ray
            valid=bool(ray_world[2]<-.02)
            if valid:
                mission=observation['mission'];origin_world=own[0]+own[2]@D@origin
                plane=float(mission.get('water_datum_enu_m',0.))+float(mission.get('nominal_deck_height_above_water_m',.45))
                scale=(origin_world[2]-plane)/-ray_world[2]
                point=origin_world+scale*ray_world if 0<scale<100 else None
                self.last_bearing=(now,ray_world,point);self.last_strong=now;self.strong_count+=1
                if self.strong_count>=3:self.seen_latch=True
        if not valid:
            self.strong_count=0
            if self.seen_latch and self.last_strong is not None and now-self.last_strong>.3:
                self.loss_events.append(now);self.seen_latch=False
        while self.loss_events and now-self.loss_events[0]>12.:self.loss_events.popleft()
    def _climb(self,observation,own,now,reason,current,memory):
        if self.attempts>=2:return False
        mission=observation['mission'];clearance=mission.get('recovery_clearance',{})
        if not clearance.get('valid') or not clearance.get('no_dynamic_boat_state'):return False
        maximum=clearance.get('max_altitude_enu_m')
        if maximum is None or not math.isfinite(float(maximum)):return False
        # The declared nominal boat envelope is conservative when no accepted
        # geometry is available. A recent geometric track can justify a lower
        # above-deck ascent; neither authorizes downward motion.
        z=float(own[0][2]);plane=float(mission.get('water_datum_enu_m',0.))+float(mission.get('nominal_deck_height_above_water_m',.45))
        nominal_safe=z-plane>float(mission.get('coarse_height_uncertainty_m',.4))+.05+.05+.22+.1
        metric_safe=memory is not None and memory['established'] and memory['measurement_age_s']<1.5 and memory['relative_position'][2]-.22-3*memory['position_sigma_m']>.12
        if not nominal_safe and not metric_safe:return False
        goal=min(z+2.5,float(maximum)-.5)
        if goal-z<1.:return False
        self.phase='recovery_climb';self.phase_start=now;self.climb_start_z=z;self.goal_z=goal
        self.deadline=now+(goal-z)/.3+5.;self.attempts+=1;self.trigger=reason;self.settled=0.
        self.local_started=None;return True
    def _camera(self,policy,observation,own,memory,now):
        r=None;rv=None
        if memory is not None and memory['local_aim_valid']:
            r=memory['relative_position'];rv=memory['relative_velocity']
        elif self.last_bearing is not None and now-self.last_bearing[0]<3.:
            _,ray_world,point=self.last_bearing
            r=D@own[2].T@(point-own[0]) if point is not None else D@own[2].T@ray_world*5.
        pan,tilt=observation['gimbal_rad'];action=np.zeros(6)
        if r is not None and np.isfinite(r).all() and np.linalg.norm(r)>.1:
            level=body_to_heading(*observation['px4']['attitude_ned_rad'][:2]);body=level.T@r
            target_pan=math.atan2(-body[1],body[0]);target_tilt=math.atan2(body[2],np.linalg.norm(body[:2]))
            norm=np.linalg.norm(body);drift=np.zeros(3) if rv is None else level.T@rv/norm
            if rv is not None:drift-=body/norm*np.dot(body/norm,drift)
            ffpan,fftilt=bearing_rates(body/norm,drift,observation['px4']['angular_rate_frd_rad_s'])
            action[4]=3*wrap(target_pan-pan)+ffpan;action[5]=3*(target_tilt-tilt)+fftilt
        else:
            bracket=[15.,35.,65.][int(max(0.,now-(self.phase_start or now))/2.)%3]
            action[3]=-.25;action[4]=3*wrap(-pan);action[5]=1.2*(math.radians(bracket)-tilt)
        return action
    def decide(self,policy,current,observation,p,probability,fit,trusted):
        now=float(observation['image_delivery_time_s']);dt=float(observation['decision_dt_s']);own=own_state(observation)
        if self.start is None:self.start=now
        if own is None or not observation['px4'].get('armed') or observation['px4'].get('landed') or policy.controller.contact_started is not None:return None
        self._observe_bearing(policy,observation,p,probability)
        self.ever_confirmed=self.ever_confirmed or bool(trusted)
        memory=policy.visual_memory.estimate(observation)
        metric_age=math.inf if policy.metric_time is None else now-policy.metric_time
        # Distant loss is not a close-view obstruction. Preserve the existing
        # CAD-aware aircraft yaw, bearing hysteresis, camera targeting, approach
        # braking and mission progress accounting instead of replacing them
        # with an independent camera servo or climbing away from a tiny target.
        plane=float(observation['mission'].get('water_datum_enu_m',0.))+float(observation['mission'].get('nominal_deck_height_above_water_m',.45))
        weak=None if self.last_bearing is None else self.last_bearing[2]
        bearing_far=(weak is not None and now-self.last_bearing[0]<3. and np.linalg.norm(weak[:2]-own[0][:2])>4.)
        memory_far=(memory is not None and memory['local_aim_valid'] and memory['measurement_age_s']<2. and np.linalg.norm(memory['relative_position'][:2])>4.)
        if (not trusted and not self.exhausted and observation['image_valid'] and own[0][2]-plane>2.
            and self.phase not in ('recovery_climb','recovery_scan') and (bearing_far or memory_far)):
            self.phase=None;self.local_started=None;self.blocked_since=None
            raw,diag=observable_acquire(policy.controller,dict(current,visibility=probability),observation,p,finish_action=False)
            raw[2]=0.
            mission=observation['mission'];remaining_search=max(0.,float(mission.get('search_timeout_s',60.))-float(mission.get('elapsed_s',0.)))
            diag.update(recovery_active=True,recovery_trigger='far_existing_visibility_aware_acquisition',
                recovery_attempts=self.attempts,recovery_goal_altitude_enu_m=None,
                recovery_deadline_s=now+remaining_search,recovery_deadline_clock='image_delivery_time_s',
                recovery_exhausted=False,recovery_does_not_authorize_descent=True,
                far_recovery_reuses_aircraft_clear_view=True)
            return raw,diag

        if self.phase is None and fit is not None and trusted:
            self.blocked_since=None;self.local_cycles=0
        if self.phase=='local_recovery' and fit is not None and trusted:
            self.phase=None;self.local_started=None;self.cooldown=now+.3;self.local_cycles=0;self.blocked_since=None
        view_hold=getattr(policy.controller,'nearfield_visibility_hold_started',None)
        if self.phase is None and not self.exhausted and view_hold is not None and now-view_hold>=4.:
            if self._climb(observation,own,now,'final_visibility_corridor_not_settled',current,memory):
                policy.controller.nearfield_visibility_hold_started=None
            else:
                self.exhausted=True
        if self.phase=='recovery_climb':
            c=observation['mission'].get('recovery_clearance',{})
            cap=c.get('max_altitude_enu_m')
            if not c.get('valid') or cap is None or not math.isfinite(float(cap)) or cap<self.goal_z+.2:
                self.phase='recovery_scan';self.phase_start=now;self.deadline=now+2.;self.trigger='clearance_revoked'
            elif now>self.deadline:
                self.phase='recovery_scan';self.phase_start=now;self.deadline=now+2.;self.trigger='climb_time_limit'
            else:
                settled=own[0][2]>=self.goal_z-.12 and abs(own[1][2])<.15
                self.settled=self.settled+dt if settled else 0.
                if self.settled>=.24:
                    self.phase='recovery_scan';self.phase_start=now;self.deadline=now+2.
        if self.phase=='recovery_scan':
            if fit is not None and trusted:
                self.phase=None;self.cooldown=now+4.;self.loss_events.clear();self.local_started=None
            elif now>=self.deadline:
                self.phase=None;self.cooldown=now+5.;self.local_started=None
                if self.attempts>=2:self.exhausted=True
        # A near-deck lost view can become too uncertain to justify any
        # repositioning if a fixed wait consumes all remaining margin. Use the
        # SAME current ascent gate; this prediction only requests an earlier
        # view reset, never grants descent or bypasses obstacle/height limits.
        if self.phase=='local_recovery' and observation['image_valid'] and memory is not None and memory['established'] and memory['local_aim_valid'] and memory['relative_position'][2]<2.:
            future=policy.visual_memory.predict(now+.4)
            if future is not None:
                x,P=future;future_sigma=float(np.sqrt(max(0.,np.linalg.eigvalsh(P[:3,:3])[-1])))
                future_height=float(own[0][2]+own[1][2]*.4-x[2])
                if future_height-.22-3*future_sigma<=.12:
                    self._climb(observation,own,now,'visibility_margin_expiring',current,memory)
        if self.phase=='local_recovery' and now>=self.deadline:
            if observation['image_valid'] and self._climb(observation,own,now,'persistent_metric_loss',current,memory):pass
            else:
                self.phase=None;self.cooldown=now+3.;self.local_started=None
                if not observation['image_valid'] or self.attempts>=2 or self.local_cycles>=2:self.exhausted=True
        if self.phase is None and now>=self.cooldown and not self.exhausted:
            low=float(own[0][2])-float(observation['mission'].get('water_datum_enu_m',0.))-float(observation['mission'].get('nominal_deck_height_above_water_m',.45))<2.
            visible_recent=self.last_strong is not None and now-self.last_strong<8.
            # A low, unconfirmed handoff must obtain a usable view before
            # accelerating through a nearby target. This weak plane estimate
            # selects a viewing manoeuvre only; it never grants descent.
            close_view=False
            if self.last_bearing is not None and self.strong_count>=3:
                stamp,_,weak_point=self.last_bearing
                close_view=weak_point is not None and now-stamp<=.12 and np.linalg.norm(weak_point[:2]-own[0][:2])<4.
            low_handoff=not self.ever_confirmed and low and close_view and now-self.start>=.12 and metric_age>.6
            low_stall=not self.ever_confirmed and low and now-self.start>=8. and metric_age>.6 and (visible_recent or now-self.start>=16.)
            repeated=len(self.loss_events)>=2 and metric_age>.6 and (low or close_view)
            if observation['image_valid'] and (low_handoff or low_stall or repeated):
                started=self._climb(observation,own,now,'low_close_handoff' if low_handoff else 'low_unconfirmed_view' if low_stall else 'repeated_reacquisition',current,memory)
                if not started:
                    if self.blocked_since is None:self.blocked_since=now
                    elif now-self.blocked_since>=4.:self.exhausted=True
        # Cooldown limits repeated unconfirmed view resets, not braking and
        # local camera reacquisition after a new measured loss.
        if self.phase is None and self.ever_confirmed and metric_age>.16 and not self.exhausted:
            self.phase='local_recovery';self.phase_start=now;self.deadline=now+2.;self.local_started=now;self.trigger='metric_gap';self.local_cycles+=1
        if self.phase is None:return None
        action=self._camera(policy,observation,own,memory,now)
        if memory is not None and memory['motion_hold_valid']:
            xy=D@own[2].T@memory['velocity_world'];length=np.linalg.norm(xy[:2])
            action[:2]=xy[:2]*min(1.,.8/max(length,1e-9))
        if self.phase=='recovery_climb':action[2]=float(np.clip(.8*(own[0][2]-self.goal_z),-.4,0.))
        diag=dict(control_phase=self.phase,pose_valid=False,pad_visibility_probability=probability,
            recovery_active=True,recovery_trigger=self.trigger,recovery_attempts=self.attempts,
            recovery_goal_altitude_enu_m=self.goal_z,recovery_deadline_s=self.deadline,
            recovery_deadline_clock='image_delivery_time_s',
            recovery_climb_progress_m=None if self.climb_start_z is None else float(own[0][2]-self.climb_start_z),
            recovery_exhausted=self.exhausted,recovery_uses_predicted_memory=memory is not None and memory['local_aim_valid'],
            recovery_memory_age_s=memory['measurement_age_s'] if memory is not None else None,
            recovery_memory_sigma_m=memory['position_sigma_m'] if memory is not None else None,
            recovery_static_clearance_prior=True,recovery_does_not_authorize_descent=True)
        return action,diag
