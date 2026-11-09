from pathlib import Path
import hashlib,json,subprocess,sys
R=Path(__file__).parent;O=R/'search_v46';assert not(O/'launch.json').exists()
assert json.loads((O/'source_test_receipt.json').read_text())['status']=='passed'
r=json.loads((R/'perception_training_v45/result.json').read_text());assert r['improved_validation_candidate'],'No technically admissible new checkpoint; do not fly'
point=r['selected_validation']['selected_operating_point'];assert point['target_recall']>=.4 and all(point[k]==0 for k in ['wrong_object_acceptances','ambiguous_acceptances','background_acceptances'])
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();checkpoint=R/'perception_training_v45/best.pt';assert sha(checkpoint)==r['selected_sha256']
binding=dict(checkpoint=str(checkpoint),recognizer_sha256=sha(checkpoint),actor_sha256=sha(O/'sources/target_learning/expert_adapter_v46.py'),harness_sha256=sha(O/'sources/run_semantic_collection_v46.py'),source_manifest_sha256=sha(O/'sources/source_hashes.json'),prior_sha256=sha(O/'sources/target_learning/fixed_own_aircraft.npz'),experimental_only=True,created_before_any_native_flight=True)
(O/'candidate_binding.json').write_text(json.dumps(binding,indent=2))
with(O/'coordinator.log').open('x')as log:p=subprocess.Popen([sys.executable,str(R/'queue_search_v46.py')],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(O/'launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)))
