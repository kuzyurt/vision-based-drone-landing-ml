"""Same V33 actor/weights; qualified vertical launch under the declared start."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;PREV=ROOT/'search_v33/sources';NEW=ROOT/'search_v34/sources';OUT=ROOT/'search_v34'
assert not NEW.exists();NEW.mkdir(parents=True)
for name in ['target_learning','collection_pipeline']:shutil.copytree(PREV/name,NEW/name)
s=(PREV/'run_semantic_collection_v33.py').read_text();a='    base_env=episode.Environment\n    class SceneEnvironment(base_env):';b="    base_env=episode.Environment\n    from mission_setup import VerticalLaunchEnvironment\n    assert VerticalLaunchEnvironment.__mro__[1]is base_env\n    VerticalLaunchEnvironment.audit_directory=out\n    class SceneEnvironment(VerticalLaunchEnvironment):"
assert s.count(a)==1;s=s.replace(a,b);compile(s,'run_semantic_collection_v34.py','exec');(NEW/'run_semantic_collection_v34.py').write_text(s)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(NEW/'target_learning/expert_adapter_v33.py')==sha(PREV/'target_learning/expert_adapter_v33.py')
(OUT/'source_receipt.json').write_text(json.dumps(dict(actor_checkpoint_unchanged=True,physics_and_scoring_unchanged=True,mission_safety_thresholds_unchanged=True,preparation_only_change='Qualified VerticalLaunchEnvironment starts physically on the launch pad below prescribed airborne initial XY; no lateral ferry/home-distance mismatch.',sources={p.relative_to(NEW).as_posix():sha(p)for p in NEW.rglob('*.py')}),indent=2))
env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only','EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v33/runtime_probe.json','PYTHONPATH':str(NEW)+':'+str(OLD),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
args=[sys.executable,str(NEW/'run_semantic_collection_v34.py'),'--name','approved_curriculum_20261020/search_v34/far_vertical','--scenario-file',str(ROOT/'semantic_pilots/search_far_scenario.json'),'--semantic-contract',str(ROOT/'semantic_pilots/search_far_contract.json'),'--instance','244','--scene','basic','--omit-overview']
with(OUT/'far_vertical.log').open('x')as log:p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(OUT/'state.json').write_text(json.dumps(dict(status='running',pid=p.pid,case='far_vertical',actor_unchanged=True,training_started=False)));print(json.dumps(dict(pid=p.pid,revision='search_v34_vertical_initial_setup')),flush=True)
