from pathlib import Path
import collections,json,math,numpy as np
root=Path(__file__).resolve().parent;rows=[json.loads(s)for s in(root/'expert_visible_native_v13c/steps.jsonl').open()];votes={};examples=[];phases=collections.Counter();motion=[];yaw=[];fallback=[]
for row in rows:
 o=row['observation'];d=row['output'].get('learner_diagnostics',{});phase=d.get('expert_intent',{}).get('phase',d.get('control_phase'));phases[phase]+=1;yaw.append(math.pi/2-o['px4']['attitude_ned_rad'][2]+o['gimbal_rad'][0]);motion.append(row['output']['executed_action'])
 if d.get('mission_fallback_active'):fallback.append(dict(time_s=row['task_time_s'],trigger=d.get('fallback_trigger')))
 for t in d.get('expert_visual_tracks',[]):
  fresh=o['image_delivery_time_s']-t['capture_s']<=.25
  if fresh and t['target_probability']>=.98:
   info=votes.setdefault(t['track_id'],dict(captures=set(),max_consecutive=0,max_presence=0.));info['captures'].add(t['capture_s']);info['max_consecutive']=max(info['max_consecutive'],t['identity_confirmations']);info['max_presence']=max(info['max_presence'],t['presence'])
 if row['frame_index']in[0,10,25,50,100,200,400,600,800,1000]:
  fresh=[t for t in d.get('expert_visual_tracks',[])if o['image_delivery_time_s']-t['capture_s']<=.25]
  examples.append(dict(frame=row['frame_index'],time_s=row['task_time_s'],phase=phase,tracks=[{k:t.get(k)for k in['track_id','pixel','size_px','presence','target_probability','wrong_object_probability','unknown_probability','identity_confirmations']}for t in sorted(fresh,key=lambda t:t['target_probability'],reverse=True)[:4]]))
for k,v in votes.items():
 times=sorted(v.pop('captures'));v['unique_frames']=len(times);v['three_strong_within_point8_s']=sum(times[i]-times[i-2]<=.8 for i in range(2,len(times)))
value=dict(rows=len(rows),phase_counts=dict(phases),yaw_sweep_rad=float(np.ptp(np.unwrap(yaw))),votes=votes,first_fallback=fallback[:1],actual_command_max_abs=np.abs(motion).max(0).tolist(),examples=examples)
(root/'v13c_acquisition_diagnosis.json').write_text(json.dumps(value,indent=2));print(json.dumps(value,indent=2))
