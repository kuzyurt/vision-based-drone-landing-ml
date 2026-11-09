"""Freeze observed neural outputs/fits to isolate native/browser control math."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import copy,hashlib,importlib,json,sys,time,types
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;bundle=ROOT/'candidate_r14';out=ROOT/'r14_fixed_input_controller_fixtures.json';assert not out.exists()
pkg=types.ModuleType('r14_boundary_fixtures');pkg.__path__=[str(bundle/'code/landing_training')];sys.modules[pkg.__name__]=pkg
runtime=importlib.import_module(pkg.__name__+'.radio_robust_20261015.runtime')
marker=importlib.import_module(pkg.__name__+'.radio_robust_20261015.controller.marker_policy')
c=json.loads((bundle/'policy.json').read_text());torch.set_num_threads(1)
policy=runtime.RadioRobustRuntime(bundle/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
original_fit=marker.marker_pose;original_act=policy.controller.act
calls=[];captured=None
def clean(value):
    if isinstance(value,dict):return{k:clean(v)for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return[clean(v)for v in value]
    if isinstance(value,np.generic):return value.item()
    return value
def capture_fit(*args,**kwargs):
    result=original_fit(*args,**kwargs);calls.append(clean(result));return result
def capture_act(rgb,observation,prediction):
    global captured
    observation=copy.deepcopy(observation);prediction=np.asarray(prediction).copy()
    action,diag=original_act(rgb,observation,prediction)
    captured=dict(observation=observation,prediction=prediction.tolist(),marker_calls=copy.deepcopy(calls),expected_action=action.tolist(),expected_phase=diag['control_phase'],expected_recovery=diag.get('recovery_active'),expected_flags={k:diag.get(k)for k in ['approach_stopping_envelope_active','approach_stopping_limited','nearfield_persistent_velocity_used']})
    return action,diag
marker.marker_pose=capture_fit;policy.controller.act=capture_act
sequences=[];start=time.monotonic();active=near=0
for cohort,name,limit in [('approach_r2_cases2','freshD_city_05',12.),('near_motion_r2_gravel','freshD_gravel_05',62.)]:
    policy.reset();source=ROOT/cohort/name;rows=[json.loads(s)for s in (source/'steps.jsonl').open()];frames=[]
    with h5py.File(source/'observations.h5')as h:
        for q in rows:
            if q.get('terminal')or q['task_time_s']>limit:break
            assert time.monotonic()-start<240,'Bounded fixture preparation deadline'
            calls.clear();obs=copy.deepcopy(q['observation']);obs.pop('beacon',None)
            policy.act(np.asarray(h['rgb'][q['frame_index']],dtype=np.uint8),obs)
            captured['task_s']=q['task_time_s'];frames.append(captured)
            active+=bool(captured['expected_flags']['approach_stopping_limited']);near+=bool(captured['expected_flags']['nearfield_persistent_velocity_used'])
    sequences.append(dict(name=name,source_trace_sha256=hashlib.sha256((source/'steps.jsonl').read_bytes()).hexdigest(),frames=frames))
assert active>=12 and near>=100,(active,near)
value=dict(scope='Fixed observed NN predictions and accepted/rejected RGB-fit outputs for native/Pyodide controller portability only. Fit stubs are used only for this computation probe, never actual flights.',candidate_sha256=hashlib.sha256((bundle/'policy.json').read_bytes()).hexdigest(),sequences=sequences,limited_frames=active,near_velocity_frames=near,wall_s=time.monotonic()-start)
out.write_text(json.dumps(clean(value),separators=(',',':'))+'\n');print(json.dumps({'frames':[len(s['frames'])for s in sequences],'limited':active,'near':near,'wall_s':value['wall_s'],'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
