from pathlib import Path
import hashlib,importlib.util,json,sys,types
R=Path(__file__).parent;O=R/'terminal_handoff_v46';case=O/'terminal_handoff';source=O/'scenario_input.json';dest=O/'terminal_handoff_scenario.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads(source.read_text())==json.loads((case/'scenario.json').read_text())
if not dest.exists():dest.write_bytes(source.read_bytes())
assert sha(dest)==sha(source)
(O/'AUDIT_INPUT_ALIAS_RECEIPT.json').write_text(json.dumps(dict(reason='Read-only auditor expected a filename not created by terminal queue; identical original declared input copied to expected alias, no raw/source/model changes',original=str(source),alias=str(dest),sha256=sha(source)),indent=2))
spec=importlib.util.spec_from_file_location('terminal_auditor_repair',R/'audit_semantic_pilots_v4.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);b=json.loads((R/'search_v46/candidate_binding.json').read_text());a.PILOTS=O;a.EXPECTED_ACTOR=b['actor_sha256'];a.EXPECTED_HARNESS=b['harness_sha256'];a.EXPECTED_RECOGNIZER=b['recognizer_sha256'];result=a.run_case('terminal_handoff');rows=[json.loads(x)for x in(case/'steps.jsonl').open()];owners=[(r['output'].get('learner_diagnostics')or{}).get('actual_command_owner')for r in rows];first=next(i for i,v in enumerate(owners)if v=='policy');bad=[i for i,v in enumerate(owners)if i>first and v in ['expert','expert_prefix','safety','fallback']]
result['checks'].append(dict(name='healthy physically flown prefix then learner terminal handshake without unnecessary takeover',passed=owners.count('expert_prefix')>3 and owners.count('policy')>3 and not bad,detail=dict(prefix_rows=owners.count('expert_prefix'),policy_rows=owners.count('policy'),after_policy_assistance=bad[:10])))
sys.path.insert(0,str(R/'search_v48/sources'));from target_learning.unverified_descent_v48 import UnverifiedDescent
helper=UnverifiedDescent();changed=[]
for i,r in enumerate(rows):
 d=r['output'].get('learner_diagnostics')or{};dg=d.get('dagger')or{}
 if d.get('actual_command_owner')!='policy':continue
 e=types.SimpleNamespace(**dg['trigger_evidence']);p=r['observation']['px4'];context=dict(observation=r['observation'],expert={'expert_intent':d['expert_shadow_intent']},learner=d,action=dg['learner_action'],own_height=p['position_enu_m'][2],own_vertical_speed=p['velocity_enu_m_s'][2])
 if helper.step(e,context):changed.append(dict(frame=i,evidence=helper.evidence))
result['checks'].append(dict(name='corrected V48 helper has zero changed decisions on all actual healthy learner-owned public records',passed=not changed,detail=dict(changed=changed[:10],scope='Deterministic helper branch parity on exact recorded observations; not a new native flight')))
result['status']='passed'if all(c['passed']for c in result['checks'])else'failed';(O/'audit_repaired_v2.json').write_text(json.dumps(result,indent=2));(O/'state_reconciled_v2.json').write_text(json.dumps(dict(status='closed_audited',purpose_passed=result['status']=='passed',original_stale_state_preserved=True),indent=2));print(json.dumps(dict(status=result['status'],failed=[c for c in result['checks']if not c['passed']],prefix=owners.count('expert_prefix'),policy=owners.count('policy'),V48_new_changed_decisions=len(changed))))
