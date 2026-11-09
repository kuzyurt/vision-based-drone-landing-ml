from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).parent;P=R/'search_v48/sources';N=R/'search_v56/sources';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not N.exists();assert json.loads((R/'survey_component_test_v51.json').read_text())['status']=='passed';N.mkdir(parents=True)
for n in ['target_learning','collection_pipeline']:shutil.copytree(P/n,N/n,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['inspection_feedback_v51.py','object_verifier_v55.py']:shutil.copy2(R/n,N/'target_learning'/n)
s=(P/'target_learning/expert_adapter_v48.py').read_text().replace('from .inspection_feedback_v25 import InspectionFeedback','from .inspection_feedback_v51 import InspectionFeedback')
a='            from .object_verifier_v12 import ObjectVerifier,verify';b="            if saved['verifier_mode']=='rgb_intersection_v55':\n                from .object_verifier_v55 import ObjectVerifier,verify\n            else:\n                from .object_verifier_v12 import ObjectVerifier,verify";assert s.count(a)==1;s=s.replace(a,b);(N/'target_learning/expert_adapter_v56.py').write_text(s)
for a,b in [('run_semantic_collection_v48.py','run_semantic_collection_v56.py'),('probe_expert_v48.py','probe_expert_v56.py')]: (N/b).write_text((P/a).read_text().replace('expert_adapter_v48','expert_adapter_v56'))
for p in N.rglob('*.py'):compile(p.read_text(),str(p),'exec')
hashes={p.relative_to(N).as_posix():sha(p)for p in N.rglob('*')if p.is_file()};(N/'source_hashes.json').write_text(json.dumps(hashes,indent=2));(N.parent/'derivation.json').write_text(json.dumps(dict(parent='search_v48',changes=['Existing completed survey transition called when negative inspection requests a NEWsurvey; retained/fullness invariants unchanged','Optional fixed RGB posterior intersection, no threshold fitting, no extra training epochs, no target or wrong-design confidence increase; only if full three-group validation passes'],physics_confidence_thresholds_and_mission_budget_unchanged=True,old_failed_single_model_results_remain_false=True,no_failed_teacher_RGB_training=True),indent=2));print('V56 prepared; NO native launch or checkpoint selection yet')
