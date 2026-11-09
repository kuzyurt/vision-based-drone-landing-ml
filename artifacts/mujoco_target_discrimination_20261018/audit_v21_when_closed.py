"""Wait on coordinator exit, then audit ownership/actual cameras once on VM."""
from pathlib import Path
import argparse,collections,json,os,select,subprocess,sys,time
import h5py,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent

def save(**v):
    v.update(pid=os.getpid(),training_eligible=False)
    p=ROOT/'v21_completion_audit_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)

def main():
    p=argparse.ArgumentParser();p.add_argument('--coordinator',type=int,required=True);a=p.parse_args()
    assert not(ROOT/'v21_completion_audit_state.json').exists()
    save(status='waiting_on_coordinator_exit',coordinator=a.coordinator)
    try:fd=os.pidfd_open(a.coordinator)
    except ProcessLookupError:fd=None
    if fd is not None:
        try:
            ready,_,_=select.select([fd],[],[],1900)
            if not ready:raise TimeoutError('Coordinator exit wait exceeded original flight caps')
        finally:os.close(fd)
    subprocess.run([sys.executable,str(ROOT/'inspect_v21.py'),'--audit'],check=True,stdout=subprocess.DEVNULL,timeout=90)
    state=json.loads((ROOT/'expert_v21_pipeline_state.json').read_text())
    if state['status']!='completed':save(status='upstream_failed',upstream=state);return
    reports=[];font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    for name in ['terminal','tilt']:
        ep=ROOT/('expert_visible_native_v21_'+name)
        rows=[json.loads(line)for line in(ep/'steps.jsonl').open()]
        audit=json.loads((ep/'struggle_ownership_audit.json').read_text())
        policy_indices=[];takeover=None;faults=[];teacher_unsupported=[];history_mismatches=[]
        for i,row in enumerate(rows):
            d=row['output'].get('learner_diagnostics')or{};dd=d.get('dagger')or{};owner=dd.get('ownership',{}).get('owner')
            if owner=='policy':policy_indices.append(i)
            if owner=='expert'and takeover is None:takeover=i
            if d.get('evaluation_fault_active'):faults.append(i)
            if i+1<len(rows)and not row.get('terminal'):
                executed=np.asarray(row['output']['executed_action']);next_previous=np.asarray(rows[i+1]['observation']['previous_executed_action'])
                if not np.allclose(executed,next_previous,rtol=0,atol=1e-8):history_mismatches.append(row['frame_index'])
                if owner in ['expert','expert_prefix']and executed[2]>.02 and row['observation']['px4'].get('armed')and not row['observation']['px4'].get('landed'):
                    intent=d.get('expert_intent',d.get('expert_shadow_intent',{}))
                    if not intent.get('allow_descent')and not d.get('mission_fallback_active'):teacher_unsupported.append(row['frame_index'])
        meaningful_reason=takeover is not None and (rows[takeover]['output'].get('learner_diagnostics')or{}).get('dagger',{}).get('ownership',{}).get('reason')in[
            'sustained_loss_after_learner_acquisition','repeated_learner_acquire_loss_cycle',
            'sustained_observed_wrong_object_pursuit','near_deck_learner_cannot_establish_geometry',
            'qualified_landing_without_vertical_progress','visual_alignment_no_progress']
        chosen=[0,len(rows)-1]
        if policy_indices:chosen+=[policy_indices[0],policy_indices[len(policy_indices)//2]]
        if takeover is not None:chosen+=[max(0,takeover-150),max(0,takeover-50),takeover,min(len(rows)-1,takeover+125)]
        elif faults:chosen+=[faults[0],faults[-1]]
        chosen=sorted(set(chosen));sheet=Image.new('RGB',(1280,390*((len(chosen)+1)//2)),(12,18,24))
        with h5py.File(ep/'observations.h5','r')as h:
            assert not bool(h.attrs['training_eligible'])
            for n,i in enumerate(chosen):
                row=rows[i];dd=(row['output'].get('learner_diagnostics')or{}).get('dagger')or{};own=dd.get('ownership')or{}
                x=n%2*640;y=n//2*390;sheet.paste(Image.fromarray(np.asarray(h['rgb'][row['frame_index']])),(x,y))
                ImageDraw.Draw(sheet).text((x+2,y+362),f"t={row['task_time_s']:.2f} {own.get('owner')} {own.get('reason')or''}",font=font,fill='white')
        sheet.save(ROOT/('v21_'+name+'_actual_ownership_sheet.jpg'),quality=94)
        audit.update(actual_camera_sheet='v21_'+name+'_actual_ownership_sheet.jpg',
            actual_history_mismatches=history_mismatches,teacher_unsupported_descent_frames=teacher_unsupported,
            learner_owned_rows=len(policy_indices),meaningful_struggle_trigger_observed=bool(meaningful_reason),
            independent_policy_success=(name=='natural'and takeover is None and not faults and
                set(audit['owners'])=={'policy'}and audit['result']['outcome']=='landed'),
            camera_review_pending=True,training_eligible=False)
        (ROOT/('v21_'+name+'_actual_ownership_audit.json')).write_text(json.dumps(audit,indent=2));reports.append(audit)
        if meaningful_reason:
            at=rows[takeover]['task_time_s'];end=min(rows[-1]['task_time_s'],at+12.)
            if end-max(0.,at-8.)>=5.:
                with(ROOT/('v21_'+name+'_window_encode.log')).open('x')as log:
                    subprocess.run([sys.executable,str(ROOT/'export_actual_review_window.py'),'--episode',ep.name,
                        '--name','v21_'+name+'_actual_struggle','--task-start',str(max(0.,at-8.)),
                        '--task-end',str(end),'--max-seconds','25'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    save(status='ready_for_autonomous_actual_camera_review',reports=reports,
         note='Human rejected early prevention and directed autonomous verification; no manufactured approval')

if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
