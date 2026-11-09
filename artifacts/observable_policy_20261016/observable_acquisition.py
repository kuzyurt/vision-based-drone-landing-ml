"""Camera/own-telemetry acquisition with a clear aircraft-relative viewing sector."""
import math
import numpy as np
from .visual_acquisition import camera_geometry
from .action_guard import wrap


def heading(yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    return np.array([[c,-s,0],[s,c,0],[0,0,1.]])


def acquire_visual(controller,estimate,observation,prediction):
    controller.current_estimate=estimate;controller.stable_elapsed=0.;controller.relative=None
    action=np.zeros(6);now=float(observation['image_delivery_time_s']);dt=observation['decision_dt_s']
    yaw=math.pi/2-observation['px4']['attitude_ned_rad'][2];R=heading(yaw);D=np.diag([1.,-1.,-1.])
    pan,tilt=observation['gimbal_rad'];pixel=(np.asarray(prediction[12:14])+1.)*[320.,180.]
    capture=getattr(controller,'bearing_capture_observation',observation)
    rotation,_,focal,_=camera_geometry(capture,controller.calibration)
    _,_,_,level=camera_geometry(observation,controller.calibration)
    Rc=heading(math.pi/2-capture['px4']['attitude_ned_rad'][2])
    state=getattr(controller,'observable_acquisition_state',None)
    if state is None or now<state['now']:
        state=dict(now=now,last=None,count=0,preferred=None,scan_started=now,rejected=0)
        controller.observable_acquisition_state=state
    valid=(observation['image_valid'] and observation['image_age_s']<=.25 and estimate['visibility']>=.8
           and np.isfinite(pixel).all() and 8<pixel[0]<632 and 8<pixel[1]<352)
    history=False;rejected=False;world=None
    if valid:
        ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.]);ray/=np.linalg.norm(ray)
        measured=Rc@D@ray
        last=state['last']
        if last is not None and now-last[0]<.3:
            angle=math.acos(np.clip(np.dot(last[1],measured),-1,1))
            if angle>math.radians(12+40*(now-last[0])):
                rejected=True;valid=False;state['rejected']+=1
        if valid:
            world=measured;state['count']=state['count']+1 if last is not None and now-last[0]<.3 else 1
            state['last']=(now,world);state['scan_started']=None
    if world is None:
        last=state['last']
        if last is not None and now-last[0]<.28 and observation['image_valid']:
            world=last[1];history=True
        else:state['count']=0;state['preferred']=None
    turning=False;desired_pan=None;heading_error=None
    if world is not None:
        ray=D@R.T@world
        body=level.T@ray
        desired_pan=math.atan2(-body[1],body[0]);desired_tilt=math.atan2(body[2],np.linalg.norm(body[:2]))
        if state['preferred'] is None:
            # Static CAD calibration found clear central views at pan 0 and pi.
            state['preferred']=0. if abs(wrap(desired_pan))<math.pi/2 else math.pi
        heading_error=wrap(desired_pan-state['preferred'])
        action[3]=-float(np.clip(.9*heading_error,-.4,.4))
        # Counter-pan the actual body yaw while retaining the observed world bearing.
        action[4]=3*wrap(desired_pan-pan)+float(observation['px4']['angular_rate_frd_rad_s'][2])
        action[5]=3*(desired_tilt-tilt)
        turning=abs(heading_error)>math.radians(30)
        if state['count']>=3 and not turning and ray[2]>.02:
            action[:2]=2.*ray[:2]
            if history:action[:2]*=.35
        phase='visual_reacquire' if history else 'visual_acquire'
    else:
        if state['scan_started'] is None:state['scan_started']=now
        elapsed=now-state['scan_started']
        target=math.radians([8.,35.,65.][int(elapsed/16)%3])
        action[3]=-.4;action[4]=3*wrap(-pan);action[5]=1.2*(target-tilt)
        phase='visual_search'
    state['now']=now
    diagnostics=dict(control_phase=phase,pose_valid=False,pad_visibility_probability=float(estimate['visibility']),
        visual_bearing_only=True,range_source='unavailable',bearing_history_used=history,
        learned_center_px=pixel.tolist(),bearing_confirmed_frames=state['count'],bearing_innovation_rejected=rejected,
        view_alignment_required=turning,view_preferred_pan_deg=math.degrees(state['preferred']) if state['preferred'] is not None else None,
        view_heading_error_deg=math.degrees(heading_error) if heading_error is not None else None,
        visual_target_age_s=now-state['last'][0] if state['last'] is not None else None,
        search_uses_aircraft_yaw=True,boat_truth_used=False)
    return controller.finish(action,observation,diagnostics)
