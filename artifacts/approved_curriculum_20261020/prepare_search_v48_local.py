from pathlib import Path
R=Path(__file__).parent
s=(R/'unverified_descent_v43.py').read_text().replace('class UnverifiedDescent:', 'class UnverifiedDescent:')
s=s.replace("if e.target_confirmed or not fresh", "qualified_teacher_landing=bool(e.target_confirmed and e.pad_pose_valid and context['expert'].get('expert_intent',{}).get('allow_descent',False))\n        if qualified_teacher_landing or not fresh")
s=s.replace('sustained_actual_descent_without_target_identity','sustained_actual_descent_without_qualified_landing').replace('teacher_design_identity_confirmed=False','teacher_design_identity_confirmed=bool(e.target_confirmed),teacher_descent_authorized=qualified_teacher_landing')
(R/'unverified_descent_v48.py').write_text(s)
s=(R/'takeover_v46.py').read_text().replace('.unverified_descent_v43','.unverified_descent_v48').replace('sustained_actual_descent_without_target_identity','sustained_actual_descent_without_qualified_landing');(R/'takeover_v48.py').write_text(s)
s='''from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).parent;P=R/'search_v46/sources';N=R/'search_v48/sources'
def main():
 assert not N.exists();N.mkdir(parents=True)
 for d in ['target_learning','collection_pipeline']:shutil.copytree(P/d,N/d,ignore=shutil.ignore_patterns('__pycache__'))
 for n in ['takeover_v48.py','unverified_descent_v48.py']:shutil.copy2(R/n,N/'target_learning'/n)
 for a,b in [('target_learning/dagger_v46.py','target_learning/dagger_v48.py'),('target_learning/expert_adapter_v46.py','target_learning/expert_adapter_v48.py'),('run_semantic_collection_v46.py','run_semantic_collection_v48.py'),('probe_expert_v46.py','probe_expert_v48.py')]:
  s=(P/a).read_text().replace('takeover_v46','takeover_v48').replace('dagger_v46','dagger_v48').replace('expert_adapter_v46','expert_adapter_v48');(N/b).write_text(s)
 for f in N.rglob('*.py'):compile(f.read_text(),str(f),'exec')
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();hashes={p.relative_to(N).as_posix():sha(p)for p in N.rglob('*')if p.is_file()};(N/'source_hashes.json').write_text(json.dumps(hashes,indent=2))
 assert (N/'target_learning/expert_adapter_v48.py').read_bytes()==(P/'target_learning/expert_adapter_v46.py').read_bytes()
 (N.parent/'derivation.json').write_text(json.dumps(dict(parent='search_v46',recognizer_unchanged=True,standalone_teacher_actor_bytes_identical=True,change='Actual sustained >=1m descent without currently qualified teacher landing permission; global identity alone is insufficient',physics_confidence_time_gates_unchanged=True,no_failed_rgb_training=True,affected_paths=['DAgger only'],standalone_teacher_evidence_may_be_reused_only_with_exact_model_actor_and_execution_path_proof=True),indent=2));print('V48 built, not launched')
if __name__=='__main__':main()
''';(R/'build_search_v48.py').write_text(s)
