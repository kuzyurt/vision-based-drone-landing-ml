"""Measure expert RGB collection locally, using review-only recordings."""
import argparse
import csv
import gc
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import statistics
import signal
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
if not __package__:
    sys.path.insert(0,str(ROOT.parent));__package__='landing_training'

from .runtime import WINDOWS,cache_lock,check_px4,windows_memory
from .execution import run_batch

def worker_counts(value):
    try:counts=sorted({1,*map(int,value.split(','))})
    except ValueError:raise argparse.ArgumentTypeError('Use comma-separated integers, e.g. 1,2,3')
    if min(counts)<1 or max(counts)>128:raise argparse.ArgumentTypeError('Worker counts must be 1..128')
    return counts

def read_number(path):
    try:return int(Path(path).read_text().strip())
    except (OSError,ValueError):return None

def hardware_info():
    if WINDOWS:
        total,available=windows_memory()
        return {'cpu_model':platform.processor(),'visible_cpu_threads':os.cpu_count(),
                'effective_cpu_capacity':float(os.cpu_count() or 1),'ram_GiB':total/1024**3,
                'available_ram_GiB':available/1024**3,'platform':platform.platform(),
                'python':platform.python_version(),'nvidia_gpu_name_memory_MiB_driver':None,
                'resource_scope':'Windows host; WSL PX4 resources are additional'}
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

def software_renderer(name):
    return any(word in name.lower() for word in ('llvmpipe','softpipe','lavapipe','software rasterizer',
        'swiftshader','gdi generic','microsoft basic render driver','mesa x11'))

def renderer_info():
    import mujoco
    from OpenGL import GL
    context=mujoco.GLContext(16,16)
    try:
        context.make_current()
        info={key:GL.glGetString(token).decode() for key,token in (
            ('vendor',GL.GL_VENDOR),('renderer',GL.GL_RENDERER),('version',GL.GL_VERSION))}
        info['software_rendering']=software_renderer(info['renderer'])
        info['backend']=os.environ['MUJOCO_GL'];info['mujoco']=mujoco.__version__
        return info
    finally:context.free()

def check_ports(base,count):
    for index in range(base,base+count):
        for kind,port in ((socket.SOCK_STREAM,4560+index),(socket.SOCK_DGRAM,18000+index),
                          (socket.SOCK_DGRAM,19000+index)):
            with socket.socket(socket.AF_INET,kind) as connection:
                if kind==socket.SOCK_STREAM:connection.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                try:connection.bind(('0.0.0.0' if WINDOWS else '127.0.0.1',port))
                except OSError as exc:raise RuntimeError(f'Port {port} is occupied; choose another --instance-base') from exc

def benchmark_scenarios(mode='full',quick_seconds=10):
    from .collect import planned_scenarios
    plan=planned_scenarios()['episodes']
    if mode=='quick':
        scenario=plan[0]['scenario'].copy();scenario['duration']=quick_seconds
        return [scenario]
    cases=[]
    for round_index in range(4):
        for family,kind in enumerate(('island','beach','city','gravel','rock')):
            weather=(family+round_index)%4
            band=(family+round_index)%3;reverse=bool((family+round_index)%2)
            cases.append(next(item['scenario'].copy() for item in plan if
                              item['scenario']['kind']==kind and item['weather_group']==weather and
                              item['distance_band']==band and item['scenario']['reverse']==reverse))
    return cases

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

