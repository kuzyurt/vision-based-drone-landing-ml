from pathlib import Path
p=Path(__file__).parent
s=(p/'audit_semantic_pilots_v3.py').read_text();s=s.replace("NAMES = ('search_near'","EXPECTED_RECOGNIZER='c87dca7541d361b183ce45da5f7756bdc5a358aaf544fb2bc5c3fc08bad1e0e3'\nNAMES = ('search_near'")
s=s.replace("result.get('recognizer_sha256') == 'c87dca7541d361b183ce45da5f7756bdc5a358aaf544fb2bc5c3fc08bad1e0e3'","result.get('recognizer_sha256') == EXPECTED_RECOGNIZER")
(p/'audit_semantic_pilots_v4.py').write_text(s)
s=(p/'audit_gate_v36.py').read_text().replace("ROOT/'search_v35/audit_v36'","ROOT/'search_v39/audit'")
a="    wait(638301)\n    wait(json.loads((ROOT/'search_v35/gcs_retry_launch.json').read_text())['pid'])\n    retry=ROOT/'search_v35/infrastructure_retries/state.json'\n    assert retry.exists();wait(json.loads(retry.read_text())['coordinator_pid'])"
b="    wait(json.loads((ROOT/'search_v39/launch.json').read_text())['pid'])\n    binding=json.loads((ROOT/'search_v39/candidate_binding.json').read_text());assert sha(binding['checkpoint'])==binding['recognizer_sha256']"
assert a in s;s=s.replace(a,b).replace('audit_semantic_pilots_v3.py','audit_semantic_pilots_v4.py').replace("src=ROOT/'search_v35/sources';a.EXPECTED_ACTOR=sha(src/'target_learning/expert_adapter_v35.py');a.EXPECTED_HARNESS=sha(src/'run_semantic_collection_v35.py');results=[];sheets=[]","src=ROOT/'search_v39/sources';a.EXPECTED_ACTOR=binding['actor_sha256'];a.EXPECTED_HARNESS=binding['harness_sha256'];a.EXPECTED_RECOGNIZER=binding['recognizer_sha256'];results=[];sheets=[]")
s=s.replace("a.PILOTS=ROOT/'search_v35'/('infrastructure_retries'if name in ['yaw_resync','tilt_loss','learner_struggle','search_distractors']else'pilots')","a.PILOTS=ROOT/'search_v39/pilots'").replace('P02_v35_actual_purpose','P02_v39_actual_purpose').replace("infrastructure_failures_preserved='Fault cases used out-of-range MAVLink IDs before task; distractor case used conflicting GCS ID255 and produced zero task rows. Exact actor/harness/scenarios retried with IDs231-234 only; original failures retained.'","recognizer_sha256=binding['recognizer_sha256']")
(p/'audit_gate_v39.py').write_text(s)
for n in ['audit_semantic_pilots_v4.py','audit_gate_v39.py']:compile((p/n).read_text(),n,'exec')
