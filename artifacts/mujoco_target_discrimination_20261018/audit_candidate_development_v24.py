"""Closed actual camera, input, command and physical audit; no model selection images."""
from pathlib import Path
import json,os,select,collections
import h5py,numpy as np
from PIL import Image,ImageDraw
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'candidate_development_v24'
def save(**v):
    p=OUT/'audit_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(dict(pid=os.getpid(),**v),indent=2));tmp.replace(p)
def main():
    assert not(OUT/'audit_state.json').exists();coordinator=json.loads((OUT/'launch.json').read_text())['pid'];save(status='waiting_for_closed_development',coordinator=coordinator)
    try:fd=os.pidfd_open(coordinator)
    except ProcessLookupError:fd=None
    if fd is not None:
        try:select.select([fd],[],[],2500)
        finally:os.close(fd)
    state=json.loads((OUT/'state.json').read_text())
    if state['status']!='completed':save(status='upstream_not_completed',upstream=state);return
    reports=[]
    for case in ['wrong_board_validation','prior_hard_development']:
        ep=OUT/case;rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];summary=json.loads((ep/'summary.json').read_text())
        result=json.loads((ep/'preview_result.json').read_text());assert result['candidate_actor_alone']and result['no_teacher_handover']
        index=load_capture_index(ep/'capture_annotations.jsonl');mismatches=[];unsupported=[];metric_wrong=[];owners=collections.Counter();joined=0
        selected=sorted(set([0,len(rows)//4,len(rows)//2,3*len(rows)//4,len(rows)-1]));sheet=Image.new('RGB',(1280,3*390))
        with h5py.File(ep/'observations.h5','r')as h:
            assert h.attrs['role']=='review'and not h.attrs['training_eligible']
            for i,row in enumerate(rows):
                o=row['observation'];d=row['output'].get('learner_diagnostics')or{};a=np.asarray(row['output']['executed_action']);owners[d.get('actual_command_owner','unknown')]+=1
                assert not d.get('dagger'),'Candidate-alone cannot contain a teacher wrapper'
                if i+1<len(rows)and not np.allclose(a,rows[i+1]['observation']['previous_executed_action'],rtol=0,atol=1e-8):mismatches.append(i)
                intent=d.get('expert_intent')or{};own=o['px4']
                if a[2]>.02 and own.get('armed')and not own.get('landed')and not intent.get('allow_descent')and not d.get('mission_fallback_active'):
                    unsupported.append(dict(frame=i,phase=d.get('control_phase'),intent=intent))
                rgb=np.asarray(h['rgb'][row['frame_index']]);label=join_delivered_frame(o,rgb,index)
                if label is not None:
                    joined+=1;point=d.get('marker_center_px')
                    if d.get('metric_valid')and point is not None:
                        x,y=point
                        for inst in label['instances']:
                            a0,b,c,e=inst['bbox']
                            if inst['annotation_instance']!='target'and a0<=x<c and b<=y<e:
                                metric_wrong.append(dict(frame=i,task=row['task_time_s'],instance=inst['annotation_instance']))
                if i in selected:
                    n=selected.index(i);x=n%2*640;y=n//2*390;sheet.paste(Image.fromarray(rgb),(x,y))
                    ImageDraw.Draw(sheet).text((x+4,y+364),f"actual {row['task_time_s']:.2f}s {d.get('control_phase')} metric={d.get('metric_valid')}",fill='white')
        sheet.save(OUT/(case+'_actual_rgb.jpg'),quality=93)
        report=dict(case=case,summary=summary,result=result,owners=dict(owners),actual_history_mismatches=mismatches,
            unsupported_descent_frames=unsupported,exact_recorded_valid_rgb_joins=joined,
            metric_center_inside_non_target_instance_frames=metric_wrong,actual_camera_review_pending=True,
            assisted_by_external_teacher=False,source_kind='development/validation; NOT fresh heldout',
            physical_landed=summary['outcome']=='landed'and result['physical_flight_completed'],
            no_collision=summary['outcome']not in ['collision_failure','water_strike'],training_eligible=False)
        (OUT/(case+'_audit.json')).write_text(json.dumps(report,indent=2));reports.append(report)
    save(status='closed_reports_ready_for_actual_camera_review',reports=reports)
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
