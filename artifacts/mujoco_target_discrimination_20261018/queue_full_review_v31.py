"""Matched E-case reviews on a frozen actor; no training or policy promotion."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,sys,time
import psutil
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
PILOT=ROOT/'expert_fix_review_20261019/v31';SRC=PILOT/'sources';OUT=ROOT/'expert_fix_review_20261019/v31_full'
GiB=1024**3
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resident_bytes(process):
    try:return psutil.Process(process.pid).memory_info().rss
    except psutil.NoSuchProcess:return 0
def save(**v):
    p=OUT/'state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),training_eligible=False,**v),indent=2));tmp.replace(p)
def main():
    assert not(OUT/'state.json').exists(),'Never duplicate or overwrite evaluated review'
    pilot=json.loads((PILOT/'state.json').read_text());assert pilot['status']=='completed','Search pilots must close before wider review'
    completed={r['name']:r['result']['outcome']for r in pilot['results']}
    assert completed=={'E01':'landed','E03':'landed'},completed
    visual=json.loads((PILOT/'pilot_visual_review.json').read_text());assert visual['actual_camera_inspected'] and visual['accepted_for_expanded_review_only'] and not visual['training_eligible']
    hashes=json.loads((SRC/'source_hashes.json').read_text())
    for name,digest in hashes.items():assert sha(SRC/name)==digest,name
    gate=json.loads((PILOT/'runtime_probe.json').read_text());assert gate['status']=='runtime_hook_probe_passed'
    assert sha(SRC/'target_learning/expert_adapter_v31.py')==gate['actor_source_sha256']
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only',
        'EXPERT_RUNTIME_GATE':'expert_fix_review_20261019/v31/runtime_probe.json','PYTHONDONTWRITEBYTECODE':'1',
        'PYTHONPATH':str(SRC)+':'+str(ROOT),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    with(OUT/'takeover_checks.log').open('x')as log:subprocess.run([sys.executable,str(ROOT/'check_struggle_v22.py')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    inventory={r['case']:r for r in json.loads((ROOT/'expert_fix_review_20261019/matched_case_inventory.json').read_text())}
    order=['E10','E11','E04','E05','E02','E06','E07','E08','E09','E12'];pending=[]
    for i,name in enumerate(order):
        job=dict(inventory[name],instance=210+i,target_absent=name=='E12',original_mode=inventory[name]['prior_mode'])
        # Primary requested videos are the EXPERT driving these situations.
        # E09-E11 are explicit expert-only counterfactuals to old mixed flights,
        # never represented as an observed learner rescue.
        job['prior_mode']='expert'
        assert sha(job['scenario_path'])==job['scenario_sha256']
        pending.append(job)
    (OUT/'plan.json').write_text(json.dumps(dict(jobs=pending,actor_sha256=gate['actor_source_sha256'],recognizer_sha256=gate['recognizer_sha256'],
        source_hashes=hashes,teacher_review_not_training=True,E01_E03_reused_from='v31',E09_E10_E11_expert_only_counterfactuals=True,E04a_same_capture_source_as='E04',max_workers=8),indent=2))
    active=[];results=[];launches=[]
    try:
        while pending or active:
            # Account for unallocated growth of already-starting workers, too.
            while pending and len(active)<8:
                growth=sum(max(0,2.84*GiB-resident_bytes(t['p']))for t in active if t['p'].poll()is None)
                available=psutil.virtual_memory().available
                if available-growth-2.84*GiB<4*GiB:break
                free_gpu=float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
                if free_gpu<1024+615:break
                job=pending.pop(0);name=job['case'];log=(OUT/(name+'.log')).open('x')
                args=[sys.executable,str(SRC/'run_matched_expert_review_v31.py'),'--name','expert_fix_review_20261019/v31_full/'+name,
                    '--scenario-file',job['scenario_path'],'--scene',job['scene']or'basic','--instance',str(job['instance'])]
                if job['prior_mode']=='dagger':args+=['--mode','dagger','--prefix']
                if job.get('target_absent'):args+=['--target-absent']
                kind=(job.get('fault')or{}).get('kind')
                if kind=='gimbal_tilt':args+=['--tilt-fault']
                elif kind=='gimbal_pan':args+=['--fault','gimbal_pan','--fault-duration',str(job['fault']['duration_s'])]
                child=subprocess.Popen(args,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                active.append(dict(p=child,name=name,start=time.monotonic(),log=log))
                launches.append(dict(name=name,pid=child.pid,available_ram_gib=available/GiB,free_gpu_mib=free_gpu))
                save(status='running',stage='matched_physical_reviews',children=[dict(name=t['name'],pid=t['p'].pid)for t in active],remaining=[j['case']for j in pending],results=results,launches=launches)
            for task in active[:]:
                if task['p'].poll()is None:
                    if time.monotonic()-task['start']>5400:raise TimeoutError(task['name']+' bounded native review wall cap')
                    continue
                task['log'].close();assert task['p'].returncode==0,task['name']+' error; inspect preserved native log'
                result=json.loads((OUT/task['name']/'preview_result.json').read_text());results.append(dict(name=task['name'],result=result));active.remove(task)
                if result['outcome']!=('home_landed' if task['name']=='E12' else 'landed'):raise RuntimeError(task['name']+' did not land; stop before more buggy demos: '+result['outcome'])
                if task['name']in ['E03','E04','E05','E10','E11']and not result.get('fault_frames'):raise RuntimeError(task['name']+' configured disturbance did not execute')
                save(status='running',stage='matched_physical_reviews',children=[dict(name=t['name'],pid=t['p'].pid)for t in active],remaining=[j['case']for j in pending],results=results,launches=launches)
            if pending and not active:raise RuntimeError('Insufficient measured resources; no unsafe worker launch')
            if active:time.sleep(15)
        save(status='completed',stage='closed_needs_actual_camera_ownership_physical_audits',results=results,launches=launches)
    finally:
        for task in active:
            if task['p'].poll()is None:
                task['p'].send_signal(signal.SIGINT)
                try:task['p'].wait(timeout=25)
                except subprocess.TimeoutExpired:task['p'].terminate()
            task['log'].close()
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',stage='inspect_preserved_case_before_repair',error=repr(error));raise
