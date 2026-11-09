"""Exactly three necessary actual curriculum previews, never bulk collection."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(**value):
    value.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bulk_collection=False,training_eligible=False)
    dest=ROOT/'expert_v15_pipeline_state.json';tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(dest)
def main():
    assert not(ROOT/'expert_v15_pipeline_state.json').exists()
    jobs=[dict(case='hard',mode='expert',scene='hard',pan=140,fault='none',instance=100),
          dict(case='recovery',mode='expert',scene='basic',pan=0,fault='gimbal_pan',instance=101),
          dict(case='dagger',mode='dagger',scene='hard',pan=0,fault='none',instance=102)]
    snapshot=ROOT/'expert_source_snapshot_v15';snapshot.mkdir(exist_ok=False)
    files=[ROOT/'run_expert_review_v15.py',*(ROOT/'target_learning').glob('*.py')]
    hashes={}
    for f in files:
        dst=snapshot/f.relative_to(ROOT);dst.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(f,dst);hashes[str(f.relative_to(ROOT))]=sha(f)
    (snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
    # Actor dependency hashes must still equal the passed actual-RGB V14 probes.
    gate=json.loads((ROOT/'expert_runtime_probe_v14_r15.json').read_text())
    for name,digest in gate['actor_package_source_hashes'].items():assert sha(snapshot/'target_learning'/name)==digest
    save(stage='launching_three_review_cases',status='running',jobs=jobs)
    active=[];results=[]
    try:
        for job in jobs:
            name='expert_visible_native_v15_'+job['case'];log=(ROOT/(name+'.log')).open('x')
            args=[sys.executable,str(snapshot/'run_expert_review_v15.py'),'--name',name,'--mode',job['mode'],'--scene',job['scene'],'--pan',str(job['pan']),'--fault',job['fault'],'--instance',str(job['instance']),'--distance','8','--duration','120']
            p=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only','EXPERT_RUNTIME_GATE':'expert_runtime_probe_v14_r15.json','PYTHONDONTWRITEBYTECODE':'1'})
            active.append(dict(job=job,p=p,log=log,start=time.monotonic(),name=name))
        save(stage='three_actual_flights',status='running',children=[dict(case=t['job']['case'],pid=t['p'].pid) for t in active])
        while active:
            for task in active[:]:
                if task['p'].poll() is None:
                    if time.monotonic()-task['start']>900:raise TimeoutError(task['name']+' wall cap')
                    continue
                task['log'].close();code=task['p'].returncode
                if code:raise RuntimeError(task['name']+' failed; preserved log; code='+str(code))
                result=json.loads((ROOT/task['name']/'preview_result.json').read_text());results.append(dict(case=task['job']['case'],**result));active.remove(task)
                save(stage='three_actual_flights',status='running',results=results,children=[dict(case=t['job']['case'],pid=t['p'].pid) for t in active])
            if active:time.sleep(3)
        for job in jobs:
            script=ROOT/('package_review_v15_'+job['case']+'.py')
            with(ROOT/('package_v15_'+job['case']+'.log')).open('x')as log:
                subprocess.run([sys.executable,str(script)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=160)
        save(stage='review_previews_ready_needs_trace_and_rgb_inspection',status='completed',results=results)
    finally:
        for task in active:
            if task['p'].poll()is None:task['p'].terminate()
            task['log'].close()
if __name__=='__main__':
    try:main()
    except BaseException as error:save(stage='failed',status='failed',error=repr(error));raise
