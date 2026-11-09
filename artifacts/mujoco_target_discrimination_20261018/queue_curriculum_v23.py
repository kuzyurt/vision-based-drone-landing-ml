"""Eight measured workers, staged perception observations, hard time/resource budget."""
from pathlib import Path
import datetime,hashlib,json,os,signal,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'curriculum_v23'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc)
def save(**v):
    v.update(pid=os.getpid(),utc=utc().isoformat(),perception_only=True,training_eligible=False)
    p=OUT/'collection_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)
def available_mib():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):return int(line.split()[1])/1024
    raise RuntimeError('No measured available RAM')
def cleanup(tasks):
    for t in tasks:
        if t['p'].poll()is None:t['p'].send_signal(signal.SIGINT)
    for t in tasks:
        if t['p'].poll()is None:
            try:t['p'].wait(timeout=20)
            except subprocess.TimeoutExpired:t['p'].terminate()
        t['log'].close()
    paths={str(OUT/'episodes'/t['job']['name']/'px4')for t in tasks}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            if entry.stat().st_uid!=os.getuid():continue
            args=(entry/'cmdline').read_bytes().decode().split('\0')
            if args and Path(args[0]).name=='px4'and any(p in args for p in paths):os.kill(int(entry.name),signal.SIGTERM)
        except(FileNotFoundError,ProcessLookupError,PermissionError):pass
def main():
    assert not(OUT/'collection_state.json').exists()
    plan=json.loads((OUT/'plan.json').read_text());contract=json.loads((OUT/'contract.json').read_text())
    assert sha(OUT/'plan.json')==contract['plan_sha256']and plan['workers']==8
    (OUT/'episodes').mkdir(exist_ok=False);snapshot=OUT/'producer_snapshot';snapshot.mkdir(exist_ok=False);hashes={}
    for f in [ROOT/'run_staged_curriculum_v23.py',*(ROOT/'target_learning').glob('*.py'),*(ROOT/'collection_pipeline').glob('*.py')]:
        dst=snapshot/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst);hashes[str(f.relative_to(ROOT))]=sha(f)
    (snapshot/'producer_source_hashes.json').write_text(json.dumps(dict(files=hashes,contract_sha256=sha(OUT/'contract.json'),scope='staged_perception_only'),indent=2))
    # Validation is distributed early, then complete world pairs follow; splits
    # were already frozen, and all paired views retain their assigned role.
    jobs=list(plan['jobs']);jobs.sort(key=lambda j:(int(j['world_index'])%5,j['role']!='validation',j['world_index'],j['name']))
    active=[];done=[];pending=list(jobs);all_tasks=[];start=time.monotonic()
    cutoff=datetime.datetime(2026,10,19,9,0,tzinfo=datetime.timezone.utc)
    save(status='collecting_staged_perception',planned=len(jobs),completed=[],active=[])
    try:
        while pending or active:
            if utc()>=cutoff:
                save(status='stopping_at_frozen_data_budget',completed=done,active=[t['job']['name']for t in active],not_launched=[j['name']for j in pending])
                cleanup(active);active=[];break
            if available_mib()<4096:raise RuntimeError('Measured RAM reserve below4GiB')
            used,total=map(float,subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],text=True).strip().split(','))
            if total-used<1024:raise RuntimeError('Measured GPU reserve below1GiB')
            while pending and len(active)<8:
                occupied={t['instance']for t in active};instance=next(i for i in range(130,138)if i not in occupied)
                job=pending.pop(0);log=(OUT/(job['name']+'.log')).open('x')
                args=[sys.executable,str(snapshot/'run_staged_curriculum_v23.py'),'--name','curriculum_v23/episodes/'+job['name'],
                    '--scenario-file',job['scenario_path'],'--staging-contract',str(OUT/'contract.json'),
                    '--mode',job['mode'],'--scene','hard','--instance',str(instance),'--omit-overview']
                if job['prefix']:args+=['--prefix']
                if job['tilt_fault']:args+=['--tilt-fault']
                process=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only',
                         'EXPERT_RUNTIME_GATE':'expert_runtime_probe_v22_r15.json','PYTHONDONTWRITEBYTECODE':'1'})
                task=dict(p=process,job=job,instance=instance,log=log,start=time.monotonic());active.append(task);all_tasks.append(task)
            changed=False
            for task in active[:]:
                if task['p'].poll()is None:
                    if time.monotonic()-task['start']>5400:raise TimeoutError(task['job']['name']+' native wall cap')
                    continue
                task['log'].close();ep=OUT/'episodes'/task['job']['name']
                if task['p'].returncode:raise RuntimeError(task['job']['name']+' producer failed; inspect preserved log')
                result=json.loads((ep/'preview_result.json').read_text());summary=json.loads((ep/'summary.json').read_text())
                if summary['outcome']in ['water_strike','collision_failure']:raise RuntimeError('Physical failure stops cohort: '+task['job']['name'])
                item=dict(name=task['job']['name'],role=task['job']['role'],result=result,records=summary['records'],wall_s=time.monotonic()-task['start'])
                done.append(item);active.remove(task);changed=True
            if changed or not(OUT/'active_jobs.json').exists():
                active_receipt=[dict(name=t['job']['name'],pid=t['p'].pid,instance=t['instance'])for t in active]
                (OUT/'active_jobs.json').write_text(json.dumps(active_receipt,indent=2))
                save(status='collecting_staged_perception',planned=len(jobs),completed=done,active=active_receipt,
                    remaining=len(pending),wall_s=time.monotonic()-start,measured_available_ram_mib=available_mib())
            if active:time.sleep(8)
        manifest=dict(schema='mujoco.staged_perception_collection.v1',completed=done,
            not_launched=[j['name']for j in pending],plan_sha256=sha(OUT/'plan.json'),contract_sha256=sha(OUT/'contract.json'),
            producer_source_receipt_sha256=sha(snapshot/'producer_source_hashes.json'),wall_s=time.monotonic()-start,
            training_eligible=False,action_imitation_targets_admissible=False,
            admission_pending='exact labels/source/owner/split checks; old review recordings excluded')
        (OUT/'staged_manifest.json').write_text(json.dumps(manifest,indent=2));save(status='collection_closed_needs_perception_admission',**manifest)
    finally:cleanup(active)
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
