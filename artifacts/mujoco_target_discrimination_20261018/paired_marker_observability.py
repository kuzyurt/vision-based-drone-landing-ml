"""Exact full-CAD marker counterfactuals, no actors/training/held-out images.

Hide only the actual marker paint geom. All hull parts, pose, camera, textures
and environment stay identical. This avoids the reduced-CAD clone shortcut.
"""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import importlib,json,math,sys,time
import mujoco,numpy as np,torch
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'landing_training/outputs/domain_training_20261016T134939Z'))
from target_learning.discriminator_v5 import Discriminator,decode
from target_learning.object_verifier import ObjectVerifier,verify
from target_learning.expert_adapter import load_parent
from target_learning.scenes import annotation_groups
from target_learning.label_renderer import install,identify_water
from landing_training import environment as em
from landing_training.config import Scenario
from usv.boat_sim import quaternion
import landing_training.rendering as rendering


def main():
    torch.set_num_threads(1);begin=time.monotonic();out=ROOT/'paired_marker_observability_v1';out.mkdir(exist_ok=False)
    model=mujoco.MjModel.from_binary_path(str(ROOT/'scene_cache_v2/seed_870000/scene.mjb'));em.compile_scene=lambda *a,**k:model
    env=em.Environment(Scenario(name='counterfactual_marker_support',kind='beach',seed=981100,world_seed=981101,path_seed=981102,distance=8.,height=4.,wave_height=.03))
    groups=annotation_groups(model)
    for name,gids in groups.items():
        if name!='target':model.geom_group[gids]=3
    marker=model.geom('LandingTarget_plain').id;old_group=int(model.geom_group[marker]);assert old_group<3
    install(rendering);r=rendering.ReviewRenderer(env,overview=False);append=r.append_water
    def water(scene):append(scene);identify_water(scene,env)
    r.append_water=water
    parent=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z/candidate_r15'
    module=load_parent(parent,'paired_marker_parent');config=json.loads((parent/'policy.json').read_text())
    runtime=module.RadioRobustRuntime(parent/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
    encode=importlib.import_module(module.__package__+'.spatial_acquisition').encode_spatial
    saved=torch.load(ROOT/'perception_training_v8/best.pt',map_location='cuda',weights_only=False)
    head=Discriminator().cuda();head.load_state_dict(saved['model']);head.eval();verifier=ObjectVerifier().cuda();verifier.load_state_dict(saved['verifier']);verifier.eval()
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14);sheet=Image.new('RGB',(1280,6*390),(15,20,28));records=[]
    with torch.inference_mode():
        for view,(distance,height)in enumerate([(.3,.7),(3.,4.),(6.,4.),(12.,4.),(25.,4.),(60.,4.)]):
            point=env.pad_position.copy();bearing=env.boat_yaw+2.3;position=point+[distance*math.cos(bearing),distance*math.sin(bearing),height]
            q=env.drone.free_qadr;env.data.qpos[q:q+3]=position;env.data.qpos[q+3:q+7]=quaternion(0,0,math.atan2(point[1]-position[1],point[0]-position[0]))
            env.data.qpos[env.drone.camera_qpos]=[0.,math.atan2(height,distance)];mujoco.mj_forward(model,env.data)
            pair=[]
            for column,present in enumerate([True,False]):
                model.geom_group[marker]=old_group if present else 3;rgb=r.onboard_image();pair.append(rgb)
                image=torch.from_numpy(rgb).permute(2,0,1)[None].cuda();fine,context=encode(runtime.model.backbone,image)
                predictions=decode({k:v.cpu()for k,v in head(fine,context).items()},minimum_presence=.2,topk=24)
                predictions=verify(verifier,fine,context,predictions)[0]
                im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
                for p in predictions:
                    x,y=p['pixel'];draw.text((x,y),f'H{p["presence"]:.2f} T{p["target_probability"]:.3f} U{p["unknown_probability"]:.2f}',font=font,fill='yellow')
                sheet.paste(im,(column*640,view*390));ImageDraw.Draw(sheet).text((column*640+3,view*390+364),f'{distance:g}m horiz / {height:g}m height | '+('marker PRESENT'if present else'ONLY marker hidden'),font=font,fill='white')
                records.append(dict(horizontal_distance_m=distance,height_above_pad_m=height,marker_present=present,predictions=predictions))
                Image.fromarray(rgb).save(out/f'view_{view}_{int(present)}.png')
            changed=np.max(np.abs(pair[0].astype(int)-pair[1].astype(int)),2)
            records[-1]['counterfactual_changed_pixels']=int((changed>0).sum());records[-1]['clearly_changed_pixels_over_20_levels']=int((changed>20).sum())
    r.close();sheet.save(ROOT/'paired_marker_observability_v1.jpg',quality=94)
    (ROOT/'paired_marker_observability_v1.json').write_text(json.dumps(dict(seconds=time.monotonic()-begin,records=records,
        teacher_actions=False,training_used=False,tidewater_used=False,heldout_used=False,only_mutation='marker paint geom visibility'),indent=2))
    print(json.dumps([dict(distance=r['horizontal_distance_m'],visible_changes=r['counterfactual_changed_pixels'])for r in records if not r['marker_present']]),flush=True)

if __name__=='__main__':main()
