"""Camera/own-telemetry acquisition with a clear aircraft-relative viewing sector."""
import math
import json
from pathlib import Path
import numpy as np
from .visual_acquisition import camera_geometry
from .action_guard import wrap


_rows=json.loads(Path(__file__).with_name('camera_obstruction_map.json').read_text())['measurements']
_obstruction=np.array([r['centre_aircraft_fraction'] for r in _rows]).reshape(7,24)

def obstruction(pan,tilt):
    x=((math.degrees(pan)+180)%360)/15;y=float(np.clip(math.degrees(tilt)/15,0,6))
    x0=int(math.floor(x));x1=(x0+1)%24;y0=int(math.floor(y));y1=min(6,y0+1)
    a=x-x0;b=y-y0
    return float((1-b)*((1-a)*_obstruction[y0,x0]+a*_obstruction[y0,x1])+b*((1-a)*_obstruction[y1,x0]+a*_obstruction[y1,x1]))


def heading(yaw):
    c,s=math.cos(yaw),math.sin(yaw)
    return np.array([[c,-s,0],[s,c,0],[0,0,1.]])


def acquire_visual(controller,estimate,observation,prediction,*,finish_action=True):
    controller.current_estimate=estimate;controller.stable_elapsed=0.;controller.relative=None
    action=np.zeros(6);now=float(observation['image_delivery_time_s']);dt=observation['decision_dt_s']
    yaw=math.pi/2-observation['px4']['attitude_ned_rad'][2];R=heading(yaw);D=np.diag([1.,-1.,-1.])
    pan,tilt=observation['gimbal_rad'];pixel=(np.asarray(prediction[12:14])+1.)*[320.,180.]
    capture=getattr(controller,'bearing_capture_observation',observation)
    rotation,_,focal,_=camera_geometry(capture,controller.calibration)
    _,origin_now,_,level=camera_geometry(observation,controller.calibration)
    Rc=heading(math.pi/2-capture['px4']['attitude_ned_rad'][2])
    state=getattr(controller,'observable_acquisition_state',None)
    if state is None or now<state['now']:
        state=dict(now=now,last=None,last_strong=None,count=0,preferred=None,scan_started=now,rejected=0,view_active=False,tentative_until=None,attention_cooldown=0.,tentative=False)
        controller.observable_acquisition_state=state
    strong=estimate['visibility']>=.8
    maintained=state['last_strong'] is not None and now-state['last_strong']<1. and estimate['visibility']>=.15
    valid=(observation['image_valid'] and observation['image_age_s']<=.25 and (strong or maintained)
           and np.isfinite(pixel).all() and 8<pixel[0]<632 and 8<pixel[1]<352)
    tentative=False
    # A partial boat at the image edge may have moderate presence. Give that
    # observation camera attention first. Above-horizon false detections cannot
    # request attention, and tentative evidence cannot authorize translation.
    if not strong and not maintained and observation['image_valid'] and observation['image_age_s']<=.25:
        candidate_ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.])
        candidate_ray/=np.linalg.norm(candidate_ray)
        attention_valid=(estimate['visibility']>=.35 and np.isfinite(pixel).all()
                         and 2<pixel[0]<638 and 2<pixel[1]<358 and candidate_ray[2]>.02)
        if state['tentative_until'] is not None and now>state['tentative_until']:
            state['attention_cooldown']=now+8.;state['tentative_until']=None
            state['last']=None;state['count']=0
        if attention_valid and now>=state['attention_cooldown']:
            if state['tentative_until'] is None:state['tentative_until']=now+2.
            tentative=True;valid=True
    if strong:state['tentative_until']=None;state['tentative']=False
    horizon_ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.])
    horizon_ray/=max(np.linalg.norm(horizon_ray),1e-9)
    horizon_rejected=bool(valid and horizon_ray[2]<=.02)
    if horizon_rejected:valid=False
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
            stamp=float(observation['image_capture_time_s'])
            if last is None or now-last[0]>.3:state['elevation_samples']=[]
            samples=state.setdefault('elevation_samples',[])
            elevation=math.atan2(-world[2],np.linalg.norm(world[:2]))
            if not samples or stamp>samples[-1][0]:samples.append((stamp,elevation))
            while samples and stamp-samples[0][0]>.6:samples.pop(0)

            state['tentative']=tentative
            if strong:state['last_strong']=now
    if world is None:
        last=state['last']
        if last is not None and now-last[0]<.28 and observation['image_valid']:
            world=last[1];history=True;tentative=state['tentative']
        else:state['count']=0;state['preferred']=None;state['view_active']=False
    turning=False;desired_pan=None;heading_error=None;coarse_range=None;coarse_speed=None;observed_rate=None;forecast_rate=None;rate_limited=False
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
        risk=obstruction(desired_pan,desired_tilt)
        if risk>.10:state['view_active']=True
        if abs(heading_error)<math.radians(20):state['view_active']=False
        turning=state['view_active'] and abs(heading_error)>math.radians(20)
        if not state['view_active']:action[3]=0.
        if state['count']>=3 and not turning and ray[2]>.02 and not tentative:
            action[:2]=2.*ray[:2]
            mission=observation['mission']
            if 'water_datum_enu_m' in mission and 'nominal_deck_height_above_water_m' in mission:
                height=float(observation['px4']['position_enu_m'][2])-float(mission['water_datum_enu_m'])-float(mission['nominal_deck_height_above_water_m'])-origin_now[2]
                if height>.2:
                    # This declared plane prior governs coarse braking only.
                    # It does not authorize metric lock, descent or touchdown.
                    horizontal=origin_now[:2]+height*ray[:2]/ray[2]
                    coarse_range=float(np.linalg.norm(horizontal))
                    coarse_speed=min(2.,coarse_range)
                    # Rate, not a fixed distance, determines whether this view
                    # can be tracked. A distant/high target needs approach;
                    # an incoming low target may need braking or backing away.
                    samples=state.get('elevation_samples',[])
                    cap=.5
                    if len(samples)>=5 and samples[-1][0]-samples[0][0]>=.159:
                        t=np.asarray([v[0]-samples[-1][0] for v in samples])
                        angles=np.asarray([v[1] for v in samples])
                        if len(samples)>=8 and t[-1]-t[0]>=.279:
                            fit=np.polyfit(t,angles,2)
                            observed_rate=float(fit[1]);forecast_rate=float(fit[1]+max(0.,2*fit[0])*.35)
                        else:
                            fit=np.polyfit(t,angles,1);observed_rate=forecast_rate=float(fit[0])
                        direction=world[:2]/max(np.linalg.norm(world[:2]),1e-9)
                        own_radial=float(np.dot(np.asarray(capture['px4']['velocity_enu_m_s'])[:2],direction))
                        sensitivity=height/max(height*height+coarse_range*coarse_range,1e-9)
                        cap=float(np.clip(own_radial+(.35-max(0.,forecast_rate))/max(sensitivity,.01),-1.,2.))
                    rate_limited=cap<coarse_speed;coarse_speed=min(coarse_speed,cap)
                    if coarse_range>1e-6:action[:2]=coarse_speed*horizontal/coarse_range
            if history:action[:2]*=.35
        phase='visual_attention' if tentative else 'visual_reacquire' if history else 'visual_acquire'
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
        search_uses_aircraft_yaw=True,boat_truth_used=False,
        acquisition_strong=bool(strong),acquisition_hysteresis=bool(maintained and not strong),
        camera_centre_obstruction_fraction=obstruction(pan,tilt),tentative_camera_attention=tentative,horizon_target_rejected=horizon_rejected,coarse_plane_prior_range_m=coarse_range,coarse_horizontal_speed_m_s=coarse_speed,observed_elevation_rate_rad_s=observed_rate,forecast_elevation_rate_rad_s=forecast_rate,coarse_angular_rate_budget_rad_s=.35,coarse_angular_rate_limited=rate_limited)
    return controller.finish(action,observation,diagnostics) if finish_action else (action,diagnostics)
