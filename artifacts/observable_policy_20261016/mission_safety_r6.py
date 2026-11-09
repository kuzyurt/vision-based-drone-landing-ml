"""Public own-home mission fallback. No boat state or simulator API is read here."""
import copy,math
from collections import deque
import numpy as np


def wrap(a):return (a+math.pi)%(2*math.pi)-math.pi


class HomeReference:
    """Observe own telemetry on the known launch pad before takeoff."""
    def __init__(self):self.samples=[];self.path=[]
    def observe(self,px4):
        if not px4.get('valid'):return
        p=np.asarray(px4['position_enu_m'],dtype=float)
        if not px4.get('armed') and px4.get('landed'):
            self.samples.append((p.copy(),float(px4['attitude_ned_rad'][2])))
            self.samples=self.samples[-50:]
        elif px4.get('armed'):
            if not self.path or np.linalg.norm(p-self.path[-1])>2.:self.path.append(p.copy())
    def mission(self):
        if len(self.samples)<5:raise RuntimeError('No sufficiently observed own-home reference before takeoff')
        position=np.median([p for p,yaw in self.samples],axis=0)
        yaw=math.atan2(np.mean([math.sin(y) for p,y in self.samples]),np.mean([math.cos(y) for p,y in self.samples]))
        return dict(home_position_enu_m=position.tolist(),home_yaw_ned_rad=yaw,
            home_source='own PX4 observations on declared launch pad before takeoff',
            preparation_path_enu_m=[p.tolist() for p in self.path],
            home_authorized_for_landing=True,search_timeout_s=60.,fallback_type='time-budget return to known home; not a battery-SOC claim',
            water_datum_enu_m=0.,nominal_deck_height_above_water_m=.45,coarse_height_uncertainty_m=.4,
            coarse_range_prior_source='declared sea-level datum and nominal static boat geometry; no dynamic boat coordinates')


