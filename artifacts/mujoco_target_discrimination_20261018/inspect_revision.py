"""Compact read-only coordinator/process evidence, not a polling loop."""
from pathlib import Path
import argparse,getpass,json,os,socket
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--revision',required=True);a=p.parse_args();name='v'+str(a.revision)
state=root/f'expert_{name}_pipeline_state.json';value=json.loads(state.read_text())
result=value.pop('result',None)
if result and 'validation'in result:
    v=result['validation'];value['recognition']=dict(selected_epoch=result.get('selected_epoch'),checkpoint_sha256=result.get('checkpoint_sha256'),
        known_targets=v.get('known_targets'),object_recall=v.get('object_recall'),passed=v.get('expert_gate_passed'),
        selected=v.get('selected_operating_point'),diagnostic=v.get('diagnostic_best_effort'),unscored=v.get('unscored_old_target_instances'))
else:value['result']=result
processes=[]
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit():continue
    try:
        if entry.stat().st_uid!=os.getuid():continue
        command=(entry/'cmdline').read_bytes().replace(b'\x00',b' ').decode(errors='replace').strip()
        if command and (str(root)in command or '/px4'in command):processes.append(dict(pid=int(entry.name),command=command[:300]))
    except(FileNotFoundError,ProcessLookupError,PermissionError):pass
live=None
trace=root/('expert_visible_native_'+name)/'steps.jsonl'
if trace.exists()and trace.stat().st_size:
 with trace.open('rb')as f:
  f.seek(max(0,trace.stat().st_size-65536));tail=f.read().splitlines()
 for line in reversed(tail):
  try:row=json.loads(line);break
  except(ValueError,UnicodeDecodeError):continue
 else:row=None
 if row is not None:
  d=row['output'].get('learner_diagnostics',{});live=dict(frame=row['frame_index'],task_s=row['task_time_s'],
   actual_action=row['output'].get('executed_action'),requested_action=row['output'].get('learner_action'),outer_intervention=row['output'].get('intervention'),
   expert_phase=d.get('expert_intent',{}).get('phase'),identity=d.get('expert_observable_target_confirmed'),metric=d.get('metric_valid'),own_position=row['observation']['px4'].get('position_enu_m'))
print(json.dumps(dict(live=live,whoami=getpass.getuser(),hostname=socket.gethostname(),state=value,owned_processes=processes),indent=2))
