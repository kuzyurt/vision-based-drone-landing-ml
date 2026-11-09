from pathlib import Path
import collections,json
ROOT=Path(__file__).resolve().parent;out=ROOT/'curriculum_v23'
result={}
for ep in sorted((out/'episodes').iterdir()):
    summary=ep/'summary.json';trace=ep/'steps.jsonl'
    if not summary.exists():continue
    s=json.loads(summary.read_text());item=dict(summary=s)
    if s.get('outcome')in ['water_strike','collision_failure']:
        rows=[json.loads(l)for l in trace.open()];events=[]
        for row in rows[-90::5]:
            o=row['observation'];d=row['output'].get('learner_diagnostics')or{};own=o['px4']
            events.append(dict(task=row['task_time_s'],own=own,mission=o['mission'],
                output=row['output'],previous=o.get('previous_executed_action')))
        item['last_events']=events
        item['ownership_counts']=dict(collections.Counter((r['output'].get('learner_diagnostics')or{}).get('actual_command_owner')for r in rows))
        item['diagnostic_keys']=list(rows[-1]['output'].get('learner_diagnostics',{}))
        item['source_trace']=str(trace)
    else:item=dict(outcome=s.get('outcome'),records=s.get('records'))
    result[ep.name]=item
p=out/'stop_diagnosis_raw.json';p.write_text(json.dumps(result,indent=2));print(json.dumps(dict(file=str(p),cases={k:v.get('outcome',v.get('summary',{}).get('outcome'))for k,v in result.items()})))
