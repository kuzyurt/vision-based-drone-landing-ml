"""Learned pad orientation plus metric RGB registration and bounded touchdown."""
import copy,math
from collections import deque
import numpy as np
import torch
from scipy.optimize import least_squares
from .hybrid_policy import HybridPosePolicy,LandingController,heading_rotation,body_to_heading
from .marker_geometry import marker_pose
from .camera_geometry import compensate_capture,camera_body_transform,relative_from_pixel
from .recording import numeric_observation
from .action_guard import wrap,beacon_camera_target

class MarkerLandingController(LandingController):
    def __init__(self,calibration,slew_limits):
        self.calibration=calibration
        super().__init__(calibration['foot_local_flu'],slew_limits)
    def reset(self):
        super().reset();self.contact_started=None;self.camera_branch=None;self.current_estimate=None
    def act(self,estimate,observation):
        self.current_estimate=estimate
        now=float(observation['image_delivery_time_s']);px4=observation['px4']
        if px4.get('landed') or not px4.get('armed'):return super().act(estimate,observation)
        if self.contact_started is not None:
            roll,pitch,_=px4['attitude_ned_rad']
            speed=np.linalg.norm(estimate['relative_velocity'][:2])
            fresh=observation['beacon'].get('valid',False) and observation['beacon']['age_s']<3.
            if now-self.contact_started<=8. and fresh and speed<.15 and max(abs(roll),abs(pitch))<math.radians(8):
                action=np.zeros(6);action[:3]=numeric_observation({'observation':observation})[:3]+estimate['relative_velocity']
                action[2]=max(action[2]+.32,.30)
                return self.finish(action,observation,{'control_phase':'touchdown_commit','pose_valid':False,'pad_visibility_probability':estimate['visibility'],'contact_commit_s':now-self.contact_started})
            self.contact_started=None;self.stable_elapsed=0.
        action,diagnostics=self._tracked_act(estimate,observation)
        if (diagnostics['control_phase']=='touchdown' and diagnostics.get('stable_tracking_s',0)>=.24
                and diagnostics['estimated_lateral_error_m']<.08
                and np.linalg.norm(estimate['relative_velocity'][:2])<.10
                and abs(diagnostics['estimated_heading_error_deg'])<5.
                and diagnostics['estimated_deck_tilt_deg']<5. and estimate.get('metric_age_s',99)<2.):
            self.contact_started=now
        return action,diagnostics
    def _tracked_act(self,estimate,observation):
        dt=float(observation['decision_dt_s']);numeric=numeric_observation({'observation':observation})
        px4=observation['px4'];b=observation['beacon'];roll,pitch,yaw_ned=px4.get('attitude_ned_rad',[0.,0.,0.])
        yaw=math.pi/2-yaw_ned
        probability=float(estimate['visibility'])
        if px4.get('landed',False) or not px4.get('armed',False):
            action=np.zeros(6)
            if px4.get('armed',False):
                action[:3]=np.asarray(b.get('velocity_heading_m_s',[0.,0.,0.]))
                action[2]=max(action[2]+.32,.30)
            phase='confirm' if px4.get('armed',False) else 'disarmed'
            return self.finish(action,observation,{'control_phase':phase,'pose_valid':False,'pad_visibility_probability':probability})
        r=np.asarray(estimate['relative_position'],dtype=float)
        velocity=np.asarray(estimate['relative_velocity'],dtype=float)
        normal=np.asarray(estimate['normal'],dtype=float)
        heading=np.asarray(estimate['heading_pair'],dtype=float)
        valid=(r.shape==(3,) and velocity.shape==(3,) and normal.shape==(3,) and heading.shape==(2,)
               and all(np.isfinite(x).all() for x in [r,velocity,normal,heading])
               and probability>=.8 and observation['image_valid'] and observation['image_age_s']<=.25
               and np.linalg.norm(normal)>.5 and normal[2]<-.5 and np.linalg.norm(heading)>.5)
        fresh=b.get('valid',False) and b.get('age_s',math.inf)<3
        if not valid:
            self.stable_elapsed=0.;self.relative=None
            action=np.zeros(6);phase='acquire'
            if fresh:
                relative=np.asarray(b['relative_heading_m'],dtype=float)
                vboat=np.asarray(b['velocity_heading_m_s'],dtype=float)
                action[:2]=.4*relative[:2]+vboat[:2]
                action[2]=-np.clip(1.5-relative[2],0,.5)
                candidate=yaw+math.atan2(-relative[1],relative[0])
                action[3]=-wrap(candidate-yaw) if np.linalg.norm(relative[:2])>1. else 0.
                target=beacon_camera_target(observation)
                if target is not None:
                    action[4]=3*wrap(target[0]-observation['gimbal_rad'][0])
                    action[5]=3*(target[1]-observation['gimbal_rad'][1])
            else:action[2]=-.3
            return self.finish(action,observation,{'control_phase':phase,'pose_valid':False,'pad_visibility_probability':probability})

        # Propagate the previous estimate with relative velocity and transport
        # between heading frames before filtering, so yaw changes are not lag.
        if self.relative is not None:
            previous_enu=(heading_rotation(self.previous_yaw)@(self.relative*[1,-1,-1])
                          +heading_rotation(self.previous_yaw)@(self.relative_velocity*[1,-1,-1])*dt)
            predicted=(heading_rotation(yaw).T@previous_enu)*[1,-1,-1]
            alpha=min(1.,dt/.12)
            r=predicted+alpha*(r-predicted)
        self.relative=r.copy();self.relative_velocity=velocity.copy();self.previous_yaw=yaw
        normal=normal/np.linalg.norm(normal)
        relative_tangent=r-normal*np.dot(r,normal)
        lateral=float(np.linalg.norm(relative_tangent))
        speed=float(np.linalg.norm(velocity[:2]))
        deck_tilt=math.acos(np.clip(-normal[2],-1,1))
        delta=.5*math.atan2(heading[0],heading[1]);candidate=yaw+delta
        if self.heading_target is None:self.heading_target=candidate
        else:self.heading_target+=min(1.,dt/.25)*.5*wrap(2*(candidate-self.heading_target))
        heading_error=wrap(self.heading_target-yaw)
        feet_heading=(body_to_heading(roll,pitch)@self.feet.T).T
        clearance=float(np.min((feet_heading-r)@normal))
        ready=(lateral+estimate.get('metric_uncertainty_m',0.)<.12 and speed<.18 and abs(heading_error)<math.radians(8)
               and deck_tilt<math.radians(8) and b.get('dock_ready',False))
        self.stable_elapsed=self.stable_elapsed+dt if ready else 0.
        phase='align' if lateral>.15 else 'match'
        boat_velocity=numeric[:3]+velocity
        offset=r[:2]+normal[:2]*(r[2]/max(-normal[2],.5))
        action=np.zeros(6)
        action[:2]=boat_velocity[:2]+1.1*offset+.45*velocity[:2]
        action[2]=boat_velocity[2]-.8*(max(1.2,clearance)-clearance)
        if self.stable_elapsed>=.24:
            phase='descend';action[2]=boat_velocity[2]+(.22 if clearance>.65 else .10)
        elif clearance<1.2:
            phase='recover';action[2]=boat_velocity[2]-.4*(1.2-clearance)
        if ready and clearance<.03:
            phase='touchdown';action[:3]=boat_velocity;action[2]=max(boat_velocity[2]+.32,.30)
        if px4.get('landed',False):
            phase='confirm';action[:3]=boat_velocity;action[2]=max(boat_velocity[2]+.32,.30)
        if not px4.get('armed',False):
            action[:4]=0.;phase='disarmed'
        action[3]=0. if phase in ('touchdown','confirm','disarmed') else -heading_error
        # Camera aim uses the same relative estimate and measured roll/pitch.
        camera_observation=dict(observation)
        camera_observation['beacon']={'valid':True,'age_s':0.,'relative_heading_m':r.tolist()}
        target=beacon_camera_target(camera_observation)
        if target is not None:
            action[4]=3*wrap(target[0]-observation['gimbal_rad'][0])
            action[5]=3*(target[1]-observation['gimbal_rad'][1])
        info={'control_phase':phase,'pose_valid':True,'estimated_relative_position':r.tolist(),
              'estimated_relative_velocity':velocity.tolist(),'estimated_lateral_error_m':lateral,
              'estimated_clearance_m':clearance,'estimated_heading_error_deg':math.degrees(heading_error),
              'estimated_deck_tilt_deg':math.degrees(deck_tilt),'stable_tracking_s':self.stable_elapsed,
              'pad_visibility_probability':probability}
        return self.finish(action,observation,info)

    def recover_metric(self,estimate,observation):
        self.current_estimate=estimate;self.stable_elapsed=0.;self.relative=None
        numeric=numeric_observation({'observation':observation})
        r=np.asarray(estimate['relative_position']);normal=np.asarray(estimate['normal']);normal/=max(np.linalg.norm(normal),1e-6)
        velocity=np.asarray(estimate['relative_velocity']);boat=numeric[:3]+velocity
        offset=r[:2]+normal[:2]*(r[2]/max(-normal[2],.5))
        correction=.4*offset;norm=np.linalg.norm(correction)
        if norm>.2:correction*=.2/norm
        action=np.zeros(6);action[:3]=boat;action[:2]+=correction
        feet=(body_to_heading(*observation['px4']['attitude_ned_rad'][:2])@self.feet.T).T
        clearance=float(np.min((feet-r)@normal))
        action[2]-=.4*np.clip(1.2-clearance,0,.75)
        yaw=math.pi/2-observation['px4']['attitude_ned_rad'][2]
        if self.heading_target is not None:action[3]=-wrap(self.heading_target-yaw)
        aim=dict(observation);aim['beacon']={'valid':True,'age_s':0.,'relative_heading_m':r.tolist()}
        target=beacon_camera_target(aim)
        if target is not None:
            action[4]=3*wrap(target[0]-observation['gimbal_rad'][0]);action[5]=3*(target[1]-observation['gimbal_rad'][1])
        return self.finish(action,observation,{'control_phase':'metric_recovery','pose_valid':False,'pad_visibility_probability':0.,'estimated_clearance_m':clearance})

    def finish(self,action,observation,diagnostics):
        e=self.current_estimate
        if diagnostics.get('pose_valid') and diagnostics.get('estimated_clearance_m',99)<.65 and diagnostics.get('estimated_lateral_error_m',99)<.10 and self.camera_branch is None:
            self.camera_branch=round(observation['gimbal_rad'][0]/math.pi)*math.pi
        if self.camera_branch is not None and diagnostics['control_phase'] not in ('acquire','disarmed'):
            action[4]=3*wrap(self.camera_branch-observation['gimbal_rad'][0])
            target=np.diag([1.,-1.,-1.])@body_to_heading(*observation['px4']['attitude_ned_rad'][:2]).T@np.asarray(e['relative_position'])
            def residual(tilt):
                T=camera_body_transform(self.calibration,[self.camera_branch,tilt[0]])
                ray=T[:3,:3].T@(target-T[:3,3]);norm=np.linalg.norm(ray)
                return ray/max(norm,1e-6)-[0.,0.,-1.]
            fit=least_squares(residual,[np.clip(observation['gimbal_rad'][1],-math.radians(10)+1e-6,math.pi/2-1e-6)],bounds=([-math.radians(10)],[math.pi/2]),max_nfev=10)
            action[5]=3*(fit.x[0]-observation['gimbal_rad'][1])
            diagnostics['camera_corridor_pan_rad']=self.camera_branch
        return super().finish(action,observation,diagnostics)

