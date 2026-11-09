import transport
code="""
from pathlib import Path
import json
R=Path(__ROOT__)
for name in ['visible_start','search_near','search_mid','search_far','search_distractors','yaw_resync','tilt_loss','learner_struggle']:
 p=R/'search_v46/pilots'/name/'steps.jsonl'
 if not p.exists():print(name,'setup');continue
 with p.open('rb')as f:f.seek(max(0,p.stat().st_size-120000));lines=f.read().splitlines()
 try:
  r=json.loads(lines[-1]);d=r['output'].get('learner_diagnostics')or{};g=d.get('dagger')or{};print(name,r.get('task_time_s'),d.get('control_phase'),d.get('actual_command_owner'),d.get('expert_observable_target_confirmed'),g.get('ownership'),g.get('struggle_evidence',{}).get('unverified_descent'))
 except Exception as e:print(name,str(e))
print('TERMINAL',(R/'terminal_handoff_v46/state.json').read_text())
""".replace('__ROOT__',repr(transport.REMOTE))
print(transport.vm.ssh(transport.vm.PYTHON,'-c',code,capture_output=True,text=True).stdout)
