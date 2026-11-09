"""Fresh static MuJoCo perception views; no controller, PX4 or teacher commands."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import argparse,hashlib,json,math,sys,time
import h5py,mujoco,numpy as np
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml');SRC=ROOT/'search_v35/sources'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(SRC));sys.path.insert(0,str(BASE/'landing_training/outputs/domain_training_20261016T134939Z'))
from landing_training import paths,environment,rendering
from landing_training.config import Scenario
from landing_training.expert import camera_projection
quaternion=environment.quaternion
from target_learning.scenes import annotation_groups
from target_learning.label_renderer import install,identify_water
from target_learning.glare import sun_glints,water_mask_for_scene
from collection_pipeline.live_capture_bridge import declared_specs
from collection_pipeline.capture_annotations import make_capture
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job',required=True);a=parser.parse_args();job=json.loads(Path(a.job).read_text());out=ROOT/'static_repair_v44b'/job['name'];out.mkdir(exist_ok=False);start=time.monotonic();rng=np.random.default_rng(job['seed'])
    proof=json.loads((ROOT/'world_contract_v1/proof.json').read_text());cache=proof['models']['hard'];assert sha(cache['mjb'])==cache['sha256'];environment.compile_scene=lambda *a,**k:mujoco.MjModel.from_binary_path(cache['mjb'])
    s=Scenario(name=job['name'],kind=job['kind'],world_seed=job['world_seed'],path_seed=job['path_seed'],seed=job['seed'],distance=8.,height=6.,boat_speed=.3,duration=180.,wave_height=.03,world_rotation_deg=job['rotation'])
    env=environment.Environment(s);groups=annotation_groups(env.model);nominal=mujoco.MjData(env.model)
    for name,value in [('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)]:nominal.qpos[env.model.jnt_qposadr[env.model.joint(name).id]]=value
    mujoco.mj_forward(env.model,nominal);placed=[]
    for name,gids in sorted(groups.items()):
        if name=='target':continue
        bid=env.model.body(name).id;mid=int(env.model.body_mocapid[bid]);radius=max(float(np.linalg.norm(nominal.geom_xpos[g]-nominal.xpos[bid])+env.model.geom_rbound[g])for g in gids)
        for trial in range(3000):
            theta=rng.uniform(-math.pi,math.pi);distance=rng.uniform(8+radius,30+radius);xy=env.pad_position[:2]+distance*np.array([math.cos(theta),math.sin(theta)])
            if env.boat.navigation.world.distance(xy)[0]<5+radius:continue
            if any(np.linalg.norm(xy-q)<radius+r+1 for q,r in placed):continue
            env.data.mocap_pos[mid,:2]=xy;placed.append((xy.copy(),radius));break
        else:raise RuntimeError('Cannot place static distractor without overlap')
    import domain_visuals;domain_visuals.install();install(rendering)
    old_append=rendering.ReviewRenderer.append_water
    def append(self,scene):old_append(self,scene);identify_water(scene,self.env)
    rendering.ReviewRenderer.append_water=append
    renderer=rendering.ReviewRenderer(env,overview=False);specs=declared_specs(env.model,groups);water=water_mask_for_scene(renderer.onboard,env);provenance=sha(a.job);subjects=['target']*6+[n for n in groups if n!='target']+['background']*2;records=[]
    from landing_training.run_episode import camera_image
    from types import SimpleNamespace
    with h5py.File(out/'data.h5','x')as h:
        h.attrs.update(schema='approved.static.visual-development.v36',role=job['role'],teacher_actions=False,action_targets_admissible=False)
        images=h.create_dataset('rgb',(job['frames'],360,640,3),dtype='u1',chunks=(1,360,640,3),compression='lzf');labels=h.create_dataset('labels',(job['frames'],),dtype=h5py.string_dtype())
        try:
            for i in range(job['frames']):
                name=subjects[i%len(subjects)];point=env.pad_position.copy()if name in ['target','background']else env.data.mocap_pos[int(env.model.body_mocapid[env.model.body(name).id])].copy()+[0,0,.4]
                near=bool(i%3==0);distance=float(rng.choice([.15,.4,.8,1.5,3.]))if near else float(rng.choice([5,8,12,20,28,40,52,60]));height=float(point[2]+rng.uniform(.7,2.5))if near else float(rng.uniform(4,8));pan=float(np.deg2rad(rng.choice([-140,-90,-45,0,0,0,45,90,140])))
                for _ in range(100):
                    theta=rng.uniform(-math.pi,math.pi);xy=point[:2]+distance*np.array([math.cos(theta),math.sin(theta)])
                    if env.boat.navigation.world.distance(xy)[0]>=5:break
                else:raise RuntimeError('No static camera water position')
                yaw=math.atan2(point[1]-xy[1],point[0]-xy[0]);yaw+=float(rng.uniform(-.35,.35))+(math.pi if name=='background'else 0)
                q=env.drone.free_qadr;env.data.qpos[q:q+3]=[*xy,height];env.data.qpos[q+3:q+7]=quaternion(float(rng.uniform(-.04,.04)),float(rng.uniform(-.04,.04)),yaw)
                tilt=float(np.clip(math.atan2(height-point[2],distance)+rng.uniform(-.08,.08),.01,1.5));env.data.qpos[env.drone.camera_qpos]=[pan,tilt];env.data.time=i*.04;mujoco.mj_forward(env.model,env.data)
                # Static image placement aligns the actual camera heading, including pan.
                # This is not a task command or an expert trajectory.
                ray=-env.data.cam_xmat[env.model.camera('drone_onboard').id].reshape(3,3)[:,2];delta=(math.atan2(point[1]-xy[1],point[0]-xy[0])+(math.pi if name=='background'else 0.)-math.atan2(ray[1],ray[0])+math.pi)%(2*math.pi)-math.pi
                yaw+=delta;env.data.qpos[q+3:q+7]=quaternion(0.,0.,yaw);mujoco.mj_forward(env.model,env.data)
                contact=any((int(env.model.geom_bodyid[c.geom1])in env.drone.bodies)!=(int(env.model.geom_bodyid[c.geom2])in env.drone.bodies)for c in env.data.contact[:env.data.ncon])
                hide_marker=bool(i%4==2)
                for gid in groups['target']:
                    if env.model.geom(gid).name=='LandingTarget_plain':env.model.geom_group[gid]=5 if hide_marker else 0
                rgb=renderer.onboard_image();renderer.onboard.enable_segmentation_rendering()
                try:seg=renderer.onboard_image()
                finally:renderer.onboard.disable_segmentation_rendering()
                sunaz=float(rng.uniform(-math.pi,math.pi));sunel=float(rng.uniform(.12,.8));sun=[math.cos(sunaz)*math.cos(sunel),math.sin(sunaz)*math.cos(sunel),math.sin(sunel)]
                rgb,glare=sun_glints(rgb,water(seg),env,sun_direction=sun,roughness=float(rng.uniform(.07,.2)),strength=float(rng.uniform(.3,2)))
                effect=dict(brightness=float(rng.uniform(.85,1.15)),contrast=float(rng.uniform(.9,1.1)),blur_radius=float(rng.choice([0,.15,.3])),blackout=False)
                rgb=camera_image(rgb,SimpleNamespace(image_brightness=effect["brightness"],image_contrast=effect["contrast"],image_blur_px=effect["blur_radius"]));pad,_=camera_projection(env,env.pad_position);label=make_capture(rgb,seg,specs,capture_s=i*.04,geom_object_type=int(mujoco.mjtObj.mjOBJ_GEOM),retained_pixels=np.ones((360,640),bool),render_provenance_sha256=provenance,target_pad_center_px=pad)
                label.update(role=job['role'],world_seed=job['world_seed'],path_seed=job['path_seed'],kind=job['kind'],index=i,static_view=True,teacher_actions=False,view_subject=name,view_distance_m=distance,view_height_m=height,view_yaw_rad=yaw,view_tilt_rad=tilt,glare=glare,image_effects=effect,marker_hidden_render_only=hide_marker,palette=job['palette'],view_pan_rad=pan,near_view=near,static_view_contact_excluded=bool(contact))
                images[i]=rgb;labels[i]=json.dumps(label);records.append(label)
                if i%16==0:(out/'state.json').write_text(json.dumps(dict(status='static_rendering',frames=i+1,total=job['frames'],elapsed_s=time.monotonic()-start)))
        finally:renderer.close()
    receipt=dict(status='closed_static_visual_development',job=job,frames=len(records),data_sha256=sha(out/'data.h5'),job_sha256=provenance,source_sha256=sha(__file__),model_sha256=cache['sha256'],teacher_actions=False,physical_flights=False,tidewater_used=False,heldout_used=False,elapsed_s=time.monotonic()-start)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2));(out/'state.json').write_text(json.dumps(receipt));print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
