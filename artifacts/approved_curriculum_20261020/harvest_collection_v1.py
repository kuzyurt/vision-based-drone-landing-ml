"""Closed-case exact RGB audit and explicit perception-only admission."""
from pathlib import Path
import argparse,ctypes,datetime as dt,hashlib,importlib.util,json,os,select
ROOT=Path(__file__).resolve().parent;COL=ROOT/'collection_v1';OUT=ROOT/'admission_new_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,v):
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,indent=2,allow_nan=False));t.replace(p)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--coordinator-pid',type=int,required=True);args=parser.parse_args();OUT.mkdir(exist_ok=False)
    plan=json.loads((COL/'plan.json').read_text());jobs={j['name']:j for j in plan['jobs']};spec=importlib.util.spec_from_file_location('readonly_closed_auditor',ROOT/'audit_semantic_pilots_v3.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);a.PILOTS=COL/'episodes';src=ROOT/'search_v35/sources';a.EXPECTED_ACTOR=sha(src/'target_learning/expert_adapter_v35.py');a.EXPECTED_HARNESS=sha(src/'run_semantic_collection_v35.py')
    libc=ctypes.CDLL(None,use_errno=True);fd=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC);assert fd>=0;assert libc.inotify_add_watch(fd,os.fsencode(COL),0x00000008|0x00000080)>=0
    try:pidfd=os.pidfd_open(args.coordinator_pid)
    except ProcessLookupError:pidfd=None
    poll=select.poll();poll.register(fd,select.POLLIN)
    if pidfd is not None:poll.register(pidfd,select.POLLIN)
    seen=set();admitted=[];rejected=[];paused={}
    try:
        while True:
            state=json.loads((COL/'state.json').read_text())if(COL/'state.json').exists()else{}
            for item in state.get('results',[]):
                name=item['name']
                if name in seen:continue
                seen.add(name);job=jobs[name];case=COL/'episodes'/name
                try:
                    assert item['exit_code']==0 and not item.get('interrupted')and(case/'preview_result.json').exists(),'incomplete/infrastructure case'
                    result=a.run_case(name)
                    if job['family']=='E11':
                        rows=[json.loads(x)for x in(case/'steps.jsonl').open()];expired=sum(bool((r['output'].get('learner_diagnostics')or{}).get('expert_expired_memory_downlook'))and(r['output'].get('learner_diagnostics')or{}).get('actual_command_owner')=='expert'for r in rows)
                        result['checks'].append(dict(name='E11 actual post-takeover expired-memory path',passed=expired>0,detail=str(expired)));result['status']='passed'if all(c['passed']for c in result['checks'])else'failed'
                    ap=OUT/(name+'_audit.json');atomic(ap,result)
                    assert result['status']=='passed','purpose/source/capture/physical audit failed'
                    scenario=json.loads((case/'scenario.json').read_text());assert scenario==job['scenario'],'actual scenario differs from frozen plan'
                    entry=dict(name=name,role=job['role'],family=job['family'],source=str(case/'observations.h5'),source_sha256=sha(case/'observations.h5'),annotations=str(case/'capture_annotations.jsonl'),annotations_sha256=sha(case/'capture_annotations.jsonl'),audit=str(ap),audit_sha256=sha(ap),scenario_sha256=sha(case/'scenario.json'),world_seed=scenario['world_seed'],path_seed=scenario['path_seed'],kind=scenario['kind'],raw_training_eligible=False,granted_heads=['visible_design','marker_visibility','marker_pixel'],teacher_action_labels=False,actor_source_sha256=a.EXPECTED_ACTOR,harness_sha256=a.EXPECTED_HARNESS)
                    admitted.append(entry)
                except Exception as e:
                    why=repr(e);rejected.append(dict(name=name,reason=why,family=job['family'],source=str(case),raw_eligibility_changed=False));paused[job['family']]=why;atomic(COL/'paused_families.json',paused)
                    if 'result'in locals()and result.get('name')==name:
                        safety=[c for c in result.get('checks',[])if not c['passed']and any(k in c['name']for k in ['SHA/time','command history','no executed down','no water/collision','source/actor','no-radio'])]
                        if safety:atomic(COL/'stop_requested.json',dict(reason='audited safety/input/provenance failure',case=name,checks=safety))
                roles={r:{e['world_seed']for e in admitted if e['role']==r}for r in ['training','validation']};assert not roles['training']&roles['validation']
                manifest=dict(schema='approved.curriculum.new-perception-admission.v1',entries=admitted,rejections=rejected,source_plan_sha256=sha(COL/'plan.json'),data_contract_sha256=sha(COL/'data_contract.json'),raw_eligibility_never_changed=True,teacher_action_targets=False,old_quarantined_or_retired_data_used=False,world_split_disjoint=True,created_utc=dt.datetime.now(dt.timezone.utc).isoformat());atomic(OUT/'manifest.json',manifest);atomic(OUT/'state.json',dict(status='watching_closed_cases',admitted=len(admitted),rejected=len(rejected),coordinator_pid=args.coordinator_pid))
            finished=state.get('status')in ['closed_needs_admission','failed_collection_stopped']
            if finished:break
            events=poll.poll(60000)
            for eventfd,_ in events:
                if eventfd==fd:
                    try:os.read(fd,1024*1024)
                    except BlockingIOError:pass
                elif eventfd==pidfd:finished=True
            if finished:
                state=json.loads((COL/'state.json').read_text());unseen=[x for x in state.get('results',[])if x['name']not in seen]
                if not unseen:break
        atomic(OUT/'state.json',dict(status='closed',admitted=len(admitted),rejected=len(rejected),seen=len(seen),raw_eligibility_never_changed=True))
    finally:
        os.close(fd)
        if pidfd is not None:os.close(pidfd)
if __name__=='__main__':main()
