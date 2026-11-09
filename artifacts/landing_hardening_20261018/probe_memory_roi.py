"""Independent optical counterexample: remembered ROI must ignore bad detector XY."""
from pathlib import Path
import importlib,json,math,sys,types
import numpy as np
ROOT=Path(__file__).resolve().parent;bundle=ROOT/sys.argv[1]
pkg=types.ModuleType('roi_probe');pkg.__path__=[str(bundle/'code/landing_training/radio_robust_20261015/controller')];sys.modules[pkg.__name__]=pkg
m=importlib.import_module(pkg.__name__+'.marker_policy');geometry=importlib.import_module(pkg.__name__+'.visual_acquisition')
config=json.loads((bundle/'policy.json').read_text());policy=m.MarkerPosePolicy(None,config['calibration'],config['slew_limits'],'cpu')
def observation(t):
 return dict(px4=dict(valid=True,position_age_s=0.,attitude_age_s=0.,position_enu_m=[0.,0.,3.45],velocity_enu_m_s=[0.,0.,0.],attitude_ned_rad=[0.,0.,math.pi/2],angular_rate_frd_rad_s=[0.,0.,0.],armed=True,landed=False,gimbal_commanded_rad=[0.,math.radians(35)]),beacon=dict(valid=False,age_s=3.1),gimbal_rad=[0.,math.radians(35)],image_capture_time_s=t,image_delivery_time_s=t,image_age_s=0.,image_valid=True,decision_dt_s=.04,previous_executed_action=[0.]*6,mission=dict(elapsed_s=t,budget_s=180.,water_datum_enu_m=0.,nominal_deck_height_above_water_m=.45,coarse_height_uncertainty_m=.4))
r=np.array([3.,0.,3.])
for i in range(25):
 t=i*.04;assert policy.visual_memory.observe(r,observation(t),t,normal_heading=[0,0,-1])
policy.metric_time=.96;policy.visibility_recovery.ever_confirmed=True
now=1.56;o=observation(now);assert policy.visual_memory.estimate(o)['tracking_prior_valid']
rotation,origin,focal,_=geometry.camera_geometry(o,config['calibration']);ray=rotation.T@(r-origin)
expected=np.array([320+focal*ray[0]/-ray[2],180-focal*ray[1]/-ray[2]])
captured={}
def spy(rgb,observation,calibration,estimate):captured.update(estimate);return None
m.marker_pose=spy
p=np.zeros(15,dtype=np.float32);p[0]=-10.;p[1:4]=r;p[8]=1.;p[11]=-1.;p[12:14]=[-.8,0.]
action,diag=policy.act(np.zeros((360,640,3),dtype=np.uint8),o,p)
actual=np.asarray(captured['_image_pixel']);error=float(np.linalg.norm(actual-expected))
print(json.dumps(dict(bundle=bundle.name,expected_pixel=expected.tolist(),requested_pixel=actual.tolist(),pixel_error=error,remembered_roi_requested=diag['geometric_fit_requested_from_memory'],scope='Synthetic accepted-geometry memory and fixed calibration; no flight/boat-truth input')))
if '--expect-correct' in sys.argv:assert error<1e-6,error
else:assert error>100.,error
