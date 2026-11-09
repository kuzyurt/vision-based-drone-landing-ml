from pathlib import Path
import collections,json,numpy as np
root=Path(__file__).resolve().parent;episode=root/'expert_visible_native_v13b';rows=[json.loads(s)for s in(episode/'steps.jsonl').open()if s.strip()]
flags=collections.Counter();commands=[];examples=[];parts=collections.Counter()
for i,row in enumerate(rows):
 o=row['observation'];d=row['output'].get('learner_diagnostics',{});intent=d.get('expert_intent',{});mission=o['mission'].get('target_discrimination',{})
 for key in['search_corridor_valid','upward_corridor_valid']:flags[key]+=bool(mission.get(key))
 flags['allow_approach']+=bool(intent.get('allow_approach'));flags['known_identity']+=bool(d.get('expert_observable_target_confirmed'))
 flags['localizer_inside_box']+=bool(d.get('expert_marker_localizer',{}).get('inside_predicted_identity_box'))
 if i+1<len(rows):commands.append(rows[i+1]['observation']['previous_executed_action'])
 if i%100==0 or(intent.get('phase')=='target_inspect'and len(examples)<20):
  examples.append(dict(time_s=row['task_time_s'],own=o['px4'],gimbal=o['gimbal_rad'],mission=mission,intent=intent,marker=d.get('expert_marker_localizer'),visibility=d.get('image_head_visibility'),metric_acceptance=d.get('metric_acceptance'),metric_invalid_reason=d.get('metric_invalid_reason'),track_count=len(d.get('expert_visual_tracks',[]))))
 first=rows[0]['observation']['px4']['position_enu_m'];last=rows[-1]['observation']['px4']['position_enu_m'];a=np.array(commands)
summary=json.loads((episode/'summary.json').read_text());out=dict(rows=len(rows),flags=dict(flags),own_start=first,own_end=last,own_displacement=(np.array(last)-first).tolist(),command_max_abs=np.max(np.abs(a),axis=0).tolist(),performance=summary.get('performance'),examples=examples,diagnostic_keys=list(rows[300]['output']['learner_diagnostics']))
(root/'v13b_failure_diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k not in['examples','diagnostic_keys']},indent=2));print(json.dumps(dict(first_inspect=next(e for e in examples if e['intent'].get('phase')=='target_inspect'),diagnostic_keys=out['diagnostic_keys']),indent=2))
