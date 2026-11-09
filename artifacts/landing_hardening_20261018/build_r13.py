"""Separate stopping-distance envelope for uninitialized visual acquisition."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
source=ROOT/'candidate_r10';dest=ROOT/'candidate_r13';assert not dest.exists()
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
controller=dest/'code/landing_training/radio_robust_20261015/controller'
module='''"""Observed bearing + own motion braking; no metric/descent permission.

The .6m/s2 braking budget and .4s reaction allowance are conservative engineering
settings below the recorded R12 slowdown (~.9m/s2), not certified physical bounds.
65deg is a viewing reserve below the unchanged90deg gimbal stop. This is an
approach constraint only until independently observed metric motion is ready.
"""
from collections import deque
import math
import numpy as np
from .visual_acquisition import camera_geometry
from .hybrid_policy import heading_rotation

def observe(controller,observation,capture,prediction,probability):
    now=float(observation['image_delivery_time_s']);stamp=float(observation['image_capture_time_s'])
    samples=getattr(controller,'approach_bearing_samples',None)
    if samples is None:samples=controller.approach_bearing_samples=deque()
    pixel=(np.asarray(prediction[12:14])+1.)*[320.,180.]
    if not(observation['image_valid'] and observation['image_age_s']<=.25 and probability>=.8 and np.isfinite(pixel).all() and 8<pixel[0]<632 and 8<pixel[1]<352):return
    rotation,origin,focal,_=camera_geometry(capture,controller.calibration)
    Rc=heading_rotation(math.pi/2-capture['px4']['attitude_ned_rad'][2]);D=np.diag([1.,-1.,-1.])
    ray=rotation@np.array([(pixel[0]-320)/focal,-(pixel[1]-180)/focal,-1.]);world=Rc@D@ray;world/=np.linalg.norm(world)
    horizontal=float(np.linalg.norm(world[:2]))
    if world[2]>=-.02 or horizontal<.02:return
    mission=observation['mission']
    if 'water_datum_enu_m'not in mission or 'nominal_deck_height_above_water_m'not in mission:return
    plane=float(mission['water_datum_enu_m'])+float(mission['nominal_deck_height_above_water_m'])
    own=capture['px4'];position=np.asarray(own['position_enu_m'])+np.asarray(own['velocity_enu_m_s'])*float(own.get('position_age_s',0.))
    height=float((position+Rc@D@origin)[2])-plane
    if height<=.2:return
    elevation=math.atan2(-world[2],horizontal)
    if samples and (stamp<=samples[-1][0] or stamp-samples[-1][0]>.3):samples.clear()
    samples.append((stamp,elevation))
    while samples and stamp-samples[0][0]>.6:samples.popleft()
    controller.approach_view=dict(time=now,direction_world=world[:2]/horizontal,height=height,range=height*horizontal/-world[2],own_velocity=np.asarray(own['velocity_enu_m_s']).copy())

def limit(controller,action,observation,diagnostics):
    action=np.asarray(action,dtype=float).copy()
    if diagnostics.get('control_phase')not in ['visual_acquire','visual_reacquire','align','visual_approach','recover','match']:return action,diagnostics
    if diagnostics.get('view_alignment_required'):return action,diagnostics
    estimate=getattr(controller,'current_estimate',None)
    if diagnostics.get('pose_valid') and estimate is not None and estimate.get('motion_ready'):return action,diagnostics
    view=getattr(controller,'approach_view',None);now=float(observation['image_delivery_time_s'])
    if view is None or now-view['time']>.12:return action,diagnostics
    R=heading_rotation(math.pi/2-observation['px4']['attitude_ned_rad'][2]);D=np.diag([1.,-1.,-1.])
    direction=R.T[:2,:2]@view['direction_world'];direction[1]*=-1.
    requested=float(action[:2]@direction);samples=controller.approach_bearing_samples
    cap=.5;rate=None;boat_radial=None;closing=None
    if len(samples)>=5 and samples[-1][0]-samples[0][0]>=.159:
        t=np.asarray([s[0]-samples[-1][0]for s in samples]);angles=np.asarray([s[1]for s in samples])
        rate=float(np.polyfit(t,angles,1)[0]);h=view['height'];r=view['range']
        sensitivity=h/max(h*h+r*r,1e-9)
        vertical_rate=float(view['own_velocity'][2])*r/max(h*h+r*r,1e-9)
        own_radial=float(view['own_velocity'][:2]@view['direction_world'])
        boat_radial=float(np.clip(own_radial-(rate-vertical_rate)/max(sensitivity,.001),-3.,3.))
        reserve=h/math.tan(math.radians(65.));distance=max(0.,r-reserve)
        acceleration=.6;reaction=.4
        closing=math.sqrt((acceleration*reaction)**2+2*acceleration*distance)-acceleration*reaction
        cap=float(np.clip(boat_radial+closing,-2.,2.))
    changed=requested>cap
    if changed:action[:2]+=(cap-requested)*direction
    length=np.linalg.norm(action[:2])
    if length>2.:action[:2]*=2./length
    diagnostics.update(approach_stopping_envelope_active=True,approach_stopping_limited=bool(changed),approach_radial_speed_cap_m_s=cap,approach_world_elevation_rate_rad_s=rate,approach_inferred_boat_radial_m_s=boat_radial,approach_allowed_closing_m_s=closing,approach_plane_prior_range_m=view['range'],approach_braking_budget_m_s2=.6,approach_reaction_allowance_s=.4,approach_motion_handoff_initialized=bool(estimate is not None and estimate.get('motion_ready')))
    return action,diagnostics
'''
(controller/'approach_envelope.py').write_text(module);compile(module,'approach_envelope.py','exec')
p=controller/'marker_policy.py';s=p.read_text();s='from .approach_envelope import observe as observe_approach, limit as limit_approach\n'+s
a='    def reset(self):\n        super().reset()';assert s.count(a)==2
# Reset the controller observer independently of the policy-level reset.
s=s.replace(a,a+"\n        self.approach_bearing_samples=None;self.approach_view=None",1)
a='    def act(self, estimate, observation):';assert s.count(a)==1
s=s.replace(a,"    def finish(self,action,observation,diagnostics):\n        action,diagnostics=limit_approach(self,action,observation,diagnostics)\n        return super().finish(action,observation,diagnostics)\n\n"+a)
a="        age = float(observation['image_age_s'])";assert s.count(a)==1
s=s.replace(a,a+'\n        observe_approach(self.controller,observation,capture,p,probability)')
p.write_text(s);compile(s,str(p),'exec')
c=json.loads((dest/'policy.json').read_text());c.update(reliability_qualified=False,closed_loop_evaluated=False,automatic_deployment=False)
c['hardening_r13']=dict(parent_policy_sha256=hashlib.sha256((source/'policy.json').read_bytes()).hexdigest(),cause='R12 braking begins too late relative to measured command slew and aircraft response; brief metric handoff bypasses acquisition constraint before visual motion is initialized.',change='Shared observed-bearing stopping-distance envelope before the existing single guard pass, through uninitialized metric handoff; no fixed following distance, descent permission, scoring or physics change.',braking_budget_m_s2=.6,reaction_allowance_s=.4,new_training=False,qualification_unestablished=True)
c['file_hashes']={p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.rglob('*')if p.is_file()and p.name!='policy.json'}
(dest/'policy.json').write_text(json.dumps(c,indent=2)+'\n')
plan=json.loads((ROOT/'r12_pilot5_plan.json').read_text());plan['cases']=[q for q in plan['cases']if q['source_case']in ['freshD_city_05','freshD_beach_10']]
(ROOT/'r13_approach2_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'candidate_sha256':hashlib.sha256((dest/'policy.json').read_bytes()).hexdigest(),'targeted_cases':len(plan['cases'])}))
