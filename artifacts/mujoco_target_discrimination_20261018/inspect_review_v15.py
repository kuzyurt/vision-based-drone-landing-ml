from pathlib import Path
import json,getpass,socket
root=Path(__file__).resolve().parent
result=dict(whoami=getpass.getuser(),hostname=socket.gethostname(),state=json.loads((root/'expert_v15_pipeline_state.json').read_text()),cases=[])
for case in ['hard','recovery','dagger']:
    directory=root/('expert_visible_native_v15_'+case);v=dict(case=case)
    for name in ['preview_result.json','scene_spawn_receipt.json']:
        if(directory/name).exists():v[name]=json.loads((directory/name).read_text())
    trace=directory/'steps.jsonl'
    if trace.exists()and trace.stat().st_size:
        with trace.open('rb')as f:f.seek(max(0,trace.stat().st_size-100000));lines=f.read().splitlines()
        for line in reversed(lines):
            try:row=json.loads(line);break
            except(ValueError,UnicodeDecodeError):continue
        else:row=None
        if row:
            d=row['output'].get('learner_diagnostics')or{}
            v['live']=dict(task_s=row['task_time_s'],frame=row['frame_index'],phase=d.get('expert_intent',d.get('expert_shadow_intent',{})).get('phase'),identity=d.get('expert_observable_target_confirmed'),metric=d.get('metric_valid'),owner=d.get('actual_command_owner'),fault_triggered=d.get('evaluation_fault_triggered'),fault_frames=d.get('evaluation_fault_frames'),outer_intervention=row['output'].get('intervention'))
    log=root/('expert_visible_native_v15_'+case+'.log')
    if log.exists():v['log_tail']=log.read_text(errors='replace')[-1800:]
    result['cases'].append(v)
print(json.dumps(result,indent=2))