def summarize(count,batches,episodes,mean_seconds,mode='quick'):
    frames=sum(b['frames'] for b in batches);span=sum(b['recording_span_s'] for b in batches)
    fps=frames/span;wall=sum(b['wall_s'] for b in batches)
    jobs=[job for batch in batches for job in batch['jobs']]
    batch_fps=[b['frames']/b['recording_span_s'] for b in batches]
    stage={}
    for job in jobs:
        for key,value in job['performance']['stages_s'].items():stage[key]=stage.get(key,0.)+value
    simulated=sum(job['recorded_flight_s'] for job in jobs)
    return {'workers':count,'repeats':len(batches),'recorded_frames':frames,'recording_fps':fps,
            'recording_fps_by_repeat':batch_fps,'recording_fps_min':min(batch_fps),'recording_fps_max':max(batch_fps),
            'recording_fps_stdev':statistics.stdev(batch_fps) if len(batch_fps)>1 else None,
            'simulated_seconds_per_wall_second':simulated/span,
            'measured_batch_wall_s':wall,'measured_episodes':len(jobs),
            'complete_episode_pipeline_per_hour':len(jobs)*3600/wall,
            'mean_batch_setup_s':sum(b['wall_s']-b['recording_span_s'] for b in batches)/len(batches),
            'max_worker_ram_MiB':max(job['max_rss_MiB'] for job in jobs),
            'hdf5_bytes':sum(job['hdf5_bytes'] for job in jobs),
            'stage_worker_seconds':stage,
            'physics_worker_s':sum(job['performance']['physics_s'] for job in jobs),
            'px4_sync_worker_s':sum(job['performance']['px4_sync_s'] for job in jobs),
            'sensor_send_worker_s':sum(job['performance']['sensor_send_s'] for job in jobs),
            'projected_collection_hours':episodes*wall/len(jobs)/3600 if mode=='full' else None,
            'projection_basis':'measured full episode pipeline including setup, shutdown, and artifact hashing; sample only' if mode=='full' else 'quick abort probe; no production time projection',
            'batches':batches}

