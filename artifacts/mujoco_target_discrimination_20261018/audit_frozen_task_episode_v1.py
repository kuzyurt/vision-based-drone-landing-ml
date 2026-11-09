"""Independent closed RGB/input/command/physical audit. No task actions."""
from pathlib import Path
import argparse,hashlib,json
import h5py,numpy as np
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(ep):
    ep=Path(ep);result=json.loads((ep/'preview_result.json').read_text());summary=json.loads((ep/'summary.json').read_text())
    rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];index=load_capture_index(ep/'capture_annotations.jsonl')
    joined=0;history=[];descent=[];wrong=[];visible_absent=[];fault=[];metric_missing=[];recovery=[]
    absent=result.get('evaluation_job',{}).get('target_absent',False)
    with h5py.File(ep/'observations.h5','r')as h:
        assert h.attrs['role']=='review'and not h.attrs['training_eligible']
        for i,row in enumerate(rows):
            obs=row['observation'];d=row['output'].get('learner_diagnostics')or{};action=np.asarray(row['output']['executed_action']);own=obs['px4']
            assert not d.get('dagger'),'Standalone candidate may not have a teacher'
            assert not obs.get('beacon',{}).get('valid'),'No-radio evaluation must not receive valid radio'
            if i+1<len(rows)and not np.allclose(action,rows[i+1]['observation']['previous_executed_action'],rtol=0,atol=1e-8):history.append(i)
            if action[2]>.02 and own.get('armed')and not own.get('landed')and not(d.get('expert_intent')or{}).get('allow_descent')and not d.get('mission_fallback_active'):descent.append(i)
            rgb=np.asarray(h['rgb'][row['frame_index']]);label=join_delivered_frame(obs,rgb,index)
            if label is not None:
                joined+=1
                if absent and any(k['annotation_instance']=='target'for k in label['instances']):visible_absent.append(i)
                point=d.get('marker_center_px')
                if d.get('metric_valid')and point is not None:
                    for instance in label['instances']:
                        a,b,c,e=instance['bbox'];x,y=point
                        if instance['annotation_instance']!='target'and a<=x<c and b<=y<e:wrong.append(dict(frame=i,instance=instance['annotation_instance']))
            if d.get('evaluation_fault_active'):fault.append(i)
            if not d.get('metric_valid'):metric_missing.append(i)
            if d.get('recovery_active'):recovery.append(i)
    assert result['candidate_actor_alone']and result['no_teacher_handover']
    violations=dict(actual_history_mismatches=history,unsupported_descent=descent,wrong_object_metric=wrong,visible_target_when_absent=visible_absent)
    expected='home_landed'if absent else'landed'
    physical=summary['outcome']==expected and result['physical_flight_completed']
    events=summary.get('events',[])
    strict_event=any(e['kind']==expected for e in events)
    native_failure=summary['outcome']in ['water_strike','collision_failure']
    report=dict(outcome=summary['outcome'],expected=expected,physical_success=bool(physical and strict_event),
        audit_passed=not any(violations.values())and joined>0,violations=violations,exact_rgb_joins=joined,rows=len(rows),
        actual_fault_frames=len(fault),metric_missing_frames=len(metric_missing),recovery_active_frames=len(recovery),
        fault_triggered=result['fault_triggered'],native_safety_failure=native_failure,events=events,
        actor_sha256=result['actor_source_sha256'],recognizer_sha256=result['recognizer_sha256'],
        final_task_s=rows[-1]['task_time_s'],summary_sha256=sha(ep/'summary.json'),trace_sha256=sha(ep/'steps.jsonl'),
        no_training=True,cold_static_gate_passed=result['recognition_qualification_gate_passed'])
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episode');p.add_argument('--output',required=True);a=p.parse_args()
    result=audit(a.episode);Path(a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
