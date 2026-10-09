"""Shared spawned-worker scheduler for benchmarks and approved collection."""
import multiprocessing
import queue
import signal
import time
import traceback
from pathlib import Path
from .runtime import WINDOWS,process_usage

def collection_worker(job,result_queue,cancel_event):
    signal.signal(signal.SIGINT,signal.SIG_IGN)
    if not WINDOWS:
        def cancel(signum,frame):raise KeyboardInterrupt('Collection cancelled')
        signal.signal(signal.SIGTERM,cancel)
    try:
        from dataclasses import replace
        from .config import Scenario
        from .run_episode import run_episode
        controller=None
        if job.get('checkpoint'):
            from .policy import PolicyRuntime
            controller=PolicyRuntime(job['checkpoint']);controller.reset()
        scenario=replace(Scenario(**job['scenario']),name=job['name'])
        summary=run_episode(scenario,job['directory'],role=job.get('role','review'),video=False,
                            instance=job['instance'],approval_bundle=job.get('approval_bundle'),
                            controller=controller,cancel_event=cancel_event)
        if job.get('checkpoint'):
            import json
            from .gate import file_hash
            summary['collection_checkpoint_sha256']=file_hash(job['checkpoint'])
            (Path(job['directory'])/'summary.json').write_text(json.dumps(summary,indent=2))
        result={'ok':summary['failure'] is None,'name':job['name'],'directory':job['directory'],
                'frames':summary['records'],'outcome':summary['outcome'],'flight_wall_s':summary['wall_seconds'],
                'performance':summary['performance'],**process_usage(),
                'record_start':summary['performance']['record_start'],
                'record_end':summary['performance']['record_end']}
    except BaseException as exc:
        result={'ok':False,'name':job['name'],'directory':job['directory'],
                'error':f'{type(exc).__name__}: {exc}','traceback':traceback.format_exc()}
    result_queue.put(result)

def iter_jobs(jobs,workers,instance_base=20,*,cancel_event=None):
    """One isolated PX4 instance per slot; the parent alone writes the manifest."""
    context=multiprocessing.get_context('spawn');results=context.Queue()
    cancel=cancel_event if cancel_event is not None else context.Event()
    pending=iter(jobs);active={}
    def launch(slot):
        try:job=dict(next(pending))
        except StopIteration:return
        job['instance']=instance_base+slot
        process=context.Process(target=collection_worker,args=(job,results,cancel))
        process.start();active[job['name']]=(slot,process,job)
    try:
        for slot in range(workers):launch(slot)
        while active:
            try:result=results.get(timeout=.5)
            except queue.Empty:
                if any(process.exitcode is not None for _,process,_ in active.values()):
                    # Queue feeder may trail process exit briefly.
                    try:result=results.get(timeout=2)
                    except queue.Empty:raise RuntimeError('Worker exited without a result')
                else:continue
            slot,process,job=active.pop(result['name']);process.join(timeout=5)
            if process.is_alive():
                active[result['name']]=(slot,process,job)
                raise RuntimeError('Worker reported a result but did not exit')
            if not result['ok']:raise RuntimeError(result['error']+'\n'+result['traceback'])
            launch(slot)
            yield result
    finally:
        cancel.set()
        for _,process,_ in active.values():process.join(timeout=20)
        for _,process,job in active.values():
            if process.is_alive():
                if WINDOWS:
                    from .px4 import stop_wsl_runtime
                    stop_wsl_runtime(Path(job['directory'])/'px4')
                process.terminate();process.join(timeout=5)
        results.close();results.join_thread()

def run_batch(jobs,*,cancel_event=None):
    started=time.perf_counter()
    base=jobs[0].get('instance',20)
    return list(iter_jobs(jobs,len(jobs),base,cancel_event=cancel_event)),time.perf_counter()-started
