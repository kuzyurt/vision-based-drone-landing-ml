"""Actual recorded impossible fit, plus the controller's memory-update boundary."""
from pathlib import Path
import copy,importlib,json,math,sys,types
import numpy as np
ROOT=Path(__file__).resolve().parent;bundle=ROOT/'candidate_r6';pkg=types.ModuleType('physical_probe');pkg.__path__=[str(bundle/'code/landing_training/radio_robust_20261015/controller')];sys.modules[pkg.__name__]=pkg
context=importlib.import_module(pkg.__name__+'.physical_pose_context');module=importlib.import_module(pkg.__name__+'.marker_policy')
audit=json.loads((ROOT/'replay_r4_handoff_memory.json').read_text());item=next(x for x in audit['details'] if x['metric_acceptance']=='acquired')
rows=[json.loads(l) for l in (ROOT/'r4_extended8_development/near_low_camera_handoff/steps.jsonl').open()];o=rows[item['frame']]['observation'];bad=dict(relative_position=item['memory_relative_position'])
result=context.fit_height_context(bad,o);assert not result['compatible'];assert result['inferred_height_enu_m']<-7.
own=context.own_state(o);good=dict(relative_position=[0.,0.,own[0][2]-.45]);assert context.fit_height_context(good,o)['compatible']
with_wrong_radio=copy.deepcopy(o);with_wrong_radio['beacon'].update(valid=True,relative_heading_m=[20.,20.,20.]);assert context.fit_height_context(bad,with_wrong_radio)==result
stale=copy.deepcopy(o);stale['px4']['position_age_s']=1.;assert not context.fit_height_context(good,stale)['compatible']
invalid=copy.deepcopy(o);invalid['mission']['coarse_height_uncertainty_m']=float('nan');assert not context.fit_height_context(good,invalid)['compatible']
config=json.loads((bundle/'policy.json').read_text());policy=module.MarkerPosePolicy(None,config['calibration'],config['slew_limits'],'cpu')
module.marker_pose=lambda *args:bad
p=np.zeros(15,dtype=np.float32);p[0]=10.;p[1:4]=[3.,0.,3.];p[8]=1.;p[11]=-1.
action,diag=policy.act(np.zeros((360,640,3),dtype=np.uint8),o,p)
assert not diag['metric_valid'] and diag['metric_acceptance']=='inconsistent_declared_deck_height';assert policy.visual_memory.accepted==0
value=dict(status='passed',actual_recorded_fit=result,impossible_fit_blocked_before_memory_update=True,plausible_fit_compatible=True,wrong_radio_cannot_change_gate=True,scope='Read-only physical-context/controller boundary probe; no new flight')
(ROOT/'r6_physical_context_probe.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
