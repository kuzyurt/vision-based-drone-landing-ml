from pathlib import Path
import json,math,collections
import numpy as np,h5py
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
ROOT=Path(__file__).resolve().parent;ep=ROOT/'candidate_development_v24/wrong_board_validation'
rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];phases=collections.Counter();scan=[];samples=[]
for row in rows:
    d=row['output'].get('learner_diagnostics')or{}
    if 'expert_intent'not in d:continue # MissionSafety owns the final fallback command.
    intent=d['expert_intent'];phase=intent['phase'];phases[phase]+=1
    own=row['observation']['px4'];item=dict(task=row['task_time_s'],intent=intent,actual=row['output']['executed_action'],
        yaw_ned=own['attitude_ned_rad'][2],position=own['position_enu_m'],gimbal=row['observation']['gimbal_rad'],
        tracks=d['expert_visual_tracks'],prior=row['observation']['mission']['target_discrimination'],
        guard=d.get('expert_override_guard'),capture_error=d['expert_capture_history_error_s'])
    if phase=='scan':scan.append(item)
    if len(samples)==0 or item['task']-samples[-1]['task']>=5:
        item['frame_index']=row['frame_index'];item['observation']=row['observation'];samples.append(item)
index=load_capture_index(ep/'capture_annotations.jsonl')
with h5py.File(ep/'observations.h5','r')as h:
    for item in samples:
        o=item.pop('observation');label=join_delivered_frame(o,np.asarray(h['rgb'][item['frame_index']]),index)
        item['actual_target_annotation']=[i for i in label['instances']if i['annotation_instance']=='target']if label else[]
yaw=np.unwrap([math.pi/2-r['observation']['px4']['attitude_ned_rad'][2]for r in rows])
conflicts=[i for i in scan if abs(i['intent']['yaw_rate_rad_s'])>.1 and abs(i['actual'][3])<.05]
report=dict(phase_counts=dict(phases),total_actual_absolute_body_yaw_rad=float(np.abs(np.diff(yaw)).sum()),
    scan_frames=len(scan),scan_request_but_nearzero_executed_yaw_frames=len(conflicts),
    first_conflicts=conflicts[:4],samples=samples,scope='Actual logged public inputs/commands; diagnosis, not counterfactual physical success')
(ROOT/'candidate_development_v24/search_diagnosis.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items()if k not in ['samples','first_conflicts']},indent=2))
