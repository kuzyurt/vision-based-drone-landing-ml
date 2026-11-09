"""Compact owned staged-data progress; never opens an active HDF5 writer."""
from pathlib import Path
import collections,json
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'curriculum_v23'
state=json.loads((OUT/'collection_state.json').read_text());done=state.pop('completed',[])
result=dict(state=state,completed_count=len(done),completed_by_role=dict(collections.Counter(j['role']for j in done)),
    completed_outcomes=dict(collections.Counter(j['result']['outcome']for j in done)),live=[])
for active in state.get('active',[]):
    name=active if isinstance(active,str)else active['name'];ep=OUT/'episodes'/name;trace=ep/'steps.jsonl'
    item=dict(name=name,producer_receipt_present=(ep/'staged_production_receipt.json').exists(),
              actual_hook_assertions_passed=(ep/'native_hook_bindings.json').exists())
    if trace.exists()and trace.stat().st_size:
        with trace.open('rb')as f:f.seek(max(0,trace.stat().st_size-524288));tail=f.read().splitlines()
        for line in reversed(tail):
            try:row=json.loads(line);break
            except(ValueError,UnicodeDecodeError):continue
        else:row=None
        if row:
            d=row['output'].get('learner_diagnostics')or{};dd=d.get('dagger')or{}
            item.update(task_s=round(row['task_time_s'],2),row_role=row.get('role'),split=row.get('split'),
                owner=dd.get('ownership',{}).get('owner','observable_expert'),phase=d.get('control_phase'),
                annotation_bytes=(ep/'capture_annotations.jsonl').stat().st_size if(ep/'capture_annotations.jsonl').exists()else 0)
    result['live'].append(item)
if state['status']=='failed':
    result['coordinator_tail']=(OUT/'coordinator.log').read_text()[-4000:]
    logs=sorted(OUT.glob('*.log'),key=lambda p:p.stat().st_mtime,reverse=True)
    result['worker_log_tails']={p.name:p.read_text()[-2200:]for p in logs[:3]}
print(json.dumps(result,indent=2))
