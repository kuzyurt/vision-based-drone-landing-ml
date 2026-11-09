"""Actual recorded initial view-reset sequence for controller-port parity."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import importlib,json,sys,tarfile,types
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;bundle=ROOT/'candidate_r4';out=ROOT/'r4_browser_fixtures';out.mkdir(exist_ok=False)
package=types.ModuleType('browser_gold');package.__path__=[str(bundle/'code/landing_training')];sys.modules['browser_gold']=package
runtime=importlib.import_module('browser_gold.radio_robust_20261015.runtime');config=json.loads((bundle/'policy.json').read_text())
torch.set_num_threads(1);p=runtime.RadioRobustRuntime(bundle/'pose.pt',config['calibration'],config['slew_limits'],'cpu',allow_visual_landing=True)
original=p.model.forward_features
def forward(*args,**kwargs):
 result=original(*args,**kwargs);p.browser_prediction=result[0].clone();return result
p.model.forward_features=forward;decode=p.decode_spatial
def spatial(*args):
 result=decode(*args);p.browser_spatial=result;return result
p.decode_spatial=spatial;frames=[]
with h5py.File(ROOT/'r4_close2_development/near_front_low/observations.h5') as f:
 for i in range(12):
  rgb=np.asarray(f['rgb'][i],dtype=np.uint8);observation=json.loads(f['steps'][i])['observation']
  action,diag=p.act(rgb,observation);presence,pixel=p.browser_spatial
  prediction=torch.cat((p.browser_prediction.flatten(),presence.flatten(),pixel.flatten()/pixel.new_tensor([320.,180.])-1.,p.model.last_fusion_weights.flatten()))
  rgb.tofile(out/f'rgb-{i}.bin')
  frames.append(dict(observation=observation,prediction=prediction.tolist(),reference_action=action.tolist(),reference_phase=diag['control_phase'],metric_valid=diag.get('metric_valid'),recovery_active=diag.get('recovery_active'),guard_feedback=diag.get('guard_target_feedback_source'),elapsed=float(observation['mission']['elapsed_s'])))
assert any(f['recovery_active'] for f in frames),[f['reference_phase'] for f in frames]
assert all(f['guard_feedback']=='own_issued_command' for f in frames)
(out/'neural.json').write_text(json.dumps(frames))
with tarfile.open(str(out)+'.tar.gz','w:gz') as tar:
 for path in out.iterdir():tar.add(path,arcname=path.name)
source=ROOT/'candidate_r4';controller=source/'code/landing_training/radio_robust_20261015/controller';files=[source/'policy.json',controller.parent/'runtime_fixes.py']+[p for p in controller.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
with tarfile.open(ROOT/'candidate_r4_controller.tar.gz','w:gz') as tar:
 for path in files:tar.add(path,arcname=path.relative_to(source))
print(json.dumps(dict(frames=len(frames),phases=[f['reference_phase'] for f in frames],archive_bytes=(ROOT/'r4_browser_fixtures.tar.gz').stat().st_size)))
