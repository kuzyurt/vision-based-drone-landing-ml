"""Read-only actual progress around handover; truth is offline scoring only."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
report={}
for case in ['near_deck','near_deck_tilt']:
    ep=ROOT/('expert_visible_native_v19_'+case)
    rows=[json.loads(s)for s in(ep/'steps.jsonl').open()]
    chosen=[];last=-1
    for row in rows:
        t=row['task_time_s']
        if not 50<=t<=80:continue
        bucket=int(t)//2
        if bucket==last:continue
        last=bucket;d=row['output'].get('learner_diagnostics')or{};dd=d.get('dagger')or{};own=row['observation']['px4']
        chosen.append(dict(task_s=round(t,2),owner=dd.get('ownership',{}).get('owner'),phase=d.get('control_phase'),
            trigger=dd.get('ownership',{}).get('reason'),gimbal_deg=[round(v*57.29578,1)for v in row['observation']['gimbal_rad']],
            own_z=own['position_enu_m'][2],own_vz=own['velocity_enu_m_s'][2],
            learner_clearance=d.get('estimated_clearance_m'),learner_lateral=d.get('estimated_lateral_error_m'),
            teacher_clearance=dd.get('trigger_evidence',{}).get('observable_clearance_m'),
            pixel_error=dd.get('trigger_evidence',{}).get('pixel_error'),metric=d.get('metric_confirmed'),
            recovery_active=d.get('recovery_active'),action=row['output']['executed_action'],
            outer=row['output'].get('intervention'),fallback=d.get('mission_fallback_reason',d.get('mission_safety_trigger')),
            offline_actual_clearance=row.get('privileged',{}).get('clearance_m')))
    report[case]=dict(samples=chosen,summary=json.loads((ep/'summary.json').read_text()))
(ROOT/'v19_progress_and_recovery_diagnosis.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v['samples']for k,v in report.items()},indent=2))
