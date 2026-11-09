"""Necessary one-frame and guard boundary checks; no new simulation/render."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import ast,copy,hashlib,importlib,json,math,sys
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2];BUNDLE=ROOT/'candidate_r2b'
sys.dont_write_bytecode=True;sys.path.insert(0,str(BASE));import landing_training
landing_training.__path__.insert(0,str(BUNDLE/'code/landing_training'))
for p in BUNDLE.rglob('*.py'):ast.parse(p.read_text())
config=json.loads((BUNDLE/'policy.json').read_text())
for name,expected in config['file_hashes'].items():assert hashlib.sha256((BUNDLE/name).read_bytes()).hexdigest()==expected,name
from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
from landing_training.radio_robust_20261015.controller.action_guard import ActionGuard
from landing_training.radio_robust_20261015.controller.supervision import supervise_action
torch.set_num_threads(1);p=RadioRobustRuntime(BUNDLE/'pose.pt',config['calibration'],config['slew_limits'],'cpu',allow_visual_landing=True)
with h5py.File(ROOT/'baseline_development/near_front_low/observations.h5','r') as h:
    observation=json.loads(h['steps'][0])['observation'];rgb=np.asarray(h['rgb'][0],dtype=np.uint8)
action,diag=p.act(rgb,observation);assert np.isfinite(action).all() and action.shape==(6,)
# Synthetic public-clearance branch probe, explicitly not a physical flight.
o=copy.deepcopy(observation);o['mission']['recovery_clearance']=dict(valid=True,no_dynamic_boat_state=True,max_altitude_enu_m=10.5)
p.controller.visibility_recovery.start=float(o['image_delivery_time_s'])-9.
recovery_action,recovery_diag=p.act(rgb,o)
assert recovery_diag['control_phase']=='recovery_climb' and recovery_action[2]<0,recovery_diag
o['mission']['recovery_clearance']['max_altitude_enu_m']=o['px4']['position_enu_m'][2]+.1
revoked_action,revoked_diag=p.act(rgb,o)
assert revoked_diag['control_phase']=='recovery_scan' and revoked_action[2]==0,revoked_diag
guard=ActionGuard();target=math.radians(60);encoder=math.radians(80)
for _ in range(100):
    o=dict(decision_dt_s=.04,gimbal_rad=[0.,encoder],gimbal_commanded_rad=[0.,target],image_valid=True)
    command=np.zeros(6);command[5]=math.radians(40)
    actual,d=guard.apply(command,o,dict(pad_visibility_probability=1.));target+=actual[5]*.04;encoder=target
assert abs(math.degrees(encoder)-90)<1e-8
assert d['guard_target_feedback_source']=='own_issued_command'
o=copy.deepcopy(observation);o['mission']['recovery_clearance']=dict(valid=True,no_dynamic_boat_state=True,max_altitude_enu_m=o['px4']['position_enu_m'][2]+.1)
climb=np.array([.1,.1,-.4,0,0,0]);bounded,reason=supervise_action(climb,o,10.,180.)
assert bounded[2]==0 and reason=='mapped_vertical_clearance'
o['px4']['position_age_s']=1.;bounded,reason=supervise_action(np.ones(6)*.1,o,10.,180.)
assert np.array_equal(bounded[:4],np.zeros(4)) and reason=='estimator_unavailable_or_stale'
value=dict(status='passed',scope='AST/source hashes, one actual RGB frame, actual corrected gimbal guard handoff, mapped ascent veto and stale-estimator body-command suppression',initial_phase=diag['control_phase'],new_training=False,new_flight=False)
(ROOT/'r2_preflight.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