def save_report(output,report):
    temporary=output/'report.tmp';temporary.write_text(json.dumps(report,indent=2));temporary.replace(output/'report.json')
    fields=('workers','repeats','recorded_frames','recording_fps','mean_batch_setup_s',
            'max_worker_ram_MiB','hdf5_bytes','projected_collection_hours')
    with (output/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(report['results'])

def main(argv=None):
    def cancel(signum,frame):raise KeyboardInterrupt('Benchmark cancelled')
    signal.signal(signal.SIGTERM,cancel)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=worker_counts,default=worker_counts('1,2,3'),help='Concurrent worker counts; always includes 1 as a baseline')
    parser.add_argument('--mode',choices=('quick','full'),default='quick',help='Quick: throughput probe that reaches the expert time-reserve abort; full: normal flights')
    parser.add_argument('--repeats',type=int,default=3,help='Repeat each worker count; full mode cycles a 20-case map/weather/distance/direction matrix')
    parser.add_argument('--quick-seconds',type=float,default=10,help='Quick scenario limit (8..30 s); expert abort reserve is 5 s')
    parser.add_argument('--episodes',type=int,default=1200,help='Dataset episode count for time projection')
    parser.add_argument('--mean-episode-seconds',type=float,default=60,help='Legacy compatibility option; projections now use measured full flights')
    parser.add_argument('--instance-base',type=int,default=20,help='First PX4 instance; adjust if ports are already in use')
    parser.add_argument('--gl',choices=('egl','glfw','osmesa'),default=os.environ.get('MUJOCO_GL','glfw' if WINDOWS else 'egl'),help='Actual MuJoCo rendering backend, selected before import')
    parser.add_argument('--output',type=Path,help='New output directory; existing directories are never replaced')
    args=parser.parse_args(argv)
    if sys.platform not in ('linux','win32'):parser.error('Supported hosts: Linux/WSL or Windows rendering with WSL PX4')
    if args.repeats<1 or args.episodes<1:parser.error('Repeats and episodes must be positive')
    if not 8<=args.quick_seconds<=30 or not 1<=args.mean_episode_seconds<=180:parser.error('Invalid quick duration or mean episode length')
    if not 0<=args.instance_base<=254-max(args.workers):parser.error('PX4 instance range must reserve MAVLink system 255 for the GCS')
    check_px4()
    # One native thread per numeric library prevents nested pools from consuming
    # all CPU cores in every independent simulation. GL driver threads are intact.
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
    sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
    os.environ['MUJOCO_GL']=args.gl
    os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'build/benchmark_cache'))
    output=(args.output or ROOT/'outputs'/('collection_benchmark_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f'))).resolve()
    if output.exists():parser.error('Output already exists; choose a new directory')
    from .gate import source_fingerprint
    from .scene import compile_scene
    info=hardware_info();info['graphics']=renderer_info()
    print(f'CPU: {info["cpu_model"]}; capacity {info["effective_cpu_capacity"]:g} cores; RAM {info["ram_GiB"]:.1f} GiB',flush=True)
    print(f'Renderer: {info["graphics"]["renderer"]} ({args.gl})',flush=True)
    if info['graphics']['software_rendering']:print('Rendering uses the CPU; these timings do not measure your RTX rendering performance.',flush=True)
    check_ports(args.instance_base,max(args.workers))
    cases=benchmark_scenarios(args.mode,args.quick_seconds)
    # Precompile before spawning. Workers also lock cache access during loading.
    print('Preparing the shared model cache (first run may take longer).',flush=True)
    cache_started=time.perf_counter()
    with cache_lock():model=compile_scene()
    cache_prepare_s=time.perf_counter()-cache_started
    del model;gc.collect()
    maximum_bytes=sum((int(cases[r%len(cases)]['duration']*25)+1)*640*360*3*n
                      for n in args.workers for r in range(args.repeats))+1024**3
    disk_path=output.parent
    while not disk_path.exists():disk_path=disk_path.parent
    if shutil.disk_usage(disk_path).free<maximum_bytes:
        parser.error(f'Reserve {maximum_bytes/1e9:.1f} GB free for worst-case raw RGB, or reduce workers/repeats')
    output.mkdir(parents=True)
    report={'schema':'aerodock.landing.collection-benchmark.v2','role':'review','training_eligible':False,
            'status':'running','hardware':info,'mode':args.mode,'video_export':False,'camera_views':'onboard only, matching production collection','cache_prepare_s':cache_prepare_s,
            'runtime_source_sha256':source_fingerprint(runtime_only=True),'projection':{'episodes':args.episodes,'policy_hz':25,'method':'measured full episode cost' if args.mode=='full' else 'disabled for quick probe'},
            'sample_scenarios':[cases[r%len(cases)] for r in range(args.repeats)],
            'limitations':['Full-flight projections extrapolate the measured scenario sample; use repeats 20 to cover the entire matrix.',
                           'Quick mode measures approach recording throughput and intentionally reaches the expert time-reserve abort; it does not test landing reliability.',
                           'Full mode cycles 20 stratified cases across five maps, four weather groups, three distance bands and both directions; this is not the complete 1200-episode distribution.',
                           'Observed memory does not include a GPU VRAM peak measurement.'],
            'results':[]}
    save_report(output,report)
    print(f'REVIEW ONLY — output: {output}\nProduction time projection: '+('measured full flights' if args.mode=='full' else 'disabled for short abort probes'),flush=True)
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
                validation_started=time.perf_counter()
                for row in rows:
                    validate_recording(row,report['runtime_source_sha256'])
                    from .gate import file_hash
                    hash_started=time.perf_counter();row['artifact_sha256']=file_hash(Path(row['directory'])/'observations.h5')
                    wall+=time.perf_counter()-hash_started
                validation_wall=time.perf_counter()-validation_started
                batches.append({'wall_s':wall,'recording_span_s':span,'frames':sum(r['frames'] for r in rows),'jobs':rows,'validation_wall_s':validation_wall})
            result=summarize(count,batches,args.episodes,args.mean_episode_seconds,args.mode)
            result['speedup_vs_one']=result['recording_fps']/report['results'][0]['recording_fps'] if report['results'] else 1.
            report['results'].append(result);save_report(output,report)
            print(f'{count} workers: {result["recording_fps"]:.2f} recorded frames/s; {result["speedup_vs_one"]:.2f}×; '+(f'projected {result["projected_collection_hours"]:.1f} hours (sample only)' if args.mode=='full' else 'no full-dataset projection'),flush=True)
        report['status']='completed'
        report['recommended_measured_worker_count']=max(report['results'],key=lambda r:r['complete_episode_pipeline_per_hour'])['workers']
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
