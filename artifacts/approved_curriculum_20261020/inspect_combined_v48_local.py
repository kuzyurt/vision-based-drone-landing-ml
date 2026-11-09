import transport
code="""
from pathlib import Path
import json,psutil
R=Path(__ROOT__)
for scope,names in [('search_v46',['search_mid','search_far','search_distractors','tilt_loss']),('search_v48',['learner_struggle','expired_memory'])]:
 for name in names:
  p=R/scope/'pilots'/name/'steps.jsonl'
  if not p.exists():print(scope,name,'setup');continue
  with p.open('rb')as f:f.seek(max(0,p.stat().st_size-180000));lines=f.read().splitlines()
  try:
   r=json.loads(lines[-1]);d=r['output'].get('learner_diagnostics')or{};dg=d.get('dagger')or{};print(scope,name,'task',r.get('task_time_s'),'phase',d.get('control_phase'),'owner',d.get('actual_command_owner'),'ID',d.get('expert_observable_target_confirmed'),'z',r['observation']['px4']['position_enu_m'][2],'intent',d.get('expert_intent'),'ownership',dg.get('ownership'))
  except Exception as e:print(name,str(e))
print('terminal', (R/'terminal_handoff_v46/state.json').read_text());print('RAM',psutil.virtual_memory().available/1024**3)
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
