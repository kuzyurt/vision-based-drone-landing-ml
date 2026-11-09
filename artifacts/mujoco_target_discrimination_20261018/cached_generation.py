"""Separate memory-heavy MJCF compilation from parallel cached-MJB rendering."""
import os
os.environ.update(MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,multiprocessing,resource,sys,time
import generate_discrimination as original
ROOT=Path(__file__).resolve().parent;BASE=original.BASE

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=original.save

def compile_one(job):
    from target_learning.scenes import compile_variant
    import mujoco
    directory=Path(job['directory'])
    model=compile_variant(BASE/'landing_training/build/combined_1000us.xml',directory,seed=job['seed'])
    del model
    result=dict(seed=job['seed'],mjb=str(directory/'scene.mjb'),sha256=sha(directory/'scene.mjb'),
                compile_peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024.)
    save(directory/'cache_receipt.json',result);return result

def generate_cached(job):
    import mujoco
    from target_learning import scenes
    entry=job['cached_model'];path=Path(entry['mjb']);assert sha(path)==entry['sha256']
    def load(base_xml,out,**kw):
        assert kw['seed']==entry['seed']
        out=Path(out);out.mkdir(parents=True,exist_ok=False)
        save(out/'cache_reference.json',entry)
        return mujoco.MjModel.from_binary_path(str(path))
    scenes.compile_variant=load
    result=original.generate(job)
    result['render_peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024.
    result['cached_binary_model']=entry
    save(Path(job['directory'])/'report.json',result)
    return result

def build_cache(output):
    out=ROOT/output;out.mkdir(exist_ok=False);entries={};jobs=[]
    # Reuse all16already completed, verified benchmark-world binary models.
    old=ROOT/'perception_bench_4w'
    plan=json.loads((old/'plan.json').read_text())
    for j in plan['jobs']:
        path=Path(j['directory'])/'variant/scene.mjb'
        assert (Path(j['directory'])/'report.json').exists()and path.exists()
        entries[str(j['seed'])]=dict(seed=j['seed'],mjb=str(path),sha256=sha(path),source='completed prior4worker cohort')
    for i in range(30):jobs.append(dict(seed=870000+i*100,directory=str(out/f'seed_{870000+i*100}')))
    begin=time.monotonic()
    # Fresh process per compiled scene releases MuJoCo's retained MJCF compiler
    # state. Kernel OOM evidence showed4.4GiB/process in uncached8worker cohort.
    with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),max_tasks_per_child=1)as pool:
        for result in pool.map(compile_one,jobs):
            entries[str(result['seed'])]=result
            save(out/'index.json',dict(status='compiling',entries=entries,completed=len(entries)-16,planned=30,
                                      wall_s=time.monotonic()-begin,compile_workers=2))
    save(out/'index.json',dict(status='completed',entries=entries,wall_s=time.monotonic()-begin,compile_workers=2))
    print(json.dumps(dict(status='compiled',worlds=len(entries),seconds=time.monotonic()-begin)),flush=True)

def generate(a):
    out=ROOT/a.output;out.mkdir(exist_ok=False);index=json.loads((ROOT/a.index).read_text());assert index['status']=='completed'
    jobs=[]
    for i in range(a.worlds):
        role='training' if i<a.worlds-10 else 'validation' if i<a.worlds-5 else 'heldout'
        if a.development:role='development'
        seed=a.seed+i*100;name=f'{role}_{i:03d}';entry=index['entries'][str(seed)]
        jobs.append(dict(name=name,role=role,seed=seed,map=['island','beach','city','gravel','rock'][i%5],
            frames=a.frames,directory=str(out/name),cached_model=entry))
    save(out/'plan.json',dict(jobs=jobs,workers=a.workers,teacher_collection=False,cached_binary_rendering=True,
                            no_tidewater_inputs=True,world_split_frozen_before_generation=True))
    begin=time.monotonic();results=[]
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn'),max_tasks_per_child=1)as pool:
            futures=[pool.submit(generate_cached,j)for j in jobs]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result());save(out/'state.json',dict(status='rendering',completed=len(results),planned=len(jobs),wall_s=time.monotonic()-begin))
        result=dict(status='completed',entries=results,teacher_collection=False,
            wall_s=time.monotonic()-begin,completed_frames=sum(r['frames']for r in results),
            images_per_wall_s=sum(r['frames']for r in results)/(time.monotonic()-begin),
            peak_worker_rss_mib=max(r['render_peak_rss_mib']for r in results),world_split_frozen_before_generation=True)
        save(out/'manifest.json',result);save(out/'state.json',dict(status='completed',completed=len(results),planned=len(jobs),wall_s=time.monotonic()-begin))
        print(json.dumps({k:v for k,v in result.items()if k!='entries'}),flush=True)
    except BaseException as e:
        save(out/'state.json',dict(status='failed',error=repr(e),completed=len(results),wall_s=time.monotonic()-begin));raise

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','generate']);p.add_argument('--output',required=True)
    p.add_argument('--index');p.add_argument('--workers',type=int,default=4);p.add_argument('--worlds',type=int,default=16)
    p.add_argument('--frames',type=int,default=16);p.add_argument('--seed',type=int,default=850000);p.add_argument('--development',action='store_true');a=p.parse_args()
    if a.mode=='compile':build_cache(a.output)
    else:generate(a)

if __name__=='__main__':main()
