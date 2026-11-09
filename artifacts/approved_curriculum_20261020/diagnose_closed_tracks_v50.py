from pathlib import Path
import json
R=Path(__file__).parent;out={}
for name in ['search_mid','search_far']:
 c=R/'search_v46/pilots'/name;assert(c/'preview_result.json').exists();ann={round(a['capture_s']*1e6):a for a in map(json.loads,(c/'capture_annotations.jsonl').open())};seen=set();matched=[];ids=[];first_completed=None;band_before=[]
 for line in(c/'steps.jsonl').open():
  r=json.loads(line);d=r['output'].get('learner_diagnostics')or{};intent=d.get('expert_intent')or{}
  if first_completed is None and intent.get('reason')=='full_survey_complete_investigate_retained_visual_candidate':first_completed=dict(t=r.get('task_time_s'),band=d.get('expert_scan_band'),epoch=d.get('expert_survey_epoch'))
  for t in d.get('expert_visual_tracks',[]):
   key=(t['track_id'],t['capture_s'])
   if key in seen:continue
   seen.add(key);a=ann.get(round(t['capture_s']*1e6));p=t.get('pixel')
   if not a or p is None:continue
   boxes=[x for x in a['instances']if x['bbox'][0]<=p[0]<x['bbox'][2]and x['bbox'][1]<=p[1]<x['bbox'][3]];inst=min(boxes,key=lambda x:(x['bbox'][2]-x['bbox'][0])*(x['bbox'][3]-x['bbox'][1]))if boxes else None
   item=dict(task_s=r.get('task_time_s'),track=t['track_id'],name=inst['annotation_instance']if inst else'background',confirmations=t['confirmations'],identity_confirmations=t['identity_confirmations'],p=t['target_probability'],wrong=t.get('wrong_object_probability'),presence=t['presence'],size=t['size_px'],context=inst.get('identity')if inst else None)
   if inst and inst['annotation_instance']=='target':matched.append(item)
   if t['target_probability']>=.98 and t['identity_confirmations']>=3:ids.append(item)
 out[name]=dict(first_completed_wrapper_scan=first_completed,distinct_target_track_measurements=len(matched),target_confirmations_atleast3=sum(t['confirmations']>=3 for t in matched),target_identity_confirmed=sum(t['p']>=.98 and t['identity_confirmations']>=3 for t in matched),target_examples=matched[:8],strong_identity_instances={n:sum(t['name']==n for t in ids)for n in sorted(set(t['name']for t in ids))},strong_identity_examples=ids[:10])
(R/'search_v46/closed_track_associations.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
