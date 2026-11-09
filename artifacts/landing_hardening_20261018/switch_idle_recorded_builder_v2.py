"""Replace ONLY the still-idle owned orchestration process, preserving sources."""
from pathlib import Path
import datetime,hashlib,json,psutil,shutil,subprocess,sys
r=Path(__file__).resolve().parent
state=json.loads((r/'combined_r14_builder_state.json').read_text())
assert state['status']=='waiting_for_owned_paired_audit',state
p=psutil.Process(439489);assert any(s.endswith('/continue_combined_r14.py')for s in p.cmdline())
assert not p.children(recursive=True),'Builder already started child work'
assert shutil.disk_usage(r).free>300*1024**3,'Insufficient room for preserving actual RGB'
p.terminate();p.wait(timeout=5)
receipt=dict(status='idle_orchestrator_replaced_before_any_new_flights',old_pid=439489,old_state=state,original_source_preserved=True,reason='Frozen E cases have recording disabled; existing --record-all-rgb recorder flag preserves actual camera evidence, especially failures. Scenarios/physics/inputs/acceptance unchanged.',e_world_plan_sha256=hashlib.sha256((r/'fresh_edge_E60.json').read_bytes()).hexdigest(),additional_recorder_flag='--record-all-rgb',free_gib=shutil.disk_usage(r).free/1024**3,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(r/'combined_builder_v1_retirement.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert not(r/'combined_r14_builder_v2_state.json').exists()
with(r/'continue_combined_r14_v2.log').open('x')as log:
    child=subprocess.Popen([sys.executable,str(r/'continue_combined_r14_v2.py')],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(r/'combined_builder_v2_receipt.json').write_text(json.dumps({'pid':child.pid,'source_sha256':hashlib.sha256((r/'continue_combined_r14_v2.py').read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps({'new_idle_builder_pid':child.pid,'record_all_rgb':True,'sources_and_scenario_plan_preserved':True}))
