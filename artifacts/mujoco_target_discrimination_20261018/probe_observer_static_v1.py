"""ONE cached MuJoCo capture to check annotation/RGB binding. No flight or training."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,math,sys,time
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'landing_training/outputs/domain_training_20261016T134939Z'))
import mujoco,numpy as np
from PIL import Image,ImageDraw
from landing_training import environment as em,rendering
from landing_training.config import Scenario
from landing_training.run_episode import camera_image
from landing_training.expert import camera_projection
from usv.boat_sim import quaternion
from target_learning.scenes import annotation_groups
from target_learning.label_renderer import install,identify_water
from target_learning.glare import sun_glints,water_mask_for_scene
from collection_pipeline.capture_annotations import ObjectSpec,make_capture,CaptureSidecar,load_capture_index,join_delivered_frame,rgb_hash
import domain_visuals

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    began=time.monotonic();out=ROOT/'observer_static_probe_v1';out.mkdir(exist_ok=False)
    domain_visuals.install();install(rendering)
    fixture=json.loads((ROOT/'expert_visible_native_v15_hard/scene_spawn_receipt.json').read_text())
    model_path=ROOT/'hard_scene_probe_v3/hard_scene.mjb';assert sha(model_path)==fixture['model_sha256']
    model=mujoco.MjModel.from_binary_path(str(model_path));em.compile_scene=lambda *a,**kw:model
    scenario=Scenario(name='observer_static_probe_only',kind='beach',seed=960100,world_seed=960101,path_seed=960102,distance=8.,height=4.,wave_height=.03,image_brightness=.93,image_contrast=1.05,image_blur_px=.3)
    env=em.Environment(scenario);groups=annotation_groups(model)
    for placement in fixture['placements']:
        mid=int(model.body_mocapid[model.body(placement['name']).id]);env.data.mocap_pos[mid,:2]=placement['xy']
    for name,value in [('platform_slide',.4),('aft_lid_slide',.46),('fore_lid_slide',.46)]:env.data.qpos[model.jnt_qposadr[model.joint(name).id]]=value
    mujoco.mj_forward(model,env.data);point=env.pad_position.copy();angle=env.boat_yaw+math.pi
    q=env.drone.free_qadr;env.data.qpos[q:q+3]=point+[8*math.cos(angle),8*math.sin(angle),4.]
    env.data.qpos[q+3:q+7]=quaternion(0,0,math.atan2(-math.sin(angle),-math.cos(angle)))
    env.data.qpos[env.drone.camera_qpos]=[0.,math.atan2(4.,8.)];mujoco.mj_forward(model,env.data)
    specs=[]
    part_names={'frame':['FrameLoadPaths_plain','LidRails_textured','BayCoaming_plain'],'aft':['AftSlidingLid_textured','obstacle_AftSlidingLid_textured'],'fore':['ForeSlidingLid_textured','obstacle_ForeSlidingLid_textured'],'mast':['CameraMast_textured','DockCameraHousing_textured']}
    for name,ids in groups.items():
        parts={k:tuple(g for g in ids if model.geom(g).name.removeprefix('hard_clone_')in names)for k,names in part_names.items()}if name in ['target','decoy_blank_clone']else{}
        markers=tuple(g for g in ids if model.geom(g).name=='LandingTarget_plain'or 'copied_marker'in model.geom(g).name)
        design='target'if name=='target'else'unverified'if name=='decoy_blank_clone'else'other'
        category='board'if 'board'in name else'buoy'if 'buoy'in name else'debris'if 'debris'in name else'boat'
        specs.append(ObjectSpec(name,design,category,tuple(ids),parts,markers,'present'if markers else'absent'))
    r=rendering.ReviewRenderer(env,overview=False);append=r.append_water
    def water(scene):append(scene);identify_water(scene,env)
    r.append_water=water
    try:
        raw=r.onboard_image();r.onboard.enable_segmentation_rendering();seg=r.onboard_image();r.onboard.disable_segmentation_rendering()
        cid=model.camera('drone_onboard').id;matrix=env.data.cam_xmat[cid].reshape(3,3);az=math.atan2(-matrix[1,2],-matrix[0,2])+.12;el=math.radians(30)
        sun=[math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)]
        glared,glare=sun_glints(raw,water_mask_for_scene(r,env)(seg),env,sun_direction=sun,roughness=.12,strength=.9)
        final=camera_image(glared,scenario);pixel,_=camera_projection(env,point)
        provenance=dict(model_sha256=fixture['model_sha256'],image_effects=dict(brightness=.93,contrast=1.05,blur_px=.3),sun=sun,segmentation_drives_actor=False)
        digest=hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
        label=make_capture(final,seg,specs,capture_s=float(env.data.time),geom_object_type=int(mujoco.mjtObj.mjOBJ_GEOM),retained_pixels=np.ones((360,640),bool),render_provenance_sha256=digest,target_pad_center_px=pixel[0].tolist())
        Image.fromarray(final).save(out/'actual_final_rgb.png');canvas=Image.fromarray(final);draw=ImageDraw.Draw(canvas)
        for inst in label['instances']:
            colour='lime'if inst['identity']==1 else'orange'if inst['identity']==-1 else'cyan'
            draw.rectangle(inst['bbox'],outline=colour,width=2);draw.text(tuple(inst['bbox'][:2]),f'{inst["annotation_instance"]}:ID{inst["identity"]}',fill=colour)
        canvas.save(out/'annotation_overlay.png')
        writer=CaptureSidecar(out/'capture_annotations.jsonl');writer.append(label);writer.close();index=load_capture_index(out/'capture_annotations.jsonl')
        assert join_delivered_frame(dict(image_valid=True,image_capture_time_s=float(env.data.time),image_delivery_time_s=3.),final,index)['capture_uid']==label['capture_uid']
        assert rgb_hash(glared)!=rgb_hash(final),'Fixture must exercise final image effects'
        target=next(i for i in label['instances']if i['annotation_instance']=='target')
        assert target['identity']==1 and target['marker_visibility_label']==1 and target['pad_label_available']
        report=dict(status='one_static_capture_observer_passed',actor_called=False,px4_started=False,teacher_trajectory=False,training_eligible=False,bulk_collection=False,capture_uid=label['capture_uid'],target=target,instances=len(label['instances']),glare=glare,provenance=provenance,wall_s=time.monotonic()-began)
        (out/'probe_receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    finally:r.close()
if __name__=='__main__':main()
