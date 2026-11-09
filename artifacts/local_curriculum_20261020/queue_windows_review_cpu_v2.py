"""One-per-purpose review batch, no bulk data or training; own processes only."""
from pathlib import Path
import ctypes,datetime,hashlib,json,os,subprocess,sys,time
import psutil
import local_paths
from audit_windows_review import audit
from review_gallery_cpu_v2 import update as gallery
R=local_paths.ROOT;B=R/'review_batch_v1'

def main():
    old=json.loads((B/'state.json').read_text());assert old['status']=='waiting_safe_resources' and not old['active']
    assert not(B/'cpu_continuation_launch_v2.json').exists(),'Existing review batch must be inspected, not duplicated'
    probe=json.loads((B/'platform_annotation_probe_v2/actual_audit.json').read_text());assert probe['status']=='probe_passed'and probe['technical_contract_passed']
    assert json.loads((R/'px4_takeoff_probe_v2/result_recovered_v1.json').read_text())['status']=='passed_closed_trace_recovered_receipt'
    assert json.loads((R/'windows_physics_math_test.json').read_text())['status']=='passed'
    plan=json.loads((B/'cpu_continuation_plan_v2.json').read_text());critical=['run_windows_review_cpu_v3.py','review_helpers.py','windows_px4_v2.py','px4_windows_bridge_v2.mjs','windows_renderer.py','windows_kernels.py','fast_physics_windows.py','local_paths.py','audit_windows_review.py']
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();binding={n:sha(R/n)for n in critical}
    (B/'cpu_continuation_binding_v2.json').write_text(json.dumps(dict(frozen_before_first_batch_flight=True,sources=binding,runtime_probe_sha256=sha(R/'runtime_probe_windows_v1.json'),model_index_sha256=sha(R/'models/index.json'),plan_sha256=sha(B/'cpu_continuation_plan_v2.json')),indent=2))
    (B/'cpu_continuation_launch_v2.json').write_text(json.dumps(dict(pid=os.getpid(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),mode='one actual expert flight at a time; model/PX4 RAM exceeds render-only worker footprint',maximum_actual_review_workers=1)))
    pending=list(plan['jobs']);completed=[];active=None;started=time.monotonic();watchdog=3600;waiting_since=None
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    def save(status,error=None):
        s=dict(status=status,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),coordinator_pid=os.getpid(),active=[dict(name=active['job']['name'],pid=active['process'].pid)]if active else[],remaining=[j['name']for j in pending],completed=completed,wall_s=time.monotonic()-started,error=error,training_or_bulk_started=False)
        q=B/'state.tmp';q.write_text(json.dumps(s,indent=2));q.replace(B/'state.json');gallery(s)
    try:
        save('starting')
        while pending or active:
            if active:
                p=active['process'];elapsed=time.monotonic()-active['start']
                if p.poll()is None:
                    if elapsed>watchdog:raise TimeoutError('Actual case wall watchdog: '+active['job']['name'])
                else:
                    active['log'].close();name=active['job']['name'];case=B/name;result_path=case/'preview_result.json';result=json.loads(result_path.read_text())if result_path.exists()else None;error_path=case/'error.json';error=json.loads(error_path.read_text())if error_path.exists()else None;review=None
                    if (case/'closed.json').exists()and result is not None:
                        review=audit(case)
                    entry=dict(name=name,exit_code=p.returncode,result=result,audit=review,error=error,video_ready=(case/'review.receipt.json').exists())
                    completed.append(entry);active=None;save('running')
                    if review and not review['technical_contract_passed']:raise RuntimeError('Actual RGB/source/history/input contract failure: '+name)
                    if p.returncode!=0:raise RuntimeError('Review runtime/setup failed; preserve failure before next launch: '+name)
                    if name=='E04_close_loss' and review and review['actual_fault_rows']>0:
                        import h5py
                        with h5py.File(case/'observations.h5','r')as h:
                            indices=[i for i,x in enumerate(h['steps'])if json.loads(x)['output']['learner_diagnostics'].get('actual_command_owner')=='evaluation_fault']
                        begin=max(0,indices[0]/25-4);duration=min(result['frames']/25,indices[-1]/25+12)-begin
                        subprocess.run(['ffmpeg','-n','-loglevel','error','-ss',str(begin),'-i',str(case/'review.mp4'),'-t',str(duration),'-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','22','-movflags','+faststart',str(B/'E04a_detail.mp4')],check=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
                        (B/'E04a_detail_receipt.json').write_text(json.dumps(dict(same_actual_E04_flight=True,source_video_sha256=sha(case/'review.mp4'),start_task_s=begin,duration_s=duration,actual_fault_rows=indices,sha256=sha(B/'E04a_detail.mp4')),indent=2))
            if not active and pending:
                available=psutil.virtual_memory().available;gpu_free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])
                # CPU probe saved0.78GiB host RAM vs CUDA; retain1.5GiB live stop.
                # No concurrency increase or physics/control changes.
                if available<3.8*1024**3 or gpu_free<1800:
                    waiting_since=waiting_since or time.monotonic();save('waiting_safe_resources')
                    if time.monotonic()-waiting_since>43200:raise MemoryError('No safe3.8GiB free RAM /1.8GiB VRAM admission window for12hours')
                else:
                    waiting_since=None;job=pending.pop(0)
                    for n,d in binding.items():assert sha(R/n)==d,'Evaluated source changed: '+n
                    assert sha(job['job'])==job['sha256']
                    log=(B/(job['name']+'.log')).open('x');p=subprocess.Popen([sys.executable,'-u',str(R/'run_windows_review_cpu_v3.py'),'--job',job['job']],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                    active=dict(job=job,process=p,log=log,start=time.monotonic());save('actual_review_flights_running')
            if active or pending:time.sleep(10)
        save('all_review_cases_closed_needs_human_video_review')
    except BaseException as e:
        save('stopped_preserved_failure',repr(e));raise
    finally:
        if active:
            p=active['process']
            if p.poll()is None:
                # Only this case's process tree, never another application.
                try:
                    children=psutil.Process(p.pid).children(recursive=True)
                    for c in children:c.terminate()
                except psutil.NoSuchProcess:pass
                p.terminate();p.wait(timeout=10)
            active['log'].close()
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

if __name__=='__main__':main()
