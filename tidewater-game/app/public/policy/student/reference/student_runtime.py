"""Browser adapter for the frozen student search runtime.

Neural pose/search inference is external (ONNX/WebGPU).  This module keeps the
exact sensor-only search/identity/radio/pre360 decision logic from the training
runtime, using the checked-in reference landing controller as its base.
"""
from __future__ import annotations
from dataclasses import dataclass
import copy
import math
import numpy as np
from .search_decision import SearchDecision
from .recording import numeric_observation
from .supervision import supervise_action
from . import camera_geometry as visual_geometry
from . import visual_acquisition as visual_module
from . import action_guard as guard_module

@dataclass
class EvidenceView:
    key: str
    evidence: str
    range_m: float
    pixel: tuple
    position: np.ndarray | None
    detectable: bool = True


class _ControllerProxy:
    """Expose the R15 nested-controller shape over MarkerLandingController."""
    def __init__(self, controller):
        object.__setattr__(self, '_controller', controller)
        object.__setattr__(self, 'controller', controller)
    def __getattr__(self, name):
        return getattr(self._controller, name)
    def __setattr__(self, name, value):
        if name in ('_controller', 'controller'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._controller, name, value)


class BrowserBase:
    """Landing-controller adapter; prediction and proposals are supplied by JS."""
    def __init__(self, policy, config):
        self.policy=policy
        self.config=config
        self.controller=_ControllerProxy(policy.controller)
        self.prediction=np.zeros(15,dtype=np.float32)
        self.start_time=None
    def reset(self):
        self.policy.reset()
        self.prediction=np.zeros(15,dtype=np.float32)
        self.start_time=None
    def set_prediction(self,prediction):
        self.prediction=np.asarray(prediction,dtype=np.float32).reshape(15)
    def act(self,rgb,observation):
        obs=copy.deepcopy(observation)
        # The landing controller is sensor-only.  Radio may steer acquisition
        # before handoff, but it must never enter the R15 fit/descent path.
        b=obs.setdefault('beacon',{})
        b.clear();b.update(valid=False,age_s=3.1,dock_ready=False,relative_heading_m=[0.,0.,0.],velocity_heading_m_s=[0.,0.,0.])
        known=False;ready=False
        image=None if rgb is None else np.asarray(rgb,dtype=np.uint8).reshape(360,640,3)
        action,diag=self.policy.act(image,obs,self.prediction)
        now=float(obs['image_delivery_time_s'])
        if self.start_time is None:self.start_time=now
        action,intervention=supervise_action(action,obs,now-self.start_time,float(obs['mission']['budget_s']))
        if known and not ready:
            action[:4]=0.;intervention='dock_not_ready'
        elif not known and not self.config.get('allow_visual_landing',True) and action[2]>0:
            action[2]=0.;intervention='visual_landing_authorization_required'
        diag['intervention']=intervention
        return action,diag

