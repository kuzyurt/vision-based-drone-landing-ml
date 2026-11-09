"""Freeze conservative V34 controller, 18/6/35 coverage and new RGB weights."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent;PREV=ROOT/'search_v34/sources';NEW=ROOT/'search_v39/sources'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not NEW.exists();NEW.mkdir(parents=True)
    for n in ['target_learning','collection_pipeline']:shutil.copytree(PREV/n,NEW/n,ignore=shutil.ignore_patterns('__pycache__'))
    s=(NEW/'target_learning/protocol_elevation_v33.py').read_text();assert 'SCAN_TILT_BANDS_DEG=(6.,18.,35.)'in s;s=s.replace('SCAN_TILT_BANDS_DEG=(6.,18.,35.)','SCAN_TILT_BANDS_DEG=(18.,6.,35.)');(NEW/'target_learning/protocol_elevation_v39.py').write_text(s)
    s=(NEW/'target_learning/protocol_memory_elevation_v33.py').read_text().replace('.protocol_elevation_v33','.protocol_elevation_v39');(NEW/'target_learning/protocol_memory_elevation_v39.py').write_text(s)
    s=(NEW/'target_learning/expert_adapter_v33.py').read_text().replace('.protocol_memory_elevation_v33','.protocol_memory_elevation_v39');assert 'declared_red_exclusion'not in s;(NEW/'target_learning/expert_adapter_v39.py').write_text(s)
    s=(PREV/'run_semantic_collection_v34.py').read_text().replace('expert_adapter_v33','expert_adapter_v39');(NEW/'run_semantic_collection_v39.py').write_text(s)
    s=(ROOT/'search_v33/sources/probe_expert_v33.py').read_text().replace('expert_adapter_v33','expert_adapter_v39');(NEW/'probe_expert_v39.py').write_text(s)
    for f in NEW.rglob('*.py'):compile(f.read_text(),str(f),'exec')
    sources={f.relative_to(NEW).as_posix():sha(f)for f in NEW.rglob('*.py')};(NEW/'source_hashes.json').write_text(json.dumps(sources,indent=2));(NEW.parent/'derivation.json').write_text(json.dumps(dict(parent='search_v34',sources=sources,changes=['New separately validated MuJoCo RGB verifier','First scan18deg, then6/35deg with actual encoder/distinct yaw requirements','V35 ad hoc color exclusion removed; learned identity and original thresholds govern, no truth inputs'],physics_changed=False,mission_time_changed=False,teacher_data_eligibility_granted=False),indent=2))
    s=(ROOT/'queue_semantic_pilots.py').read_text().replace("OUT = ROOT / 'semantic_pilots'","OUT = ROOT / 'search_v39/pilots'").replace("'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only'","'EXPERT_RECOGNIZER_ROOT':'approved_curriculum_20261020/perception_training_v38'").replace("'EXPERT_RUNTIME_GATE':'expert_fix_review_20261019/v31/runtime_probe.json'","'EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v39/runtime_probe.json'").replace("str(V31/'sources')+':'+str(OLD)","str(ROOT/'search_v39/sources')+':'+str(OLD)").replace("str(ROOT/'run_semantic_collection_v32.py')","str(ROOT/'search_v39/sources/run_semantic_collection_v39.py')").replace("'approved_curriculum_20261020/semantic_pilots/'+name","'approved_curriculum_20261020/search_v39/pilots/'+name").replace('instance=230+i','instance=100+i').replace('>3000','>2200')
    s=s.replace("                active.remove(t)","                active.remove(t)\n                if results[-1]['result'] and results[-1]['result']['outcome'] in ['collision_failure','water_strike']:raise RuntimeError('Physical safety stop '+t['name'])")
    s=s.replace('def main():','def run_flights():',1).replace("if __name__=='__main__':\n    main()", """if __name__=='__main__':
    result=json.loads((ROOT/'perception_training_v38/result.json').read_text());assert result['improved_validation_candidate']
    point=result['selected_validation']['selected_operating_point'];assert point['target_recall']>=.4 and all(point[k]==0 for k in ['wrong_object_acceptances','ambiguous_acceptances','background_acceptances'])
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'PYTHONPATH':str(ROOT/'search_v39/sources')+':'+str(OLD),'PYTHONDONTWRITEBYTECODE':'1'}
    with(ROOT/'search_v39/runtime_probe.log').open('x')as log:
        subprocess.run([sys.executable,str(ROOT/'search_v39/sources/probe_expert_v39.py'),'--recognizer-root','approved_curriculum_20261020/perception_training_v38','--output','approved_curriculum_20261020/search_v39/runtime_probe.json'],cwd=OLD,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    assert json.loads((ROOT/'search_v39/runtime_probe.json').read_text())['status']=='runtime_hook_probe_passed'
    run_flights()""")
    (ROOT/'queue_search_v39.py').write_text(s);compile(s,'queue_search_v39.py','exec');print(json.dumps(dict(status='built_not_launched',actor_sha256=sources['target_learning/expert_adapter_v39.py'])))
if __name__=='__main__':main()
