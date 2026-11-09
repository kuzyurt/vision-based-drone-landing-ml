"""Own encoder/CAD raycasts checked against offline actual segmentation only."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import hashlib,importlib,json,sys,time,types
import mujoco,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml');SRC=ROOT/'search_v39/sources';PRIOR=ROOT/'own_cad_prior_v2';BUNDLE=ROOT.parents[1]/'landing_hardening_20261018T011610Z/candidate_r15';sys.path[:0]=[str(BASE),str(SRC)]
from landing_training import paths,environment,rendering
from landing_training.config import Scenario
from target_learning.label_renderer import install,identify_water
from own_cad_occlusion_v2 import OwnCadOcclusion
def main():
    r=json.loads((PRIOR/'receipt.json').read_text());package=types.ModuleType('own_body_calibration');package.__path__=[str(BUNDLE/'code/landing_training')];sys.modules[package.__name__]=package;camera=importlib.import_module(package.__name__+'.radio_robust_20261015.controller.camera_geometry').camera_body_transform;cal=json.loads((BUNDLE/'policy.json').read_text())['calibration'];prior=OwnCadOcclusion(PRIOR/'fixed_own_aircraft.npz',r['mesh_sha256'],camera);model=ROOT.parent/'hard_scene_probe_v3/hard_scene.mjb';environment.compile_scene=lambda *a,**k:mujoco.MjModel.from_binary_path(str(model));s=Scenario(name='own_static_prior_proof',kind='beach',world_seed=960101,path_seed=960102,seed=354001,height=6.,distance=8.,duration=120.);env=environment.Environment(s);install(rendering);old=rendering.ReviewRenderer.append_water
    def append(self,scene):old(self,scene);identify_water(scene,self.env)
    rendering.ReviewRenderer.append_water=append;renderer=rendering.ReviewRenderer(env,overview=False);fixed={env.model.geom(z['geom_name']).id for z in r['records']};world={g for g in range(env.model.ngeom)if g not in set(g for g in range(env.model.ngeom)if env.drone.in_subtree(int(env.model.geom_bodyid[g])))};rng=np.random.default_rng(39001);results=[];images=[];samples=[];start=time.monotonic()
    try:
        for k,(pan,tilt)in enumerate([(140,18),(140,35),(90,35),(-140,35),(-90,18),(0,35),(0,80),(45,50),(-45,50),(170,6)]):
            q=env.drone.free_qadr;env.data.qpos[q:q+3]=[*env.task_start_xy,6.];env.data.qpos[q+3:q+7]=environment.quaternion(0.,0.,env.boat_yaw+math.pi if False else env.boat_yaw+np.pi);env.data.qpos[env.drone.camera_qpos]=np.radians([pan,tilt]);env.data.time=k*.04;mujoco.mj_forward(env.model,env.data);rgb=renderer.onboard_image();renderer.onboard.enable_segmentation_rendering();seg=renderer.onboard_image();renderer.onboard.disable_segmentation_rendering();own=np.isin(seg[...,0],list(fixed))&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM));nonself=np.isin(seg[...,0],list(world))&(seg[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM));gimbal=np.radians([pan,tilt]);owncoords=np.column_stack(np.nonzero(own))[:,::-1];worldcoords=np.column_stack(np.nonzero(nonself))[:,::-1];hits=miss=fp=0;timings=[];overlay=Image.fromarray(rgb);draw=ImageDraw.Draw(overlay)
            for pixels,is_self in [(owncoords,True),(worldcoords,False)]:
                if not len(pixels):continue
                take=pixels[rng.choice(len(pixels),min(100,len(pixels)),replace=False)]
                for x,y in take:
                    t=time.monotonic();hit=prior.occluded([x+.5,y+.5],gimbal,cal);timings.append(time.monotonic()-t)
                    if is_self:hits+=hit;miss+=not hit
                    else:fp+=hit
                    if hit:draw.ellipse([x-1,y-1,x+1,y+1],fill='red')
            assert fp==0,(pan,tilt,fp);results.append(dict(pan=pan,tilt=tilt,visible_fixed_own_pixels=int(own.sum()),tested_own=min(100,len(owncoords)),own_hits=int(hits),boundary_or_missed=int(miss),tested_nonself=min(100,len(worldcoords)),false_exclusions=int(fp),mean_test_s=float(np.mean(timings)),p95_test_s=float(np.percentile(timings,95))));images.append(overlay.resize((320,180)))
        assert sum(x['own_hits']for x in results)>100
        # A closed native search contains body artifacts detected at exact own
        # encoders. This is an offline exclusion diagnostic, never training.
        rows=[json.loads(l)for l in(ROOT/'search_v39/pilots/search_mid/steps.jsonl').open()];removed=0;total=0
        for row in rows[::25]:
            o=row['observation'];d=row['output'].get('learner_diagnostics')or{}
            for t in d.get('expert_visual_tracks')or[]:
                if abs(t['capture_s']-o['image_capture_time_s'])>.001:continue
                total+=1;removed+=prior.occluded(t['pixel'],o['gimbal_rad'],cal)
        sheet=Image.new('RGB',(1280,540))
        for i,im in enumerate(images):sheet.paste(im,((i%4)*320,(i//4)*180))
        sheet.save(PRIOR/'actual_self_projection_proof.jpg',quality=87);report=dict(status='passed_static_own_cad_projection',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),occlusion_source_sha256=hashlib.sha256((ROOT/'own_cad_occlusion_v2.py').read_bytes()).hexdigest(),prior_sha256=r['mesh_sha256'],results=results,native_closed_search_diagnostic=dict(sampled_fresh_proposals=total,self_occluded=int(removed)),task_actor_read_segmentation=False,static_fixed_own_geometry_only=True,world_or_target_geometry_in_prior=False,elapsed_s=time.monotonic()-start);(PRIOR/'proof.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='results'}),flush=True)
    finally:renderer.close()
if __name__=='__main__':main()
