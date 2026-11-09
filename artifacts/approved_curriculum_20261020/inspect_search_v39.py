from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent));import transport
code="""
from pathlib import Path
import json,subprocess
p=Path(__ROOT__)/'search_v39'
for n in ['launch.json','coordinator.log','runtime_probe.json','pilots/state.json','audit/state.json','audit.log']:
 q=p/n
 if not q.exists():print(n,'MISSING');continue
 if n=='runtime_probe.json':
  d=json.loads(q.read_text());d.pop('rows',None);d.pop('actor_package_source_hashes',None);print(n,json.dumps(d))
 else:print(n,q.read_text()[-5000:])
for case in (p/'pilots').glob('*/steps.jsonl'):
 with case.open('rb')as f:
  f.seek(max(0,case.stat().st_size-160000));lines=f.read().splitlines()
 try:r=json.loads(lines[-1]);d=r['output'].get('learner_diagnostics')or{};print('CASE',case.parent.name,r.get('task_time_s'),d.get('control_phase'),'ID',d.get('expert_observable_target_confirmed'),'metric',d.get('metric_confirmed'),'owner',d.get('actual_command_owner'))
 except Exception as e:print('incomplete',case.parent.name,str(e))
print('resources',subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader,nounits'],text=True))
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