class MarkerPosePolicy(HybridPosePolicy):
    def __init__(self,checkpoint,calibration,slew_limits,device='cuda'):
        super().__init__(checkpoint,calibration,slew_limits,device)
        self.controller=MarkerLandingController(calibration,slew_limits)
        self.track=None;self.track_time=None;self.track_yaw=None;self.metric_time=None
        self.boat_velocity_enu=None;self.metric_heading_world=None;self.heading_quadrant_from_motion=False
    def reset(self):
        super().reset();self.track=None;self.track_time=None;self.track_yaw=None;self.metric_time=None;self.boat_velocity_enu=None;self.metric_heading_world=None;self.heading_quadrant_from_motion=False
    def resolve_marker_heading(self,observed_world_heading,yaw):
        moving=self.boat_velocity_enu is not None and np.linalg.norm(self.boat_velocity_enu[:2])>.10
        if moving and not self.heading_quadrant_from_motion:
            course=math.atan2(self.boat_velocity_enu[1],self.boat_velocity_enu[0])
            reference=course+round((yaw-course)/math.pi)*math.pi
            self.heading_quadrant_from_motion=True
        elif self.metric_heading_world is not None:reference=self.metric_heading_world
        else:reference=yaw
        return observed_world_heading+round((reference-observed_world_heading)/(math.pi/2))*(math.pi/2)

    def accept_metric(self,measured,prior,observation,now):
        cold=self.track is None
        reacquiring=(not cold and self.metric_time is not None and now-self.metric_time>2.)
        if cold or reacquiring:
            beacon=observation['beacon']
            if not beacon.get('valid',False) or beacon['age_s']>=3.:return False,'radio_reference_stale'
            coarse=np.asarray(beacon['relative_heading_m'])+np.asarray(beacon['velocity_heading_m_s'])*beacon['age_s']
            if abs(measured[2]-coarse[2])>.9 or np.linalg.norm(measured[:2]-coarse[:2])>.9:return False,'outside_radio_context'
            return True,'reacquired' if reacquiring else 'acquired'
        if np.linalg.norm(measured-prior)>max(.08,.10*prior[2]):return False,'tracking_innovation'
        return True,'tracked'

    @torch.inference_mode()
    def act(self,rgb,observation):
        image=torch.from_numpy(rgb.copy()).permute(2,0,1)[None,None].to(self.device)
        numeric=torch.from_numpy(numeric_observation({'observation':observation}))[None,None].to(self.device)
        prediction,_,self.hidden=self.model(image,numeric,self.hidden);p=prediction[0,0].cpu().numpy()
        probability=float(1/(1+np.exp(-np.clip(p[0],-40,40))))
        now=float(observation['image_delivery_time_s']);dt=float(observation['decision_dt_s'])
        yaw=math.pi/2-observation['px4']['attitude_ned_rad'][2];R=heading_rotation(yaw);D=np.diag([1.,-1.,-1.])
        fresh=observation['beacon'].get('valid',False) and observation['beacon']['age_s']<3.
        if fresh:
            boat=R@D@np.asarray(observation['beacon']['velocity_heading_m_s'])
            if self.boat_velocity_enu is None:self.boat_velocity_enu=boat
            else:self.boat_velocity_enu+=min(1.,dt/.3)*(boat-self.boat_velocity_enu)
        velocity=p[4:7]
        if self.boat_velocity_enu is not None:velocity=D@R.T@(self.boat_velocity_enu-np.asarray(observation['px4']['velocity_enu_m_s']))
        prior=p[1:4].copy()
        if self.track is None and fresh:prior[2]=observation['beacon']['relative_heading_m'][2]
        if self.track is not None:
            prior=D@R.T@(heading_rotation(self.track_yaw)@D@self.track)+velocity*dt
        self.history.append((now,copy.deepcopy(observation)))
        capture_time=observation['image_capture_time_s'];capture=min(self.history,key=lambda t:abs(t[0]-capture_time))[1]
        history_error=min(abs(t-capture_time) for t,_ in self.history)
        age=float(observation['image_age_s'])
        current={'relative_position':prior,'relative_velocity':velocity,'normal':p[9:12],'heading_pair':p[7:9],'visibility':probability,'contact_probability':float(1/(1+np.exp(-np.clip(p[14],-40,40))))}
        capture_yaw=math.pi/2-capture['px4']['attitude_ned_rad'][2];Rc=heading_rotation(capture_yaw)
        current_to_capture=D@Rc.T@R@D
        pose_at_capture=copy.deepcopy(current)
        pose_at_capture['relative_position']=current_to_capture@(prior-velocity*age)
        pose_at_capture['normal']=current_to_capture@current['normal']
        angle=.5*math.atan2(p[7],p[8])+yaw-capture_yaw
        if self.metric_heading_world is not None:angle=self.metric_heading_world-capture_yaw
        elif self.boat_velocity_enu is not None and np.linalg.norm(self.boat_velocity_enu[:2])>.10:angle=math.atan2(self.boat_velocity_enu[1],self.boat_velocity_enu[0])-capture_yaw
        else:angle=yaw-capture_yaw
        pose_at_capture['heading_pair']=[math.sin(2*angle),math.cos(2*angle)]
        metric_recent=self.metric_time is not None and now-self.metric_time<.5
        pose_at_capture['_tracked']=metric_recent
        if not metric_recent:
            pixel=(p[12:14]+1)*[320.,180.]
            if 0<pixel[0]<640 and 0<pixel[1]<360:
                ray_prior=relative_from_pixel(pixel,pose_at_capture['relative_position'][2],capture,self.calibration)
                if ray_prior is not None:pose_at_capture['relative_position']=ray_prior
        fit=None
        if history_error<=.021 and observation['image_valid'] and age<=.25 and probability>=.8:
            fit=marker_pose(rgb,capture,self.calibration,pose_at_capture)
        fit_candidate_valid=fit is not None;acceptance='no_registration';innovation=None
        if fit is not None:
            measured=compensate_capture(fit['relative_position'],capture,observation,velocity,age)
            innovation=float(np.linalg.norm(measured-prior))
            accepted,acceptance=self.accept_metric(measured,prior,observation,now)
            if not accepted:fit=None
            else:
                current['relative_position']=measured if acceptance in ('acquired','reacquired') else prior+.6*(measured-prior)
                self.metric_time=now
                observed_heading=capture_yaw+fit['heading_angle_heading_rad']
                self.metric_heading_world=self.resolve_marker_heading(observed_heading,yaw)
                if acceptance=='reacquired':self.controller.relative=None;self.controller.stable_elapsed=0.
        if fit is None:current['relative_position']=prior
        if self.metric_heading_world is not None:
            angle=self.metric_heading_world-yaw
            current['heading_pair']=[math.sin(2*angle),math.cos(2*angle)]
        metric_age=math.inf if self.metric_time is None else now-self.metric_time
        uncertainty=.012+.035*metric_age
        # Short propagation uses public velocity, never a refreshed noisy GNSS range.
        trusted=(metric_age<=2. and fresh and observation['image_valid'] and age<=.25)
        current['visibility']=max(.9,probability) if trusted else 0.
        current['metric_age_s']=metric_age
        if trusted:
            # Apply conservative uncertainty to the lateral acceptance radius.
            r=np.asarray(current['relative_position']);n=current['normal']/np.linalg.norm(current['normal'])
            tangent=r-n*np.dot(r,n);lateral=np.linalg.norm(tangent)
            current['metric_uncertainty_m']=uncertainty
            self.track=np.array(current['relative_position']);self.track_time=now;self.track_yaw=yaw
        elif self.track is not None:
            self.track=np.array(prior);self.track_time=now;self.track_yaw=yaw
        if not trusted and self.track is not None and self.controller.contact_started is None and observation['px4'].get('armed',False) and not observation['px4'].get('landed',False):
            action,diag=self.controller.recover_metric(current,observation)
        else:action,diag=self.controller.act(current,observation)
        diag.update(metric_valid=fit is not None,fit_candidate_valid=fit_candidate_valid,metric_acceptance=acceptance,metric_innovation_m=innovation,metric_age_s=metric_age if math.isfinite(metric_age) else None,metric_uncertainty_m=uncertainty if math.isfinite(uncertainty) else None,
                    raw_model_visibility_probability=probability,capture_history_error_s=history_error,stable_contact_probability=current['contact_probability'])
        if fit is not None:diag.update(marker_orientation_correction_deg=math.degrees(fit['orientation_correction_rad']),marker_fit_rms_px=fit['fit_rms_px'],marker_center_px=fit['center_px'],marker_paint_precision=fit['paint_precision'],marker_paint_recall=fit['paint_recall'])
        return action,diag
