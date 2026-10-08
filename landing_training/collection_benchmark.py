"""Measure expert RGB collection locally, using review-only recordings."""
import argparse
import csv
import gc
import json
import math
import multiprocessing
import os
import platform
import queue
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
if not __package__:
    sys.path.insert(0,str(ROOT.parent));__package__='landing_training'

def worker_counts(value):
    try:counts=sorted({1,*map(int,value.split(','))})
    except ValueError:raise argparse.ArgumentTypeError('Use comma-separated integers, e.g. 1,2,3')
    if min(counts)<1 or max(counts)>128:raise argparse.ArgumentTypeError('Worker counts must be 1..128')
    return counts

def read_number(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def hardware_info():
    visible=len(os.sched_getaffinity(0))
    capacity=float(visible)
    try:
        quota,period=Path('/sys/fs/cgroup/cpu.max').read_text().split()
        if quota!='max':capacity=min(capacity,int(quota)/int(period))
    except (OSError,ValueError):
        quota=read_number('/sys/fs/cgroup/cpu/cpu.cfs_quota_us')
        period=read_number('/sys/fs/cgroup/cpu/cpu.cfs_period_us')
        if quota is not None and quota>0 and period:capacity=min(capacity,quota/period)
    memory={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,value=line.split(':',1)
        if key in ('MemTotal','MemAvailable'):memory[key]=int(value.split()[0])*1024
    limit=read_number('/sys/fs/cgroup/memory.max')
    if limit is None:limit=read_number('/sys/fs/cgroup/memory/memory.limit_in_bytes')
    total=min(memory['MemTotal'],limit) if limit else memory['MemTotal']
    available=min(memory['MemAvailable'],total)
    current=read_number('/sys/fs/cgroup/memory.current')
    if limit and current is not None:
        try:
            stats=dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
            available=min(available,max(0,limit-current+int(stats.get('inactive_file',0))))
        except OSError:pass
    gpu=None
    if shutil.which('nvidia-smi'):
        try:
            result=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version',
                                   '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
            if result.returncode==0:gpu=result.stdout.strip().splitlines()
        except (OSError,subprocess.TimeoutExpired):pass
    model=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                if line.startswith('model name')),platform.machine())
    return {'cpu_model':model,'visible_cpu_threads':visible,'effective_cpu_capacity':capacity,
            'ram_GiB':total/1024**3,'available_ram_GiB':available/1024**3,
            'nvidia_gpu_name_memory_MiB_driver':gpu,'platform':platform.platform(),
            'python':platform.python_version()}

def renderer_info():
    import mujoco
    from OpenGL import GL
    context=mujoco.GLContext(16,16)
    try:
        context.make_current()
        info={key:GL.glGetString(token).decode() for key,token in (
            ('vendor',GL.GL_VENDOR),('renderer',GL.GL_RENDERER),('version',GL.GL_VERSION))}
        name=info['renderer'].lower()
        info['software_rendering']=any(word in name for word in ('llvmpipe','softpipe','software rasterizer','swiftshader'))
        info['backend']=os.environ['MUJOCO_GL'];info['mujoco']=mujoco.__version__
        return info
    finally:context.free()

def cache_lock():
    """Serialize model cache generation across benchmark processes."""
    import fcntl
    from contextlib import contextmanager
    @contextmanager
    def locked():
        ROOT.joinpath('build').mkdir(exist_ok=True)
        with (ROOT/'build/collection_benchmark.cache.lock').open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX)
            yield
    return locked()

def check_ports(base,count):
    for index in range(base,base+count):
        for kind,port in ((socket.SOCK_STREAM,4560+index),(socket.SOCK_DGRAM,18000+index),
                          (socket.SOCK_DGRAM,19000+index)):
            with socket.socket(socket.AF_INET,kind) as connection:
                if kind==socket.SOCK_STREAM:connection.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                try:connection.bind(('127.0.0.1',port))
                except OSError as exc:raise RuntimeError(f'Port {port} is occupied; choose another --instance-base') from exc

