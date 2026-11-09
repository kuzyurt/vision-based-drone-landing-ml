"""Eight-slot, time-bounded approved curriculum. Technical gates are mandatory."""
from pathlib import Path
import datetime as dt,hashlib,json,os,signal,subprocess,sys,time
import psutil
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;SRC=ROOT/'search_v46/sources';OUT=ROOT/'collection_v3';UTC=dt.timezone.utc
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(s):
    s.update(coordinator_pid=os.getpid(),utc=dt.datetime.now(UTC).isoformat());p=OUT/'state.json.tmp';p.write_text(json.dumps(s,indent=2));p.replace(OUT/'state.json')
def resources(active):
    growth=0
    for t in active:
        try:growth+=max(0,2.84*1024**3-psutil.Process(t['p'].pid).memory_info().rss)
        except psutil.NoSuchProcess:pass
    ram=psutil.virtual_memory().available-growth
    free=float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
    return ram>=6.84*1024**3 and free>=1624+600*sum(time.monotonic()-t['start']<50 for t in active)
def main():
    purpose=json.loads((ROOT/'search_v46/audit/pilot_gate_receipt.json').read_text());review=json.loads((ROOT/'search_v46/audit/agent_visual_review.json').read_text());world=json.loads((ROOT/'world_contract_v1/proof.json').read_text())
    assert purpose['status']=='passed'and purpose['cases_passed']==9
    terminal=json.loads((ROOT/'terminal_handoff_v46/audit.json').read_text());assert terminal['status']=='passed'
    binding=json.loads((ROOT/'search_v46/candidate_binding.json').read_text());assert sha(binding['checkpoint'])==binding['recognizer_sha256']==purpose['recognizer_sha256']
    assert review['status']=='passed'and review['pilot_gate_sha256']==sha(ROOT/'search_v46/audit/pilot_gate_receipt.json')
    assert world['status']=='world_bindings_passed_not_collection_permission'and len(world['proof'])==5
    probe=json.loads((ROOT/'search_v46/runtime_probe.json').read_text());assert purpose['actor_sha256']==probe['actor_source_sha256']
    for f,d in json.loads((SRC/'source_hashes.json').read_text()).items():assert sha(SRC/f)==d
    plan=json.loads((ROOT/'world_contract_v1/plan.json').read_text());OUT.mkdir(exist_ok=False);(OUT/'episodes').mkdir();(OUT/'contracts').mkdir()
    # Same immutable V35 producer/actor; worlds vary at Environment.new_world.
    jobs=[]
    for j in plan['jobs']:
        j=dict(j);j['scenario']=dict(j['scenario'])
        if j['family']=='E10':j.update(fault=None,prefix=False);j['scenario'].update(distance=12.,initial_camera_target=True,initial_pan_deg=0.)
        name=j['name'];scenario=OUT/'contracts'/(name+'_scenario.json');scenario.write_text(json.dumps(j['scenario'],indent=2));distance=j['scenario']['distance'];search=j['family']in ['E06','E07','E08']
        band=[40.,60.]if distance>=40 else[20.,40.]if distance>=20 else[5.,20.]
        contract=dict(schema='approved.curriculum.task.purpose.v1',name=name,family=j['family'],role=j['role'],target_present=True,initial_target='outside_camera'if search else'visible',actual_initial_distance_band_m=band,target_hidden_or_removed=False,initial_blackout_allowed=False,exclude_return_home_and_land_home=True,requires_fault=bool(j['fault']),requires_metric_loss=j['family']in ['E04','E10','E11'],requires_teacher_rescue=j['family']in ['E10','E11'],grants_training_eligibility=False,foreground_cross_board_for_observable_pursuit=j['family']=='E10',requires_expired_memory=j['family']=='E11')
        cp=OUT/'contracts'/(name+'_contract.json');cp.write_text(json.dumps(contract,indent=2));(OUT/'episodes'/(name+'_contract.json')).write_bytes(cp.read_bytes());(OUT/'episodes'/(name+'_scenario.json')).write_bytes(scenario.read_bytes());jobs.append(dict(j,scenario_file=str(scenario),semantic_contract=str(cp),scenario_sha256=sha(scenario),contract_sha256=sha(cp)))
    # Fixed interleaving keeps both roles and all maps in early completed data.
    jobs=sorted(jobs,key=lambda j:(int(j['name'].split('_')[-2]),j['world']['kind'],j['role']))
    freeze=dict(schema='approved.curriculum.collection-plan.v1',jobs=jobs,maximum_workers=8,original_target=64,maximum_jobs=40,planned_training=30,planned_validation=10,quantity_reduced_for_time=True,source_snapshot=str(SRC),sources_sha256=sha(SRC/'source_hashes.json'),pilot_gate_sha256=sha(ROOT/'search_v46/audit/pilot_gate_receipt.json'),world_proof_sha256=sha(ROOT/'world_contract_v1/proof.json'),recognizer_static_gate_still_failed=True,raw_eligibility=False,perception_derivative_only=True,no_action_training=True,started_utc=dt.datetime.now(UTC).isoformat(),stop_new_starts_utc='2026-10-20T08:30:00Z',hard_stop_utc='2026-10-20T09:00:00Z')
    (OUT/'plan.json').write_text(json.dumps(freeze,indent=2));(OUT/'data_contract.json').write_text(json.dumps(dict(schema='approved.curriculum.visual-data-contract.v1',raw_eligibility_unchanged=True,raw_training_eligible=False,authorized_derivatives='Exact capture-hash-bound perception labels only after closed purpose/source/ownership/physical audit. No teacher action labels.',new_source_root=str(OUT/'episodes'),source_actor_sha256=probe['actor_source_sha256'],recognizer_sha256=probe['recognizer_sha256'],world_roles=plan['worlds'],excluded_sources=['old quarantine','retired suites','V23','V24','Tidewater','original test'],authority_receipts=['PLAN_APPROVAL.json','ADDENDUM_APPROVAL.json'],purpose_gate_sha256=freeze['pilot_gate_sha256']),indent=2))
    with(OUT/'admission.log').open('x')as admission_log:
        harvester=subprocess.Popen([sys.executable,str(ROOT/'harvest_collection_v3.py'),'--coordinator-pid',str(os.getpid())],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=admission_log,stderr=subprocess.STDOUT,start_new_session=True)
    (OUT/'admission_launch.json').write_text(json.dumps(dict(pid=harvester.pid)))
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(OLD),'EXPERT_RECOGNIZER_ROOT':'approved_curriculum_20261020/perception_training_v47','EXPERT_RUNTIME_GATE':'approved_curriculum_20261020/search_v46/runtime_probe.json','PYTHONPATH':str(SRC)+':'+str(OLD),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
    soft=dt.datetime(2026,10,20,8,30,tzinfo=UTC);hard=dt.datetime(2026,10,20,9,tzinfo=UTC);pending=jobs.copy();active=[];results=[];skipped=[]
    def close(t,interrupted=False):
        t['log'].close();p=OUT/'episodes'/t['job']['name']/'preview_result.json';d=json.loads(p.read_text())if p.exists()else None;results.append(dict(name=t['job']['name'],role=t['job']['role'],family=t['job']['family'],exit_code=t['p'].poll(),result=d,wall_s=time.monotonic()-t['start'],interrupted=interrupted));active.remove(t)
        if d and d['outcome']in ['water_strike','collision_failure']:raise RuntimeError('Safety event '+t['job']['name'])
        if t['p'].returncode!=0 or d is None:raise RuntimeError('Infrastructure/source failure '+t['job']['name'])
        missing_fault=bool(t['job']['fault'])and not d.get('fault_triggered')
        if d['outcome']!='landed' or missing_fault:
            same=[j for j in pending if j['family']==t['job']['family']];skipped.extend(dict(name=j['name'],reason='family_paused_after_actual_purpose_failure')for j in same);pending[:]=[j for j in pending if j not in same]
    try:
        while pending or active:
            now=dt.datetime.now(UTC)
            if (OUT/'stop_requested.json').exists():raise RuntimeError((OUT/'stop_requested.json').read_text())
            pause_file=OUT/'paused_families.json'
            if pause_file.exists():
                paused=json.loads(pause_file.read_text());same=[j for j in pending if j['family']in paused];skipped.extend(dict(name=j['name'],reason='audited_family_failure:'+str(paused[j['family']]))for j in same);pending[:]=[j for j in pending if j not in same]
            if now>=soft and pending:skipped.extend(dict(name=j['name'],reason='time_budget_no_new_starts')for j in pending);pending=[]
            if now>=hard:
                for t in active:
                    if t['p'].poll()is None:t['p'].send_signal(signal.SIGINT)
                for t in active[:]:
                    try:t['p'].wait(timeout=25)
                    except subprocess.TimeoutExpired:t['p'].terminate();t['p'].wait(timeout=15)
                    close(t,True)
                break
            while pending and len(active)<8 and resources(active):
                used={t['instance']for t in active};instance=next(i for i in range(160,168)if i not in used);assert0=0<=instance<=254;assert assert0
                j=pending.pop(0);log=(OUT/(j['name']+'.log')).open('x');args=[sys.executable,str(SRC/'run_semantic_collection_v46.py'),'--name','approved_curriculum_20261020/collection_v3/episodes/'+j['name'],'--scenario-file',j['scenario_file'],'--semantic-contract',j['semantic_contract'],'--instance',str(instance),'--scene',j['scene'],'--omit-overview']
                if j['fault']=='pan':args+=['--fault','gimbal_pan','--fault-duration','1.2']
                if j['fault']=='tilt':args+=['--tilt-fault','--fault-duration','6.0'if j['family']=='E11'else'1.6']
                if j['dagger']:args+=['--mode','dagger']
                if j['prefix']:args+=['--prefix']
                p=subprocess.Popen(args,cwd=OLD,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);active.append(dict(p=p,job=j,instance=instance,start=time.monotonic(),log=log))
            for t in active[:]:
                if t['p'].poll()is None:
                    if time.monotonic()-t['start']>2200:raise TimeoutError(t['job']['name'])
                else:close(t)
            save(dict(status='running'if pending or active else'closed_needs_admission',active=[dict(name=t['job']['name'],pid=t['p'].pid,instance=t['instance'])for t in active],pending=len(pending),results=results,skipped=skipped,frames_rate_basis=8.669,training_started=False))
            if pending and not active and not resources(active):raise RuntimeError('Insufficient safe resources')
            if active or pending:time.sleep(10)
        save(dict(status='closed_needs_admission',active=[],pending=0,results=results,skipped=skipped,training_started=False))
    except Exception as e:
        save(dict(status='failed_collection_stopped',error=repr(e),results=results,skipped=skipped,active=[dict(name=t['job']['name'],pid=t['p'].pid)for t in active]));raise
    finally:
        for t in active:
            if t['p'].poll()is None:
                t['p'].send_signal(signal.SIGINT)
                try:t['p'].wait(timeout=25)
                except subprocess.TimeoutExpired:t['p'].terminate();t['p'].wait(timeout=15)
            t['log'].close()
if __name__=='__main__':main()
