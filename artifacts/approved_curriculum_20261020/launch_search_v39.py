from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parent;assert not(ROOT/'search_v39/launch.json').exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads((ROOT/'search_v39/source_test_receipt.json').read_text())['status']=='passed'
r=json.loads((ROOT/'perception_training_v38/result.json').read_text());checkpoint=ROOT/'perception_training_v38/best.pt';assert r['improved_validation_candidate']and sha(checkpoint)==r['selected_sha256'];p=r['selected_validation']['selected_operating_point'];assert p['target_recall']>=.4 and all(p[k]==0 for k in ['wrong_object_acceptances','ambiguous_acceptances','background_acceptances'])
binding=dict(checkpoint=str(checkpoint),recognizer_sha256=sha(checkpoint),actor_sha256=sha(ROOT/'search_v39/sources/target_learning/expert_adapter_v39.py'),harness_sha256=sha(ROOT/'search_v39/sources/run_semantic_collection_v39.py'),source_manifest_sha256=sha(ROOT/'search_v39/sources/source_hashes.json'),training_result_sha256=sha(ROOT/'perception_training_v38/result.json'),experimental_only=True,created_before_any_native_flight=True)
(ROOT/'search_v39/candidate_binding.json').write_text(json.dumps(binding,indent=2))
with(ROOT/'search_v39/coordinator.log').open('x')as log:p=subprocess.Popen([sys.executable,str(ROOT/'queue_search_v39.py')],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(ROOT/'search_v39/launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
