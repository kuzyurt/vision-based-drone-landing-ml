"""After coordinator EXIT only: preserve a compact qualification/failure diagnosis.

Ground-truth visibility is an offline audit. It never reaches task actions and
these held-out images are not training data or model-selection inputs.
"""
from pathlib import Path
import collections,datetime,hashlib,json,os,select
import h5py,numpy as np
from PIL import Image,ImageDraw
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
ROOT=Path(__file__).resolve().parent;RUN=ROOT/'frozen_task_evaluation_v3';OUT=ROOT/'frozen_task_postmortem_v1'
def save(**v):
    p=OUT/'state.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**v),indent=2));t.replace(p)
def main():
    OUT.mkdir(exist_ok=False);coordinator=json.loads((RUN/'state.json').read_text())['pid']
    save(status='waiting_for_closed_frozen_evaluation',coordinator=coordinator)
    try:fd=os.pidfd_open(coordinator)
    except ProcessLookupError:fd=None
    if fd is not None:
        try:select.select([fd],[],[],8000)
        finally:os.close(fd)
    state=json.loads((RUN/'state.json').read_text());assert state['status']!='running','No holdout diagnosis while qualification is active'
    results=state.get('results',[]);failures=[r for r in results if not r['audit']['physical_success']]
    reports=[]
    for result in failures[:3]:
        name=result['job']['name'];ep=RUN/name;rows=[json.loads(l)for l in(ep/'steps.jsonl').open()]
        index=load_capture_index(ep/'capture_annotations.jsonl');identity=[];metric=[];fallback=[];visible=[];recognizable=[];matches=[]
        for i,row in enumerate(rows):
            d=row['output'].get('learner_diagnostics')or{}
            if d.get('expert_observable_target_confirmed'):identity.append(i)
            if d.get('metric_valid'):metric.append(i)
            if d.get('mission_fallback_active'):fallback.append(i)
        selected={0};maximum=(-1,None)
        with h5py.File(ep/'observations.h5','r')as h:
            for i,row in enumerate(rows):
                rgb=np.asarray(h['rgb'][row['frame_index']]);obs=row['observation'];label=join_delivered_frame(obs,rgb,index)
                if label is None:continue
                for inst in label['instances']:
                    if inst['annotation_instance']!='target':continue
                    visible.append(i)
                    if inst['identity']==1:recognizable.append(i)
                    if inst['pixels']>maximum[0]:maximum=(inst['pixels'],i)
                    d=row['output'].get('learner_diagnostics')or{}
                    a,b,c,e=inst['bbox']
                    for track in d.get('expert_visual_tracks',[]):
                        if abs(track['capture_s']-obs['image_capture_time_s'])>1e-5:continue
                        x,y=track['pixel']
                        if a<=x<c and b<=y<e:
                            matches.append(dict(frame=i,task_s=row['task_time_s'],target_probability=track['target_probability'],
                                identity_confirmations=track['identity_confirmations'],size_px=track['size_px']))
            for indices in [visible,recognizable,identity,metric,fallback]:
                if indices:selected.add(indices[0])
            if maximum[1]is not None:selected.add(maximum[1])
            if fallback:selected.add(max(0,fallback[0]-1))
            selected.add(len(rows)-1);selected=sorted(selected)[:8]
            sheet=Image.new('RGB',(1280,((len(selected)+1)//2)*390))
            for n,i in enumerate(selected):
                row=rows[i];d=row['output'].get('learner_diagnostics')or{};x=n%2*640;y=n//2*390
                sheet.paste(Image.fromarray(np.asarray(h['rgb'][row['frame_index']])),(x,y))
                ImageDraw.Draw(sheet).text((x+3,y+364),f"actual {row['task_time_s']:.2f}s {d.get('control_phase')} ID={bool(d.get('expert_observable_target_confirmed'))} metric={bool(d.get('metric_valid'))}",fill='white')
            sheet.save(OUT/(name+'_actual_rgb.jpg'),quality=93)
        report=dict(name=name,job=result['job'],physical_audit=result['audit'],actor_independent=True,no_teacher_handover=True,
            visible_target_frames=len(visible),identity_support_heuristic_frames=len(recognizable),confirmed_identity_frames=len(identity),metric_frames=len(metric),
            fallback_start_task_s=rows[fallback[0]]['task_time_s']if fallback else None,
            max_target_visible_pixels=maximum[0],fresh_proposal_center_matches=len(matches),
            matched_target_probabilities=matches[:10],max_matched_target_probability=max([m['target_probability']for m in matches],default=None),
            heldout_retired_before_any_tuning=True,images_not_training=True,
            interpretation='Offline rendered visibility/proposal match is diagnostic, not an actor input, universal human recognition range, or proof of cause.')
        (OUT/(name+'_diagnosis.json')).write_text(json.dumps(report,indent=2));reports.append(report)
    summary=dict(status=state['status'],planned_boat=60,planned_home=10,
        completed=len(results),outcomes=dict(collections.Counter(r['audit']['outcome']for r in results)),
        completed_boat=sum(r['job']['group']=='boat'for r in results),
        boat_landings=sum(r['job']['group']=='boat'and r['audit']['physical_success']for r in results),
        completed_home=sum(r['job']['group']=='home'for r in results),
        cases=[dict(name=r['job']['name'],map=r['job']['map'],category=r['job']['category'],outcome=r['audit']['outcome'],task_s=r['audit']['final_task_s'],audit_passed=r['audit']['audit_passed'])for r in results],
        selected_failure_diagnoses=reports,goal_achieved=state.get('goal_achieved',False),no_training_or_model_tuning=True)
    (OUT/'report.json').write_text(json.dumps(summary,indent=2));save(status='closed_evidence_ready_for_actual_camera_review',completed=len(results),outcomes=summary['outcomes'])
if __name__=='__main__':
    try:main()
    except BaseException as e:
        if OUT.exists():save(status='failed',error=repr(e))
        raise
