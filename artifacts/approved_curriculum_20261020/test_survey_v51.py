from pathlib import Path
import json,math,sys,types,shutil
import numpy as np
R=Path(__file__).parent;S=R/'search_v48/sources';sys.path.insert(0,str(S))
# Test new pure component in an isolated package, without touching evaluated sources.
package=types.ModuleType('survey_component_test');package.__path__=[str(R)];sys.modules[package.__name__]=package
spec=__import__('importlib.util',fromlist=['x']);oldspec=spec.spec_from_file_location('survey_component_test.inspection_feedback_v25',S/'target_learning/inspection_feedback_v25.py');old=spec.module_from_spec(oldspec);sys.modules[oldspec.name]=old;oldspec.loader.exec_module(old)
from survey_component_test.inspection_feedback_v51 import InspectionFeedback
from target_learning.protocol_elevation_v39 import SearchProtocol

def run(keep,completed=True):
 p=SearchProtocol();p.phase='reorient_candidate';p.selected=7;p.scan_completed=completed;p.scan_coverage=2*math.pi;p.scan_band=0
 f=InspectionFeedback();f.complete_scan_s=35. if keep else 0.;f.complete_scan_xy=np.zeros(2);f.last_forward=np.array([0.,0.,-1.]);f.last_time=39.96
 info={}
 for k in range(28):
  state=types.SimpleNamespace(time_s=40+k*.04,frame_id=k,image_fresh=True,own_state_fresh=True,airborne=True,landed=False,own_motion_settled=True)
  info=f.observe(p,state,[types.SimpleNamespace(track_id=7,age_s=1.)],point_world=np.array([0.,0.,-10.]),camera_world=np.zeros(3),camera_to_world=np.eye(3),focal_px=400.,own_xy=np.zeros(2),fresh_detections=[],own_angular_speed_rad_s=0.)
  if info.get('retired'):break
 return p,info
p,a=run(False);assert a['retired']and a['next_band']==1 and p.scan_band==1 and not p.scan_completed and p.survey_epoch==1 and p.scan_coverage==0.
p,b=run(True);assert b['retired']and b['completed_scan_retained']and p.scan_band==0 and p.survey_epoch==0
p,c=run(False,False);assert c['retired']and not c.get('actual_completed_survey_transition')and p.scan_band==0
report=dict(status='passed',new_survey=a,retained_survey=b,incomplete_survey=c,scope='Unit causal transition only; no physical improvement claim',first_known_far_counterfactual_task_s=38.2)
(R/'survey_component_test_v51.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
