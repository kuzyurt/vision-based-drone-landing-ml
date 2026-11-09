"""Behavior invariant: a cooldown must not suppress a newly lost visual track."""
from pathlib import Path
import importlib,json,math,sys,types
import numpy as np
ROOT=Path(__file__).resolve().parent;bundle=ROOT/sys.argv[1]
pkg=types.ModuleType('cooldown_probe');pkg.__path__=[str(bundle/'code/landing_training/radio_robust_20261015/controller')];sys.modules[pkg.__name__]=pkg
m=importlib.import_module(pkg.__name__+'.marker_policy');c=json.loads((bundle/'policy.json').read_text())
def observation(t):
 return dict(px4=dict(valid=True,position_age_s=0.,attitude_age_s=0.,position_enu_m=[0.,0.,1.1],velocity_enu_m_s=[0.,0.,0.],attitude_ned_rad=[0.,0.,math.pi/2],angular_rate_frd_rad_s=[0.,0.,0.],armed=True,landed=False,gimbal_commanded_rad=[0.,math.radians(75)]),beacon=dict(valid=False,age_s=3.1),gimbal_rad=[0.,math.radians(75)],image_capture_time_s=t,image_delivery_time_s=t,image_age_s=0.,image_valid=True,decision_dt_s=.04,previous_executed_action=[0.]*6,mission=dict(elapsed_s=t,budget_s=180.,water_datum_enu_m=0.,nominal_deck_height_above_water_m=.45,coarse_height_uncertainty_m=.4,recovery_clearance=dict(valid=True,no_dynamic_boat_state=True,max_altitude_enu_m=10.5)))
p=m.MarkerPosePolicy(None,c['calibration'],c['slew_limits'],'cpu')
for i in range(25):
 t=i*.04;assert p.visual_memory.observe([.2,0.,.65],observation(t),t,normal_heading=[0,0,-1])
p.metric_time=.96;p.visibility_recovery.ever_confirmed=True;p.visibility_recovery.cooldown=5.
o=observation(1.2);p.controller.bearing_capture_observation=o;prediction=np.zeros(15)
first=p.visibility_recovery.decide(p,{},o,prediction,0.,None,True)
if '--expect-recovered' in sys.argv:
 assert first is not None and first[1]['control_phase']=='local_recovery' and first[0][2]<=0
 o=observation(1.24);p.controller.bearing_capture_observation=o
 second=p.visibility_recovery.decide(p,{},o,prediction,0.,None,True)
 assert second is not None and second[1]['control_phase']=='recovery_climb' and second[0][2]<0
 print(json.dumps(dict(bundle=bundle.name,cooldown_does_not_suppress_local_braking=True,existing_gate_starts_bounded_climb_before_margin_expires=True,new_flight=False)))
else:
 assert first is None;print(json.dumps(dict(bundle=bundle.name,cooldown_suppresses_local_loss_recovery=True,new_flight=False)))
