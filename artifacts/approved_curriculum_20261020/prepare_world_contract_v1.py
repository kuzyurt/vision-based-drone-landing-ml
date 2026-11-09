"""Freeze unexposed split/world definitions and prove generic-cache map bindings.

Observer-only setup/render audit; no task actor or teacher actions are executed.
"""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import hashlib,inspect,json,sys,time,xml.etree.ElementTree as ET
import mujoco,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml');OUT=ROOT/'world_contract_v1'
sys.path.insert(0,str(BASE))
from landing_training import paths
from landing_training import environment,rendering
from landing_training.config import Scenario
from usv.procedural_world import World
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    OUT.mkdir(exist_ok=False);begin=time.monotonic();index=json.loads((OLD/'scene_cache_v2/index.json').read_text());basic=index['entries']['850000'];hard=dict(mjb=str(OLD/'hard_scene_probe_v3/hard_scene.mjb'),sha256=json.loads((OLD/'perception_hard_dataset_v5/plan.json').read_text())['jobs'][0]['model_sha256'])
    for rec in [basic,hard]:assert sha(rec['mjb'])==rec['sha256']
    root=ET.parse(Path(basic['mjb']).with_suffix('.xml')).getroot();static=[q.get('name')for q in root.find('worldbody').findall('geom')]
    assert set(static)=={'water_surface','seabed','observer_water_buffer'},'Cannot reuse a cache containing fixed map geometry'
    compile_original=environment.compile_scene;environment.compile_scene=lambda *a,**kw:mujoco.MjModel.from_binary_path(basic['mjb'])
    used=set()
    for p in (BASE/'landing_training/datasets/expert').glob('*/scenario.json'):
        s=json.loads(p.read_text());used.update([s.get('world_seed'),s.get('path_seed')])
    # New namespace; check every previously recorded scenario, including retired
    # metadata only. No old holdout pixels are read for selection or training.
    for p in (BASE/'landing_training/outputs').rglob('scenario.json'):
        if '__pycache__'in p.parts:continue
        s=json.loads(p.read_text());used.update([s.get('world_seed'),s.get('path_seed')])
    worlds=[];proof=[];pictures=[]
    for i,kind in enumerate(['island','beach','city','gravel','rock']):
        for role,delta in [('training',0),('validation',10000)]:
            seed=3400000000+i*100+delta
            assert seed not in used and seed+1 not in used
            worlds.append(dict(kind=kind,role=role,world_seed=seed,path_seed=seed+1))
        w=worlds[-2];s=Scenario(name='map_binding_'+kind,kind=kind,world_seed=w['world_seed'],path_seed=w['path_seed'],seed=w['world_seed']+2,distance=8.,height=6.,boat_speed=.3,duration=180.,wave_height=.03,world_rotation_deg=37.)
        env=environment.Environment(s);world=env.boat.navigation.world
        assert world.kind==kind and world.seed==w['world_seed'] and world.route.seed==w['path_seed']
        assert np.allclose(world.coast,world.original.coast@world.rotation.T)
        assert env.preparation_water_clearance_m>=5.
        env.boat.navigation.update_contacts(force=True);mujoco.mj_forward(env.model,env.data)
        assert any(env.model.geom_contype[g]for g in env.boat.navigation.contact_ids)
        renderer=rendering.ReviewRenderer(env)
        try:
            rgb=renderer.overview();assert rgb.shape==(450,800,3)
            image=Image.fromarray(rgb).resize((400,225));ImageDraw.Draw(image).text((6,6),kind+' actual setup/world',fill='white');pictures.append(image)
        finally:renderer.close()
        export=world.export();p=OUT/(kind+'_world.json');p.write_text(json.dumps(export));proof.append(dict(kind=kind,world_seed=world.seed,path_seed=world.route.seed,world_export_sha256=sha(p),actual_route_points=len(world.route.points),preparation_water_clearance_m=env.preparation_water_clearance_m,coastline_rotates_consistently=True,renderer_receives_same_world=True,actual_render_shape=list(rgb.shape),fixed_map_geometry_in_cache=False))
    sheet=Image.new('RGB',(1200,450),(20,20,20))
    for i,image in enumerate(pictures):sheet.paste(image,((i%3)*400,(i//3)*225))
    sheet.save(OUT/'actual_five_map_setup.jpg',quality=85)
    plans=[]
    trainfamilies=['E01','E02','E06','E07','E08','E04']
    for wi,w in enumerate(worlds):
        families=trainfamilies.copy()if w['role']=='training'else[['E03','E06'],['E04','E07'],['E05','E08'],['E09','E10'],['E11','E02']][wi//2]
        if w['role']=='training'and wi//2==1:families[-1]='E03'
        if w['role']=='training'and wi//2==2:families[-1]='E09'
        if w['role']=='training'and wi//2==3:families[-1]='E10'
        if w['role']=='training'and wi//2==4:families[-1]='E11'
        for k,family in enumerate(families):
            distance={'E06':8.,'E07':28.,'E08':52.}.get(family,8.)
            scenario=Scenario(name=f"new_{w['role']}_{wi:02d}_{k}_{family}",kind=w['kind'],world_seed=w['world_seed'],path_seed=w['path_seed'],seed=w['world_seed']+20+k,distance=distance,height=8. if distance>=40 else 6.,boat_speed=[.2,.35,.5][k%3],wave_height=[.0,.03,.05][k%3],wind_profile='breeze',wind_mean_m_s=1.,initial_camera_target=family not in ['E06','E07','E08'],initial_pan_deg=140. if family in ['E06','E07','E08']else 0.,initial_tilt_deg=35.,world_rotation_deg=float([0,37,89,153,225][wi//2]),image_brightness=[.9,1.,1.1][k%3],image_contrast=[.95,1.,1.05][k%3],camera_delay_steps=k%3,duration=180.)
            scenario.validate();plans.append(dict(name=scenario.name,family=family,role=w['role'],world=w,scenario=vars(scenario),scene='hard'if family in ['E02','E03','E04','E10','E11']else'basic',fault='pan'if family=='E03'else'tilt'if family in ['E04','E10','E11']else None,dagger=family in ['E09','E10','E11'],prefix=family in ['E09','E10','E11']))
    assert len(plans)==40
    report=dict(schema='approved.curriculum.world-contract.v1',status='world_bindings_passed_not_collection_permission',proof=proof,worlds=worlds,static_cache_scope='Generic CAD/water + dynamic 16 shoreline proxies; map generated at Environment.new_world and passed to actual scenery renderer. Not a cached baked coastline.',models=dict(basic=basic,hard=hard),source_hashes={str(Path(inspect.getfile(x))):sha(inspect.getfile(x))for x in [environment.Environment,rendering.ReviewRenderer,World]},setup_only=True,task_actions_executed=False,physics_or_scoring_changed=False,elapsed_s=time.monotonic()-begin)
    (OUT/'proof.json').write_text(json.dumps(report,indent=2));(OUT/'plan.json').write_text(json.dumps(dict(schema='approved.curriculum.collection-plan.v1',jobs=plans,worlds=worlds,maximum_workers=8,maximum_total=40,original_target=64,quantity_reduced_for_latest_user_8h_warning=True,collection_stop_utc='2026-10-20T09:00:00Z',delivery_target_utc='2026-10-20T13:00:00Z',requires_purpose_gate_before_launch=True,source_revision='search_v33'),indent=2));print(json.dumps({k:v for k,v in report.items()if k not in ['proof','worlds','models','source_hashes']}),flush=True)
if __name__=='__main__':main()
