"""Read recorded sensor pixels; instrument fitter rejection without a new flight."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import collections,importlib,inspect,json,select,sys,types
import h5py,numpy as np,torch
from PIL import Image
ROOT=Path(__file__).resolve().parent
try:
    fd=os.pidfd_open(383081)
except ProcessLookupError:
    fd=None
if fd is not None:
    ready,_,_=select.select([fd],[],[],1200);os.close(fd)
    if not ready:raise RuntimeError('Owned diagnostic flight did not finish within20minutes')
report=json.loads((ROOT/'r7_city08_collision_diagnostic/report.json').read_text())
assert report['status']=='completed'
case=ROOT/'r7_city08_collision_diagnostic/freshC_city_08'
out=ROOT/'r7_city08_rgb_causal_audit';out.mkdir(exist_ok=False)
bundle=ROOT/'candidate_r7';pkg=types.ModuleType('pixel_gate_audit')
pkg.__path__=[str(bundle/'code/landing_training')];sys.modules[pkg.__name__]=pkg
module=importlib.import_module(pkg.__name__+'.radio_robust_20261015.controller.marker_geometry_fast')
source=inspect.getsource(module.marker_pose_fast)
gates=[]
lines=source.splitlines()
for i,line in enumerate(lines):
    if 'return None' in line:
        gate=line.strip().split(':return None')[0]
        gates.append(gate)
        lines[i]=line.replace('return None',f'return _rejected({len(gates)-1},locals())')
events=[]
def rejected(index,variables):
    o=variables['observation'];elapsed=o['mission']['elapsed_s']
    if elapsed>=70:
        fields={}
        for key in ['pixel','prior_distance','cam','normal','prior','rms','singular','center_pixel','precision','recall','result','info']:
            value=variables.get(key)
            if value is not None:fields[key]=np.asarray(value).tolist()
        events.append(dict(task_s=elapsed,gate=gates[index],values=fields))
    return None
namespace=dict(module.marker_pose_fast.__globals__,_rejected=rejected)
exec(compile('\n'.join(lines),str(Path(__file__)),'exec'),namespace)
module.marker_pose_fast=namespace['marker_pose_fast']
runtime=importlib.import_module(pkg.__name__+'.radio_robust_20261015.runtime')
c=json.loads((bundle/'policy.json').read_text());torch.set_num_threads(1)
p=runtime.RadioRobustRuntime(bundle/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
targets=[76.,79.,80.4,80.6,81.];images=[];phase_errors=[]
with h5py.File(case/'observations.h5') as f:
    for i in range(len(f['steps'])):
        row=json.loads(f['steps'][i])
        if row.get('terminal'):continue
        rgb=np.asarray(f['rgb'][i],dtype=np.uint8)
        action,diag=p.act(rgb,row['observation'])
        expected=row['output']['learner_diagnostics']['control_phase']
        if diag['control_phase']!=expected:phase_errors.append(dict(frame=i,expected=expected,replay=diag['control_phase']))
        elapsed=row['task_time_s']
        for target in targets[:]:
            if abs(elapsed-target)<.021:
                name=f'camera_{target:.1f}s.png';Image.fromarray(rgb).save(out/name);images.append(name);targets.remove(target)
receipt=dict(scope='Read-only replay of actual onboard RGB/own telemetry; native fitter rejection paths instrumented. No new simulation/rendering, training or task truth input.',
    observed_outcome=report['results'][0]['outcome'],fitter_rejections=dict(collections.Counter(x['gate'] for x in events)),
    rejected_frames=events,replay_phase_mismatch_count=len(phase_errors),replay_phase_mismatches=phase_errors,actual_sensor_images=images)
(out/'diagnosis.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps({k:v for k,v in receipt.items() if k not in ['rejected_frames','replay_phase_mismatches']}))
