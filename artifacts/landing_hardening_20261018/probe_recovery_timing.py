"""Does a fixed wait consume the remaining justified near-deck climb margin?"""
from pathlib import Path
import importlib,json,math,sys,types
import numpy as np
ROOT=Path(__file__).resolve().parent;bundle=ROOT/'candidate_r5a'
pkg=types.ModuleType('timing_probe');pkg.__path__=[str(bundle/'code/landing_training/radio_robust_20261015/controller')];sys.modules[pkg.__name__]=pkg
m=importlib.import_module(pkg.__name__+'.marker_policy');c=json.loads((bundle/'policy.json').read_text())
def observation(t):
 return dict(px4=dict(valid=True,position_age_s=0.,attitude_age_s=0.,position_enu_m=[0.,0.,1.1],velocity_enu_m_s=[0.,0.,0.],attitude_ned_rad=[0.,0.,math.pi/2],angular_rate_frd_rad_s=[0.,0.,0.],armed=True,landed=False,gimbal_commanded_rad=[0.,math.radians(75)]),beacon=dict(valid=False,age_s=3.1),gimbal_rad=[0.,math.radians(75)],image_capture_time_s=t,image_delivery_time_s=t,image_age_s=0.,image_valid=True,decision_dt_s=.04,previous_executed_action=[0.]*6,mission=dict(elapsed_s=t,budget_s=180.,water_datum_enu_m=0.,nominal_deck_height_above_water_m=.45,coarse_height_uncertainty_m=.4,recovery_clearance=dict(valid=True,no_dynamic_boat_state=True,max_altitude_enu_m=10.5)))
def controller():
 p=m.MarkerPosePolicy(None,c['calibration'],c['slew_limits'],'cpu')
 for i in range(25):
  t=i*.04;assert p.visual_memory.observe([.2,0.,.65],observation(t),t,normal_heading=[0,0,-1])
 p.metric_time=.96;p.visibility_recovery.ever_confirmed=True;return p
rows=[]
for age in [.2,.4,.5,2.2]:
 p=controller();o=observation(.96+age);own=importlib.import_module(pkg.__name__+'.persistent_target').own_state(o);memory=p.visual_memory.estimate(o)
 allowed=p.visibility_recovery._climb(o,own,o['image_delivery_time_s'],'timing_probe',{},memory)
 rows.append(dict(loss_age_s=age,sigma_m=memory['position_sigma_m'],above_deck_margin_m=memory['relative_position'][2]-.22-3*memory['position_sigma_m'],climb_justified_by_existing_gate=allowed))
assert rows[1]['climb_justified_by_existing_gate'] and not rows[-1]['climb_justified_by_existing_gate']
print(json.dumps(dict(scope='Synthetic previously measured near-deck target; existing confidence/clearance gates unchanged; no flight',timing=rows)))
