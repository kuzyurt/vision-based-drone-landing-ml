"""Read-only compact current state, never opens active HDF5 files."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;result={}
for root,cases in [('candidate_development_v25',['wrong_board_validation','prior_hard_development']),('candidate_recovery_v25',['recovery_tilt'])]:
    out=ROOT/root;entry={}
    for name in ['state','audit_state']:
        p=out/(name+'.json')
        if p.exists():
            state=json.loads(p.read_text())
            if 'reports'in state:
                state['reports']=[dict(case=r['case'],physical_landed=r['physical_landed'],outcome=r['summary']['outcome'],
                    history_mismatches=len(r['actual_history_mismatches']),unsupported_descent=len(r['unsupported_descent_frames']),
                    wrong_metric=len(r['metric_center_inside_non_target_instance_frames']),
                    feedback_events=r.get('inspection_feedback_events'),fault_frames=len(r.get('actual_fault_frames',[])))for r in state['reports']]
            entry[name]=state
    for case in cases:
        ep=out/case;trace=ep/'steps.jsonl'
        if not trace.exists():continue
        with trace.open('rb')as f:f.seek(max(0,trace.stat().st_size-524288));tail=f.read().splitlines()
        for line in reversed(tail):
            try:row=json.loads(line);break
            except (ValueError,UnicodeDecodeError):continue
        else:continue
        d=row['output'].get('learner_diagnostics')or{}
        entry[case]=dict(task_s=row['task_time_s'],phase=d.get('control_phase'),intent=d.get('expert_intent'),
            metric=d.get('metric_valid'),feedback=d.get('inspection_feedback'),actual_fault_frames=d.get('evaluation_fault_frames'),
            actual_fault_triggered=d.get('evaluation_fault_triggered'))
    if entry.get('state',{}).get('status')=='failed':
        entry['coordinator_error']=(out/'coordinator.log').read_text()[-2500:]
    result[root]=entry
print(json.dumps(result,indent=2))
