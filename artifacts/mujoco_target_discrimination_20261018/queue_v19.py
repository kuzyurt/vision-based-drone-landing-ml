"""Three bounded development roll-ins, all prior evidence preserved."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(**value):
    value.update(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        bulk_collection=False,training_eligible=False,human_review_status='old handover rejected; autonomous revision explicitly requested')
    p=ROOT/'expert_v19_pipeline_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)

def main():
    assert not(ROOT/'expert_v19_pipeline_state.json').exists()
    snapshot=ROOT/'expert_source_snapshot_v19';snapshot.mkdir(exist_ok=False)
    files=[ROOT/'run_expert_review_v19.py',ROOT/'check_struggle_v19.py',*(ROOT/'target_learning').glob('*.py')]
    hashes={}
    for f in files:
        dest=snapshot/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
        hashes[str(f.relative_to(ROOT))]=sha(f)
    (snapshot/'hashes.json').write_text(json.dumps(hashes,indent=2))
    gate=json.loads((ROOT/'expert_runtime_probe_v18_r15.json').read_text())
    assert gate['status']=='runtime_hook_probe_passed'
    # The recognizer/expert/protocol are identical to the verified actual-RGB
    # V18 package. New ownership code is separately checked, then flown below.
    for name,digest in gate['actor_package_source_hashes'].items():
        assert sha(snapshot/'target_learning'/name)==digest,'Prior expert dependency changed: '+name
    with(ROOT/'check_struggle_v19.log').open('x')as log:
        subprocess.run([sys.executable,str(snapshot/'check_struggle_v19.py')],cwd=ROOT,check=True,
                       stdout=log,stderr=subprocess.STDOUT,timeout=20)
    jobs=[dict(case='natural',prefix=False,tilt=False,pan=0),
          dict(case='near_deck',prefix=True,tilt=False,pan=140),
          dict(case='near_deck_tilt',prefix=True,tilt=True,pan=140)]
    active=[];results=[]
    try:
        for i,job in enumerate(jobs):
            name='expert_visible_native_v19_'+job['case'];log=(ROOT/(name+'.log')).open('x')
            args=[sys.executable,str(snapshot/'run_expert_review_v19.py'),'--name',name,'--mode','dagger',
                  '--scene','hard','--pan',str(job['pan']),'--instance',str(100+i),'--distance','8','--duration','120']
            if job['prefix']:args+=['--prefix']
            if job['tilt']:args+=['--tilt-fault']
            process=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only',
                     'EXPERT_RUNTIME_GATE':'expert_runtime_probe_v18_r15.json','PYTHONDONTWRITEBYTECODE':'1'})
            active.append(dict(name=name,job=job,p=process,log=log,start=time.monotonic()))
        save(stage='three_genuine_struggle_development_flights',status='running',
             children=[dict(case=t['job']['case'],pid=t['p'].pid)for t in active])
        while active:
            for task in active[:]:
                if task['p'].poll()is None:
                    if time.monotonic()-task['start']>1800:raise TimeoutError(task['name']+' wall cap')
                    continue
                task['log'].close()
                if task['p'].returncode:raise RuntimeError(task['name']+' failed; inspect preserved log')
                result=json.loads((ROOT/task['name']/'preview_result.json').read_text())
                results.append(dict(case=task['job']['case'],**result));active.remove(task)
                save(stage='three_genuine_struggle_development_flights',status='running',results=results,
                     children=[dict(case=t['job']['case'],pid=t['p'].pid)for t in active])
            if active:time.sleep(5)
        save(stage='needs_actual_struggle_ownership_and_camera_audit',status='completed',results=results)
    finally:
        for task in active:
            if task['p'].poll()is None:task['p'].terminate()
            task['log'].close()

if __name__=='__main__':
    try:main()
    except BaseException as error:save(stage='failed',status='failed',error=repr(error));raise
