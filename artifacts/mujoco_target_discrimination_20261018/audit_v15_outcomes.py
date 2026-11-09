"""Read actual closed traces; offline diagnostics never feed the actor."""
from pathlib import Path
import collections,json,math,numpy as np
ROOT=Path(__file__).resolve().parent
result={}
for case in ['hard','recovery','dagger']:
    directory=ROOT/('expert_visible_native_v15_'+case);rows=[json.loads(s)for s in(directory/'steps.jsonl').open()]
    tracks={};takeovers=[];phases=collections.Counter();fallback=[];fault=0;owner=collections.Counter();yaw=[]
    for row in rows:
        o=row['observation'];d=row['output'].get('learner_diagnostics')or{};intent=d.get('expert_intent',d.get('expert_shadow_intent',{}));phases[intent.get('phase',d.get('control_phase'))]+=1
        yaw.append(math.pi/2-o['px4']['attitude_ned_rad'][2]+o['gimbal_rad'][0])
        ownership=d.get('dagger',{}).get('ownership',{});owner[d.get('actual_command_owner',ownership.get('owner','expert'))]+=1
        if ownership.get('owner')=='expert' and not takeovers:takeovers.append(dict(task_s=row['task_time_s'],**ownership,evidence=d['dagger']['trigger_evidence']))
        fault+=bool(d.get('evaluation_fault_active'))
        if d.get('mission_fallback_active')and not fallback:fallback.append(dict(task_s=row['task_time_s'],trigger=d.get('fallback_trigger')))
        for t in d.get('expert_visual_tracks',[]):
            if o['image_delivery_time_s']-t['capture_s']>.25:continue
            v=tracks.setdefault(t['track_id'],dict(max_target_probability=0.,max_confirmations=0,strong_captures=set(),supported_captures=set(),first_pixel=t['pixel'],first_size=t['size_px'],first_target=t['target_probability']))
            v['max_target_probability']=max(v['max_target_probability'],t['target_probability']);v['max_confirmations']=max(v['max_confirmations'],t['identity_confirmations'])
            if t['target_probability']>=.98:v['strong_captures'].add(t['capture_s'])
            if t['target_probability']>=.98 and t.get('identity_support_probability',1)>=.8 and max(t['size_px'])>=24:v['supported_captures'].add(t['capture_s'])
    for v in tracks.values():
        for key in ['strong_captures','supported_captures']:v[key]=len(v[key])
    summary=json.loads((directory/'summary.json').read_text())
    result[case]=dict(preview=json.loads((directory/'preview_result.json').read_text()),recorded_task_s=rows[-1]['task_time_s'],rows=len(rows),phase_counts=dict(phases),actual_owners=dict(owner),takeovers=takeovers,actual_fault_rows=fault,first_fallback=fallback,yaw_sweep_rad=float(np.ptp(np.unwrap(yaw))),tracks=tracks,physical_events=summary['events'])
(ROOT/'v15_actual_outcome_diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:{key:v[key]for key in ['recorded_task_s','phase_counts','actual_owners','takeovers','actual_fault_rows','first_fallback','yaw_sweep_rad','tracks']}for k,v in result.items()},indent=2))