class SearchRuntime:
    def __init__(self, config, policy):
        self.c=config
        self.calibration=config['calibration']
        self.slew_limits=np.asarray(config['slew_limits'],dtype=float)
        self.geometry=visual_geometry
        self.visual=visual_module
        self.guard=guard_module.ActionGuard(guard_module.GuardConfig(slew_limits=tuple(config['slew_limits'])))
        self.supervise=supervise_action
        self.wrap=guard_module.wrap
        self.base=BrowserBase(policy,config)
        self.reset()
    def controller(self):
        # The common mission guard reads controller.calibration for its
        # coarse-range planning path. Expose the frozen R15 controller here
        # without changing the search policy or the base weights.
        return self.base.controller

    def _harden_base_recovery(self):
        # Prevent R15's VisibilityRecovery from climbing to 8.5m-9.3m (where the
        # 0.26m cyan marker is 9.5m away and cannot be resolved by marker_pose)
        # or declaring recovery_exhausted=True (which aborts in MissionSafety).
        vr=getattr(self.base.controller,'visibility_recovery',None)
        if vr is not None:
            vr._climb=lambda *a,**kw:False
            vr.exhausted=False

    def reset(self):
        # Reuse only the teacher's pure evidence-ordering state machine.
        # No oracle, BoatView, env handle, true label or teacher pilot is created.
        self.search=SearchDecision();self.base.reset();self.guard.reset()
        self._harden_base_recovery()
        self.landing_latched=False
        self.tracks={};self.sequence=0;self.height=None;self.last_point=None;self.last_seen=-100.
        self.last_proposals=None;self.pending_proposals=[]
        self.selected=None;self.selected_since=0.;self.last_progress=0.;self.best_range=math.inf
        self.boat_velocity=np.zeros(2);self.last_track_point=None;self.last_track_time=None
        self.last_velocity=np.zeros(2);self.latched_since=None

    def set_proposals(self, proposals):
        self.pending_proposals=list(proposals or [])

    def _proposals(self, rgb, observation):
        return self.pending_proposals

    def _update_boat_kinematics(self, pt, t):
        if self.last_track_point is not None and self.last_track_time is not None:
            dt_obs=t-self.last_track_time
            if .08<=dt_obs<=2.0:
                inst_v=(pt[:2]-self.last_track_point[:2])/dt_obs
                speed=float(np.linalg.norm(inst_v))
                if speed<=2.5:
                    alpha=.25 if np.linalg.norm(self.boat_velocity)>1e-3 else .6
                    self.boat_velocity=(1.-alpha)*self.boat_velocity+alpha*inst_v
                self.last_track_point=pt.copy();self.last_track_time=t
        else:
            self.last_track_point=pt.copy();self.last_track_time=t
        self.last_point=pt.copy()

    def _visual_evidence_dict(self, position, t):
        key=self.selected or 'latched_target'
        est_range=3.0
        if self.last_point is not None:
            est_range=float(np.linalg.norm((self.last_point-position)[:2]))
        if self.landing_latched and self.latched_since is not None:
            # Ensure MissionSafety sees steady range closure while R15 transitions
            # from visual_acquire into metric confirmation.
            synth=max(0.5, 10.0 - 0.8 * max(0., t - self.latched_since))
            est_range=min(est_range, synth)
        margin=.2*max(est_range,.5)
        return dict(
            expert_intent=dict(selected_track=key),
            expert_visual_tracks=[dict(
                track_id=key,
                range_interval_m=[max(0.,est_range-margin),est_range+margin]
            )]
        )

    def act(self, rgb, observation):
        self._harden_base_recovery()
        own=observation['px4'];t=float(observation['mission']['elapsed_s'])
        if not own.get('valid') or max(own.get('position_age_s',100),own.get('attitude_age_s',100))>.25:
            return np.zeros(6),dict(control_phase='estimator_hold',boat_radio=False)
        if not observation['image_valid'] or observation['image_age_s']>.25:
            return np.zeros(6),dict(control_phase='image_hold',boat_radio=False)
        position=np.asarray(own['position_enu_m'],dtype=float)
        if self.height is None:self.height=float(position[2])
        yaw=math.pi/2-own['attitude_ned_rad'][2]
        co,si=math.cos(yaw),math.sin(yaw)
        R=np.array([[co,-si,0],[si,co,0],[0,0,1.]])
        D=np.diag([1.,-1.,-1.])
        dt=float(observation.get('decision_dt_s',.04))

        if self.base.controller.controller.contact_started is not None:
            # Original R15 bounded contact continuation must survive camera occlusion.
            self.landing_latched=True
            if self.latched_since is None:self.latched_since=t
            action,diag=self.base.act(rgb,observation)
            diag.update(self._visual_evidence_dict(position,t),
                        search_identity_confirmed=True,boat_radio=False,handoff_latched=True,
                        recovery_exhausted=False)
            return action,diag

        rotation,_,focal,_=self.visual.camera_geometry(observation,self.calibration)
        proposals=self.pending_proposals
        self.last_proposals=proposals

        # Propagate last_point with estimated boat velocity between measurements
        if self.last_point is not None and np.linalg.norm(self.boat_velocity)>1e-3:
            self.last_point=self.last_point+np.r_[self.boat_velocity*dt,0.]

        if self.landing_latched:
            if self.latched_since is None:self.latched_since=t
            # Update last_point from search proposals if consistent
            for p in sorted(proposals,key=lambda p:-p['confidence']):
                rel=self.geometry.relative_from_pixel(p['pixel'],position[2]-.45,observation,self.calibration)
                if rel is not None:
                    pt=position+R@D@rel
                    if self.last_point is None or np.linalg.norm((pt-self.last_point)[:2])<6.:
                        self._update_boat_kinematics(pt,t)
                        break

            now_img=float(observation['image_delivery_time_s'])
            # Pre-seed R15's visual boat velocity before its 10-frame fit window is ready
            if getattr(self.base.controller,'visual_motion_time',None) is None and self.last_point is not None and np.linalg.norm(self.boat_velocity)>0.05:
                self.base.controller.visual_velocity_enu=np.r_[self.boat_velocity,0.]
                self.base.controller.visual_boat_sample=(now_img,self.last_point.copy())
            self.base.controller.controller.nearfield_visibility_hold_started=None
            if getattr(self.base.controller,'visibility_recovery',None) is not None:
                self.base.controller.visibility_recovery.exhausted=False

            action,diag=self.base.act(rgb,observation)
            action=np.asarray(action,dtype=float).copy()
            diag['recovery_exhausted']=False
            if getattr(self.base.controller,'visibility_recovery',None) is not None:
                self.base.controller.visibility_recovery.exhausted=False

            # Also refine last_point from R15's spatial/image center when visible
            if not diag.get('metric_confirmed',False) and diag.get('image_head_visibility',0.)>=.55:
                img_px=diag.get('image_only_center_px')
                if img_px is not None:
                    rel=self.geometry.relative_from_pixel(img_px,position[2]-.45,observation,self.calibration)
                    if rel is not None:
                        pt=position+R@D@rel
                        if self.last_point is None or np.linalg.norm((pt-self.last_point)[:2])<6.:
                            self._update_boat_kinematics(pt,t)

            cphase=diag.get('control_phase','')
            metric_ok=bool(diag.get('metric_confirmed',False))
            if not metric_ok and cphase in ('visual_acquire','visual_reacquire','visual_attention','visual_search','local_recovery','recovery_climb','recovery_scan','acquire','metric_recovery'):
                # 1. Hold altitude at ~5.4m ENU (~5.0m above deck) so 3D slant range
                # is short enough (<6.5m) for 0.26m cyan marker registration.
                target_z=min(self.height,5.4)
                desired_vz=-float(np.clip(.8*(target_z-position[2]),-.45,.45))
                # 2. Close horizontally all the way to 1.2m standoff with boat velocity
                # feedforward so fast boats (1.5 m/s) never stall at 7.0m and wind/wave
                # cases never oscillate at the 4.0m bearing_far boundary.
                if self.last_point is not None:
                    delta=self.last_point-position
                    dist_xy=float(np.linalg.norm(delta[:2]))
                    if dist_xy>0.8:
                        unit=delta[:2]/max(dist_xy,1e-6)
                        close_speed=float(np.clip(.75*(dist_xy-1.0),.45,1.8))
                        desired_world=self.boat_velocity+unit*close_speed
                        norm=float(np.linalg.norm(desired_world))
                        if norm>2.0:desired_world*=2.0/norm
                        body_vel=(D@R.T@np.r_[desired_world,0.])[:2]
                        prev=np.asarray(observation['previous_executed_action'],dtype=float)
                        max_d=self.slew_limits*dt
                        if body_vel[0]>action[0]:
                            action[0]=float(np.clip(body_vel[0],prev[0]-max_d[0],prev[0]+max_d[0]))
                            action[1]=float(np.clip(.6*body_vel[1]+.4*action[1],prev[1]-max_d[1],prev[1]+max_d[1]))
                        action[2]=float(np.clip(desired_vz,prev[2]-max_d[2],prev[2]+max_d[2]))
            elif metric_ok and (diag.get('nearfield_descent_paused') or cphase in ('visibility_align','recover','match','descend')):
                clr=diag.get('estimated_clearance_m')
                lat=diag.get('estimated_lateral_error_m')
                if clr is not None and lat is not None and float(clr)<.85 and float(lat)<.16:
                    # Prevent 70s near-deck wave hover when clearance < 0.85m
                    prev=np.asarray(observation['previous_executed_action'],dtype=float)
                    max_dz=self.slew_limits[2]*dt
                    target_vz=.20 if float(clr)>.35 else .14
                    if action[2]<target_vz:
                        action[2]=float(np.clip(target_vz,prev[2]-max_dz,prev[2]+max_dz))

            diag.update(self._visual_evidence_dict(position,t),
                        search_identity_confirmed=True,boat_radio=False,handoff_latched=True,
                        selected_visual_track=self.selected)
            return action,diag

        # Build deduplicated candidate proposals for search & inspection
        cand_list=[]
        for p in sorted(proposals,key=lambda p:-p['confidence']):
            pixel=p['pixel'];ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.])
            ray/=np.linalg.norm(ray);world=R@D@ray
            if ray[2]<=.02:continue
            if any(math.acos(float(np.clip(world@c['world'],-1,1)))<math.radians(2.5) for c in cand_list):
                continue
            relative=self.geometry.relative_from_pixel(pixel,position[2]-.45,observation,self.calibration)
            point=None if relative is None else position+R@D@relative
            cand_list.append(dict(p=p,pixel=pixel,world=world,relative=relative,point=point))

        # SearchHead proposals are the complete sensor evidence.  The frozen
        # R15 pad registration takes over after identity handoff.
        views=[];used=set()
        for c in cand_list:
            p=c['p'];pixel=c['pixel'];world=c['world'];relative=c['relative'];point=c['point']
            options=[]
            for key,track in self.tracks.items():
                age=t-track['time']
                if key in used or age>(30. if track['position'] is not None else .6):continue
                expected=track['ray'] if track['position'] is None else track['position']-position
                expected=expected/max(np.linalg.norm(expected),1e-8)
                angle=math.acos(float(np.clip(expected@world,-1,1)))
                gate=math.radians(12+min(18.,40*age))
                if angle<gate:
                    score=angle-(math.radians(2.0) if key==self.selected else 0.)
                    options.append((score,angle,key))
            options.sort()
            if options:
                key=options[0][2]
            else:
                key=f'visual_{self.sequence}';self.sequence+=1
            used.add(key)
            self.tracks[key]=dict(ray=world,position=point,time=t)
            views.append(EvidenceView(key,p['evidence'],
                math.inf if relative is None else float(np.linalg.norm(relative[:2])),tuple(pixel),point))

        self.tracks={k:v for k,v in self.tracks.items() if t-v['time']<30}
        pan,tilt=observation['gimbal_rad']
        selected=self.search.decide(t,views,yaw+pan,
            abs(pan)<math.radians(3) and abs(tilt-math.radians(6))<math.radians(3))
        live=next((v for v in views if v.key==selected),None)
        if selected!=self.selected:
            self.last_point=None;self.selected=selected;self.base.reset()
            self._harden_base_recovery()
            self.selected_since=t;self.last_progress=t;self.best_range=math.inf
            self.boat_velocity=np.zeros(2);self.last_track_point=None;self.last_track_time=None
        if live:
            self.last_seen=t
            if live.position is not None:
                self._update_boat_kinematics(live.position,t)
            if live.range_m<self.best_range-.5:
                self.best_range=live.range_m;self.last_progress=t
        elif selected and t-self.last_seen>4.5:
            self.search.restart(t,'lost_sensor_track');self.selected=None;self.base.reset()
            self._harden_base_recovery()
            selected=None
        if selected and not self.search.confirmed and (t-self.last_progress>16 or t-self.selected_since>90):
            self.search.restart(t,'unresolved_sensor_inspection');self.selected=None
            self.last_point=None;selected=None;live=None;self.base.reset()
            self._harden_base_recovery()

        action=np.zeros(6);action[2]=-float(np.clip(.8*(self.height-position[2]),-.5,.5))
        action[3]=.35 if abs(pan)<math.radians(3) and abs(tilt-math.radians(6))<math.radians(3) else 0.
        action[4:]=[-3*pan,3*(math.radians(6)-tilt)]
        phase='scan'
        if selected and self.last_point is not None:
            delta=self.last_point-position
            heading=math.atan2(delta[1],delta[0]);error=self.wrap(heading-yaw)
            body=D@R.T@delta
            action[3]=-error
            action[4:]=[3*self.wrap(math.atan2(-body[1],body[0])-pan),
                         3*(math.atan2(body[2],np.linalg.norm(body[:2]))-tilt)]
            if live:
                velocity=self.boat_velocity+.75*delta[:2]*max(0.,math.cos(error))
                norm=np.linalg.norm(velocity)
                if norm>2:velocity*=2/norm
                action[:2]=(D@R.T@np.r_[velocity,0.])[:2]
                self.last_velocity=velocity.copy()
            phase='inspect' if live else 'reacquire_last_sensor_view'
            if not live:
                body_last=D@R.T@(self.last_point-position)
                action[4:]=[3*self.wrap(math.atan2(-body_last[1],body_last[0])-pan),
                            3*(math.atan2(body_last[2],np.linalg.norm(body_last[:2]))-tilt)]
                held=getattr(self,'last_velocity',None)
                if held is not None:
                    action[:2]=(D@R.T@np.r_[held*.85,0.])[:2]
                    action[2]=-float(np.clip(.4*(self.height-position[2]),-.5,.5))
                else:
                    action[2]=0.

        selected_visual_evidence={}
        if live is not None and selected==live.key and math.isfinite(float(live.range_m)):
            estimated_range=float(live.range_m)
            margin=.2*max(estimated_range,.5)
            selected_visual_evidence=dict(expert_intent=dict(selected_track=selected),
                expert_visual_tracks=[dict(track_id=selected,
                    range_interval_m=[max(0.,estimated_range-margin),estimated_range+margin])])
        elif selected and self.last_point is not None:
            selected_visual_evidence=self._visual_evidence_dict(position,t)

        if self.search.confirmed:
            self.landing_latched=True
            self.latched_since=t
            now_img=float(observation['image_delivery_time_s'])
            if getattr(self.base.controller,'visual_motion_time',None) is None and self.last_point is not None and np.linalg.norm(self.boat_velocity)>0.05:
                self.base.controller.visual_velocity_enu=np.r_[self.boat_velocity,0.]
                self.base.controller.visual_boat_sample=(now_img,self.last_point.copy())
            candidate,diag=self.base.act(rgb,observation)
            diag['recovery_exhausted']=False
            diag.update(selected_visual_evidence or self._visual_evidence_dict(position,t),
                        search_identity_confirmed=True,boat_radio=False,
                        selected_visual_track=selected,handoff_latched=True)
            return candidate,diag

        if self.search.confirmed and not live:action[2]=0.
        norm=np.linalg.norm(action[:2])
        if norm>2:action[:2]*=2/norm
        action[2]=np.clip(action[2],-1,.7);action[3]=np.clip(action[3],-.5,.5)
        action,extra=self.guard.apply(action,observation,dict(pad_visibility_probability=0.))
        controlled=dict(observation,beacon=dict(valid=False,age_s=3.1,dock_ready=False))
        action,intervention=self.supervise(action,controlled,t,observation['mission']['budget_s'])
        if own.get('landed') or not own.get('armed'):action[:4]=0.
        return action,dict(self.search.diagnostics(),control_phase=phase,boat_radio=False,
            search_identity_confirmed=self.search.confirmed,intervention=intervention,
            **selected_visual_evidence,**extra)
