"""Event-triggered short 4/8/12-worker throughput; no bulk/training/promotion."""
from pathlib import Path
import hashlib,json,os,select,signal,subprocess,sys,time
import h5py,numpy as np
from collection_pipeline.capture_annotations import load_capture_index,join_delivered_frame
ROOT=Path(__file__).resolve().parent
def save(**v):
    v.update(pid=os.getpid(),bulk_collection=False,training_eligible=False)
    p=ROOT/'native_throughput_v22_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2));tmp.replace(p)
def wait_exit(pid,cap):
    try:fd=os.pidfd_open(pid)
    except ProcessLookupError:return
    try:
        if not select.select([fd],[],[],cap)[0]:raise TimeoutError('Upstream process exit wait')
    finally:os.close(fd)
def memory_available():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):return int(line.split()[1])/1024
    raise RuntimeError('No verified available-memory reading')
def gpu_memory():
    v=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],text=True)
    used,total=map(float,v.strip().split(','));return used,total
def worker_peak(pid):
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmHWM:'):return int(line.split()[1])/1024
    except FileNotFoundError:pass
    return 0.
def main():
    assert not(ROOT/'native_throughput_v22_state.json').exists()
    save(status='waiting_on_v22_exit_events')
    wait_exit(json.loads((ROOT/'expert_v22_launch.json').read_text())['pid'],1800)
    state=json.loads((ROOT/'expert_v22_pipeline_state.json').read_text())
    if state['status']!='completed' or any(r['result']['outcome']!='landed'for r in state.get('results',[])):
        save(status='not_run_upstream_recovery_not_passed',upstream=state);return
    wait_exit(json.loads((ROOT/'v22_completion_audit_launch.json').read_text())['pid'],180)
    audit=json.loads((ROOT/'v22_tilt_actual_ownership_audit.json').read_text())
    if audit['actual_history_mismatches']or audit['teacher_unsupported_descent_frames']:
        save(status='not_run_upstream_actual_command_audit_failed');return
    # Throughput readiness is not teacher/data eligibility or model promotion.
    snapshot=ROOT/'expert_source_snapshot_v22';script=snapshot/'run_annotated_development_v22.py'
    rates=[];skipped=[]
    for workers in [4,8,12]:
        if rates:
            per_worker=max(r['peak_worker_rss_mib']for r in rates)
            per_gpu=max(r['peak_gpu_used_mib']/r['workers']for r in rates)
            _,gpu_total=gpu_memory()
            if per_worker*workers>memory_available()-4096 or per_gpu*workers>gpu_total-1536:
                skipped.append(dict(workers=workers,reason='measured worker RSS/VRAM leaves insufficient reserve',
                    peak_worker_rss_mib=per_worker,estimated_worker_gpu_mib=per_gpu));continue
        group=ROOT/f'native_bench_v22_{workers}w';group.mkdir(exist_ok=False)
        active=[];all_tasks=[];start=time.monotonic();peak_rss=0.;peak_gpu=0.;minimum_available=memory_available()
        save(status='running_short_native_cohort',workers=workers,completed=rates,skipped=skipped)
        try:
            for i in range(workers):
                name=f'native_bench_v22_{workers}w/job_{i:02d}';log=(group/f'worker_{i:02d}.log').open('x')
                process=subprocess.Popen([sys.executable,str(script),'--name',name,'--mode','dagger','--scene','hard',
                    '--distance','8','--instance',str(110+i),'--duration','120','--annotation-probe-seconds','2'],
                    cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                    env={**os.environ,'TARGET_EXPERIMENT_ROOT':str(ROOT),'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only',
                         'EXPERT_RUNTIME_GATE':'expert_runtime_probe_v22_r15.json','PYTHONDONTWRITEBYTECODE':'1'})
                task=dict(p=process,name=name,log=log);active.append(task);all_tasks.append(task)
            while active:
                available=memory_available();used,total=gpu_memory()
                minimum_available=min(minimum_available,available);peak_gpu=max(peak_gpu,used)
                peak_rss=max(peak_rss,max([worker_peak(t['p'].pid)for t in active]+[0.]))
                if available<4096 or total-used<1024:raise RuntimeError('Measured RAM/VRAM reserve guard reached')
                if time.monotonic()-start>600:raise TimeoutError('Short native benchmark cohort wall cap')
                for task in active[:]:
                    if task['p'].poll()is None:continue
                    task['log'].close()
                    if task['p'].returncode:raise RuntimeError(task['name']+' failed; inspect preserved log')
                    active.remove(task)
                if active:time.sleep(4)
            frames=0;starts=[];ends=[];unique=0;captured=0
            for task in all_tasks:
                ep=ROOT/task['name'];summary=json.loads((ep/'summary.json').read_text());perf=summary['performance']
                index=load_capture_index(ep/'capture_annotations.jsonl')
                assert len(index)>=45 and not json.loads((ep/'capture_annotation_receipt.json').read_text())['unbound_capture']
                delivered=[]
                with h5py.File(ep/'observations.h5','r')as h:
                    for line in(ep/'steps.jsonl').open():
                        row=json.loads(line);label=join_delivered_frame(row['observation'],np.asarray(h['rgb'][row['frame_index']]),index)
                        if label:delivered.append(label['capture_uid'])
                frames+=len(delivered);unique+=len(set(delivered));captured+=len(index)
                starts.append(perf['record_start']);ends.append(perf['record_end'])
            row=dict(workers=workers,wall_s=time.monotonic()-start,annotated_captures=captured,delivered_images=frames,
                unique_captures=unique,images_per_wall_s=unique/(time.monotonic()-start),
                images_per_active_recording_s=unique/(max(ends)-min(starts)),active_recording_window_s=max(ends)-min(starts),
                peak_worker_rss_mib=peak_rss,peak_gpu_used_mib=peak_gpu,minimum_available_ram_mib=minimum_available)
            rates.append(row);(group/'throughput.json').write_text(json.dumps(row,indent=2))
        finally:
            for task in active:
                if task['p'].poll()is None:task['p'].send_signal(signal.SIGINT)
            for task in active:
                if task['p'].poll()is None:
                    try:task['p'].wait(timeout=15)
                    except subprocess.TimeoutExpired:task['p'].terminate()
                task['log'].close()
            # Native PX4 starts its own session; clean only exact runtime paths
            # belonging to this cohort if graceful Python cleanup was interrupted.
            owned_paths={str(ROOT/t['name']/'px4')for t in all_tasks}
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():continue
                try:
                    if entry.stat().st_uid!=os.getuid():continue
                    args=(entry/'cmdline').read_bytes().decode().split('\0')
                    if args and Path(args[0]).name=='px4'and any(path in args for path in owned_paths):os.kill(int(entry.name),signal.SIGTERM)
                except(FileNotFoundError,ProcessLookupError,PermissionError):pass
    assert rates
    chosen=max(rates,key=lambda r:r['images_per_active_recording_s'])
    result=dict(status='completed',cohorts=rates,skipped=skipped,selected_workers=chosen['workers'],
        criterion='Exact annotated native workload useful captures per active recording wall second; startup also reported',
        scope='2s task cohorts with physical PX4 preparation; development only, not new curriculum eligibility')
    (ROOT/'native_throughput_v22.json').write_text(json.dumps(result,indent=2));save(**result)
if __name__=='__main__':
    try:main()
    except BaseException as error:save(status='failed',error=repr(error));raise
