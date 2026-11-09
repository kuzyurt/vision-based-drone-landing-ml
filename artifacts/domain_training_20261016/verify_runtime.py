"""Brief recorded-frame parity and runtime-hook check; no new flights."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import copy,json,sys,time
from pathlib import Path
import numpy as np
import h5py,torch
ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE));import landing_training
landing_training.__path__.append(str(ROOT/'policy_bundle/code/landing_training'))
from landing_training.radio_robust_20261015.runtime import RadioRobustRuntime
from landing_training.radio_robust_20261015.controller.visual_acquisition import paint_prior
from landing_training.radio_robust_20261015.controller.recording import numeric_observation
from landing_training.radio_robust_20261015.controller.marker_geometry import marker_pose_reference
import native_marker,runtime_fixes
torch.set_num_threads(1)
config=json.loads((ROOT/'policy_bundle/policy.json').read_text())
runtime=RadioRobustRuntime(ROOT/'policy_bundle/pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
native=native_marker.install();runtime_fixes.install()
results=[]
for name in ['validation_0008_forward','validation_0498_forward','validation_0388_forward','validation_0138_forward']:
    with h5py.File(BASE/'landing_training/datasets/expert'/name/'observations.h5') as f:
        rgb=np.array(f['rgb'][100]);obs=json.loads(f['steps'][100])['observation']
        capture=json.loads(f['steps'][100-round(obs['image_age_s']/.04)])['observation']
    obs['beacon']={'valid':False,'age_s':3.1,'dock_ready':False};capture['beacon']=copy.deepcopy(obs['beacon'])
    numeric=torch.from_numpy(numeric_observation({'observation':obs}))[None,None].cuda()
    numeric[...,22]=runtime.model.backbone.observation_mean[22]
    with torch.inference_mode():
        p=runtime.model(torch.from_numpy(rgb).permute(2,0,1)[None,None].cuda(),numeric,None,numeric.new_tensor([100.,10.]).reshape(1,1,2))[0][0,0].cpu().numpy()
    estimate=dict(relative_position=p[1:4],relative_velocity=p[4:7],heading_pair=p[7:9],normal=p[9:12],visibility=float(1/(1+np.exp(-p[0]))),_image_pixel=(p[12:14]+1)*[320,180])
    seed=paint_prior(rgb,capture,config['calibration'],estimate)
    start=time.perf_counter();reference=None if seed is None else marker_pose_reference(rgb,capture,config['calibration'],seed);reference_s=time.perf_counter()-start
    start=time.perf_counter();fast=native(rgb,capture,config['calibration'],estimate);native_s=time.perf_counter()-start
    error=None if reference is None or fast is None else float(np.max(np.abs(reference['relative_position']-fast['relative_position'])))
    assert reference is not None and fast is not None and error<1e-4,(name,error)
    runtime.reset();action,diagnostics=runtime.act(rgb,obs)
    assert np.isfinite(action).all()
    results.append(dict(name=name,position_max_error_m=error,reference_s=reference_s,native_s=native_s,phase=diagnostics['control_phase']))
    print(json.dumps(results[-1]),flush=True)
(ROOT/'runtime_equivalence.json').write_text(json.dumps(dict(passed=True,frames=results),indent=2))
from PIL import Image
images=[]
for name,index in [('training_beach_00_0',100),('training_island_01_0',30)]:
    with h5py.File(ROOT/'dataset'/name/'observations.h5') as f:images.append(Image.fromarray(np.array(f['rgb'][min(index,len(f['rgb'])-1)])))
canvas=Image.new('RGB',(1280,360));canvas.paste(images[0],(0,0));canvas.paste(images[1],(640,0));canvas.save(ROOT/'visual_preview.jpg')