def worker(job,result_queue):
    # Convert parent cancellation into Python cleanup, including PX4.close().
    signal.signal(signal.SIGINT,signal.SIG_IGN)
    def cancel(signum,frame):raise KeyboardInterrupt('Benchmark cancelled')
    signal.signal(signal.SIGTERM,cancel)
    try:
        import resource
        from dataclasses import replace
        from .config import Scenario
        import landing_training.environment as environment
        import landing_training.run_episode as episode
        compile_original=environment.compile_scene
        def locked_compile(*args,**kwargs):
            with cache_lock():return compile_original(*args,**kwargs)
        environment.compile_scene=locked_compile
        times={};recorder_original=episode.Recorder
        class TimedRecorder(recorder_original):
            def __init__(self,*args,**kwargs):
                times['record_start']=time.perf_counter()
                super().__init__(*args,**kwargs)
            def close(self):
                super().close();times['record_end']=time.perf_counter()
        episode.Recorder=TimedRecorder
        scenario=replace(Scenario(**job['scenario']),name=job['name'])
        summary=episode.run_episode(scenario,job['directory'],role='review',video=False,instance=job['instance'])
        cpu=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
        result={'ok':summary['failure'] is None,'name':job['name'],'directory':job['directory'],
                'frames':summary['records'],'outcome':summary['outcome'],
                'flight_wall_s':summary['wall_seconds'],'max_rss_MiB':cpu.ru_maxrss/1024,
                'cpu_seconds':cpu.ru_utime+cpu.ru_stime+children.ru_utime+children.ru_stime,**times}
    except BaseException as exc:
        if isinstance(exc,KeyboardInterrupt):result_queue.cancel_join_thread()
        result={'ok':False,'name':job['name'],'error':f'{type(exc).__name__}: {exc}',
                'traceback':traceback.format_exc()}
    result_queue.put(result)

def run_batch(jobs):
    context=multiprocessing.get_context('spawn');results_queue=context.Queue()
    processes=[context.Process(target=worker,args=(job,results_queue)) for job in jobs]
    results=[];started=time.perf_counter()
    try:
        for process in processes:process.start()
        while len(results)<len(jobs):
            try:result=results_queue.get(timeout=.5)
            except queue.Empty:
                if any(p.exitcode not in (None,0) for p in processes):
                    raise RuntimeError('Benchmark worker exited unexpectedly; inspect the output directory')
                if all(p.exitcode==0 for p in processes):
                    raise RuntimeError('Benchmark worker finished without reporting a result')
                continue
            results.append(result)
            if not result['ok']:raise RuntimeError(result['error'])
        for process in processes:process.join()
        return results,time.perf_counter()-started
    finally:
        for process in processes:
            if process.pid and process.is_alive():process.terminate()
        for process in processes:
            if process.pid:process.join()
        results_queue.close()

def validate_recording(result,runtime_hash):
    import h5py
    import numpy as np
    from .recording import numeric_observation
    directory=Path(result['directory']);summary=json.loads((directory/'summary.json').read_text())
    rows=[json.loads(line) for line in (directory/'steps.jsonl').read_text().splitlines()]
    if summary['failure'] or summary['runtime_source_sha256']!=runtime_hash:raise ValueError('Failed or stale benchmark flight')
    if summary['role']!='review' or summary['training_eligible']:raise ValueError('Benchmark must remain review-only')
    if not rows or len(rows)!=summary['records'] or not rows[-1].get('terminal'):raise ValueError('Incomplete recording')
    if rows[0]['privileged']['vertical_clearance_m']<1.2 or not rows[0]['observation']['px4']['armed']:raise ValueError('Not an airborne start')
    if any(rows[-1]['output']['executed_action']) or rows[-1]['output']['action_supervision_valid']:raise ValueError('Invalid terminal action')
    if summary['outcome']=='landed' and (rows[-1]['observation']['px4']['armed'] or not rows[-1]['observation']['px4']['landed']):raise ValueError('Landing not confirmed by PX4')
    with h5py.File(directory/'observations.h5') as data:
        if data.attrs['role']!='review' or data.attrs['training_eligible'] or data['rgb'].shape!=(len(rows),360,640,3):raise ValueError('Invalid RGB role/count')
        for index,row in enumerate(rows):
            if json.loads(data['steps'][index])!=row or row['frame_index']!=index:raise ValueError('RGB/row order mismatch')
            if not np.isfinite(numeric_observation(row)).all():raise ValueError('Non-finite observation')
            if np.max(np.abs(np.array(row['privileged']['dock_joint_m'])-[.4,.46,.46]))>.008:raise ValueError('Dock must be open and raised')
            if index and abs(row['time_s']-rows[index-1]['time_s']-.04)>1e-6:raise ValueError('Decision clock must remain 25 Hz')
    result['raw_recording_audit_passed']=True
    result['hdf5_bytes']=(directory/'observations.h5').stat().st_size
    result['recorded_flight_s']=rows[-1]['task_time_s']

