"""Resume after verified compiler OOM; cached render workers and original data."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def save(value):
    value.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid())
    p=ROOT/'perception_pipeline_v2_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)

def run(name,script,args,timeout):
    with (ROOT/(name+'.log')).open('x')as log:
        p=subprocess.Popen([sys.executable,str(ROOT/script),*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        save(dict(stage=name,status='running',child_pid=p.pid,expert_collection=False))
        try:code=p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.terminate();p.wait(timeout=30);raise
        if code:raise RuntimeError(name+f' failed code{code}; read its preserved log')

def main():
    assert not(ROOT/'perception_pipeline_v2_state.json').exists();start=time.monotonic();rates=[]
    try:
        run('scene_cache_v2','cached_generation.py',['compile','--output','scene_cache_v2'],900)
        for workers in [4,8,12]:
            if rates:
                safe=int((28*1024)/max(r['peak_worker_rss_mib']for r in rates))
                if workers>safe:continue
            name=f'cached_bench_v2_{workers}w'
            run(name,'cached_generation.py',['generate','--output',name,'--index','scene_cache_v2/index.json',
                '--workers',str(workers),'--frames','16','--development'],180)
            m=json.loads((ROOT/name/'manifest.json').read_text());rates.append(dict(workers=workers,images_per_s=m['images_per_wall_s'],wall_s=m['wall_s'],peak_worker_rss_mib=m['peak_worker_rss_mib']))
        if rates[-1]['workers']==12 and rates[-1]['images_per_s']>rates[-2]['images_per_s']*1.05 and rates[-1]['peak_worker_rss_mib']*16<28*1024:
            name='cached_bench_v2_16w'
            run(name,'cached_generation.py',['generate','--output',name,'--index','scene_cache_v2/index.json',
                '--workers','16','--frames','16','--development'],180)
            m=json.loads((ROOT/name/'manifest.json').read_text());rates.append(dict(workers=16,images_per_s=m['images_per_wall_s'],wall_s=m['wall_s'],peak_worker_rss_mib=m['peak_worker_rss_mib']))
        best=max(rates,key=lambda r:r['images_per_s'])['workers']
        (ROOT/'perception_throughput_v2.json').write_text(json.dumps(dict(cohorts=rates,selected_workers=best,
            uncached8worker_failure='Kernel-verified global OOM at approximately4GiB per compiler process; all evidence retained.',
            scope='Cached static MuJoCo RGB/segmentation/glare/HDF5 generation including startup; native-flight throughput still unmeasured.'),indent=2))
        run('perception_dataset_v2','cached_generation.py',['generate','--output','perception_dataset_v2',
            '--index','scene_cache_v2/index.json','--workers',str(best),'--worlds','30','--frames','128','--seed','870000'],1800)
        run('perception_training_v2','train_discriminator.py',['--manifest','perception_dataset_v2/manifest.json','--output','perception_training_v2','--epochs','30'],3600)
        result=json.loads((ROOT/'perception_training_v2/result.json').read_text())
        save(dict(status='perception_bootstrap_complete',stage='inspect_metrics_then_runtime_expert_previews',elapsed_s=time.monotonic()-start,expert_collection=False,trained=result))
    except BaseException as exc:
        save(dict(status='failed',error=repr(exc),elapsed_s=time.monotonic()-start,expert_collection=False));raise

if __name__=='__main__':main()
