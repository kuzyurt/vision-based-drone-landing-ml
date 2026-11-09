from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,sys,time
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z');OUT=ROOT/'expert_fix_review_20261019/v31';SRC=OUT/'sources'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    p=OUT/'state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),training_eligible=False,**v),indent=2));tmp.replace(p)
def main():
    assert not(OUT/'state.json').exists();hashes=json.loads((SRC/'source_hashes.json').read_text())
    for name,digest in hashes.items():assert sha(SRC/name)==digest,name
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only','EXPERT_RUNTIME_GATE':'expert_fix_review_20261019/v31/runtime_probe.json',
        'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(SRC)+':'+str(ROOT),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    save(status='running',stage='meaningful_camera_search_memory_checks')
    for name in ['check_protocol_repair.py','check_inspection_memory.py','check_axis_continuity.py','check_metric_continuity.py']:
        with(OUT/(name+'.log')).open('x')as log:subprocess.run([sys.executable,str(SRC/name)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    with(OUT/'probe.log').open('x')as log:subprocess.run([sys.executable,str(SRC/'probe_expert_v31.py'),'--recognizer-root','perception_training_v12_rgb_only','--output',env['EXPERT_RUNTIME_GATE']],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    gate=json.loads((ROOT/env['EXPERT_RUNTIME_GATE']).read_text());assert gate['status']=='runtime_hook_probe_passed'
    inventory={r['case']:r for r in json.loads((ROOT/'expert_fix_review_20261019/matched_case_inventory.json').read_text())}
    jobs=[dict(inventory[name],instance=190+i,target_absent=name=='E12')for i,name in enumerate(['E01','E03'])]
    (OUT/'pilot_plan.json').write_text(json.dumps(dict(jobs=jobs,actor_sha256=gate['actor_source_sha256'],source_hashes=hashes,review_only=True),indent=2))
    active=[];results=[]
    try:
        for job in jobs:
            name=job['case'];assert sha(job['scenario_path'])==job['scenario_sha256'];log=(OUT/(name+'.log')).open('x')
            args=[sys.executable,str(SRC/'run_matched_expert_review_v31.py'),'--name','expert_fix_review_20261019/v31/'+name,'--scenario-file',job['scenario_path'],'--scene',job['scene']or'basic','--instance',str(job['instance'])]
            if job['prior_mode']=='dagger':args+=['--mode','dagger','--prefix']
            if job['target_absent']:args+=['--target-absent']
            kind=(job.get('fault')or{}).get('kind')
            if kind=='gimbal_tilt':args+=['--tilt-fault']
            elif kind=='gimbal_pan':args+=['--fault','gimbal_pan','--fault-duration',str(job['fault']['duration_s'])]
            p=subprocess.Popen(args,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);active.append(dict(p=p,name=name,start=time.monotonic(),log=log))
        save(status='running',stage='four_matched_teacher_path_pilots',children=[dict(name=t['name'],pid=t['p'].pid)for t in active])
        while active:
            for t in active[:]:
                if t['p'].poll()is None:
                    if time.monotonic()-t['start']>4200:raise TimeoutError(t['name'])
                    continue
                t['log'].close();assert t['p'].returncode==0,t['name']+' failed; inspect preserved log'
                r=json.loads((OUT/t['name']/'preview_result.json').read_text());results.append(dict(name=t['name'],result=r));active.remove(t)
                expected='home_landed'if t['name']=='E12'else'landed'
                if r['outcome']!=expected:raise RuntimeError(t['name']+' not physically completed as required: '+r['outcome'])
                save(status='running',stage='four_matched_teacher_path_pilots',children=[dict(name=x['name'],pid=x['p'].pid)for x in active],results=results)
            if active:time.sleep(15)
        save(status='completed',stage='closed_needs_camera_ownership_audit',results=results)
    finally:
        for t in active:
            if t['p'].poll()is None:
                t['p'].send_signal(signal.SIGINT)
                try:t['p'].wait(timeout=25)
                except subprocess.TimeoutExpired:t['p'].terminate()
            t['log'].close()
if __name__=='__main__':
    try:main()
    except BaseException as e:save(status='failed',stage='diagnose_preserved_failure_before_expansion',error=repr(e));raise
