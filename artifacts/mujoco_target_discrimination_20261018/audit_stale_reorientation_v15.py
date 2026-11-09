from pathlib import Path
import json
root=Path(__file__).resolve().parent;rows=[json.loads(s)for s in(root/'expert_visible_native_v15_recovery/steps.jsonl').open()]
spans=[];active=None
for row in rows:
    d=row['output'].get('learner_diagnostics')or{};intent=d.get('expert_intent',{});selected=intent.get('selected_track');now=row['observation']['image_delivery_time_s']
    track=next((t for t in d.get('expert_visual_tracks',[])if t['track_id']==selected),None)
    key=selected if intent.get('phase')=='reorient_candidate' else None
    if key is not None:
        if active is None or active['track']!=key:
            if active:spans.append(active)
            active=dict(track=key,start=row['task_time_s'],end=row['task_time_s'],rows=0,age_start=now-track['capture_s']if track else None,max_age=0.)
        active['end']=row['task_time_s'];active['rows']+=1
        if track:active['max_age']=max(active['max_age'],now-track['capture_s'])
    elif active:spans.append(active);active=None
if active:spans.append(active)
for span in spans:span['duration_s']=span['end']-span['start']+.04
result=dict(status='read_only',reorientation_spans=sorted(spans,key=lambda x:-x['duration_s']),code_cause='SearchProtocol returns reorient_candidate for stale chosen BEFORE the inspection no-progress timer. This timer therefore does not bound reacquisition when the detector cannot refresh the remembered candidate.',truth_used_for_actor=False)
(root/'v15_stale_reorientation_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
