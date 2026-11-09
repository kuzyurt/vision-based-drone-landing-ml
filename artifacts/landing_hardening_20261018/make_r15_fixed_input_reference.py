"""Recompute only changed controller math on preserved fixed NN/RGB-fit inputs."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import copy,hashlib,importlib,json,sys,time,types
import numpy as np
r=Path(__file__).resolve().parent;bundle=r/'candidate_r15';out=r/'r15_fixed_input_controller_fixtures.json';assert not out.exists()
source=r/'r14_fixed_input_controller_fixtures.json';assert hashlib.sha256(source.read_bytes()).hexdigest()=='60eae669686d55ad84434c59dbc6f3e327c542ab054a238297bf4a6f6cbf4996'
fixture=json.loads(source.read_text());c=json.loads((bundle/'policy.json').read_text())
pkg=types.ModuleType('r15_fixed_controller');pkg.__path__=[str(bundle/'code/landing_training')];sys.modules[pkg.__name__]=pkg
mp=importlib.import_module(pkg.__name__+'.radio_robust_20261015.controller.marker_policy')
fix=importlib.import_module(pkg.__name__+'.radio_robust_20261015.runtime_fixes');fix.install(pkg.__name__+'.radio_robust_20261015')
calls=[]
def fixed_marker(*args,**kwargs):
    assert calls,'Unexpected marker request';value=calls.pop(0)
    return None if value is None else{k:np.asarray(v)if isinstance(v,list)else v for k,v in value.items()}
mp.marker_pose=fixed_marker
policy=mp.MarkerPosePolicy(None,c['calibration'],c['slew_limits'],'cpu');start=time.monotonic();terminal=limited=near=frames=0
for sequence in fixture['sequences']:
    policy.reset();policy.controller.visual_search_started=None
    for f in sequence['frames']:
        calls=list(f['marker_calls']);a,d=policy.act(None,copy.deepcopy(f['observation']),np.asarray(f['prediction'],dtype=np.float32));assert not calls
        f.update(expected_action=a.tolist(),expected_phase=d['control_phase'],expected_recovery=d.get('recovery_active'),expected_flags={k:d.get(k)for k in ['approach_stopping_envelope_active','approach_stopping_limited','nearfield_persistent_velocity_used']},expected_terminal_budget=d.get('nearfield_visibility_plan',{}).get('visibility_speed_limit_m_s'),expected_terminal_pause=d.get('nearfield_visibility_plan',{}).get('pause_descent'))
        terminal+=f['expected_terminal_budget']is not None;limited+=bool(d.get('approach_stopping_limited'));near+=bool(d.get('nearfield_persistent_velocity_used'));frames+=1
assert terminal>=100 and limited>=12 and near>=100
fixture.update(candidate_sha256=hashlib.sha256((bundle/'policy.json').read_bytes()).hexdigest(),scope='Controller-only native reference on preserved fixed NN predictions/accepted RGB fits. No neural rerun, renderer or flight; stubs confined to this computation boundary.',original_fixed_inputs_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),terminal_budget_frames=terminal,limited_frames=limited,near_velocity_frames=near,wall_s=time.monotonic()-start)
out.write_text(json.dumps(fixture,separators=(',',':'))+'\n');print(json.dumps({'frames':frames,'terminal':terminal,'limited':limited,'near':near,'wall_s':fixture['wall_s'],'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
