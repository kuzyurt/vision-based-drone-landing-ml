"""Diagnose rejected registrations on existing RGB; no new flight or training."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import collections,inspect,json,sys,time
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
sys.path.insert(0,str(BASE));import landing_training
landing_training.__path__.insert(0,str(ROOT/'bundle_spatial_r5/code/landing_training'))
from landing_training.radio_robust_20261015.controller import marker_geometry_fast
original=marker_geometry_fast.marker_pose_fast
source=inspect.getsource(original);gate=[0]
while 'return None' in source:
    gate[0]+=1;source=source.replace('return None',f"return reject('gate_{gate[0]}',locals())",1)
current_t=0.;rejections=[]
def reject(gate,values):
    if current_t>=80.:
        d=dict(time=current_t,gate=gate)
        for k in ['prior_distance','rms','lower','upper','precision','recall','singular','center_pixel','pixel','result','prior','normal','angle','v']:
            if k in values:
                a=np.asarray(values[k]);d[k]=float(a) if a.ndim==0 else a.tolist()
        rejections.append(d)
    return None
namespace=dict(original.__globals__,reject=reject);exec(compile(source,__file__,'exec'),namespace)
marker_geometry_fast.marker_pose_fast=namespace['marker_pose_fast']
from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
torch.set_num_threads(1);bundle=ROOT/'bundle_spatial_r5';config=json.loads((bundle/'policy.json').read_text())
runtime=RadioRobustRuntime(bundle/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
case=ROOT/'fresh_holdout_spatial_r5/fresh_beach_05_0_inland'
rows=[json.loads(x) for x in (case/'steps.jsonl').read_text().splitlines()];rows=[x for x in rows if not x.get('terminal') and x['task_time_s']<85.5]
started=time.monotonic();checks=[]
with h5py.File(case/'observations.h5','r') as h:
    for i,row in enumerate(rows):
        current_t=row['task_time_s'];obs=row['observation'];obs.pop('beacon',None)
        action,d=runtime.act(h['rgb'][i],obs)
        if current_t>=80.:
            checks.append(dict(time=current_t,recorded_phase=row['output']['learner_diagnostics']['control_phase'],replay_phase=d['control_phase'],
                recorded_metric=row['output']['learner_diagnostics']['metric_valid'],replay_metric=d['metric_valid'],acceptance=d['metric_acceptance']))
value=dict(status='completed_existing_rgb_diagnosis',frames=len(rows),wall_seconds=time.monotonic()-started,
    training=False,new_simulation=False,rejection_counts=dict(collections.Counter(x['gate'] for x in rejections)),rejections=rejections,checks=checks)
(ROOT/'r5_close_registration_diagnosis.json').write_text(json.dumps(value,indent=2))
print(json.dumps(dict(frames=len(rows),wall_seconds=value['wall_seconds'],rejection_counts=value['rejection_counts'],last_rejections=rejections[-4:]),indent=2))