class MissionSafety:
    def __init__(self,policy,slew_limits):
        self.policy=policy;self.slew=np.asarray(slew_limits);self.reset()
    def reset(self):
        self.policy.reset();self.home=None;self.phase=None;self.settled=0.;self.return_z=None
        self.start_z=None;self.first_invalid_image=None;self.last_metric=None;self.trigger=None
        self.breadcrumbs=[];self.return_route=[]
        self.home_contact_proxy_s=0.
        self.camera_history=deque(maxlen=16);self.coarse_samples=deque();self.last_visual_supported=None
        self.last_metric_finish=None;self.last_finish_support=None;self.finish_deadline=None;self.reserve_pressure_started=None
    def act(self,rgb,observation):
        mission=observation['mission'];p=observation['px4'];elapsed=float(mission['elapsed_s']);now=float(observation['image_delivery_time_s'])
        home=mission.get('home_position_enu_m')
        if home is None or not mission.get('home_authorized_for_landing'):
            raise RuntimeError('Mission requires an authorized own-home reference')
        home=np.asarray(home,dtype=float)
        if home.shape!=(3,) or not np.isfinite(home).all():raise ValueError('Invalid own-home mission coordinate')
        position=np.asarray(p.get('position_enu_m',[0,0,0]),dtype=float)
        if self.start_z is None:self.start_z=float(position[2])
        self.camera_history.append((now,dict(px4=copy.deepcopy(p),gimbal_rad=list(observation['gimbal_rad']))))
        if self.phase is None and p.get('valid') and (not self.breadcrumbs or np.linalg.norm(position-self.breadcrumbs[-1])>2.):
            self.breadcrumbs.append(position.copy())
        if observation['image_valid']:self.first_invalid_image=None
        elif self.first_invalid_image is None:self.first_invalid_image=elapsed
        diagnostics={}
        if self.phase is None:
            action,diagnostics=self.policy.act(rgb,observation)
            if diagnostics.get('metric_valid'):
                self.last_metric=elapsed
                clearance=max(0.,float(diagnostics.get('estimated_clearance_m',self.start_z-home[2])))
                lateral=max(0.,float(diagnostics.get('estimated_lateral_error_m',5.)))
                # A registration dropout is expected during alignment and when
                # the pad grows out of the camera frame near touchdown.
                self.last_metric_finish=clearance/.18+lateral/.5+25.
            metric_age=elapsed-self.last_metric if self.last_metric is not None else float('inf')
            fresh=metric_age<3.
            route=[home]+[np.asarray(v) for v in mission.get('preparation_path_enu_m',[])]+self.breadcrumbs+[position]
            horizontal=sum(float(np.linalg.norm(b[:2]-a[:2])) for a,b in zip(route,route[1:]))
            return_seconds=horizontal/1.2+max(0.,position[2]-home[2])/.18+15.
            remaining=float(mission['budget_s'])-elapsed
            coarse=(diagnostics.get('control_phase')=='visual_acquire' and diagnostics.get('raw_model_visibility_probability',0)>=.8
                and diagnostics.get('bearing_confirmed_frames',0)>=3 and not diagnostics.get('view_alignment_required',False) and observation['image_valid'])
            finish_estimate=None;range_estimate=None;progress_stalled=False
            if coarse:
                # Rough planning range from own altitude, declared water datum
                # and static boat geometry. No actual boat position is read.
                from landing_training.radio_robust_20261015.controller.visual_acquisition import camera_geometry
                capture=min(self.camera_history,key=lambda item:abs(item[0]-observation['image_capture_time_s']))[1]
                rotation,origin,focal,_=camera_geometry(capture,self.policy.controller.calibration)
                pixel=diagnostics['learned_center_px'];ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.]);ray/=np.linalg.norm(ray)
                height=float(capture['px4']['position_enu_m'][2])-float(mission.get('water_datum_enu_m',0.))-float(mission.get('nominal_deck_height_above_water_m',.45))-origin[2]
                if height>.2 and ray[2]>.02:
                    range_estimate=height*np.linalg.norm(ray[:2])/ray[2]
                    self.coarse_samples.append((elapsed,range_estimate))
                    while self.coarse_samples and elapsed-self.coarse_samples[0][0]>12.:self.coarse_samples.popleft()
                    if len(self.coarse_samples)>=20 and elapsed-self.coarse_samples[0][0]>=10.:
                        values=list(self.coarse_samples)
                        progress_stalled=float(np.median([v[1] for v in values[:5]])-np.median([v[1] for v in values[-5:]]))<1.
                    conservative_range=(height+float(mission['coarse_height_uncertainty_m']))*np.linalg.norm(ray[:2])/ray[2]
                    finish_estimate=conservative_range/.7+max(0.,height)/.2+12.
                else:coarse=False
            tracked_support=(metric_age<10. and observation['image_valid']
                             and diagnostics.get('raw_model_visibility_probability',0)>=.8)
            if (coarse and not progress_stalled) or tracked_support:self.last_visual_supported=elapsed
            visible_recent=self.last_visual_supported is not None and elapsed-self.last_visual_supported<10.
            search_over=elapsed>=float(mission.get('search_timeout_s',60.)) and metric_age>=10. and not visible_recent
            supported_finish=coarse and not progress_stalled and finish_estimate is not None and finish_estimate<remaining-10.
            metric_finish_supported=(tracked_support and self.last_metric_finish is not None and self.last_metric_finish<remaining-8.)
            supported_finish=supported_finish or metric_finish_supported
            if supported_finish:
                predicted_finish=finish_estimate if coarse and finish_estimate is not None else self.last_metric_finish
                self.last_finish_support=elapsed;self.finish_deadline=elapsed+predicted_finish
            recent_finish=(self.last_finish_support is not None and elapsed-self.last_finish_support<5.
                           and self.finish_deadline<float(mission['budget_s'])-8.)
            supported_finish=supported_finish or recent_finish
            pressure=remaining<1.25*return_seconds and not fresh and not supported_finish
            if pressure:
                if self.reserve_pressure_started is None:self.reserve_pressure_started=elapsed
            else:self.reserve_pressure_started=None
            reserve_low=pressure and elapsed-self.reserve_pressure_started>=3.
            completing=diagnostics.get('control_phase') in ['touchdown_commit','confirm','disarmed'] or p.get('landed')
            if completing:search_over=False;reserve_low=False
            camera_failed=self.first_invalid_image is not None and elapsed-self.first_invalid_image>=3.
            if search_over or reserve_low or camera_failed:
                self.phase='return_home';self.trigger='camera_unavailable' if camera_failed else 'return_time_reserve' if reserve_low else 'search_timeout'
                self.return_z=max(self.start_z,float(home[2])+2.,max(float(v[2]) for v in route))+.5
                self.return_route=[v.copy() for v in route[-2::-1]]
            else:
                diagnostics.update(mission_fallback_active=False,mission_home_source=mission['home_source'],mission_return_time_estimate_s=return_seconds,
                    mission_coarse_range_m=range_estimate,mission_visual_progress_stalled=progress_stalled,
                    mission_coarse_finish_estimate_s=finish_estimate,mission_supported_visual_finish=supported_finish)
                return action,diagnostics
        action=np.zeros(6)
        valid=p.get('valid') and p.get('position_age_s',99)<.5 and p.get('attitude_age_s',99)<.5
        if not valid:
            return action,dict(control_phase='home_estimator_hold',mission_fallback_active=True,pose_valid=False,
                metric_valid=False,pad_visibility_probability=0.,fallback_trigger=self.trigger)
        velocity=np.asarray(p['velocity_enu_m_s']);error=home-position
        while len(self.return_route)>1 and np.linalg.norm(self.return_route[0][:2]-position[:2])<1.:
            self.return_route.pop(0)
        waypoint=self.return_route[0] if self.return_route else home
        navigation_error=waypoint-position if self.phase=='return_home' else error
        yaw_ned=p['attitude_ned_rad'][2];yaw=math.pi/2-yaw_ned;c,s=math.cos(yaw),math.sin(yaw)
        world_xy=1.0*navigation_error[:2]-.5*velocity[:2];length=np.linalg.norm(world_xy)
        if self.phase=='return_home' and position[2]<self.return_z-.4:world_xy=-.5*velocity[:2]
        cap=1.5 if self.phase=='return_home' else .5
        if length>cap:world_xy*=cap/length
        action[:2]=[c*world_xy[0]+s*world_xy[1],s*world_xy[0]-c*world_xy[1]]
        yaw_error=wrap(float(mission['home_yaw_ned_rad'])-yaw_ned)
        action[3]=np.clip(yaw_error,-.3,.3)
        action[4]=np.clip(-3*wrap(observation['gimbal_rad'][0]),-math.radians(50),math.radians(50))
        action[5]=np.clip(2*(math.radians(65)-observation['gimbal_rad'][1]),-math.radians(40),math.radians(40))
        if self.phase=='return_home':
            action[2]=np.clip(.8*(position[2]-self.return_z),-.4,.4)
            ready=np.linalg.norm(error[:2])<.08 and np.linalg.norm(velocity[:2])<.12 and abs(yaw_error)<math.radians(8)
            self.settled=self.settled+observation['decision_dt_s'] if ready else 0.
            if self.settled>=.4:self.phase='land_home'
        if self.phase=='land_home':
            action[2]=.18 if position[2]-home[2]>.4 else .10
            near=(abs(position[2]-home[2])<.22 and np.linalg.norm(error[:2])<.10 and abs(velocity[2])<.03
                and max(abs(p['attitude_ned_rad'][0]),abs(p['attitude_ned_rad'][1]))<math.radians(5))
            self.home_contact_proxy_s=self.home_contact_proxy_s+observation['decision_dt_s'] if near else 0.
            if self.home_contact_proxy_s>=1.:self.phase='home_touchdown_commit'
            if np.linalg.norm(error[:2])>.25:
                action[2]=0.;self.phase='return_home';self.settled=0.
        if self.phase=='home_touchdown_commit':action[2]=.32
        if p.get('landed'):
            action[2]=.3 if p.get('armed') else 0.
            self.phase='home_confirm' if p.get('armed') else 'home_disarmed'
        previous=np.asarray(observation['previous_executed_action']);delta=self.slew*float(observation['decision_dt_s'])
        action=np.clip(action,previous-delta,previous+delta)
        if not p.get('armed'):action[:4]=0.
        diagnostics=dict(control_phase=self.phase,mission_fallback_active=True,fallback_trigger=self.trigger,
            mission_home_source=mission['home_source'],mission_home_horizontal_error_m=float(np.linalg.norm(error[:2])),
            mission_home_relative_height_m=float(position[2]-home[2]),pose_valid=False,metric_valid=False,
            pad_visibility_probability=0.,radio_position_available=False,boat_truth_used=False)
        return action,diagnostics
