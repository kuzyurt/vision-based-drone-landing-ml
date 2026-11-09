"""Read-only health snapshot. Does not open active HDF5 or tune the policy."""
from pathlib import Path
import collections,datetime,json,os,subprocess
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'frozen_task_evaluation_v3'
state=json.loads((OUT/'state.json').read_text());results=state.get('results',[])
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=state['status'],coordinator=state['pid'],
    completed=len(results),outcomes=dict(collections.Counter(r['audit']['outcome']for r in results)),
    completed_cases=[dict(name=r['job']['name'],map=r['job']['map'],category=r['job']['category'],outcome=r['audit']['outcome'],task_s=r['audit']['final_task_s'],audit_passed=r['audit']['audit_passed'])for r in results],
    remaining=state.get('remaining'),active=[])
for child in state.get('children',[]):
    item=dict(child);ep=OUT/child['name'];trace=ep/'steps.jsonl'
    if trace.exists():
        with trace.open('rb')as f:f.seek(max(0,trace.stat().st_size-262144));lines=f.read().splitlines()
        for line in reversed(lines):
            try:row=json.loads(line);break
            except(ValueError,UnicodeDecodeError):continue
        else:row=None
        if row:
            d=row['output'].get('learner_diagnostics')or{}
            item.update(task_s=row['task_time_s'],phase=d.get('control_phase'),mission_fallback=bool(d.get('mission_fallback_active')),last_trace_age_s=max(0,datetime.datetime.now().timestamp()-trace.stat().st_mtime))
    if(ep/'preview_result.json').exists():item['closed_outcome']=json.loads((ep/'preview_result.json').read_text())['outcome']
    report['active'].append(item)
report['mem_available_kib']=int(next(l.split()[1]for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')))
report['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],text=True).strip()
print(json.dumps(report,indent=2))
