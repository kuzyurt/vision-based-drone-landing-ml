"""Closed retired-suite public state analysis; no model inference or training."""
from pathlib import Path
import collections,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent;RUN=ROOT/'frozen_task_evaluation_v3';OUT=ROOT/'frozen_task_postmortem_v1'
state=json.loads((RUN/'state.json').read_text());assert state['status'].startswith('retired_')
reports=[]
for record in state['results']:
    if record['audit']['physical_success']:continue
    rows=[json.loads(l)for l in(RUN/record['job']['name']/'steps.jsonl').open()]
    searching=[]
    for row in rows:
        d=row['output'].get('learner_diagnostics')or{}
        if not d.get('mission_fallback_active'):searching.append(row)
    count=collections.Counter();selected=[];positions=[];feedback=[];maxxy=0.
    for row in searching:
        d=row['output'].get('learner_diagnostics')or{};intent=d.get('expert_intent')or{}
        prior=row['observation']['mission'].get('target_discrimination')or{}
        count['frames']+=1;count['approach_corridor_valid']+=bool(prior.get('search_corridor_valid'))
        count['intent_allow_approach']+=bool(intent.get('allow_approach'));count['phase:'+str(intent.get('phase'))]+=1
        action=row['output']['executed_action'];count['nonzero_horizontal_command']+=bool(np.linalg.norm(action[:2])>.02)
        positions.append(row['observation']['px4']['position_enu_m'][:2])
        if(d.get('inspection_feedback')or{}).get('retired'):feedback.append(dict(task=row['task_time_s'],event=d['inspection_feedback']))
        chosen=next((t for t in d.get('expert_visual_tracks',[])if t['track_id']==intent.get('selected_track')),None)
        if chosen and (not selected or chosen['track_id']!=selected[-1]['track_id']):
            selected.append(dict(task_s=row['task_time_s'],track_id=chosen['track_id'],phase=intent.get('phase'),
                detection_channel_is_boat=chosen.get('original_detection_channel_is_boat'),
                presence=chosen['presence'],target_probability=chosen['target_probability'],unknown_probability=chosen.get('unknown_probability'),
                wrong_probability=chosen.get('wrong_object_probability'),range_interval=chosen['range_interval_m']))
    positions=np.asarray(positions)
    reports.append(dict(name=record['job']['name'],map=record['job']['map'],category=record['job']['category'],
        public_search_counts=dict(count),max_own_displacement_from_task_start_m=float(np.linalg.norm(positions-positions[0],axis=1).max()),
        selected_candidate_changes=selected,inspection_feedback_events=feedback,
        conclusion_scope='Actual public-state and executed commands only. No counterfactual physical success asserted.'))
(OUT/'public_search_diagnosis.json').write_text(json.dumps(dict(retired_state=state['status'],cases=reports,no_training=True),indent=2))
print(json.dumps(dict(cases=reports),indent=2))
