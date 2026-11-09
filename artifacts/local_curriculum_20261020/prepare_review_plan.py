"""Freeze one actual review per E01-E11; E04a is a detail of E04, E12 excluded."""
import local_paths
import datetime,hashlib,json,zipfile

def main():
    r=local_paths.ROOT;out=r/'review_batch_v1';out.mkdir(exist_ok=False);jobs=out/'jobs';jobs.mkdir()
    backup=json.loads((local_paths.PREVIOUS/'policy_backups/LATEST_VERIFIED.json').read_text())
    with zipfile.ZipFile(backup['local_archive'])as z:
        def scenario(name):return json.loads(z.read('new_experiment/search_v46/pilots/'+name+'_scenario.json'))
        specs=[('E01_nominal','visible_start','basic','visible','expert',False,None),('E02_distractors','search_distractors','hard','outside_camera','expert',False,None),('E03_yaw','yaw_resync','hard','visible','expert',False,'gimbal_pan'),('E04_close_loss','tilt_loss','hard','visible','expert',False,'gimbal_tilt'),('E05_visible_start','visible_start','basic','visible','expert',False,None),('E06_search_near','search_near','basic','outside_camera','expert',False,None),('E07_search_mid','search_mid','basic','outside_camera','expert',False,None),('E08_search_far','search_far','basic','outside_camera','expert',False,None),('E09_terminal_handoff','visible_start','basic','visible','dagger',True,None),('E10_natural_rescue','learner_struggle','hard','visible','dagger',False,None),('E11_expired_memory','expired_memory','hard','visible','dagger',True,'gimbal_tilt')]
        entries=[]
        for i,(name,parent,scene,view,mode,prefix,fault)in enumerate(specs):
            s=scenario(parent);s['name']='windows_review_'+name
            if name=='E05_visible_start':s['seed']=3200000050
            lohi=[40.,60.]if s['distance']>=40 else[20.,40.]if s['distance']>=28 else[12.,30.]if s['distance']==20 else[5.,20.]
            job=dict(name=name,scenario=s,scene=scene,initial_target=view,distance_band=lohi,mode=mode,prefix=prefix,fault=fault,fault_duration=2. if name=='E11_expired_memory'else 1.2 if name=='E03_yaw'else 1.6,foreground_board=name=='E10_natural_rescue',instance=710+i,target_present=True,target_hidden=False,exclude_home_commands=True,training_eligible=False,requires_actual_metric_loss=name in ['E04_close_loss','E11_expired_memory'],requires_actual_learner_struggle_then_expert=name in ['E10_natural_rescue','E11_expired_memory'],requires_no_unnecessary_post_handoff_assistance=name=='E09_terminal_handoff',glare_strength=1.4 if name=='E02_distractors'else .9)
            p=jobs/(name+'.json');p.write_text(json.dumps(job,indent=2));entries.append(dict(name=name,job=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    files={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.glob('*.py')}
    files.update({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.glob('*.mjs')})
    plan=dict(schema='windows.native.first.review.batch.v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),jobs=entries,source_hashes=files,maximum_render_annotation_workers_measured=2,maximum_actual_expert_workers_initial=1,reason='Expert + PX4 memory has not been measured as a two-worker cohort; admit conservatively with live guards',E04a='same actual E04 flight, event-centered detail only',E12='excluded: no new home-return/landing training or rendering',review_only=True,training_or_bulk_authorized_by_this_manifest=False,known_development=True,independent_final_benchmark=False,original_physics_and_scoring_unchanged=True,platform='Windows Python MuJoCo + real pinned PX4 WASM Windows Node, no Linux',Windows_native_Linux_parity_claimed=False)
    (out/'plan.json').write_text(json.dumps(plan,indent=2));(out/'state.json').write_text(json.dumps(dict(status='plan_frozen_preparing_first_annotation_probe',remaining=[j['name']for j in entries],completed=[],active=[]),indent=2));print(json.dumps(dict(jobs=len(entries),review_only=True)))

if __name__=='__main__':main()
