"""Discover resources and find the best measured expert-collection concurrency."""
import argparse
import csv
from datetime import datetime,timezone
import gc
import json
import math
import multiprocessing
import os
from pathlib import Path
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
if not __package__:
    sys.path.insert(0,str(ROOT.parent));__package__='landing_training'

from .resource_monitor import GIB,ResourceMonitor,available_memory,cpu_topology,nvidia_snapshot,renderer_gpu_indices
from .runtime import WINDOWS,cache_lock,check_px4

class TrialStopped(RuntimeError):pass

def requested_worker_counts(value):
    try:counts=sorted(set(int(item) for item in value.split(',')))
    except ValueError:raise argparse.ArgumentTypeError('Use comma-separated worker counts, e.g. 32,64')
    if not counts or min(counts)<1 or max(counts)>128:
        raise argparse.ArgumentTypeError('Worker counts must be 1..128')
    return counts

def probe_backends(requested=None):
    """MuJoCo chooses its GL implementation at import: probe in fresh processes."""
    candidates=[requested] if requested else (['glfw'] if WINDOWS else ['egl']+(['glfw'] if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY') else [])+['osmesa'])
    results=[]
    for backend in candidates:
        env=os.environ.copy();env['MUJOCO_GL']=backend
        command=[sys.executable,'-c','import json; from landing_training.collection_benchmark import renderer_info; print(json.dumps(renderer_info()))']
        try:
            result=subprocess.run(command,cwd=ROOT.parent,env=env,capture_output=True,text=True,timeout=30)
            if result.returncode:results.append({'backend':backend,'error':result.stderr.strip()[-2000:]});continue
            results.append({'backend':backend,'graphics':json.loads(result.stdout.strip().splitlines()[-1])})
        except (OSError,ValueError,subprocess.TimeoutExpired) as exc:results.append({'backend':backend,'error':str(exc)})
    usable=[r for r in results if 'graphics' in r]
    accelerated=[r for r in usable if not r['graphics']['software_rendering']]
    accelerated.sort(key=lambda r:'nvidia' not in (r['graphics'].get('vendor','')+' '+r['graphics']['renderer']).lower())
    return (accelerated or usable)[0]['graphics'] if usable else None,results

def initial_worker_cap(hardware,requested,instance_base):
    cpu=max(1,math.ceil(hardware['effective_cpu_capacity']))
    ram=max(1,int(available_memory()*.75/(1.75*GIB)))
    return min(requested or cpu,ram,128,254-instance_base)

def best_result(results,margin=.03):
    """Prefer fewer workers when speed differs by less than the noise margin."""
    if not results:return None
    maximum=max(r['complete_episode_pipeline_per_hour'] for r in results)
    contenders=[r for r in results if r['complete_episode_pipeline_per_hour']>=maximum*(1-margin)]
    return min(contenders,key=lambda r:r['workers'])

def refinement_counts(results,cap):
    best=best_result(results,0.)['workers'];tested={r['workers'] for r in results}
    lower=max((n for n in tested if n<best),default=1)
    upper=min((n for n in tested if n>best),default=cap)
    candidates={best-1,best+1,(lower+best)//2,(best+upper+1)//2}
    return sorted(n for n in candidates if 1<=n<=cap and n not in tested)

def prune_recordings(batch_root):
    """Only remove this trial's disposable raw files after validation."""
    for directory in batch_root.iterdir():
        if not directory.is_dir():continue
        for name in ('observations.h5','steps.jsonl'):
            path=directory/name
            if path.is_file():path.unlink()

def run_trial(count,cases,repeats,phase,output,settings,deadline,ram_budget,gpu_indices):
    from .collection_benchmark import check_ports,validate_recording,summarize
    from .execution import run_batch
    from .gate import file_hash
    check_ports(settings.instance_base,count)
    trial=output/f'{phase}_{count:03d}';trial.mkdir()
    batches=[];resource_reports=[];trial_started=time.monotonic()
    for repeat in range(repeats):
        for case_index,scenario in enumerate(cases):
            if time.monotonic()>=deadline:raise TrialStopped('tuning time budget reached')
            batch_dir=trial/f'repeat_{repeat+1:02d}_case_{case_index+1:02d}';batch_dir.mkdir()
            required=(int(scenario['duration']*25)+1)*640*360*3*count+GIB
            if shutil.disk_usage(output).free<required:raise TrialStopped('insufficient disk headroom for this batch')
            jobs=[{'scenario':scenario,'instance':settings.instance_base+i,
                   'name':f'{phase}_{count:03d}_{repeat:02d}_{case_index:02d}_{i:03d}',
                   'directory':str(batch_dir/f'worker_{i:03d}')} for i in range(count)]
            cancel=multiprocessing.get_context('spawn').Event()
            monitor=ResourceMonitor(cancel,ram_budget_bytes=ram_budget,
                reserve_bytes=settings.ram_reserve_bytes,deadline=deadline,
                gpu_indices=gpu_indices,vram_fraction=settings.vram_fraction)
            parent_times=os.times();parent_cpu=parent_times.user+parent_times.system
            try:
                with monitor:
                    if cancel.is_set():raise TrialStopped(monitor.reason)
                    rows,wall=run_batch(jobs,cancel_event=cancel)
                if monitor.reason:raise TrialStopped(monitor.reason)
            except BaseException:
                telemetry=monitor.report();(batch_dir/'resources.json').write_text(json.dumps(telemetry,indent=2))
                if not settings.keep_recordings:prune_recordings(batch_dir)
                if monitor.reason:raise TrialStopped(monitor.reason)
                raise
            usage=monitor.report();end_times=os.times()
            cpu=sum(row['cpu_seconds'] for row in rows)+end_times.user+end_times.system-parent_cpu
            usage['mean_cpu_cores_accounted']=cpu/wall
            usage['accounting_scope']='worker/PX4 lifecycle plus parent CPU; GPU query subprocess overhead excluded' if not WINDOWS else 'Windows processes only; WSL PX4 CPU excluded'
            span=max(row['record_end'] for row in rows)-min(row['record_start'] for row in rows)
            validation_started=time.perf_counter()
            for row in rows:
                validate_recording(row,settings.runtime_hash)
                hash_started=time.perf_counter();row['artifact_sha256']=file_hash(Path(row['directory'])/'observations.h5')
                wall+=time.perf_counter()-hash_started
            batches.append({'wall_s':wall,'recording_span_s':span,'frames':sum(row['frames'] for row in rows),
                            'jobs':rows,'validation_wall_s':time.perf_counter()-validation_started})
            resource_reports.append(usage);(batch_dir/'resources.json').write_text(json.dumps(usage,indent=2))
            if not settings.keep_recordings:prune_recordings(batch_dir)
    result=summarize(count,batches,settings.episodes,60,'full' if phase=='confirm' else 'quick')
    durations=[b['wall_s'] for b in batches]
    result.update(phase=phase,scenario_count=len(cases),repeat_count=repeats,resources=resource_reports,
        trial_wall_s=time.monotonic()-trial_started,raw_recordings_retained=settings.keep_recordings,
        mean_used_cpu_cores=sum(u['mean_cpu_cores_accounted']*d for u,d in zip(resource_reports,durations))/sum(durations),
        peak_used_cpu_cores_sampled=max(u['peak_cpu_cores_sampled'] for u in resource_reports),
        peak_ram_GiB=max(u['peak_process_tree_rss_GiB'] for u in resource_reports),
        gpu_rendering_used=not settings.graphics['software_rendering'])
    peaks=[g['peak_vram_used_MiB']/1024 for u in resource_reports for g in u['gpus'] if g['index'] in gpu_indices and g['peak_vram_used_MiB'] is not None]
    result['peak_device_vram_GiB']=max(peaks) if peaks else None
    utilization=[g for u in resource_reports for g in u['gpus'] if g['index'] in gpu_indices and g['mean_utilization_percent'] is not None]
    samples=sum(g['samples'] for g in utilization)
    result['mean_device_gpu_utilization_percent']=sum(g['mean_utilization_percent']*g['samples'] for g in utilization)/samples if samples else None
    (trial/'result.json').write_text(json.dumps(result,indent=2))
    return result

def adjusted_cap(results,hardware,requested,base,gpu_indices):
    cap=initial_worker_cap(hardware,requested,base)
    per_worker=max(r['max_worker_ram_MiB'] for r in results)*1024**2*1.3
    cap=min(cap,max(1,int(available_memory()*.75/per_worker)))
    for result in results:
        for usage in result['resources']:
            for device in usage['gpus']:
                if device['index'] not in gpu_indices:continue
                total=device['vram_total_MiB'];peak=device['peak_vram_used_MiB'];baseline=device['baseline_vram_used_MiB']
                if None in (total,peak,baseline):continue
                incremental=max(0,peak-baseline)/result['workers']
                if incremental>0:cap=min(cap,max(1,int((total*.85-baseline)/(incremental*1.25))))
    return cap

def write_report(output,report):
    report['elapsed_wall_s']=time.monotonic()-report['_started']
    public={k:v for k,v in report.items() if not k.startswith('_')}
    temporary=output/'report.tmp';temporary.write_text(json.dumps(public,indent=2));temporary.replace(output/'report.json')
    fields=('phase','workers','recording_fps','complete_episode_pipeline_per_hour','mean_used_cpu_cores',
            'peak_used_cpu_cores_sampled','peak_ram_GiB','peak_device_vram_GiB','mean_device_gpu_utilization_percent','gpu_rendering_used')
    with (output/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(report['results'])

def recommend(output,report,args):
    confirmed=[r for r in report['results'] if r['phase']=='confirm']
    pool=confirmed or [r for r in report['results'] if r['phase']=='probe']
    best=best_result(pool,args.tie_margin)
    if not best:
        (output/'summary.md').write_text(f"# Collection tuning result\n\nStatus: {report['status']}\n\nNo successful configuration measured.\n\n{report.get('error',report.get('stop_reason',''))}\n")
        return
    graphics=report['graphics']
    episode_limit=max(1,min(20,int(max(0,shutil.disk_usage(output).free-GIB)/(180*25*640*360*3))))
    command=[sys.executable,'-m','landing_training.collect','--review','PATH_TO_APPROVED_REVIEW',
             '--output','PATH_TO_DATASET','--workers',str(best['workers']),'--gl',graphics['backend'],
             '--instance-base',str(args.instance_base),'--max-episodes',str(episode_limit)]
    result={'workers':best['workers'],'backend':graphics['backend'],'gpu_rendering_used':best['gpu_rendering_used'],
            'recording_fps':best['recording_fps'],'complete_episode_pipeline_per_hour':best['complete_episode_pipeline_per_hour'],
            'mean_used_cpu_cores':best['mean_used_cpu_cores'],'peak_ram_GiB':best['peak_ram_GiB'],
            'peak_used_cpu_cores_sampled':best['peak_used_cpu_cores_sampled'],
            'peak_device_vram_GiB':best['peak_device_vram_GiB'],
            'mean_device_gpu_utilization_percent':best.get('mean_device_gpu_utilization_percent'),
            'projected_collection_hours':best['projected_collection_hours'],
            'basis':'full-flight comparison across measured finalists' if len(confirmed)>1 else 'one finalist confirmed on full flights' if confirmed else 'short probes only; full-flight confirmation unfinished',
            'scope':'best measured configuration within search/resource/time limits; not a proven global optimum',
            'collect_command':subprocess.list2cmdline(command) if WINDOWS else shlex.join(command),
            'production_collection_started':False}
    report['recommendation']=result;(output/'recommended_configuration.json').write_text(json.dumps(result,indent=2))
    lines=['# Collection tuning result','',f"Status: {report['status']}",f"Renderer: {graphics['renderer']}",
        f"GPU rendering: {result['gpu_rendering_used']}",f"Allocated CPU capacity: {report['hardware']['effective_cpu_capacity']:g} logical core equivalents",
        f"Recommended workers: {result['workers']}",f"Recorded FPS: {result['recording_fps']:.2f}",
        f"Mean CPU used: {result['mean_used_cpu_cores']:.2f} core equivalents",f"Peak process-tree RAM: {result['peak_ram_GiB']:.2f} GiB",
        f"Peak sampled CPU use: {result['peak_used_cpu_cores_sampled']:.2f} core equivalents",
        'Peak device VRAM: '+(f"{result['peak_device_vram_GiB']:.2f} GiB (device-wide, including other workloads)" if result['peak_device_vram_GiB'] is not None else 'unavailable'),
        'Mean GPU utilization: '+(f"{result['mean_device_gpu_utilization_percent']:.1f}% (device-wide)" if result['mean_device_gpu_utilization_percent'] is not None else 'unavailable'),
        f"Recommendation basis: {result['basis']}",'','See report.json and results.csv for all candidates, timings, utilization and limitations.',
        '',result['scope'],'','Production collection still requires a current user-approved review bundle.','',
        '```',result['collect_command'],'```']
    (output/'summary.md').write_text('\n'.join(lines)+'\n')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-counts',type=requested_worker_counts,help='Compare exactly these counts on full flights; skip adaptive search and short probes, e.g. 32,64')
    parser.add_argument('--max-workers',type=int,help='Search ceiling; default is detected CPU allocation, additionally limited by RAM/VRAM')
    parser.add_argument('--max-minutes',type=float,default=20,help='Total tuning budget, including setup/probes; active trials are cancelled at the limit')
    parser.add_argument('--quick-seconds',type=float,default=10)
    parser.add_argument('--probe-repeats',type=int,default=1)
    parser.add_argument('--finalists',type=int,default=2)
    parser.add_argument('--confirm-scenarios',type=int,default=3,help='Full-flight matrix prefix, 1..20; 20 covers all map/weather cases')
    parser.add_argument('--confirm-repeats',type=int,default=1)
    parser.add_argument('--episodes',type=int,default=1200)
    parser.add_argument('--tie-margin',type=float,default=.03,help='Prefer fewer workers when throughput is within this fractional margin')
    parser.add_argument('--instance-base',type=int,default=20)
    parser.add_argument('--gl',choices=('egl','glfw','osmesa'))
    parser.add_argument('--require-gpu',action='store_true',help='Fail before benchmarking if OpenGL is software rendering')
    parser.add_argument('--keep-recordings',action='store_true',help='Keep audited review RGB/JSONL; default discards only this run’s disposable raw data')
    parser.add_argument('--scan-only',action='store_true')
    parser.add_argument('--hourly-price',type=float,help='Optional listed compute rate for tuning-cost reporting')
    parser.add_argument('--budget',type=float,help='Optional compute budget in the same currency as hourly-price')
    parser.add_argument('--currency',default='USD')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if sys.platform not in ('linux','win32'):parser.error('Supported hosts: Linux/WSL and Windows with WSL PX4')
    if args.max_workers is not None and not 1<=args.max_workers<=128:parser.error('max-workers must be 1..128')
    if args.worker_counts and args.max_workers is not None and max(args.worker_counts)>args.max_workers:
        parser.error('worker-counts exceeds max-workers; omit max-workers or increase it')
    if not math.isfinite(args.max_minutes) or args.max_minutes<=0:parser.error('max-minutes must be positive and finite')
    if not 8<=args.quick_seconds<=30 or not 1<=args.confirm_scenarios<=20:parser.error('Invalid scenario duration or confirmation matrix size')
    if min(args.probe_repeats,args.confirm_repeats,args.finalists,args.episodes)<1:parser.error('Repeats, finalists and episodes must be positive')
    if not 0<=args.tie_margin<.25 or not 0<=args.instance_base<=252:parser.error('Invalid tie margin or instance base')
    if args.worker_counts and args.instance_base+max(args.worker_counts)>254:
        parser.error('Worker counts exceed the available PX4 instance range')
    for value in (args.hourly_price,args.budget):
        if value is not None and (not math.isfinite(value) or value<=0):parser.error('Prices and budgets must be positive and finite')
    if args.budget is not None and args.hourly_price is None:parser.error('budget requires hourly-price')
    def cancelled(signum,frame):raise KeyboardInterrupt('Tuning cancelled')
    signal.signal(signal.SIGTERM,cancelled)
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
    os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
    os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'build/benchmark_cache'))
    output=(args.output or ROOT/'outputs'/('autotune_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f'))).resolve()
    if output.exists():parser.error('Output directory already exists; choose a new one')
    output.mkdir(parents=True);started=time.monotonic()
    budget_s=args.max_minutes*60
    if args.budget is not None:budget_s=min(budget_s,args.budget/args.hourly_price*3600)
    deadline=started+budget_s
    from .collection_benchmark import hardware_info,benchmark_scenarios
    hardware=hardware_info();hardware.update(cpu_topology());devices,gpu_error=nvidia_snapshot()
    disk=shutil.disk_usage(output)
    hardware['output_filesystem']={'path':str(output),'free_GiB':disk.free/GIB,'total_GiB':disk.total/GIB}
    graphics,probes=probe_backends(args.gl)
    report={'schema':'aerodock.landing.autotune.v1','status':'scanned' if args.scan_only else 'running',
            'role':'review','training_eligible':False,'_started':started,'hardware':hardware,
            'gpu_inventory':devices,'gpu_inventory_note':gpu_error,'graphics':graphics,'backend_probes':probes,
            'budget_s':budget_s,'results':[],'stopped_trials':[],
            'search_mode':'fixed_full_flights' if args.worker_counts else 'adaptive',
            'settings':vars(args)|{'output':str(output)},
            'limitations':['Short probes deliberately abort and do not measure normal landing reliability.',
                'The search is bounded; untested worker counts/backends are not claimed optimal.',
                'Resource samples can miss brief peaks. Device-wide GPU counters include other workloads.',
                'Windows resource totals exclude PX4 inside WSL; unsupported GPU telemetry is null.',
                'Workers use the selected OpenGL device; multi-GPU load balancing is not implemented.',
                'Full-flight estimates extrapolate only the measured scenario prefix.',
                'Optional cost estimates exclude storage, bandwidth, minimum deposits and payment fees.']}
    write_report(output,report)
    print(f"CPU allocation: {hardware['effective_cpu_capacity']:g}; RAM: {hardware['ram_GiB']:.1f} GiB",flush=True)
    print('Renderer: '+(graphics['renderer'] if graphics else 'unavailable'),flush=True)
    if args.scan_only:return 0
    if graphics is None or (args.require_gpu and graphics['software_rendering']):
        report['status']='blocked';report['error']='No usable renderer' if graphics is None else 'GPU required but actual OpenGL renderer is software'
        write_report(output,report);print(report['error'],flush=True);return 1
    os.environ['MUJOCO_GL']=graphics['backend'];args.graphics=graphics
    args.ram_reserve_bytes=int(min(GIB,max(256*1024**2,hardware['ram_GiB']*GIB*.1)))
    ram_budget=available_memory()*.8;args.vram_fraction=.9
    selected=renderer_gpu_indices(graphics['renderer'],devices)
    report['uniquely_identified_nvidia_gpu_indices']=selected
    cap=max(args.worker_counts) if args.worker_counts else initial_worker_cap(hardware,args.max_workers,args.instance_base)
    report['initial_worker_cap']=cap;report['search_worker_cap']=cap
    def trial(count,phase):
        if time.monotonic()>=deadline:raise TrialStopped('tuning time budget reached')
        print(f'Testing {count} workers ({phase})',flush=True)
        result=run_trial(count,probe_cases if phase=='probe' else confirm_cases,
            args.probe_repeats if phase=='probe' else args.confirm_repeats,phase,output,args,deadline,ram_budget,selected)
        report['results'].append(result);write_report(output,report)
        print(f"  {result['recording_fps']:.2f} FPS; {result['complete_episode_pipeline_per_hour']:.1f} episodes/h; CPU {result['mean_used_cpu_cores']:.2f}; peak RAM {result['peak_ram_GiB']:.2f} GiB",flush=True)
        return result
    code=0
    try:
        check_px4()
        from .scene import compile_scene
        from .gate import source_fingerprint
        cache_started=time.monotonic()
        with cache_lock():model=compile_scene()
        del model;gc.collect();report['model_cache_prepare_s']=time.monotonic()-cache_started
        args.runtime_hash=source_fingerprint(runtime_only=True);report['runtime_source_sha256']=args.runtime_hash
        probe_cases=benchmark_scenarios('quick',args.quick_seconds) if not args.worker_counts else []
        confirm_cases=benchmark_scenarios('full')[:args.confirm_scenarios]
        report['probe_scenarios']=probe_cases;report['confirmation_scenarios']=confirm_cases
        if args.worker_counts:
            print('Fixed full-flight comparison: '+','.join(map(str,args.worker_counts)),flush=True)
            for count in args.worker_counts:
                try:trial(count,'confirm')
                except TrialStopped as exc:
                    report['stopped_trials'].append({'workers':count,'phase':'confirm','reason':str(exc)})
                    print(f'Stopped {count} workers: {exc}',flush=True)
                    if 'time budget' in str(exc):raise
        else:
            trial(1,'probe');growth=2;flat=0
            while growth<=cap:
                try:result=trial(growth,'probe')
                except TrialStopped as exc:
                    report['stopped_trials'].append({'workers':growth,'phase':'probe','reason':str(exc)})
                    if 'time budget' in str(exc):raise
                    cap=growth-1;break
                probes_done=[r for r in report['results'] if r['phase']=='probe']
                previous=max(r['complete_episode_pipeline_per_hour'] for r in probes_done[:-1])
                flat=flat+1 if result['complete_episode_pipeline_per_hour']<=previous*(1+args.tie_margin) else 0
                cap=min(cap,adjusted_cap(probes_done,hardware,args.max_workers,args.instance_base,selected))
                if flat>=2 or growth>=cap:break
                growth=min(cap,growth*2)
            while True:
                probes_done=[r for r in report['results'] if r['phase']=='probe']
                nearby=refinement_counts(probes_done,cap)
                if not nearby:break
                for count in nearby:
                    if count>cap:continue
                    try:trial(count,'probe')
                    except TrialStopped as exc:
                        report['stopped_trials'].append({'workers':count,'phase':'probe','reason':str(exc)})
                        if 'time budget' in str(exc):raise
                        cap=min(cap,count-1)
            report['search_worker_cap']=cap
            available=[r for r in report['results'] if r['phase']=='probe' and r['workers']<=cap]
            preferred=best_result(available,args.tie_margin)
            ranked=sorted(available,key=lambda r:r['complete_episode_pipeline_per_hour'],reverse=True)
            finalists=([preferred]+[r for r in ranked if r is not preferred])[:args.finalists] if preferred else []
            # Confirm lower counts first, so a larger failed trial leaves a validated fallback.
            for candidate in sorted(finalists,key=lambda r:r['workers']):
                try:trial(candidate['workers'],'confirm')
                except TrialStopped as exc:
                    report['stopped_trials'].append({'workers':candidate['workers'],'phase':'confirm','reason':str(exc)})
                    if 'time budget' in str(exc):raise
        report['status']='stopped' if args.worker_counts and report['stopped_trials'] else 'completed'
        if report['status']=='stopped':report['stop_reason']='Requested configurations hit resource limits; see stopped_trials'
    except TrialStopped as exc:report['status']='stopped';report['stop_reason']=str(exc)
    except KeyboardInterrupt:report['status']='cancelled';code=130
    except Exception as exc:report['status']='failed';report['error']=f'{type(exc).__name__}: {exc}';code=1
    finally:
        if args.hourly_price is not None:report['estimated_compute_cost']={'amount':(time.monotonic()-started)/3600*args.hourly_price,'currency':args.currency,'rate_per_hour':args.hourly_price}
        recommend(output,report,args);write_report(output,report)
    if report.get('recommendation'):
        r=report['recommendation']
        print(f"Best measured: {r['workers']} workers; {r['recording_fps']:.2f} FPS; mean CPU {r['mean_used_cpu_cores']:.2f} cores; RAM peak {r['peak_ram_GiB']:.2f} GiB; GPU rendering {r['gpu_rendering_used']}",flush=True)
        vram=f"{r['peak_device_vram_GiB']:.2f} GiB" if r['peak_device_vram_GiB'] is not None else 'unavailable'
        util=f"{r['mean_device_gpu_utilization_percent']:.1f}%" if r['mean_device_gpu_utilization_percent'] is not None else 'unavailable'
        print(f'Device-wide VRAM peak: {vram}; GPU utilization: {util}',flush=True)
    print(f'Report: {output / "summary.md"}\nDetails: {output / "report.json"}',flush=True)
    if report.get('error'):print(report['error'],flush=True)
    return code

if __name__=='__main__':raise SystemExit(main())
