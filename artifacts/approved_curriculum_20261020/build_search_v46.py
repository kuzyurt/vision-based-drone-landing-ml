from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).parent
P=R/'search_v42/sources';N=R/'search_v46/sources'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 assert not N.exists();N.mkdir(parents=True)
 for d in ['target_learning','collection_pipeline']:shutil.copytree(P/d,N/d,ignore=shutil.ignore_patterns('__pycache__'))
 for name in ['takeover_v46.py','unverified_descent_v43.py']:shutil.copy2(R/name,N/'target_learning'/name)
 s=(P/'target_learning/dagger_v21.py').read_text().replace('from .takeover_v21 import StruggleTakeover','from .takeover_v46 import StruggleTakeover');(N/'target_learning/dagger_v46.py').write_text(s)
 s=(P/'target_learning/expert_adapter_v42.py').read_text();(N/'target_learning/expert_adapter_v46.py').write_text(s)
 s=(P/'run_semantic_collection_v42.py').read_text().replace('expert_adapter_v42','expert_adapter_v46').replace('target_learning.dagger_v21','target_learning.dagger_v46');assert 'dagger_v46'in s;(N/'run_semantic_collection_v46.py').write_text(s)
 s=(P/'probe_expert_v42.py').read_text().replace('expert_adapter_v42','expert_adapter_v46');(N/'probe_expert_v46.py').write_text(s)
 for f in N.rglob('*.py'):compile(f.read_text(),str(f),'exec')
 hashes={f.relative_to(N).as_posix():sha(f)for f in N.rglob('*')if f.is_file()};(N/'source_hashes.json').write_text(json.dumps(hashes,indent=2))
 (N.parent/'derivation.json').write_text(json.dumps(dict(parent='search_v42',changes=['Measured sustained actual descent without teacher design ID now latches verification expert; not tiny startup descent','Fresh close/partial-view verifier only if separate V45 validation passes'],no_physics_confidence_or_time_relaxation=True,no_failed_rgb_training=True,public_replay_first_changed_task_s=14.24,does_not_predict_physical_rescue=True),indent=2))
 s=(R/'queue_search_v42.py').read_text().replace('search_v42','search_v46').replace('collection_v42','collection_v46').replace('probe_expert_v42','probe_expert_v46').replace('perception_training_v38','perception_training_v45').replace('instance=120+i','instance=140+i')
 # Always persist terminal failure and reap only this cohort's exact owned PX4.
 s=s.replace("if __name__=='__main__':", "if __name__=='__main__':",1)
 (R/'queue_search_v46.py').write_text(s)
 s=(R/'audit_gate_v42.py').read_text().replace('search_v42','search_v46').replace('expert_adapter_v42','expert_adapter_v46').replace('collection_v42','collection_v46').replace('P02_v42','P02_v46')
 old="return ((reason=='sustained_observed_wrong_object_pursuit'"
 new="u=e.get('unverified_descent')or{}\n                return ((reason=='sustained_actual_descent_without_target_identity'and u.get('actual_height_loss_m',0)>=1. and u.get('observed_descent_s',0)>=3. and u.get('distinct_capture_count',0)>=10 and u.get('after_one_metre_threshold_s',0)>=2. and u.get('teacher_design_identity_confirmed')is False)or(reason=='sustained_observed_wrong_object_pursuit'"
 assert old in s;s=s.replace(old,new);(R/'audit_gate_v46.py').write_text(s)
 for old,new in [('launch_audit_v42.py','launch_audit_v46.py')]: (R/new).write_text((R/old).read_text().replace('search_v42','search_v46').replace('audit_gate_v42','audit_gate_v46'))
 for f in [R/'queue_search_v46.py',R/'audit_gate_v46.py',R/'launch_audit_v46.py']:compile(f.read_text(),str(f),'exec')
 print('built V46 not launched')
if __name__=='__main__':main()
