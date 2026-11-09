"""Actual full-runtime recorded RGB branch check; no flight claim."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import copy,importlib,json,sys,time,types
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;bundle=ROOT/'candidate_approach_r2';out=ROOT/'approach_r2_runtime_branch_probe.json';assert not out.exists()
pkg=types.ModuleType('approach_runtime_probe');pkg.__path__=[str(bundle/'code/landing_training')];sys.modules[pkg.__name__]=pkg
runtime=importlib.import_module(pkg.__name__+'.radio_robust_20261015.runtime');c=json.loads((bundle/'policy.json').read_text());torch.set_num_threads(1)
policy=runtime.RadioRobustRuntime(bundle/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
source=ROOT/'r13_approach2/freshD_city_05';rows=[json.loads(q)for q in (source/'steps.jsonl').open()];active=limited=frames=handoff=0;first=None;start=time.monotonic()
with h5py.File(source/'observations.h5')as h:
    for q in rows:
        if q.get('terminal')or q['task_time_s']>6.4:break
        obs=copy.deepcopy(q['observation']);obs.pop('beacon',None)
        action,diag=policy.act(np.asarray(h['rgb'][q['frame_index']],dtype=np.uint8),obs)
        assert np.isfinite(action).all()and np.linalg.norm(action[:2])<=2.+1e-8
        frames+=1;active+=bool(diag.get('approach_stopping_envelope_active'));limited+=bool(diag.get('approach_stopping_limited'));handoff+=bool(diag.get('pose_valid')and diag.get('approach_stopping_envelope_active'))
        if diag.get('approach_stopping_limited')and q['task_time_s']>3 and first is None:first=dict(task_s=q['task_time_s'],cap=diag['approach_radial_speed_cap_m_s'],phase=diag['control_phase'])
assert active>50 and limited>20 and handoff>0,(active,limited,handoff)
report=dict(status='passed',scope='Actual RadioRobustRuntime with neural inference and recorded RGB/own observations, not helper-only. Counterfactual decisions on recorded trajectory only; no flight claim.',frames=frames,active_frames=active,limited_frames=limited,initial_metric_handoff_constrained_frames=handoff,first_limited_after3s=first,wall_s=time.monotonic()-start)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
