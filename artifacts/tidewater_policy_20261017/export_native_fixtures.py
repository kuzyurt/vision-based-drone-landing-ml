"""Read eight recorded camera observations; run the preserved native candidate."""
import importlib, json, sys, tarfile, types
from pathlib import Path
import h5py
import numpy as np
import torch

root=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/vision_first_fusion_20261017T184307Z')
out=root/'tidewater_browser_fixtures_20261017'
out.mkdir(exist_ok=True)
assert not any(out.iterdir()), 'Do not overwrite fixtures'
bundle=root/'candidate'
package=types.ModuleType('browser_gold');package.__path__=[str(bundle/'code/landing_training')];sys.modules['browser_gold']=package
runtime=importlib.import_module('browser_gold.radio_robust_20261015.runtime')
config=json.loads((bundle/'policy.json').read_text())
torch.set_num_threads(1)
p=runtime.RadioRobustRuntime(bundle/'pose.pt',config['calibration'],config['slew_limits'],'cpu',allow_visual_landing=True)
original=p.model.forward_features
def forward(*args,**kwargs):
    result=original(*args,**kwargs);p.browser_prediction=result[0].clone();return result
p.model.forward_features=forward
decode=p.decode_spatial
def spatial(*args):
    result=decode(*args);p.browser_spatial=result;return result
p.decode_spatial=spatial
frames=[]
with h5py.File(root/'repeat_flights/wrong_bias_5m_east/observations.h5') as f:
    print('datasets',[(k,f[k].shape) for k in f],flush=True)
    key='steps'
    # Separate recorded viewpoints exercise search, approach, metric fitting and
    # touchdown. Recurrent/controller states advance identically in both ports.
    indices=np.linspace(0,len(f['rgb'])-1,8).astype(int)
    for i,index in enumerate(indices):
        rgb=np.asarray(f['rgb'][index],dtype=np.uint8)
        observation=json.loads(f[key][index])['observation']
        action,diag=p.act(rgb,observation)
        presence,pixel=p.browser_spatial
        prediction=torch.cat((p.browser_prediction.flatten(),presence.flatten(),pixel.flatten()/pixel.new_tensor([320.,180.])-1.,p.model.last_fusion_weights.flatten()))
        rgb.tofile(out/f'rgb-{i}.bin');np.transpose(rgb,(2,0,1)).copy().tofile(out/f'image-{i}.bin')
        frames.append(dict(observation=observation,prediction=prediction.tolist(),next_hidden=p.hidden.flatten().tolist(),reference_action=action.tolist(),reference_phase=diag['control_phase'],metric_valid=diag.get('metric_valid'),source_frame=int(index),elapsed=float(observation['image_delivery_time_s'])-float(json.loads(f[key][indices[0]])['observation']['image_delivery_time_s'])))
(out/'neural.json').write_text(json.dumps(frames))
with tarfile.open(str(out)+'.tar.gz','w:gz') as archive:
    for file in out.iterdir():archive.add(file,arcname=file.name)
print('fixture_archive',str(out)+'.tar.gz',flush=True)
