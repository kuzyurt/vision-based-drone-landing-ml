"""Additional MuJoCo-only hard negatives; no teacher actions or actor truth.

Reuse a verified compiled hard CAD scene, then randomize the rendered world,
camera, layout, lighting and target presence. Labels stay offline only.
"""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import concurrent.futures,json,math,multiprocessing,time
import numpy as np
import generate_discrimination as old
ROOT=Path(__file__).resolve().parent


def generate(job):
    import h5py,mujoco
    from landing_training import environment as em
    from landing_training.config import Scenario
    from landing_training.expert import camera_projection
    from usv.boat_sim import quaternion
    from target_learning.scenes import annotation_groups
    from target_learning.glare import sun_glints,water_mask_for_scene
    from target_learning.label_renderer import install,identify_water
    import domain_visuals,landing_training.rendering as rendering
    domain_visuals.install();install(rendering)
    directory=Path(job['directory']);directory.mkdir(exist_ok=False)
    source=ROOT/'hard_scene_probe_v3/hard_scene.mjb'
    assert old.sha(source)==job['model_sha256']
    model=mujoco.MjModel.from_binary_path(str(source));em.compile_scene=lambda *a,**k:model
    env=em.Environment(Scenario(name=job['name'],kind=job['map'],seed=job['seed'],world_seed=job['seed']+1,
        path_seed=job['seed']+2,distance=8.,height=4.,wave_height=.03,initial_camera_target=False))
    groups=annotation_groups(model);rng=np.random.default_rng(job['seed']);origin=env.pad_position.copy()
    for name in groups:
        if name=='target':continue
        mid=int(model.body_mocapid[model.body(name).id]);a=rng.uniform(-math.pi,math.pi);radius=rng.uniform(4,22)
        env.data.mocap_pos[mid,:2]=origin[:2]+radius*np.array([math.cos(a),math.sin(a)])
        env.data.mocap_quat[mid]=quaternion(0,0,rng.uniform(-math.pi,math.pi))
    mujoco.mj_forward(model,env.data);r=rendering.ReviewRenderer(env,overview=False);append=r.append_water
    def water(scene):append(scene);identify_water(scene,env)
    r.append_water=water
    target_ids=groups['target'];original_groups=model.geom_group[target_ids].copy()
    context_ids={name:{part:[g for g in ids if model.geom(g).name.removeprefix('hard_clone_') in names] for part,names in {'frame':['FrameLoadPaths_plain','LidRails_textured','BayCoaming_plain'], 'aft':['AftSlidingLid_textured','obstacle_AftSlidingLid_textured'], 'fore':['ForeSlidingLid_textured','obstacle_ForeSlidingLid_textured'], 'mast':['CameraMast_textured','DockCameraHousing_textured']}.items()} for name,ids in groups.items()}
    marker_ids={name:[g for g in ids if model.geom(g).name in ['LandingTarget_plain','hard_clone_LandingTarget_plain']
        or 'copied_marker' in model.geom(g).name] for name,ids in groups.items()}
    # The reduced static clone retained its visible platform surface, but not
    # the separate paint geom (the latter was in a different original group).
    # Use a well-resolved expected pad surface for absence evidence; never
    # interpret an empty annotation ID list as proof of a missing blue marker.
    marker_ids['decoy_blank_clone']=[g for g in groups['decoy_blank_clone']if model.geom(g).name=='hard_clone_LandingPlatform_textured']
    assert marker_ids['decoy_blank_clone']
    az=rng.uniform(-math.pi,math.pi);el=rng.uniform(.08,.5)
    sun=[math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)]
    begin=time.monotonic();counts={'positive':0,'negative':0,'unknown':0};cid=model.camera('drone_onboard').id
    with h5py.File(directory/'samples.h5','x')as h:
        h.attrs.update(role=job['role'],world_seed=job['seed'],teacher_actions=False,source='MuJoCo hard-negative rendering; no Tidewater')
        rgb_store=h.create_dataset('rgb',(job['frames']*2,360,640,3),dtype='u1',chunks=(1,360,640,3),compression='lzf')
        rows=h.create_dataset('labels',(job['frames']*2,),dtype=h5py.string_dtype())
        for i in range(job['frames']):
            env.data.time=i*.08;hidden=rng.random()<.25;model.geom_group[target_ids]=3 if hidden else original_groups
            focus=str(rng.choice(list(groups))) if i%3 else 'target'
            point=env.pad_position.copy() if focus=='target'else env.data.xpos[model.body(focus).id]+[0,0,.3]
            distance=float(np.exp(rng.uniform(math.log(1.5),math.log(65))));height=rng.uniform(2,8)
            if i%10==0:distance=rng.uniform(.03,.5);height=rng.uniform(.45,1.2)
            angle=rng.uniform(-math.pi,math.pi);q=env.drone.free_qadr
            env.data.qpos[q:q+3]=point+[distance*math.cos(angle),distance*math.sin(angle),height]
            yaw=math.atan2(-math.sin(angle),-math.cos(angle))+rng.uniform(-.35,.35)
            env.data.qpos[q+3:q+7]=quaternion(0,0,yaw)
            env.data.qpos[env.drone.camera_qpos]=[rng.uniform(-.1,.1),np.clip(math.atan2(height,distance)+rng.uniform(-.1,.1),0,math.pi/2)]
            mujoco.mj_forward(model,env.data);rgb=r.onboard_image()
            r.onboard.enable_segmentation_rendering();seg=r.onboard_image();r.onboard.disable_segmentation_rendering()
            paint=model.geom('LandingTarget_plain').id;paint_group=int(model.geom_group[paint])
            model.geom_group[paint]=3;blank=r.onboard_image();model.geom_group[paint]=paint_group
            glare=None
            if i%3!=1:
                roughness=rng.uniform(.07,.20);strength=rng.uniform(.2,1.3);water_pixels=water_mask_for_scene(r,env)(seg)
                rgb,glare=sun_glints(rgb,water_pixels,env,sun_direction=sun,roughness=roughness,strength=strength)
                blank,_=sun_glints(blank,water_pixels,env,sun_direction=sun,roughness=roughness,strength=strength)
            instances=[]
            for name,ids in groups.items():
                mask=np.isin(seg[...,0],ids)&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM));yy,xx=np.nonzero(mask)
                if len(xx)<3:continue
                box=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];w=box[2]-box[0];hh=box[3]-box[1]
                clipped=box[0]<2 or box[1]<2 or box[2]>638 or box[3]>358
                context=len(xx)>=128 and max(w,hh)>=24
                parts={part:int((np.isin(seg[...,0],gids)&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))).sum()) for part,gids in context_ids[name].items()}
                if name in ['target','decoy_blank_clone']:
                    # Visible hull/frame plus a lid or both lids distinguish
                    # structural context from a shared marker-only crop. A
                    # one-pixel frame-edge clipping is NOT identity blindness.
                    context=context and sum(n>=16 for n in parts.values())>=2 and sum(parts.values())>=128
                else:
                    # Do not claim that a cropped piece of a printed board or
                    # another hull establishes that whole object's identity.
                    context=context and not clipped
                marker=np.isin(seg[...,0],marker_ids[name])&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))
                my,mx=np.nonzero(marker);marker_pixels=len(mx)
                # The same hull's unmarked pad is distinguishable only when its
                # pad surface is actually visible; no hidden identity labels.
                support=context and (marker_pixels>=4 if name=='target'else marker_pixels>=512 if name=='decoy_blank_clone'else True)
                identity=(1 if name=='target' else 0) if support else -1
                counts['positive'if identity==1 else 'negative'if identity==0 else 'unknown']+=1
                pad=None
                if name=='target' and marker_pixels>=4:
                    p,_=camera_projection(env,env.pad_position);pad=p[0].tolist()
                instances.append(dict(annotation_instance=name,boat=True,bbox=box,pixels=len(xx),identity=identity,
                    identity_support=float(support),marker_visible_pixels=marker_pixels,pad_pixel=pad,visible_context_parts=parts,pad_label_available=name not in ['decoy_false_cross_boat','decoy_false_cross_board'],
                    camera_range_annotation_only=float(np.linalg.norm(env.data.cam_xpos[cid]-env.data.xpos[model.body('boat'if name=='target'else name).id]))))
            # Re-render only to obtain visibility annotations that were not
            # preserved in V5. Verify exact RGB correspondence before reusing
            # any frozen V5 feature cache for these new labels.
            with h5py.File(ROOT/'perception_hard_dataset_v5'/job['name']/'samples.h5','r')as prior:
                assert np.array_equal(rgb,prior['rgb'][i]), 'RGB changed; feature cache cannot be reused'
            import copy
            changed=np.max(np.abs(rgb.astype(int)-blank.astype(int)),axis=2)
            contrast_pixels=int((changed>20).sum())
            for variant,image in enumerate([rgb,blank]):
                labelled=copy.deepcopy(instances)
                for inst in labelled:
                    if inst['annotation_instance']=='target':
                        context_parts=inst['visible_context_parts']
                        context_visible=(sum(v>=16 for v in context_parts.values())>=2 and sum(context_parts.values())>=128)
                        supported=context_visible and contrast_pixels>=32
                        inst['identity']=(1 if variant==0 else 0)if supported else -1
                        inst['identity_support']=float(supported)
                        inst['marker_contrast_pixels_annotation_only']=contrast_pixels
                        if variant:
                            inst['annotation_instance']='counterfactual_unmarked_full_cad'
                            inst['pad_pixel']=None;inst['pad_label_available']=False
                index=i*2+variant;rgb_store[index]=image
                rows[index]=json.dumps(dict(index=index,source_view_index=i,variant='original'if variant==0 else'marker_paint_hidden',
                    role=job['role'],world_seed=job['seed'],instances=labelled,target_hidden=bool(hidden),glare=glare,
                    marker_contrast_pixels_annotation_only=contrast_pixels,
                    camera_position_annotation_only=env.data.cam_xpos[cid].tolist(),camera_rotation_annotation_only=env.data.cam_xmat[cid].tolist(),
                    own_body_qpos_annotation_only=env.data.qpos[env.drone.free_qadr:env.drone.free_qadr+7].tolist(),gimbal_annotation_only=env.data.qpos[env.drone.camera_qpos].tolist()))
    r.close();result=dict(path=str(directory/'samples.h5'),sha256=old.sha(directory/'samples.h5'),role=job['role'],
        world_seed=job['seed'],frames=job['frames']*2,source_views=job['frames'],wall_s=time.monotonic()-begin,identity_counts_first_variant_before_contrast_rule=counts,paired_exact_cad=True,only_counterfactual_mutation='marker paint visibility')
    old.save(directory/'report.json',result);return result


