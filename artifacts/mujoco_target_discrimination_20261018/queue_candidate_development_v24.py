"""Frozen new-weights runtime proof and two bounded actor-alone development cases."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys,time,signal
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'candidate_development_v24'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(**v):
    v.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),fresh_holdout=False,training_used=False)
    p=OUT/'state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)
def main():
    assert not(OUT/'state.json').exists();snapshot=OUT/'source_snapshot';snapshot.mkdir(exist_ok=False)
    for f in [ROOT/'probe_expert_v24.py',ROOT/'run_candidate_development_v24.py',*(ROOT/'target_learning').glob('*.py'),*(ROOT/'collection_pipeline').glob('*.py')]:
        dst=snapshot/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
    hashes={str(f.relative_to(snapshot)):sha(f)for f in snapshot.rglob('*.py')};(snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
    weights=ROOT/'perception_training_v24/best.pt';assert sha(weights)=='664bbc576404135ba975c90989c0846356ea0c234c0b57d85204605f40d03891'
    save(stage='new_weights_actual_rgb_probe',status='running',candidate_sha256=sha(weights))
    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v24',
         'EXPERT_RUNTIME_GATE':'expert_runtime_probe_v24_r15.json','PYTHONDONTWRITEBYTECODE':'1'}
    with(OUT/'probe.log').open('x')as log:
        subprocess.run([sys.executable,str(snapshot/'probe_expert_v24.py'),'--recognizer-root','perception_training_v24',
            '--output','expert_runtime_probe_v24_r15.json'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150,env=env)
    gate=json.loads((ROOT/'expert_runtime_probe_v24_r15.json').read_text());assert gate['status']=='runtime_hook_probe_passed'
    jobs=[dict(name='wrong_board_validation',scenario=ROOT/'curriculum_v23/validation_world_10_0.json',instance=100),
          dict(name='prior_hard_development',scenario=ROOT/'expert_visible_native_v22_tilt/scenario.json',instance=101)]
    active=[];results=[]
    try:
        for job in jobs:
            assert job['scenario'].exists();log=(OUT/(job['name']+'.log')).open('x')
            args=[sys.executable,str(snapshot/'run_candidate_development_v24.py'),'--name','candidate_development_v24/'+job['name'],
                '--scenario-file',str(job['scenario']),'--mode','expert','--scene','hard','--instance',str(job['instance']),'--omit-overview']
            process=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env)
            active.append(dict(p=process,name=job['name'],start=time.monotonic(),log=log))
        save(stage='two_actor_alone_development_flights',status='running',children=[dict(name=t['name'],pid=t['p'].pid)for t in active])
        while active:
            for task in active[:]:
                if task['p'].poll()is None:
                    if time.monotonic()-task['start']>2200:raise TimeoutError(task['name'])
                    continue
                task['log'].close()
                if task['p'].returncode:raise RuntimeError(task['name']+' failed; inspect actual preserved log')
                results.append(dict(name=task['name'],result=json.loads((OUT/task['name']/'preview_result.json').read_text())))
                active.remove(task);save(stage='two_actor_alone_development_flights',status='running',results=results,
                    children=[dict(name=t['name'],pid=t['p'].pid)for t in active])
            if active:time.sleep(8)
        save(stage='closed_needs_actual_rgb_ownership_physical_audit',status='completed',results=results)
    finally:
        for task in active:
            if task['p'].poll()is None:
                task['p'].send_signal(signal.SIGINT)
                try:task['p'].wait(timeout=20)
                except subprocess.TimeoutExpired:task['p'].terminate()
            task['log'].close()
if __name__=='__main__':
    try:main()
    except BaseException as error:save(stage='failed',status='failed',error=repr(error));raise
