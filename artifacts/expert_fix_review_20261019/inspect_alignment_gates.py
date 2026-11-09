from pathlib import Path
import json
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
for case in ['E01','E03','E10']:
    f=ROOT/'expert_fix_review_20261019/v30'/case/'steps.jsonl'
    if not f.exists():continue
    rows=[]
    for line in f.open():
        try:r=json.loads(line)
        except json.JSONDecodeError:continue
        if not rows or r['task_time_s']-rows[-1]['task_time_s']>=5:rows.append(r)
    for r in rows[-8:]:
        d=r['output'].get('learner_diagnostics')or{}
        keys=['control_phase','metric_valid','metric_confirmed','metric_acceptance','metric_innovation_m','visual_motion_ready','visual_motion_window_s','estimated_lateral_error_m','estimated_relative_velocity','estimated_heading_error_deg','stable_tracking_s','camera_axis_error_deg','camera_sync_error_deg','camera_sync_descent_hold','approach_motion_handoff_initialized','approach_stopping_limited']
        print(json.dumps(dict(case=case,task=r['task_time_s'],action=r['output']['executed_action'],**{k:d.get(k)for k in keys})))
