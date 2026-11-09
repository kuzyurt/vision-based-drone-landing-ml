"""Read-only exact-capture scoring; never imported by an actor."""
from pathlib import Path
import hashlib,json,math
import h5py

def associations(case,prior_audit):
 checks=prior_audit['checks'];assert any(c['passed']and c['name']=='all valid delivered RGB frames have exact annotation SHA/time joins'for c in checks)
 assert prior_audit['raw_files_before_after']['stable']
 captures={}
 for line in(case/'capture_annotations.jsonl').open():
  a=json.loads(line);key=round(a['capture_s']*1e6)
  if key in captures:assert captures[key]['rgb_sha256']==a['rgb_sha256']
  else:captures[key]=a
 def inside(point,box,margin=0):return box[0]+margin<=point[0]<box[2]-margin and box[1]+margin<=point[1]<box[3]-margin
 wrong_teacher=[];wrong_learner=[];coverage=0;joins=0
 with h5py.File(case/'observations.h5','r')as h:
  for i,encoded in enumerate(h['steps']):
   r=json.loads(encoded);o=r['observation'];d=r['output'].get('learner_diagnostics')or{};owner=d.get('actual_command_owner');p=d.get('marker_center_px')
   if not o['image_valid']or p is None or len(p)!=2 or not all(math.isfinite(float(x))for x in p):continue
   a=captures[round(float(o['image_capture_time_s'])*1e6)];joins+=1
   age=d.get('metric_age_s');sigma=d.get('metric_uncertainty_m');fresh=bool(d.get('metric_confirmed')and age is not None and age<=.16 and sigma is not None and sigma<=.15)
   if not fresh:continue
   coverage+=1;target=next((z for z in a['instances']if z['annotation_instance']=='target'),None)
   if target is not None and inside(p,target['bbox']):continue
   wrong=[z for z in a['instances']if z['annotation_instance']!='target'and z['identity']!=-2 and inside(p,z['bbox'],2)and z['structural_pixels']>=128]
   if not wrong:continue
   item=dict(frame=i,task_s=r.get('task_time_s'),owner=owner,point=p,other_instances=[z['annotation_instance']for z in wrong],requested_down=r['output']['executed_action'][2],capture_uid=a['capture_uid'])
   if owner in ['expert','expert_prefix']:wrong_teacher.append(item)
   elif owner=='policy':wrong_learner.append(item)
 return dict(scope='Additional offline bbox/registered-marker association proof after prior all-image SHA+capture audit; not perfect segmentation recognition and never actor input',fresh_registered_geometry_frames=coverage,finite_point_capture_joins=joins,wrong_teacher_count=len(wrong_teacher),wrong_teacher_examples=wrong_teacher[:15],wrong_learner_count=len(wrong_learner),wrong_learner_examples=wrong_learner[:15],passed=not wrong_teacher)
