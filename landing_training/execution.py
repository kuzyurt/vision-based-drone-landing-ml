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
            import torch
            from .policy import PolicyRuntime
            torch.set_num_threads(job.get('cpu_threads',1))
            controller=PolicyRuntime(job['checkpoint'],device=job.get('device','cpu'));controller.reset()
        scenario=replace(Scenario(**job['scenario']),name=job['name'])
        summary=run_episode(scenario,job['directory'],role=job.get('role','review'),video=job.get('video',False),
                            instance=job['instance'],approval_bundle=job.get('approval_bundle'),
                            controller=controller,cancel_event=cancel_event,record_images=job.get('record_images',True))
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

def iter_jobs(jobs,workers,instance_base=20,*,cancel_event=None,can_launch=None):
    """One isolated PX4 instance per slot; the parent alone writes the manifest."""
    context=multiprocessing.get_context('spawn');results=context.Queue()
    cancel=cancel_event if cancel_event is not None else context.Event()
    pending=iter(jobs);active={};next_job=None
    def launch(slot):
        nonlocal next_job
        if cancel.is_set():return
        if next_job is None:
            try:next_job=dict(next(pending))
            except StopIteration:return
        if can_launch is not None and not can_launch(next_job,[job for _,_,job in active.values()]):return
        job=next_job;next_job=None
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
            if not result['ok']:
                if cancel.is_set():continue
                raise RuntimeError(result.get('error','Episode failed; see '+result['directory'])+'\n'+result.get('traceback',''))
            yield result
            # Commit a complete recording before admitting another flight.
            launch(slot)
            for available_slot in set(range(workers))-{s for s,_,_ in active.values()}-{slot}:
                launch(available_slot)
    finally:
        if active:cancel.set()
        deadline=time.monotonic()+20
        for _,process,_ in active.values():process.join(timeout=max(0.,deadline-time.monotonic()))
        forced=[]
        for _,process,job in active.values():
            if process.is_alive():
                if WINDOWS:
                    from .px4 import stop_wsl_runtime
                    stop_wsl_runtime(Path(job['directory'])/'px4')
                process.terminate();forced.append((process,job))
        deadline=time.monotonic()+5
        for process,job in forced:
            process.join(timeout=max(0.,deadline-time.monotonic()))
            if process.is_alive():process.kill();process.join(timeout=2)
        if not WINDOWS:
            from .px4 import stop_owned_native_runtime
            # An abrupt worker death skips its finally block even when there is
            # no live Python process left to terminate. Its PX4 may still run.
            for _,_,job in active.values():stop_owned_native_runtime(Path(job['directory'])/'px4')
        results.close();results.join_thread()

def run_batch(jobs,*,cancel_event=None):
    started=time.perf_counter()
    base=jobs[0].get('instance',20)
    return list(iter_jobs(jobs,len(jobs),base,cancel_event=cancel_event)),time.perf_counter()-started
