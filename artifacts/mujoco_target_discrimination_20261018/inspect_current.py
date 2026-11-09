"""Compact read-only coordinator/process evidence, not a polling loop."""
from pathlib import Path
import argparse,getpass,json,os,socket
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--revision',type=int,required=True);a=p.parse_args();name='v'+str(a.revision)
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
print(json.dumps(dict(whoami=getpass.getuser(),hostname=socket.gethostname(),state=value,owned_processes=processes),indent=2))
