"""Closed recording audit. Simulator labels are read only here, never by actors."""
import local_paths
from pathlib import Path
import hashlib,json,math
import h5py,numpy as np

def audit(case,*,probe=False):
    case=Path(case);closed=json.loads((case/'closed.json').read_text());assert closed['failure']is None and not closed['cleanup_errors'],closed
    annotations={}
    for line in(case/'capture_annotations.jsonl').open():
        value=json.loads(line);key=round(value['capture_s']*1e6)
        if key in annotations:assert annotations[key]['rgb_sha256']==value['rgb_sha256']
        annotations[key]=value
    receipt=json.loads((case/'capture_annotation_receipt.json').read_text());assert not receipt['unbound_capture'] and not receipt['actor_input']
    result=json.loads((case/'preview_result.json').read_text());job=json.loads((case/'purpose_contract.json').read_text());binding=json.loads((case/'source_receipt.json').read_text())
    gate=json.loads((local_paths.ROOT/'runtime_probe_windows_v1.json').read_text());assert binding['actor_source_sha256']==gate['actor_source_sha256'] and binding['recognizer_sha256']==gate['recognizer_sha256']
    history=[];bad_images=[];bad_inputs=[];bad_descent=[];wrong_teacher=[];wrong_policy=[];hypotheses=[];counts={};fault_rows=[];first_teacher=None;metric_loss=0;recovery=0;valid_joined=0;previous=None;rows=0;unclean_terminal=[]
    def inside(point,box,margin=0):return box[0]+margin<=point[0]<box[2]-margin and box[1]+margin<=point[1]<box[3]-margin
    with h5py.File(case/'observations.h5','r')as h:
        assert not h.attrs['training_eligible'] and h.attrs['role']=='review'
        assert len(h['rgb'])==len(h['steps'])==closed['frames']
        for i,encoded in enumerate(h['steps']):
            r=json.loads(encoded);o=r['observation'];d=r['output']['learner_diagnostics'];owner=d['actual_command_owner'];counts[owner]=counts.get(owner,0)+1;rows+=1
            rgb=np.asarray(h['rgb'][i]);label=annotations.get(round(o['image_capture_time_s']*1e6))
            if label is None or hashlib.sha256(rgb.tobytes()).hexdigest()!=label['rgb_sha256']:bad_images.append(i)
            else:valid_joined+=1
            if previous is not None and previous['output']['command_was_sent_after_frame']:
                error=float(np.max(np.abs(np.asarray(o['previous_executed_action'])-previous['output']['executed_action'])))
                if error>1e-10:history.append(dict(frame=i,maximum_error=error))
            if any(k in o for k in ['privileged','pad_position_enu_m','target_position','segmentation','instance_id']):bad_inputs.append(i)
            if o['beacon'].get('valid'):bad_inputs.append(i)
            sent=r['output']['command_was_sent_after_frame'];down=float(r['output']['executed_action'][2]);intent=d.get('expert_intent',{})
            terminal_support=bool(o['px4'].get('landed')or(intent.get('phase')=='target_contact_confirmation'and d.get('control_phase')in ['touchdown_commit','confirm']))
            if sent and owner in ['expert','expert_prefix'] and down>.02 and not intent.get('allow_descent',False)and not terminal_support:bad_descent.append(i)
            if sent and owner=='evaluation_fault':fault_rows.append(i)
            if owner=='expert'and counts.get('policy',0)>0 and first_teacher is None:first_teacher=dict(frame=i,task_s=r['task_time_s'],reason=d.get('dagger',{}).get('ownership',{}).get('reason'),struggle_evidence=d.get('dagger',{}).get('struggle_evidence'),ownership=d.get('dagger',{}).get('ownership'))
            if counts.get('policy',0)>0 and owner in ['expert','expert_prefix','safety','fallback']:unclean_terminal.append(i)
            metric_loss+=int(not d.get('metric_confirmed',False));recovery+=int(d.get('recovery_active',False))
            point=d.get('marker_center_px');age=d.get('metric_age_s');sigma=d.get('metric_uncertainty_m')
            if label and point is not None and len(point)==2 and all(math.isfinite(float(x))for x in point)and d.get('metric_confirmed')and age is not None and age<=.16 and sigma is not None and sigma<=.15:
                target=next((x for x in label['instances']if x['annotation_instance']=='target'),None)
                if target is None or not inside(point,target['bbox']):
                    other=[x['annotation_instance']for x in label['instances']if x['identity']!=-2 and x['annotation_instance']!='target'and x['structural_pixels']>=128 and inside(point,x['bbox'],2)]
                    if other:
                        row=dict(frame=i,owner=owner,objects=other,phase=d.get('control_phase'),identity=bool(d.get('expert_observable_target_confirmed')),descent_allowed=bool(intent.get('allow_descent')),actual_down=down if sent else None)
                        if owner in ['expert','expert_prefix']:
                            (wrong_teacher if row['identity']or row['descent_allowed']or(sent and down>.02)else hypotheses).append(row)
                        elif owner=='policy':wrong_policy.append(row)
            previous=r
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('purpose_audit',local_paths.PREVIOUS/'semantic_contract.py');purpose=module_from_spec(spec);spec.loader.exec_module(purpose)
    initial=json.loads((case/'initial_view_receipt.json').read_text());contract=dict(initial_target=job['initial_target'],actual_initial_distance_band_m=job['distance_band'])
    precondition=True;precondition_error=None
    try:purpose.initial_view(initial,contract)
    except ValueError as e:precondition=False;precondition_error=str(e)
    trace=[json.loads(x)for x in(case/'semantic_camera_trace.jsonl').open()];discovery=True;discovery_error=None
    try:purpose.discovery(trace,contract)
    except ValueError as e:discovery=False;discovery_error=str(e)
    effects=[json.loads(x)for x in(case/'render_effects.jsonl').open()];glare_frames=sum(x.get('bright_glint_pixels',0)>30 for x in effects)
    wrong_object_views=sum(any(x['identity']==0 and x['structural_pixels']>=32 for x in a['instances'])for a in annotations.values())
    checks=dict(raw_review_ineligible=True,all_RGB_exact_capture_joins=not bad_images,actual_command_history_matches=not history,no_forbidden_task_inputs=not bad_inputs,precondition=precondition,discovery=discovery,no_unqualified_teacher_descent=not bad_descent,no_qualified_wrong_teacher_geometry=not wrong_teacher,physical_target_landing=result['strict_physical_target_landing'])
    if job.get('fault'):checks['fault_actually_executed']=len(fault_rows)>0
    if job.get('requires_actual_metric_loss'):checks['actual_loss_and_recovery']=bool(result['near_metric_missing_frames']>0 and result['recovery_active_frames']>0)
    if job.get('requires_actual_learner_struggle_then_expert'):checks['genuine_latched_expert_rescue']=bool(counts.get('policy',0)>0 and first_teacher and first_teacher['struggle_evidence']and counts.get('expert',0)>3)
    if job.get('requires_no_unnecessary_post_handoff_assistance'):checks['healthy_terminal_handoff']=bool(counts.get('expert_prefix',0)>0 and counts.get('policy',0)>0 and not unclean_terminal)
    if job['name']=='E02_distractors':checks['actual_distractor_views']=wrong_object_views>0;checks['actual_glare']=glare_frames>0
    technical=all(checks[k]for k in ['raw_review_ineligible','all_RGB_exact_capture_joins','actual_command_history_matches','no_forbidden_task_inputs'])
    report=dict(status='probe_passed'if probe and technical and precondition else'passed'if all(checks.values())else'failed',technical_contract_passed=technical,checks=checks,probe_only=probe,physical_outcome=result['outcome'],frames=rows,valid_capture_joins=valid_joined,actual_owners=counts,first_educational_takeover=first_teacher,actual_fault_rows=len(fault_rows),actual_glare_frames=glare_frames,actual_wrong_object_view_captures=wrong_object_views,command_mismatches=history[:8],image_mismatches=bad_images[:8],forbidden_input_rows=bad_inputs[:8],unsupported_teacher_descent_rows=bad_descent[:8],wrong_qualified_teacher_geometry=wrong_teacher[:8],unqualified_other_object_hypotheses=len(hypotheses),wrong_learner_geometry_rows=len(wrong_policy),precondition_error=precondition_error,discovery_error=discovery_error,training_eligible=False,production_qualified=False,assisted_is_not_independent_learner_success=True)
    (case/'actual_audit.json').write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('--probe',action='store_true');a=p.parse_args();print(json.dumps(audit(a.case,probe=a.probe)))
