"""Compact actual ownership snapshot; --audit scans closed trajectories once."""
from pathlib import Path
from collections import Counter
import argparse,json
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--audit',action='store_true');a=p.parse_args()
state=json.loads((ROOT/'expert_v19_pipeline_state.json').read_text());output=dict(state=state,cases=[])
for name in ['natural','near_deck','near_deck_tilt']:
    path=ROOT/('expert_visible_native_v19_'+name);trace=path/'steps.jsonl';entry=dict(case=name)
    if not trace.exists():entry['trace']='not yet recording';output['cases'].append(entry);continue
    result=path/'preview_result.json'
    if a.audit and result.exists():
        rows=[json.loads(line)for line in trace.open()];owners=Counter();reasons=Counter();events=[];previous=None;faults=0
        for row in rows:
            d=row['output'].get('learner_diagnostics')or{};dd=d.get('dagger')or{};own=dd.get('ownership')or{}
            owner=own.get('owner','mission_or_other');owners[owner]+=1
            if own.get('reason'):reasons[own['reason']]+=1
            signature=(owner,own.get('reason'),d.get('actual_command_owner'))
            if signature!=previous:
                events.append(dict(frame=row['frame_index'],task_s=row['task_time_s'],owner=owner,
                    reason=own.get('reason'),actual_owner=d.get('actual_command_owner'),
                    learner_metric=dd.get('struggle_evidence',{}).get('learner_metric_now'),
                    evidence=dd.get('struggle_evidence'),prefix_handoff_s=dd.get('prefix_handoff_s')))
                previous=signature
            faults+=int(bool(d.get('evaluation_fault_active')))
        entry.update(result=json.loads(result.read_text()),owners=dict(owners),reasons=dict(reasons),
                     ownership_events=events,actual_fault_rows=faults,training_eligible=False,
                     note='Actual executed command and RGB audit still required; assisted never learner-only success')
        (path/'struggle_ownership_audit.json').write_text(json.dumps(entry,indent=2))
    else:
        with trace.open('rb')as f:f.seek(max(0,trace.stat().st_size-524288));tail=f.read().splitlines()
        for line in reversed(tail):
            try:row=json.loads(line);break
            except(ValueError,UnicodeDecodeError):continue
        else:row=None
        if row:
            d=row['output'].get('learner_diagnostics')or{};dd=d.get('dagger')or{}
            entry.update(task_s=row['task_time_s'],ownership=dd.get('ownership'),prefix_finished=dd.get('prefix_finished'),
                struggle=dd.get('struggle_evidence'),phase=d.get('control_phase'),outer=row['output'].get('intervention'))
        if result.exists():entry['result']=json.loads(result.read_text())
    output['cases'].append(entry)
print(json.dumps(output,indent=2))