def main():
    out=ROOT/'perception_paired_dataset_v9';out.mkdir(exist_ok=False)
    model_sha=old.sha(ROOT/'hard_scene_probe_v3/hard_scene.mjb');jobs=[]
    for i in range(15):
        role='training'if i<10 else 'validation';name=f'{role}_{i:03d}'
        jobs.append(dict(name=name,role=role,seed=990000+i*100,map=['island','beach','city','gravel','rock'][i%5],
            frames=128,directory=str(out/name),model_sha256=model_sha))
    old.save(out/'plan.json',dict(jobs=jobs,workers=8,teacher_actions=False,split_frozen_before_generation=True,
        original_heldout_unused=True,no_tidewater=True,paired_exact_cad=True,observable_identity_rule='>=32 changed RGB pixels above20levels and two visible structural groups; otherwise both identities unknown',source_sha256=old.sha(__file__)))
    begin=time.monotonic();results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=8,mp_context=multiprocessing.get_context('spawn'),max_tasks_per_child=1)as pool:
        for result in pool.map(generate,jobs):
            results.append(result);old.save(out/'state.json',dict(stage='rendering',completed=len(results),planned=len(jobs)))
    value=dict(status='completed',entries=results,wall_s=time.monotonic()-begin,teacher_collection=False)
    old.save(out/'manifest.json',value);old.save(out/'state.json',dict(stage='completed',**value))
    print(json.dumps({k:v for k,v in value.items()if k!='entries'},default=lambda v:v.item()),flush=True)

if __name__=='__main__':main()

