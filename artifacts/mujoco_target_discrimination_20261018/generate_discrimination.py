"""MuJoCo-only static perception samples. No teacher actions or trajectories.

These supervised images bootstrap recognition for an observation-limited expert.
They do not waive the required review of expert flights before bulk collection.
"""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import argparse,concurrent.futures,datetime,hashlib,json,math,multiprocessing,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'landing_training/outputs/domain_training_20261016T134939Z'))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    path=Path(path);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False));temp.replace(path)

def generate(job):
    import h5py,mujoco
    from PIL import Image
    from landing_training import paths,environment as module
    from landing_training.config import Scenario
    from landing_training.rendering import ReviewRenderer
    from landing_training.expert import camera_projection,pad_visibility
    from usv.boat_sim import quaternion
    from target_learning.scenes import compile_variant,annotation_groups
    from target_learning.glare import sun_glints,water_mask_for_scene
    from target_learning.label_renderer import install as install_labels,identify_water
    import domain_visuals
    # The renderer is replaced locally only; task physics is not modified.
    domain_visuals.install()
    import landing_training.rendering as rendering
    install_labels(rendering)
    started=time.monotonic();directory=Path(job['directory']);directory.mkdir(parents=True,exist_ok=False)
    model=compile_variant(BASE/'landing_training/build/combined_1000us.xml',directory/'variant',seed=job['seed'])
    module.compile_scene=lambda *a,**kw:model
    scenario=Scenario(name=job['name'],kind=job['map'],world_seed=job['seed']+1,path_seed=job['seed']+2,
        seed=job['seed'],distance=8.,height=4.,wave_height=.03,boat_speed=.3,initial_camera_target=False)
    env=module.Environment(scenario);r=rendering.ReviewRenderer(env,overview=False)
    groups=annotation_groups(model);rng=np.random.default_rng(job['seed']+33)
    origin=env.pad_position.copy()
    for name in groups:
        if name=='target':continue
        mid=int(model.body_mocapid[model.body(name).id])
        theta=rng.uniform(-math.pi,math.pi);radius=rng.uniform(4.,16.)
        env.data.mocap_pos[mid,:2]=origin[:2]+radius*np.array([math.cos(theta),math.sin(theta)])
    mujoco.mj_forward(model,env.data)
    original_append=r.append_water
    def append(scene):
        original_append(scene);identify_water(scene,env)
    r.append_water=append
    # Sun is fixed in world coordinates per generated world, not locked to target.
    azimuth=rng.uniform(-math.pi,math.pi);elevation=rng.uniform(math.radians(5),math.radians(30))
    sun=[math.cos(azimuth)*math.cos(elevation),math.sin(azimuth)*math.cos(elevation),math.sin(elevation)]
    target_ids=groups['target'];target_group=model.geom_group[target_ids].copy()
    frame_rows=[];glint_frames=0;identity_counts=dict(target=0,wrong=0,unknown=0)
    h=h5py.File(directory/'samples.h5','x');h.attrs.update(role=job['role'],world_seed=job['seed'],
        source='MuJoCo3.14 static scene rendering; no Tidewater inputs',teacher_actions=False,
        identity_gate='Provisional image-support rule; not a measured recognition distance. Calibrate on validation.')
    rgb_store=h.create_dataset('rgb',(job['frames'],360,640,3),dtype='u1',chunks=(1,360,640,3),compression='lzf')
    label_store=h.create_dataset('labels',(job['frames'],),dtype=h5py.string_dtype())
    try:
        for i in range(job['frames']):
            env.data.time=i*.08
            target_hidden=bool(rng.random()<.18);model.geom_group[target_ids]=3 if target_hidden else target_group
            keys=list(groups);focus='target' if rng.random()<.40 else str(rng.choice(keys))
            if focus=='target':point=env.pad_position.copy()
            else:point=env.data.xpos[model.body(focus).id].copy()+[0,0,.3]
            distance=float(np.exp(rng.uniform(math.log(2),math.log(65))))
            height=float(rng.uniform(2.,8.))
            if i%12==0 and focus=='target' and not target_hidden:
                distance=float(rng.uniform(.03,1.));height=float(rng.uniform(.42,1.5))
            bearing=float(azimuth+math.pi+rng.normal(0,.2)) if i%3==0 else float(rng.uniform(-math.pi,math.pi))
            position=point+[distance*math.cos(bearing),distance*math.sin(bearing),height]
            q=env.drone.free_qadr;env.data.qpos[q:q+3]=position
            yaw=math.atan2(point[1]-position[1],point[0]-position[0])+rng.uniform(-.35,.35)
            env.data.qpos[q+3:q+7]=quaternion(0,0,yaw)
            env.data.qpos[env.drone.camera_qpos]=[rng.uniform(-.15,.15),np.clip(math.atan2(height,distance)+rng.uniform(-.12,.12),0,math.pi/2)]
            mujoco.mj_forward(model,env.data)
            rgb=r.onboard_image();r.onboard.enable_segmentation_rendering();seg=r.onboard_image();r.onboard.disable_segmentation_rendering()
            glare_info=None
            if i%3!=1:
                rgb,glare_info=sun_glints(rgb,water_mask_for_scene(r,env)(seg),env,sun_direction=sun,
                    roughness=float(rng.uniform(.07,.20)),strength=float(rng.uniform(.2,1.3)))
                glint_frames+=int(glare_info['bright_glint_pixels']>30)
            # Every label is derived AFTER rendering and isolated from any task
            # actor; no expert/controller is called during image generation.
            pad_pixel,_=camera_projection(env,env.pad_position)
            visible,_=pad_visibility(env)
            focal=180/math.tan(math.radians(float(model.cam_fovy[model.camera('drone_onboard').id]))/2)
            pad_depth=float(-((env.pad_position-env.data.cam_xpos[model.camera('drone_onboard').id])@env.data.cam_xmat[model.camera('drone_onboard').id].reshape(3,3))[2])
            pad_span_px=focal*.26/max(pad_depth,.001)
            instances=[]
            for name,ids in groups.items():
                mask=np.isin(seg[...,0],ids)&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))
                yy,xx=np.nonzero(mask)
                if len(xx)<3:continue
                bbox=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
                boat=name=='target' or name in ['decoy_red','decoy_similar','decoy_dark']
                # Conservative bootstrapping rule, NOT a claim that these pixel
                # counts guarantee human/model recognition. Identity is ignored
                # below support and calibrated against unseen validation worlds.
                identifiable=(len(xx)>=128 and max(bbox[2]-bbox[0],bbox[3]-bbox[1])>=24)
                identity=-1
                if boat and identifiable:
                    if name=='target':identity=1 if visible and not target_hidden and pad_span_px>=12 else -1
                    else:identity=0
                if boat:identity_counts['target' if identity==1 else 'wrong' if identity==0 else 'unknown']+=1
                instances.append(dict(annotation_instance=name,boat=boat,bbox=bbox,pixels=int(len(xx)),
                    identity=identity,identity_provisional=True,
                    pad_pixel=pad_pixel[0].tolist() if name=='target' and visible and not target_hidden else None))
            row=dict(index=i,role=job['role'],world_seed=job['seed'],instances=instances,
                     target_hidden=target_hidden,glare=glare_info,focus_annotation_only=focus)
            rgb_store[i]=rgb;label_store[i]=json.dumps(row,separators=(',',':'));frame_rows.append(row)
            if i in [0,1,2,3]:Image.fromarray(rgb).save(directory/f'example_{i:02d}.jpg',quality=91)
    finally:h.close();r.close()
    report=dict(name=job['name'],role=job['role'],world_seed=job['seed'],frames=job['frames'],
        wall_s=time.monotonic()-started,path=str(directory/'samples.h5'),sha256=sha(directory/'samples.h5'),
        bright_glare_frames=glint_frames,identity_instances=identity_counts,no_teacher_actions=True,
        render_parameters=dict(sun_world_unit=sun),split_group=job['name'])
    save(directory/'report.json',report);return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=8)
    p.add_argument('--worlds',type=int,default=30);p.add_argument('--frames',type=int,default=64);p.add_argument('--seed',type=int,default=830000)
    p.add_argument('--development',action='store_true')
    a=p.parse_args();assert 1<=a.workers<=16 and a.worlds>=5 and a.frames>0
    out=ROOT/a.output;out.mkdir(exist_ok=False);jobs=[]
    for i in range(a.worlds):
        role='training' if i<a.worlds-10 else 'validation' if i<a.worlds-5 else 'heldout'
        if a.worlds<15 or a.development:role='development'
        name=f'{role}_{i:03d}'
        jobs.append(dict(name=name,role=role,seed=a.seed+i*100,map=['island','beach','city','gravel','rock'][i%5],
                         frames=a.frames,directory=str(out/name)))
    save(out/'plan.json',dict(jobs=jobs,workers=a.workers,teacher_collection=False,
         no_tidewater_inputs=True,original_data_modified=False,
         source_hashes={str(f.relative_to(ROOT)):sha(f)for f in ROOT.glob('*.py')}))
    begin=time.monotonic();results=[]
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn'))as pool:
            for r in pool.map(generate,jobs):
                results.append(r);save(out/'state.json',dict(status='rendering',completed=len(results),planned=len(jobs),wall_s=time.monotonic()-begin))
        save(out/'manifest.json',dict(status='completed',entries=results,teacher_collection=False,
            wall_s=time.monotonic()-begin,completed_frames=sum(r['frames']for r in results),
            images_per_wall_s=sum(r['frames']for r in results)/(time.monotonic()-begin),world_split_frozen_before_generation=True))
        save(out/'state.json',dict(status='completed',completed=len(results),planned=len(jobs),wall_s=time.monotonic()-begin))
        print((out/'manifest.json').read_text(),flush=True)
    except BaseException as exc:
        save(out/'state.json',dict(status='failed',error=repr(exc),completed=len(results),wall_s=time.monotonic()-begin));raise

if __name__=='__main__':main()
