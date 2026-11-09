"""Isolate controller portability from recursive native/WASM fitter drift."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
from pathlib import Path
import copy, importlib, json, sys, types
import numpy as np
ROOT=Path(__file__).resolve().parent
bundle=ROOT/'candidate_r7'
pkg=types.ModuleType('fixed_fit_portability')
pkg.__path__=[str(bundle/'code/landing_training/radio_robust_20261015')]
sys.modules[pkg.__name__]=pkg
importlib.import_module(pkg.__name__+'.native_marker').install(pkg.__name__)
importlib.import_module(pkg.__name__+'.runtime_fixes').install(pkg.__name__)
mod=importlib.import_module(pkg.__name__+'.controller.marker_policy')
c=json.loads((bundle/'policy.json').read_text())
p=mod.MarkerPosePolicy(None,c['calibration'],c['slew_limits'],'cpu')
p.reset();p.controller.visual_search_started=None
original=mod.marker_pose
captured=[]
def clean(v):
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
    if isinstance(v,(np.ndarray,list,tuple)):return [clean(x) for x in v]
    if isinstance(v,np.generic):return v.item()
    return v
def marker(*args,**kwargs):
    fit=original(*args,**kwargs);captured.append(clean(fit));return fit
mod.marker_pose=marker
frames=json.loads((ROOT/'r7_browser_fixtures/neural.json').read_text())
result=[]
for i,f in enumerate(frames):
    captured.clear();o=copy.deepcopy(f['observation'])
    o['beacon'].update(valid=False,relative_heading_m=[0.]*3,velocity_heading_m_s=[0.]*3,age_s=3.1)
    pred=np.asarray(f['prediction'],dtype=np.float32);v=pred[:15].copy()
    if p.metric_time is None or o['image_delivery_time_s']-p.metric_time>.5:
        v[0]=pred[15];v[12:14]=pred[16:18]
    rgb=np.fromfile(ROOT/'r7_browser_fixtures'/f'rgb-{i}.bin',dtype=np.uint8).reshape(360,640,3)
    action,diag=p.act(rgb,o,v)
    assert max(abs(action-np.asarray(f['reference_action'])))<1e-12
    result.append(dict(frame=i,marker_calls=copy.deepcopy(captured)))
out=ROOT/'r7_fixed_fit_controller_fixtures.json'
assert not out.exists();out.write_text(json.dumps(result),encoding='utf-8')
print(json.dumps(dict(frames=len(result),fit_requests=sum(len(x['marker_calls']) for x in result),scope='Frozen RGB fits for controller-only portability; separate real-RGB fitter drift and closed-loop checks remain required.')))
