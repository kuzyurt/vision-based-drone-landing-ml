"""One actual-RGB probe then two causally necessary physical cases."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(**v):
    v.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bulk_collection=False,training_eligible=False)
    p=ROOT/'expert_v21_pipeline_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)
def main():
    assert not(ROOT/'expert_v21_pipeline_state.json').exists()
    snapshot=ROOT/'expert_source_snapshot_v21';snapshot.mkdir(exist_ok=False);hashes={}
    for f in [ROOT/'check_struggle_v21.py',ROOT/'probe_expert_v21.py',ROOT/'run_annotated_development_v21.py',*(ROOT/'target_learning').glob('*.py'),*(ROOT/'collection_pipeline').glob('*.py')]:
        dst=snapshot/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst);hashes[str(f.relative_to(ROOT))]=sha(f)
    (snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
    with(ROOT/'check_struggle_v21.log').open('x')as log:
        subprocess.run([sys.executable,str(snapshot/'check_struggle_v21.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=20)
    save(stage='actual_rgb_runtime_probe',status='running')
    with(ROOT/'expert_runtime_probe_v21.log').open('x')as log:
        subprocess.run([sys.executable,str(snapshot/'probe_expert_v21.py'),'--recognizer-root','perception_training_v12_rgb_only',
            '--output','expert_runtime_probe_v21_r15.json','--replay','r15'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
            check=True,timeout=150,env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT)})
    gate=json.loads((ROOT/'expert_runtime_probe_v21_r15.json').read_text());assert gate['status']=='runtime_hook_probe_passed'
    jobs=[dict(case='terminal',fault=False,instance=100),dict(case='tilt',fault=True,instance=101)]
    active=[];results=[]
    try:
        for job in jobs:
            name='expert_visible_native_v21_'+job['case'];log=(ROOT/(name+'.log')).open('x')
            args=[sys.executable,str(snapshot/'run_annotated_development_v21.py'),'--name',name,'--mode','dagger',
                '--scene','hard','--pan','140','--instance',str(job['instance']),'--distance','8','--duration','120','--prefix']
            if job['fault']:args+=['--tilt-fault']
            process=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only',
                     'EXPERT_RUNTIME_GATE':'expert_runtime_probe_v21_r15.json','PYTHONDONTWRITEBYTECODE':'1'})
            active.append(dict(p=process,name=name,log=log,start=time.monotonic()))
        save(stage='two_actual_terminal_and_recovery_cases',status='running',children=[dict(name=t['name'],pid=t['p'].pid)for t in active])
        while active:
            for task in active[:]:
                if task['p'].poll()is None:
                    if time.monotonic()-task['start']>1500:raise TimeoutError(task['name'])
                    continue
                task['log'].close()
                if task['p'].returncode:raise RuntimeError(task['name']+' failed; inspect preserved log')
                results.append(dict(name=task['name'],result=json.loads((ROOT/task['name']/'preview_result.json').read_text())))
                active.remove(task);save(stage='two_actual_terminal_and_recovery_cases',status='running',results=results,
                    children=[dict(name=t['name'],pid=t['p'].pid)for t in active])
            if active:time.sleep(5)
        save(stage='completed_needs_actual_camera_ownership_annotation_audit',status='completed',results=results)
    finally:
        for task in active:
            if task['p'].poll()is None:task['p'].terminate()
            task['log'].close()
if __name__=='__main__':
    try:main()
    except BaseException as error:save(stage='failed',status='failed',error=repr(error));raise
