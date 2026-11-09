"""Event-driven audit of all eight closed real flights, not launch success."""
from pathlib import Path
import datetime as dt,hashlib,importlib.util,json,os,select,sys,time
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'search_v48/audit'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def wait(pid):
    try:fd=os.pidfd_open(int(pid))
    except ProcessLookupError:return
    try:p=select.poll();p.register(fd,select.POLLIN);p.poll()
    finally:os.close(fd)
def main():
    OUT.mkdir(exist_ok=False);(OUT/'state.json').write_text(json.dumps(dict(status='waiting_native_closure')))
    wait(json.loads((ROOT/'search_v48/launch.json').read_text())['pid'])
    binding=json.loads((ROOT/'search_v48/candidate_binding.json').read_text());assert sha(binding['checkpoint'])==binding['recognizer_sha256']
    spec=importlib.util.spec_from_file_location('closed_readonly_auditor',ROOT/'audit_semantic_pilots_v4.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    src=ROOT/'search_v48/sources';a.EXPECTED_ACTOR=binding['actor_sha256'];a.EXPECTED_HARNESS=binding['harness_sha256'];a.EXPECTED_RECOGNIZER=binding['recognizer_sha256'];results=[];sheets=[]
    for name in ['learner_struggle','expired_memory']:
        a.PILOTS=ROOT/'search_v48/pilots'
        case=a.PILOTS/name
        try:result=a.run_case(name)
        except Exception as e:result=dict(name=name,status='failed',error=repr(e))
        if name in ['learner_struggle','expired_memory'] and(case/'steps.jsonl').exists():
            rows=[json.loads(x)for x in(case/'steps.jsonl').open()];transitions=[];previous=None;latched=False;latched_ok=True;expired=0;policy=0
            for i,row in enumerate(rows):
                d=row['output'].get('learner_diagnostics')or{};owner=d.get('actual_command_owner');dg=d.get('dagger')or{};policy+=owner=='policy'
                if owner=='expert'and previous=='policy':
                    transitions.append(dict(frame=i,task_s=row.get('task_time_s'),ownership=dg.get('ownership'),struggle=dg.get('struggle_evidence'),learner_wrong_observed=dg.get('wrong_candidate_selected_by_learner')));latched=True
                if latched and owner=='policy':latched_ok=False
                if owner=='expert'and d.get('expert_expired_memory_downlook'):expired+=1
                if owner not in ['evaluation_fault']:previous=owner
            def genuine(t):
                o=t.get('ownership')or{};e=t.get('struggle')or{};reason=o.get('reason','')
                u=e.get('unverified_descent')or{}
                return ((reason=='sustained_actual_descent_without_qualified_landing'and u.get('actual_height_loss_m',0)>=1. and u.get('observed_descent_s',0)>=3. and u.get('distinct_capture_count',0)>=10 and u.get('after_one_metre_threshold_s',0)>=2. and u.get('teacher_descent_authorized')is False)or(reason=='sustained_observed_wrong_object_pursuit'and e.get('wrong_pursuit_duration_s',0)>=3.)or(reason=='sustained_loss_after_learner_acquisition'and e.get('loss_duration_s',0)>=6. and not e.get('learner_recovery_progressing'))or(reason=='repeated_learner_acquire_loss_cycle'and e.get('loss_events_last20s',0)>=2 and not e.get('learner_recovery_progressing'))or(reason=='near_deck_learner_cannot_establish_geometry'and e.get('near_deck_missing_geometry_s',0)>=3.))
            checks=result.setdefault('checks',[]);checks.append(dict(name='genuine observable struggle and latched expert rescue, no preventive takeover',passed=policy>0 and bool(transitions)and all(genuine(t)for t in transitions)and latched_ok,detail=dict(policy_rows=policy,transitions=transitions,latched=latched_ok)))
            if name=='learner_struggle':
                first=json.loads((case/'initial_view_receipt.json').read_text());checks.append(dict(name='natural actual learner start, visible foreground copied-cross board',passed=first.get('foreground_board_pixels',0)>=32 and not any((r['output'].get('learner_diagnostics')or{}).get('actual_command_owner')=='expert_prefix'for r in rows),detail=first.get('foreground_board_pixels')))
            if name=='expired_memory':checks.append(dict(name='actual post-takeover expired-memory camera path',passed=expired>0,detail=expired))
            result['rescue_semantics']=dict(transitions=transitions,expired_memory_expert_frames=expired);result['status']='passed'if all(x['passed']for x in checks)else'failed'
        results.append(result);(OUT/(name+'_audit.json')).write_text(json.dumps(result,indent=2,allow_nan=False))
        if not(case/'observations.h5').exists():continue
        with h5py.File(case/'observations.h5','r')as h:
            n=len(h['steps']);indices=np.linspace(0,n-1,6).astype(int).tolist()if n else[]
            fault=result.get('fault_rows',[])
            if fault:indices=sorted(set([0,max(0,fault[0]-5),fault[0]+len(fault)//2,min(n-1,fault[-1]+30),min(n-1,fault[-1]+200),n-1]))
            sheet=Image.new('RGB',(960,420),(16,16,16));draw=ImageDraw.Draw(sheet)
            for k,i in enumerate(indices[:6]):
                row=json.loads(h['steps'][i]);d=row['output'].get('learner_diagnostics')or{};im=Image.fromarray(h['rgb'][i]).resize((320,180));sheet.paste(im,((k%3)*320,(k//3)*210));draw.text(((k%3)*320+3,(k//3)*210+181),f"{name} {row.get('task_time_s',0):.2f}s {d.get('control_phase')}\nowner {d.get('actual_command_owner')} ID {d.get('expert_observable_target_confirmed')} metric {d.get('metric_valid')}",fill='white')
            p=OUT/(name+'_actual_rgb.jpg');sheet.save(p,quality=87);sheets.append(dict(name=name,path=str(p.relative_to(ROOT)),sha256=sha(p)))
    passed=sum(x['status']=='passed'for x in results);receipt=dict(schema='approved.curriculum.gate.v1',gate_id='P02_v48_affected_actual_purpose',status='passed'if passed==2 else'failed',finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),cases_passed=passed,cases_total=2,results=[dict(name=r['name'],status=r['status'],failed_checks=[c for c in r.get('checks',[])if not c['passed']],error=r.get('error'),outcome=r.get('outcome'))for r in results],actual_rgb_sheets=sheets,actor_sha256=a.EXPECTED_ACTOR,harness_sha256=a.EXPECTED_HARNESS,recognizer_static80_gate_still_false=True,bulk_collection_allowed=False,awaiting_agent_actual_rgb_review=True,raw_training_eligibility_granted=False,recognizer_sha256=binding['recognizer_sha256'])
    (OUT/'pilot_gate_receipt.json').write_text(json.dumps(receipt,indent=2));(OUT/'state.json').write_text(json.dumps(dict(status='closed_needs_actual_rgb_review',passed=passed,total=2)));print(json.dumps({k:v for k,v in receipt.items()if k not in ['actual_rgb_sheets']}),flush=True)
if __name__=='__main__':main()