def summarize(count,batches,episodes,mean_seconds):
    frames=sum(b['frames'] for b in batches);span=sum(b['recording_span_s'] for b in batches)
    fps=frames/span
    setup=sum(b['wall_s']-b['recording_span_s'] for b in batches)/len(batches)
    seconds=episodes*mean_seconds*25/fps+math.ceil(episodes/count)*setup
    jobs=[job for batch in batches for job in batch['jobs']]
    return {'workers':count,'repeats':len(batches),'recorded_frames':frames,'recording_fps':fps,
            'mean_batch_setup_s':setup,'measured_batch_wall_s':sum(b['wall_s'] for b in batches),
            'max_worker_ram_MiB':max(job['max_rss_MiB'] for job in jobs),
            'hdf5_bytes':sum(job['hdf5_bytes'] for job in jobs),
            'projected_collection_hours':seconds/3600,'batches':batches}

def save_report(output,report):
    temporary=output/'report.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(output/'report.json')
    fields=('workers','repeats','recorded_frames','recording_fps','mean_batch_setup_s',
            'max_worker_ram_MiB','hdf5_bytes','projected_collection_hours')
    with (output/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(report['results'])

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=worker_counts,default=worker_counts('1,2,3'),help='Concurrent worker counts; always includes 1 as a baseline')
    parser.add_argument('--mode',choices=('quick','full'),default='quick',help='Quick: throughput probe that reaches the expert time-reserve abort; full: normal flights')
    parser.add_argument('--repeats',type=int,default=1,help='Repeat each worker count; full mode cycles near/middle/far start cases')
    parser.add_argument('--quick-seconds',type=float,default=10,help='Quick scenario limit (8..30 s); expert abort reserve is 5 s')
    parser.add_argument('--episodes',type=int,default=1200,help='Dataset episode count for time projection')
    parser.add_argument('--mean-episode-seconds',type=float,default=60,help='Explicit assumed mean recorded flight length for projection (1..180 s)')
    parser.add_argument('--instance-base',type=int,default=20,help='First PX4 instance; adjust if ports are already in use')
    parser.add_argument('--gl',choices=('egl','glfw','osmesa'),default=os.environ.get('MUJOCO_GL','egl'),help='Actual MuJoCo rendering backend, selected before import')
    parser.add_argument('--output',type=Path,help='New output directory; existing directories are never replaced')
    args=parser.parse_args(argv)
    if sys.platform!='linux':parser.error('Run this native PX4 benchmark in Linux or WSL2; see landing_training/README.md')
    if args.repeats<1 or args.episodes<1:parser.error('Repeats and episodes must be positive')
    if not 8<=args.quick_seconds<=30 or not 1<=args.mean_episode_seconds<=180:parser.error('Invalid quick duration or mean episode length')
    if not 0<=args.instance_base<=254-max(args.workers):parser.error('PX4 instance range must reserve MAVLink system 255 for the GCS')
    binary=ROOT/'.vendor/PX4-Autopilot/build/px4_sitl_landing/bin/px4'
    if not binary.is_file():parser.error('Native PX4 is missing. Run bash landing_training/setup.sh from the repository root first.')
    # One native thread per numeric library prevents nested pools from consuming
    # all CPU cores in every independent simulation. GL driver threads are intact.
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
    sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
    os.environ['MUJOCO_GL']=args.gl
    os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'build/benchmark_cache'))
    output=(args.output or ROOT/'outputs'/('collection_benchmark_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f'))).resolve()
    if output.exists():parser.error('Output already exists; choose a new directory')
    from .collect import planned_scenarios
    from .gate import source_fingerprint
    from .scene import compile_scene
    info=hardware_info();info['graphics']=renderer_info()
    print(f'CPU: {info["cpu_model"]}; capacity {info["effective_cpu_capacity"]:g} cores; RAM {info["ram_GiB"]:.1f} GiB',flush=True)
    print(f'Renderer: {info["graphics"]["renderer"]} ({args.gl})',flush=True)
    if info['graphics']['software_rendering']:print('Rendering uses the CPU; these timings do not measure your RTX rendering performance.',flush=True)
    check_ports(args.instance_base,max(args.workers))
    plan=planned_scenarios()['episodes']
    if args.mode=='quick':cases=[plan[0]['scenario'].copy()];cases[0]['duration']=args.quick_seconds
    else:
        cases=[next(item['scenario'] for item in plan if item['distance_band']==band and item['weather_group']==0 and
                    not item['scenario']['reverse'] and item['scenario']['kind']==('island','beach','rock')[band]) for band in range(3)]
    # Precompile before spawning. Workers also lock cache access during loading.
    print('Preparing the shared model cache (first run may take longer).',flush=True)
    with cache_lock():model=compile_scene()
    del model;gc.collect()
    maximum_bytes=sum((int(cases[r%len(cases)]['duration']*25)+1)*640*360*3*n
                      for n in args.workers for r in range(args.repeats))+1024**3
    disk_path=output.parent
    while not disk_path.exists():disk_path=disk_path.parent
    if shutil.disk_usage(disk_path).free<maximum_bytes:
        parser.error(f'Reserve {maximum_bytes/1e9:.1f} GB free for worst-case raw RGB, or reduce workers/repeats')
    output.mkdir(parents=True)
    report={'schema':'aerodock.landing.collection-benchmark.v1','role':'review','training_eligible':False,
            'status':'running','hardware':info,'mode':args.mode,'video_export':False,'camera_views':'external and onboard, matching current collection',
            'runtime_source_sha256':source_fingerprint(runtime_only=True),'projection':{'episodes':args.episodes,'assumed_mean_episode_s':args.mean_episode_seconds,'policy_hz':25},
            'limitations':['Time estimates assume measured throughput persists and the stated mean episode length.',
                           'Quick mode measures approach recording throughput and intentionally reaches the expert time-reserve abort; it does not test landing reliability.',
                           'Full mode cycles three calm scenarios; neither mode measures the complete weather/map distribution.',
                           'Observed memory does not include a GPU VRAM peak measurement.'],
            'results':[]}
    save_report(output,report)
    print(f'REVIEW ONLY — output: {output}\nProjection: {args.episodes} episodes × {args.mean_episode_seconds:g} recorded seconds',flush=True)
    code=0
    try:
        for count in args.workers:
            if report['results']:
                measured=max(r['max_worker_ram_MiB'] for r in report['results'])
                needed=measured*1024**2*count*1.25+1024**3
                if hardware_info()['available_ram_GiB']*1024**3<needed:
                    raise RuntimeError(f'{count} workers need approximately {needed/1024**3:.1f} GiB with memory headroom; reduce --workers')
            batches=[]
            for repeat in range(args.repeats):
                scenario=cases[repeat%len(cases)]
                jobs=[{'scenario':scenario,'instance':args.instance_base+i,
                       'name':f'workers_{count:03d}_repeat_{repeat+1:03d}_job_{i:03d}',
                       'directory':str(output/f'workers_{count:03d}_repeat_{repeat+1:03d}_job_{i:03d}')} for i in range(count)]
                print(f'Benchmark: {count} worker(s), repeat {repeat+1}/{args.repeats}',flush=True)
                rows,wall=run_batch(jobs)
                span=max(r['record_end'] for r in rows)-min(r['record_start'] for r in rows)
                for row in rows:validate_recording(row,report['runtime_source_sha256'])
                batches.append({'wall_s':wall,'recording_span_s':span,'frames':sum(r['frames'] for r in rows),'jobs':rows})
            result=summarize(count,batches,args.episodes,args.mean_episode_seconds)
            result['speedup_vs_one']=result['recording_fps']/report['results'][0]['recording_fps'] if report['results'] else 1.
            report['results'].append(result);save_report(output,report)
            print(f'{count} workers: {result["recording_fps"]:.2f} frames/s; {result["speedup_vs_one"]:.2f}×; projected {result["projected_collection_hours"]:.1f} hours',flush=True)
        report['status']='completed'
        report['recommended_measured_worker_count']=max(report['results'],key=lambda r:r['recording_fps'])['workers']
    except KeyboardInterrupt:
        report['status']='cancelled';code=130
    except Exception as exc:
        report['status']='failed';report['error']=f'{type(exc).__name__}: {exc}';code=1
        print(report['error'],file=sys.stderr)
    finally:save_report(output,report)
    print(f'Results: {output / "report.json"}\nTable: {output / "results.csv"}',flush=True)
    return code

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(f'Benchmark setup failed: {exc}\nSee landing_training/README.md for setup and rendering backends.',file=sys.stderr)
        raise SystemExit(1)
