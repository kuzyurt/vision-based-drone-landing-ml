"""Baseline spatial predictions on MuJoCo pilot images, no training/teacher use."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import hashlib,importlib,json,sys,time,types
import numpy as np,torch
from PIL import Image
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
BUNDLE=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z/candidate_r15'
sys.path.insert(0,str(BASE))
pkg=types.ModuleType('discrimination_baseline');pkg.__path__=[str(BUNDLE/'code/landing_training')];sys.modules[pkg.__name__]=pkg
runtime=importlib.import_module(pkg.__name__+'.radio_robust_20261015.runtime')
spatial=importlib.import_module(pkg.__name__+'.radio_robust_20261015.spatial_acquisition')

def main():
    torch.set_num_threads(1);start=time.monotonic();dest=ROOT/'frozen_vision_probe_v1.json';assert not dest.exists()
    c=json.loads((BUNDLE/'policy.json').read_text());policy=runtime.RadioRobustRuntime(BUNDLE/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
    source=ROOT/'scene_pilot_v1';report=json.loads((source/'report.json').read_text());rows=[]
    with torch.inference_mode():
        for f in report['frames']:
            rgb=np.asarray(Image.open(source/(f['name']+'.png')));x=torch.from_numpy(rgb.copy()).permute(2,0,1)[None].cuda()
            fine,context=spatial.encode_spatial(policy.model.backbone,x)
            logit,pixel=spatial.decode_spatial(policy.acquisition(fine,context));p=float(logit.sigmoid()[0]);xy=pixel[0].cpu().numpy()
            with np.load(source/(f['name']+'_masks.npz'))as masks:
                u,v=np.round(xy).astype(int);hit=[]
                if 0<=u<640 and 0<=v<360:
                    hit=[name for name in masks.files if bool(masks[name][v,u])]
                # A centre inside a bbox is tracked separately: hull cavities
                # and a pad opening do not necessarily have foreground pixels.
                boxes=[name for name,b in f['boxes'].items()if b and b[0]<=xy[0]<b[2] and b[1]<=xy[1]<b[3]]
            rows.append(dict(name=f['name'],subject=f['subject'],distance_m=f['horizontal_distance_m'],
                visibility_probability=p,pixel=xy.tolist(),visible_mask_hit=hit,bbox_hit=boxes,
                actual_target_visible_pixels=f['counts']['target'],rgb_sha256=f['rgb_sha256']))
    output=dict(status='baseline_probe_completed',wall_s=time.monotonic()-start,frames=len(rows),predictions=rows,
        no_training=True,full_resolution_input=[640,360],spatial_fine=list(fine.shape),spatial_context=list(context.shape),
        interpretation='Existing single-point acquisition has no separate generic-boat/target-identity output. Confidence is not calibrated identity.',
        source_runtime_sha256=hashlib.sha256((BUNDLE/'code/landing_training/radio_robust_20261015/runtime.py').read_bytes()).hexdigest())
    dest.write_text(json.dumps(output,indent=2));print(json.dumps({k:v for k,v in output.items()if k!='predictions'},indent=2),flush=True)

if __name__=='__main__':main()
