"""Event-gated immutable physical qualification, eight workers, no training."""
from pathlib import Path
import datetime,hashlib,json,os,select,shutil,signal,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'frozen_task_evaluation_v2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    v.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    p=OUT/'state.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
def main():
    OUT.mkdir(exist_ok=False)
    pid=json.loads((ROOT/'task_harness_development_v1_launch.json').read_text())['pid'];save(status='waiting_for_full_home_development',upstream_pid=pid)
    try:fd=os.pidfd_open(pid)
    except ProcessLookupError:fd=None
    if fd is not None:
        try:select.select([fd],[],[],2600)
        finally:os.close(fd)
    upstream=json.loads((ROOT/'task_harness_development_v1/state.json').read_text())
    if upstream['status']!='completed_needs_physical_audit':save(status='not_started_upstream_failed',upstream=upstream);return
    from audit_frozen_task_episode_v1 import audit
    proof=audit(ROOT/'task_harness_development_v1/full_home')
    (OUT/'development_home_audit.json').write_text(json.dumps(proof,indent=2))
    if not(proof['physical_success']and proof['audit_passed']):save(status='not_started_full_home_gate_failed',audit=proof);return
    for case,folder in [('wrong_board_validation','candidate_development_v25'),('prior_hard_development','candidate_development_v25'),('recovery_tilt','candidate_recovery_v25')]:
        r=json.loads((ROOT/folder/(case+'_audit.json')).read_text())
        assert r['physical_landed']and not any(r[k]for k in ['actual_history_mismatches','unsupported_descent_frames','metric_center_inside_non_target_instance_frames'])
    snapshot=OUT/'source_snapshot';snapshot.mkdir()
    for f in [ROOT/'run_frozen_task_evaluation_v2.py',ROOT/'audit_frozen_task_episode_v1.py',ROOT/'queue_frozen_task_suite_v2.py',*(ROOT/'target_learning').glob('*.py'),*(ROOT/'collection_pipeline').glob('*.py')]:
        dst=snapshot/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
    hashes={str(f.relative_to(snapshot)):sha(f)for f in snapshot.rglob('*.py')};(snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
    plan_path=ROOT/'frozen_task_suite_v2/plan.json'
    if not plan_path.exists():
        with(OUT/'freeze.log').open('x')as log:subprocess.run([sys.executable,str(ROOT/'prepare_frozen_task_suite_v2.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    plan=json.loads(plan_path.read_text());assert len(plan['jobs'])==70
    receipt=dict(plan_sha256=sha(plan_path),source_hashes=hashes,recognizer_sha256=sha(ROOT/'perception_training_v24/best.pt'),
        actor_sha256=sha(snapshot/'target_learning/expert_adapter_v25.py'),before_any_heldout_policy_flight=True,cold_gate_remains_failed=True)
    (OUT/'candidate_binding.json').write_text(json.dumps(receipt,indent=2))
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v24','EXPERT_RUNTIME_GATE':'expert_runtime_probe_v25_r15.json','PYTHONDONTWRITEBYTECODE':'1'}
    pending=list(plan['jobs']);active=[];results=[];reason=None
    try:
        while pending or active:
            now=datetime.datetime.now(datetime.timezone.utc)
            if now>=datetime.datetime(2026,10,19,13,50,tzinfo=datetime.timezone.utc):reason='authorized_time_window_preserve_and_report';break
            for task in active[:]:
                if task['p'].poll()is None:
                    if time.monotonic()-task['start']>3200:raise TimeoutError(task['job']['name'])
                    continue
                task['log'].close();job=task['job'];active.remove(task)
                if task['p'].returncode:raise RuntimeError('Native child failed; preserve and diagnose '+job['name'])
                ep=OUT/job['name'];report=audit(ep);(ep/'physical_audit.json').write_text(json.dumps(report,indent=2))
                results.append(dict(job=job,audit=report))
                if report['native_safety_failure']or not report['audit_passed']:reason='retired_safety_or_input_audit_failure';break
            boat=[r for r in results if r['job']['group']=='boat'];failed=sum(not r['audit']['physical_success']for r in boat)
            if failed>3:reason='retired_57_of_60_unreachable'
            if reason:break
            slots=set(range(110,118))-{t['instance']for t in active}
            while pending and slots:
                job=pending[0]
                # Safety suite follows the entire boat qualification, never calls diagnostic home a pass.
                if job['group']=='home'and len(boat)<60:break
                mem=int(next(l.split()[1]for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')))*1024
                gpu=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0])*1024**2
                if mem<4*1024**3+2.84*1024**3 or gpu<1024**3:break
                for name,digest in hashes.items():assert sha(snapshot/name)==digest
                assert sha(plan_path)==receipt['plan_sha256'];assert sha(job['job_file'])==job['job_sha256']
                pending.pop(0);instance=min(slots);slots.remove(instance);log=(OUT/(job['name']+'.log')).open('x')
                args=[sys.executable,str(snapshot/'run_frozen_task_evaluation_v2.py'),'--name','frozen_task_evaluation_v2/'+job['name'],'--evaluation-job',job['job_file'],'--suite-manifest',str(plan_path),'--scenario-file',job['scenario_file'],'--scene','hard','--instance',str(instance),'--omit-overview']
                p=subprocess.Popen(args,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                active.append(dict(p=p,job=job,instance=instance,start=time.monotonic(),log=log))
            save(status='running',results=results,remaining=len(pending),children=[dict(pid=t['p'].pid,name=t['job']['name'],instance=t['instance'])for t in active])
            if pending and not active:
                raise RuntimeError('No launchable worker under measured memory guards')
            if active:time.sleep(15)
        if reason:save(status=reason,results=results,remaining=len(pending))
        else:
            success_boat=sum(r['audit']['physical_success']for r in results if r['job']['group']=='boat');home=sum(r['audit']['physical_success']for r in results if r['job']['group']=='home')
            qualified=success_boat>=57 and home==10 and sum(r['audit']['fault_triggered']for r in results)>=5
            save(status='completed_qualified'if qualified else'completed_not_qualified',results=results,boat_landings=success_boat,home_landings=home,goal_achieved=qualified)
    finally:
        for task in active:
            if task['p'].poll()is None:
                task['p'].send_signal(signal.SIGINT)
                try:task['p'].wait(timeout=20)
                except subprocess.TimeoutExpired:task['p'].terminate()
            task['log'].close()
if __name__=='__main__':
    try:main()
    except BaseException as e:
        if OUT.exists():save(status='failed_needs_specific_diagnosis',error=repr(e))
        raise

