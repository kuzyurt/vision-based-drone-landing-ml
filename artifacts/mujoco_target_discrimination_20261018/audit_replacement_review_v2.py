"""Audit closed review rollouts; truth annotations remain offline-only."""
from pathlib import Path
import argparse,collections,hashlib,json,sys
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
sys.path.insert(0,str(ROOT))
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',default='v26b');p.add_argument('--case',required=True);a=p.parse_args()
    out=ROOT/'expert_fix_review_20261019'/a.revision;ep=out/a.case
    assert(ep/'preview_result.json').exists(),'Only audit closed recordings'
    rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];summary=json.loads((ep/'summary.json').read_text())
    capture_index=load_capture_index(ep/'capture_annotations.jsonl');owners=collections.Counter();phases=collections.Counter();holds=collections.Counter()
    mismatches=[];unsupported=[];joined=0;sync=[];fault=[];coverage=[];first_target_opportunity=None;metric_wrong=[];owner_blocks=[];reset_events=[];valid_images=0;metric_missing_after_fault=[];recovery=[]
    selected=sorted(set([0,len(rows)//4,len(rows)//2,3*len(rows)//4,len(rows)-1]));sheet=Image.new('RGB',(1280,1170),(12,18,25))
    with h5py.File(ep/'observations.h5','r')as h:
        assert not h.attrs['training_eligible']and h.attrs['role']=='review'
        for i,r in enumerate(rows):
            o=r['observation'];d=r['output'].get('learner_diagnostics')or{};cmd=np.asarray(r['output']['executed_action']);own=o['px4'];intent=d.get('expert_intent')or{}
            owner=d.get('actual_command_owner','unknown');owners[owner]+=1
            if not owner_blocks or owner_blocks[-1]['owner']!=owner:owner_blocks.append(dict(owner=owner,start_task_s=r['task_time_s'],end_task_s=r['task_time_s'],rows=0))
            owner_blocks[-1]['rows']+=1;owner_blocks[-1]['end_task_s']=r['task_time_s']
            marker=d.get('expert_marker_localizer')or{}
            if marker.get('destructive_metric_reset'):reset_events.append(dict(task=r['task_time_s'],**marker))
            phases[intent.get('phase',d.get('control_phase','unknown'))]+=1
            if i+1<len(rows)and not np.allclose(cmd,rows[i+1]['observation']['previous_executed_action'],rtol=0,atol=1e-8):mismatches.append(i)
            if owner in ['expert','expert_prefix'] and cmd[2]>.02 and own.get('armed')and not own.get('landed')and not intent.get('allow_descent')and not d.get('mission_fallback_active'):unsupported.append(i)
            if d.get('evaluation_fault_active'):fault.append(i)
            if d.get('recovery_active'):recovery.append(i)
            if fault and not d.get('metric_valid'):metric_missing_after_fault.append(i)
            if d.get('nearfield_descent_paused'):holds[(d.get('nearfield_visibility_plan')or{}).get('reason','unknown')]+=1
            if d.get('camera_continuity_active'):
                sync.append(dict(task=r['task_time_s'],pan=o['gimbal_rad'][0],body_yaw=np.pi/2-own['attitude_ned_rad'][2],
                    error_deg=d.get('camera_sync_error_deg'),lateral=d.get('estimated_lateral_error_m'),phase=intent.get('phase')))
            coverage.append(dict(task=r['task_time_s'],phase=intent.get('phase'),reason=intent.get('reason'),coverage=d.get('expert_scan_coverage_rad'),epoch=d.get('expert_survey_epoch')))
            rgb=np.asarray(h['rgb'][r['frame_index']]);label=join_delivered_frame(o,rgb,capture_index)
            if o.get('image_valid'):valid_images+=1
            if label is not None:
                joined+=1
                point=d.get('marker_center_px')
                if d.get('metric_valid') and point is not None:
                    px,py=point
                    for inst in label['instances']:
                        x0,y0,x1,y1=inst['bbox']
                        if inst['annotation_instance']!='target' and x0<=px<x1 and y0<=py<y1:metric_wrong.append(dict(row=i,task=r['task_time_s'],instance=inst['annotation_instance']))
                if first_target_opportunity is None and any(x.get('annotation_instance')=='target'for x in label['instances']):first_target_opportunity=r['task_time_s']
            if i in selected:
                j=selected.index(i);x=j%2*640;y=j//2*390;sheet.paste(Image.fromarray(rgb),(x,y));ImageDraw.Draw(sheet).text((x+5,y+363),f"{a.case} actual {r['task_time_s']:.2f}s {intent.get('phase')} metric={d.get('metric_valid')}",fill='white')
    sheet.save(out/(a.case+'_actual_rgb.jpg'),quality=93)
    pan=np.asarray([r['pan']+r['body_yaw']for r in sync]);dt=np.diff([r['task']for r in sync]);rate=np.abs(np.diff(np.unwrap(pan))/np.maximum(dt,1e-8))*180/np.pi if len(pan)>1 else np.array([])
    report=dict(case=a.case,outcome=summary['outcome'],rows=len(rows),owners=dict(owners),phases=dict(phases),
        command_history_mismatches=mismatches,unsupported_descent=unsupported,exact_valid_rgb_joins=joined,
        actual_fault_rows=fault,first_annotation_target_opportunity_task_s=first_target_opportunity,
        camera_continuity_frames=len(sync),world_camera_pan_rate_deg_s_p95=float(np.percentile(rate,95))if len(rate)else None,
        world_camera_pan_total_variation_deg=float(np.sum(np.abs(np.diff(np.unwrap(pan))))*180/np.pi)if len(pan)>1 else None,
        justified_visibility_hold_reasons=dict(holds),scan_state=coverage,training_eligible=False,
        actual_camera_review_pending=True,owner_blocks=owner_blocks,valid_images=valid_images,metric_wrong=metric_wrong,destructive_metric_resets=reset_events,recovery_rows=recovery,metric_missing_after_fault=metric_missing_after_fault,gate='review_only_not_training_or_deployment')
    (out/(a.case+'_audit.json')).write_text(json.dumps(report,indent=2));print(json.dumps({k:(len(v) if k in ['actual_fault_rows','recovery_rows','metric_missing_after_fault','destructive_metric_resets'] else v)for k,v in report.items()if k not in ['scan_state']}),flush=True)
if __name__=='__main__':main()
