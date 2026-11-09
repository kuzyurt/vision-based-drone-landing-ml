"""Bounded MuJoCo-only RGB/segmentation pilot, no task actions or teacher data."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import datetime, hashlib, importlib, json, math, sys, time, types
import numpy as np
import mujoco
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
PARENT=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z/candidate_r15'
OLD=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(OLD))
from landing_training import paths
from landing_training import environment as environment_module
from landing_training.config import Scenario
from landing_training.rendering import ReviewRenderer
from usv.boat_sim import quaternion
from target_learning.scenes import compile_variant,annotation_groups

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    start=time.monotonic();out=ROOT/'scene_pilot_v1';out.mkdir(exist_ok=False)
    original=environment_module.compile_scene
    base=original();base_xml=BASE/'landing_training/build/combined_1000us.xml'
    assert base_xml.exists()
    varied=compile_variant(base_xml,out/'variant')
    # Compare all original named-body inertias and original joints/actuators.
    for i in range(base.nbody):
        name=mujoco.mj_id2name(base,mujoco.mjtObj.mjOBJ_BODY,i)
        if not name:continue
        j=varied.body(name).id
        assert np.array_equal(base.body_mass[i],varied.body_mass[j]),name
        assert np.array_equal(base.body_inertia[i],varied.body_inertia[j]),name
    assert base.njnt==varied.njnt and base.nu==varied.nu
    assert base.opt.timestep==varied.opt.timestep
    environment_module.compile_scene=lambda *args,**kw:varied
    scenario=Scenario(name='discrimination_scene_pilot',kind='beach',seed=810100,world_seed=810101,
        path_seed=810102,distance=8.,height=4.,wave_height=.03,boat_speed=.3,initial_camera_target=False)
    env=environment_module.Environment(scenario)
    groups=annotation_groups(env.model);assert 'target'in groups and 'decoy_red'in groups
    for name in groups:
        if name=='target':continue
        b=env.model.body(name).id;mid=int(env.model.body_mocapid[b])
        # Scene setup only. Never passed into a task actor.
        env.data.mocap_pos[mid,:2]+=env.pad_position[:2]
    mujoco.mj_forward(env.model,env.data)
    renderer=ReviewRenderer(env,overview=False)
    original_append=renderer.append_water
    def shiny(scene):
        original_append(scene);g=scene.geoms[scene.ngeom-1];g.specular=1.;g.shininess=.9
    renderer.append_water=shiny
    frame_records=[];font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    distances=[3.,6.,12.,20.,40.,60.]
    # Camera directed at target or decoy for calibration, not an expert flight.
    subjects=['target','decoy_red','decoy_similar']
    for subject in subjects:
        for distance in distances:
            if subject=='target':point=env.pad_position.copy()
            else:point=env.data.xpos[env.model.body(subject).id].copy()+[0,0,.4]
            for side in [0,1]:
                bearing=env.boat_yaw+(math.pi/2 if side else 0)
                position=point+np.array([distance*math.cos(bearing),distance*math.sin(bearing),4.])
                q=env.drone.free_qadr;env.data.qpos[q:q+3]=position
                yaw=math.atan2(point[1]-position[1],point[0]-position[0])
                env.data.qpos[q+3:q+7]=quaternion(0,0,yaw)
                env.data.qpos[env.drone.camera_qpos]=[0.,math.atan2(4.,distance)]
                env.data.time=side*.1
                mujoco.mj_forward(env.model,env.data)
                rgb=renderer.onboard_image();assert rgb.shape==(360,640,3)
                renderer.onboard.enable_segmentation_rendering()
                seg=renderer.onboard_image();renderer.onboard.disable_segmentation_rendering()
                # Official segmentation channel0 object ID, channel1 object type.
                counts={};boxes={};masks={}
                for name,ids in groups.items():
                    mask=np.isin(seg[...,0],ids)&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))
                    counts[name]=int(mask.sum());masks[name]=mask
                    ys,xs=np.nonzero(mask)
                    boxes[name]=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1] if len(xs) else None
                name=f'{subject}_{distance:02.0f}m_{side}'
                Image.fromarray(rgb).save(out/(name+'.png'))
                np.savez_compressed(out/(name+'_masks.npz'),**masks)
                frame_records.append(dict(name=name,subject=subject,horizontal_distance_m=distance,
                    camera_side=side,counts=counts,boxes=boxes,rgb_sha256=sha(out/(name+'.png'))))
    # Full-resolution panels; no resize that could conceal readability limits.
    for subject in subjects:
        rows=[r for r in frame_records if r['subject']==subject and r['camera_side']==0]
        sheet=Image.new('RGB',(1280,3*396),(15,21,30));draw=ImageDraw.Draw(sheet)
        for i,r in enumerate(rows):
            x=(i%2)*640;y=(i//2)*396
            sheet.paste(Image.open(out/(r['name']+'.png')),(x,y))
            draw.text((x+8,y+364),f'{subject} | {r["horizontal_distance_m"]:.0f}m horizontal | {r["counts"][subject]} visible pixels',font=font,fill='white')
        sheet.save(out/(subject+'_contact_sheet.jpg'),quality=93)
    renderer.close()
    result=dict(status='scene_pilot_rendered_requires_visual_review',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        wall_s=time.monotonic()-start,images=len(frame_records),camera_rgb_shape=[360,640,3],wave_height_m=.03,
        original_body_inertia_mass_and_joint_actuator_counts_unchanged=True,
        training_images=False,teacher_flights=False,task_actions=False,frames=frame_records,
        source_hashes={str(p.relative_to(ROOT)):sha(p)for p in ROOT.rglob('*.py') if 'scene_pilot_v1'not in str(p)},
        parent_pose_sha256=sha(PARENT/'pose.pt'),parent_spatial_sha256=sha(PARENT/'spatial_acquisition.pt'))
    (out/'report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items()if k not in ['frames','source_hashes']},indent=2),flush=True)

if __name__=='__main__':main()
