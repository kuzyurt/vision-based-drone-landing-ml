"""Inspect four existing validation RGB frames, without new simulation."""
import copy
import json
from pathlib import Path
import sys
import h5py
import numpy as np
import torch

root=Path(sys.argv[1]);bundle=root/'policy_bundle'
base=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(bundle/'code'))
from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
from landing_training.radio_robust_20261015.controller.visual_acquisition import paint_prior
from landing_training.radio_robust_20261015.controller.recording import numeric_observation
from landing_training.radio_robust_20261015.controller.marker_geometry import marker_pose_reference
config=json.loads((bundle/'policy.json').read_text());torch.set_num_threads(1)
runtime=RadioRobustRuntime(bundle/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
results=[]
for name in ['validation_0008_forward','validation_0498_forward','validation_0388_forward','validation_0138_forward']:
    with h5py.File(base/'landing_training/datasets/expert'/name/'observations.h5','r') as f:
        rgb=np.array(f['rgb'][100]);obs=json.loads(f['steps'][100])['observation']
        capture_index=100-round(obs['image_age_s']/.04)
        capture=json.loads(f['steps'][capture_index])['observation']
    obs['beacon']={'valid':False,'age_s':3.1,'dock_ready':False}
    capture['beacon']=copy.deepcopy(obs['beacon'])
    numeric=torch.from_numpy(numeric_observation({'observation':obs}))[None,None].cuda()
    numeric[...,22]=runtime.model.backbone.observation_mean[22]
    with torch.no_grad():
        p=runtime.model(torch.from_numpy(rgb).permute(2,0,1)[None,None].cuda(),numeric,None,
                        numeric.new_tensor([100.,10.]).reshape(1,1,2))[0][0,0].cpu().numpy()
    est={'relative_position':p[1:4],'relative_velocity':p[4:7],'heading_pair':p[7:9],
         'normal':p[9:12],'visibility':float(1/(1+np.exp(-p[0]))),'_image_pixel':(p[12:14]+1)*[320,180]}
    seed=paint_prior(rgb,capture,config['calibration'],est)
    fit=None if seed is None else marker_pose_reference(rgb,capture,config['calibration'],seed)
    result=dict(name=name,seed=None if seed is None else seed['relative_position'].tolist(),
                fit=None if fit is None else fit['relative_position'].tolist())
    results.append(result);print(json.dumps(result),flush=True)
(root/'recorded_frame_diagnosis.json').write_text(json.dumps(results,indent=2))
