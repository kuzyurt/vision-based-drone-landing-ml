"""New MuJoCo developmental distractors: blank-pad clone, false cross and buoy."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
from copy import deepcopy
import json,math,sys,time,xml.etree.ElementTree as ET
import mujoco,numpy as np,torch
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'landing_training/outputs/domain_training_20261016T134939Z'))
from landing_training import paths
from landing_training import environment as env_module
from landing_training.config import Scenario
from landing_training.rendering import ReviewRenderer
from usv.boat_sim import quaternion
from target_learning.scenes import add_boat,annotation_groups
from target_learning.label_renderer import install,identify_water
from target_learning.discriminator import Discriminator,decode
import landing_training.rendering as rendering

def add_cross(body,z):
    for name,size in [('a','.13 .015 .002'),('b','.015 .13 .002')]:
        ET.SubElement(body,'geom',name=body.get('name')+'_false_cross_'+name,type='box',pos=f'0 0 {z}',size=size,
            rgba='.02 .8 .8 1',contype='0',conaffinity='0',group='0')

def compile_hard(out):
    # Clone static nominal CAD frames, not a moving target state. Original mesh
    # assets stay shared; its docking joints are frozen at the reviewed setup.
    source=ROOT/'scene_cache_v2/seed_870000/scene.xml';xml=ET.parse(source).getroot()
    base=mujoco.MjModel.from_binary_path(str(source.with_suffix('.mjb')));d=mujoco.MjData(base)
    for name,value in [('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)]:d.qpos[base.jnt_qposadr[base.joint(name).id]]=value
    mujoco.mj_forward(base,d);boat=base.body('boat').id;rotation=d.xmat[boat].reshape(3,3)
    lookup={g.get('name'):g for g in xml.iter('geom')if g.get('name')};world=xml.find('worldbody')
    clone=ET.SubElement(world,'body',name='decoy_blank_clone',mocap='true',pos='6 -5 .03');children={}
    for gid in annotation_groups(base)['target']:
        if base.geom_group[gid]not in (0,5):continue
        bid=int(base.geom_bodyid[gid]);name=base.body(bid).name
        if bid not in children:
            pos=rotation.T@(d.xpos[bid]-d.xpos[boat]);R=rotation.T@d.xmat[bid].reshape(3,3);q=np.empty(4);mujoco.mju_mat2Quat(q,R.ravel())
            children[bid]=ET.SubElement(clone,'body',name='hard_clone_part_'+name,pos=' '.join(map(str,pos)),quat=' '.join(map(str,q)))
        g=deepcopy(lookup[base.geom(gid).name]);g.set('name','hard_clone_'+g.get('name'))
        if base.geom(gid).name=='LandingPlatform_textured':g.set('material','LandingPlatform_plain_mat')
        children[bid].append(g)
    b=add_boat(world,xml.find('asset'),'decoy_false_cross_boat',[-6,3,.03],[.85,.86,.83],cabin=False)
    add_cross(b,.231)
    board=ET.SubElement(world,'body',name='decoy_false_cross_board',mocap='true',pos='-3 -5 .12')
    ET.SubElement(board,'geom',name='false_board',type='box',size='.35 .35 .03',rgba='.9 .93 .93 1',contype='8',conaffinity='2')
    add_cross(board,.033)
    path=out/'hard_scene.xml';path.write_text(ET.tostring(xml,encoding='unicode'))
    model=mujoco.MjModel.from_xml_path(str(path));mujoco.mj_saveModel(model,str(out/'hard_scene.mjb'));return model

def main():
    torch.set_num_threads(1);out=ROOT/'hard_scene_probe_v2';out.mkdir(exist_ok=False);begin=time.monotonic()
    model=compile_hard(out);env_module.compile_scene=lambda *a,**k:model
    env=env_module.Environment(Scenario(name='hard_object_probe',kind='beach',world_seed=980101,path_seed=980102,seed=980100,distance=8.,height=4.,wave_height=.03))
    groups=annotation_groups(model)
    for name in groups:
        if name=='target':continue
        mid=int(model.body_mocapid[model.body(name).id]);env.data.mocap_pos[mid,:2]+=env.pad_position[:2]
    # This source is developmental data. True boat hidden so accepted identities
    # anywhere in these frames would be false cold-start target confirmations.
    model.geom_group[groups['target']]=3;mujoco.mj_forward(model,env.data);install(rendering)
    r=ReviewRenderer(env,overview=False);original=r.append_water
    def append(scene):original(scene);identify_water(scene,env)
    r.append_water=append
    saved=torch.load(ROOT/'perception_training_v4/best.pt',map_location='cuda',weights_only=False)
    head=Discriminator().cuda();head.load_state_dict(saved['model']);head.eval()
    from target_learning.expert_adapter import load_parent
    bundle=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z/candidate_r15'
    module=load_parent(bundle,'hard_object_baseline');c=json.loads((bundle/'policy.json').read_text())
    runtime=module.RadioRobustRuntime(bundle/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
    spatial=__import__(module.__package__+'.spatial_acquisition',fromlist=['encode_spatial'])
    records=[];font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
    sheet=Image.new('RGB',(1280,3*396),(15,21,30))
    with torch.inference_mode():
        i=0
        for subject in ['decoy_blank_clone','decoy_false_cross_boat','decoy_false_cross_board']:
            point=env.data.xpos[model.body(subject).id]+[0,0,.25]
            for distance in [4.,10.]:
                bearing=env.boat_yaw;position=point+[distance*math.cos(bearing),distance*math.sin(bearing),4.]
                q=env.drone.free_qadr;env.data.qpos[q:q+3]=position;yaw=math.atan2(point[1]-position[1],point[0]-position[0])
                env.data.qpos[q+3:q+7]=quaternion(0,0,yaw);env.data.qpos[env.drone.camera_qpos]=[0.,math.atan2(4.,distance)]
                mujoco.mj_forward(model,env.data);rgb=r.onboard_image();Image.fromarray(rgb).save(out/f'{subject}_{distance:.0f}m.png')
                x=torch.from_numpy(rgb).permute(2,0,1)[None].cuda();fine,context=spatial.encode_spatial(runtime.model.backbone,x)
                pred=decode({k:v.cpu()for k,v in head(fine,context).items()},minimum_presence=.1,topk=24)[0]
                im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
                for p in pred:
                    if p['boat']and p['presence']>=.2:
                        x,y=p['pixel'];draw.ellipse((x-3,y-3,x+3,y+3),fill='yellow');draw.text((x+4,y),f'H{p["presence"]:.2f}/ID{p["target_probability"]:.2f}',font=font,fill='yellow')
                sx=(i%2)*640;sy=(i//2)*396;sheet.paste(im,(sx,sy));ImageDraw.Draw(sheet).text((sx+4,sy+364),f'{subject} {distance:.0f}m | TRUE TARGET ABSENT',font=font,fill='white');i+=1
                records.append(dict(subject=subject,distance_m=distance,target_absent=True,predictions=pred))
    r.close();sheet.save(ROOT/'hard_scene_probe_v2.jpg',quality=94)
    report=dict(status='developmental_hard_negatives_rendered',seconds=time.monotonic()-begin,teacher_actions=False,tidewater_inputs=False,records=records)
    (ROOT/'hard_scene_probe_v2.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(status=report['status'],seconds=report['seconds'],
        false_cold_target_peaks_at_heat_point3=sum(p['boat']and p['presence']>=.3 and p['target_probability']>=.98 for r in records for p in r['predictions']))),flush=True)

if __name__=='__main__':main()
