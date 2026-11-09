"""Bounded pre-review perception stages. Never collects expert trajectories."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def save(value):
    value.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid())
    p=ROOT/'perception_pipeline_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)

def run(name,script,args,timeout):
    log=ROOT/(name+'.log');assert not log.exists(), 'Existing stage must be inspected/resumed explicitly'
    with log.open('x')as f:
        child=subprocess.Popen([sys.executable,str(ROOT/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
            env={**os.environ,'MUJOCO_GL':'egl','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
        save(dict(stage=name,status='running',child_pid=child.pid,log=str(log),expert_collection=False))
        try:code=child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:child.wait(timeout=20)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            raise RuntimeError(name+' exceeded stage budget')
        if code:raise RuntimeError(name+f' failed with code {code}; inspect {log}')

def main():
    if (ROOT/'perception_pipeline_state.json').exists():raise FileExistsError('Pipeline state exists; inspect before resume')
    start=time.monotonic();rates=[]
    try:
        # All cohorts have identical image counts; startup is included, as it
        # also matters for this deliberately small image-generation stage.
        for workers in [4,8,12]:
            name=f'perception_bench_{workers}w'
            run(name,'generate_discrimination.py',['--output',name,'--workers',str(workers),
                '--worlds','16','--frames','4','--seed','850000','--development'],180)
            m=json.loads((ROOT/name/'manifest.json').read_text());rates.append(dict(workers=workers,images_per_s=m['images_per_wall_s'],wall_s=m['wall_s']))
        if rates[-1]['images_per_s']>rates[-2]['images_per_s']*1.05:
            name='perception_bench_16w'
            run(name,'generate_discrimination.py',['--output',name,'--workers','16',
                '--worlds','16','--frames','4','--seed','850000','--development'],180)
            m=json.loads((ROOT/name/'manifest.json').read_text());rates.append(dict(workers=16,images_per_s=m['images_per_wall_s'],wall_s=m['wall_s']))
        best=max(rates,key=lambda r:r['images_per_s'])['workers']
        (ROOT/'perception_throughput.json').write_text(json.dumps(dict(cohorts=rates,selected_workers=best,
            scope='Static RGB + segmentation + glare + lossless HDF5 generation including startup; NOT native expert-flight throughput.'),indent=2))
        run('perception_dataset_v1','generate_discrimination.py',['--output','perception_dataset_v1',
            '--workers',str(best),'--worlds','30','--frames','128','--seed','870000'],1800)
        run('perception_training_v1','train_discriminator.py',['--manifest','perception_dataset_v1/manifest.json',
            '--output','perception_training_v1','--epochs','30'],3600)
        result=json.loads((ROOT/'perception_training_v1/result.json').read_text())
        save(dict(status='perception_bootstrap_complete',stage='needs_review_of_actual_metrics_then_expert_integration',
            elapsed_s=time.monotonic()-start,expert_collection=False,trained=result))
    except BaseException as e:
        save(dict(status='failed',error=repr(e),elapsed_s=time.monotonic()-start,expert_collection=False));raise

if __name__=='__main__':main()
