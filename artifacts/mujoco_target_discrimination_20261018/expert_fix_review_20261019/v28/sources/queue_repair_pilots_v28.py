"""Small version-frozen expert review pilots; no collection/training/promotion."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,sys,time
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
OUT=ROOT/'expert_fix_review_20261019/v28';SRC=OUT/'sources'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    v.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),training_eligible=False)
    p=OUT/'state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)
def main():
    assert not(OUT/'state.json').exists(),'Never duplicate or overwrite a repair run'
    hashes=json.loads((SRC/'source_hashes.json').read_text())
    for rel,digest in hashes.items():assert sha(SRC/rel)==digest,rel
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only',
      'EXPERT_RUNTIME_GATE':'expert_fix_review_20261019/v28/runtime_probe.json','PYTHONDONTWRITEBYTECODE':'1',
      'PYTHONPATH':str(SRC)+':'+str(ROOT),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    save(status='running',stage='small_behavior_checks')
    for name in ['check_protocol_repair.py','check_camera_continuity.py','check_inspection_memory.py']:
        with(OUT/(name+'.log')).open('x')as log:subprocess.run([sys.executable,str(SRC/name)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    save(status='running',stage='actual_rgb_runtime_probe')
    with(OUT/'probe.log').open('x')as log:
        subprocess.run([sys.executable,str(SRC/'probe_expert_v28.py'),'--recognizer-root','perception_training_v12_rgb_only','--output',env['EXPERT_RUNTIME_GATE']],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    gate=json.loads((ROOT/env['EXPERT_RUNTIME_GATE']).read_text());assert gate['status']=='runtime_hook_probe_passed'
    jobs=[]
    for name,old,absent,instance in [('E12','task_harness_development_v1/full_home',True,150),('E06','expert_visible_native_v13c',False,151)]:
        old=ROOT/old;result=json.loads((old/'preview_result.json').read_text());scenario=old/'scenario.json';assert scenario.exists()
        jobs.append(dict(name=name,source=str(old),scenario=str(scenario),scenario_sha256=sha(scenario),scene=result.get('scene')or'basic',target_absent=absent,instance=instance))
    (OUT/'pilot_plan.json').write_text(json.dumps(dict(jobs=jobs,source_hashes=hashes,recognizer_sha256=gate['recognizer_sha256'],teacher_only=True,training_eligible=False),indent=2))
    active=[];results=[]
    try:
        for job in jobs:
            log=(OUT/(job['name']+'.log')).open('x');args=[sys.executable,str(SRC/'run_matched_expert_review_v28.py'),'--name','expert_fix_review_20261019/v28/'+job['name'],
                '--scenario-file',job['scenario'],'--scene',job['scene'],'--instance',str(job['instance'])]
            if job['target_absent']:args+=['--target-absent']
            p=subprocess.Popen(args,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            active.append(dict(p=p,name=job['name'],start=time.monotonic(),log=log))
        save(status='running',stage='two_search_regression_pilots',children=[dict(name=t['name'],pid=t['p'].pid)for t in active])
        while active:
            for t in active[:]:
                if t['p'].poll()is None:
                    if time.monotonic()-t['start']>2400:raise TimeoutError(t['name'])
                    continue
                t['log'].close();assert t['p'].returncode==0,t['name']+' failed; inspect preserved log'
                result=json.loads((OUT/t['name']/'preview_result.json').read_text());results.append(dict(name=t['name'],result=result));active.remove(t)
                save(status='running',stage='two_search_regression_pilots',results=results,children=[dict(name=x['name'],pid=x['p'].pid)for x in active])
            if active:time.sleep(15)
        save(status='completed',stage='closed_actual_recordings_require_audit',results=results)
    finally:
        for t in active:
            if t['p'].poll()is None:
                t['p'].send_signal(signal.SIGINT)
                try:t['p'].wait(timeout=20)
                except subprocess.TimeoutExpired:t['p'].terminate()
            t['log'].close()
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',stage='inspect_preserved_error',error=repr(error));raise
