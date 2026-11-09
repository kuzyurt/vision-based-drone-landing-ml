from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
for name in ['candidate_recovery_v25/recovery_tilt','candidate_development_v25/prior_hard_development','expert_visible_native_v21_tilt']:
    ep=ROOT/name
    if not(ep/'steps.jsonl').exists():print(json.dumps(dict(episode=name,missing=True)));continue
    rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];samples=[]
    for t in ([58.,62.,63.2,64.,65.,69.,74.,80.,86.]if 'v25/'in name else[50.,54.,58.,63.52,66.,70.,80.]):
        r=min(rows,key=lambda r:abs(r['task_time_s']-t));d=r['output'].get('learner_diagnostics')or{};o=r['observation'];p=o['px4']
        samples.append(dict(task=r['task_time_s'],phase=d.get('control_phase'),metric=d.get('metric_valid'),
            fault=d.get('evaluation_fault_active'),owner=d.get('actual_command_owner'),dagger=d.get('dagger'),
            camera_fields={k:v for k,v in o.items()if any(w in k for w in ['gimbal','camera'])},
            own_fields={k:v for k,v in p.items()if any(w in k for w in ['gimbal','attitude'])},action=r['output']['executed_action'],
            metric_fields={k:v for k,v in d.items()if any(w in k for w in ['angle','yaw','marker_center','error_px'])}))
    (ROOT/(name.replace('/','_')+'_camera_review.json')).write_text(json.dumps(samples,indent=2))
    print(json.dumps(dict(episode=name,files=[p.name for p in ep.glob('*result*')],sample=samples[:2]),indent=2))
