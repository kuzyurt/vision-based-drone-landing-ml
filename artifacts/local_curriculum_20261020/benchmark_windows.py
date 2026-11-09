"""15-second cohorts with actual memory guards; no fake results for rejected counts."""
import argparse,datetime,json,os,subprocess,sys,time
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parent
GiB=1024**3

def main():
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=15);a=p.parse_args();assert 10<=a.seconds<=20
    out=ROOT/'worker_benchmark_v1';out.mkdir(exist_ok=False);results=[];profile=None
    def gpu_free():return int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])*1024**2
    def state(status):
        (out/'state.json').write_text(json.dumps(dict(status=status,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Windows MuJoCo physics + onboard RGB + exact segmentation + SHA + compression/write metadata. No NN inference or PX4: this is not native flight throughput.',requested=[8,12,16,24],reserve_ram_bytes=2*GiB,reserve_vram_bytes=GiB,results=results),indent=2))
    def cohort(n,label):
        nonlocal profile
        available=psutil.virtual_memory().available;freegpu=gpu_free()
        ram_each=profile['ram_each'] if profile else 1.1*GiB;gpu_each=profile['gpu_each'] if profile else .5*GiB
        entry=dict(workers=n,label=label,ram_available_before=available,gpu_free_before=freegpu,estimated_worker_ram=ram_each,estimated_worker_vram=gpu_each)
        if available<2*GiB+n*ram_each or freegpu<GiB+n*gpu_each:
            entry.update(status='not_started_resource_guard',frames=None,fps=None,reason='Requested full cohort cannot preserve measured RAM/VRAM reserve; no smaller cohort is labelled as this count.');results.append(entry);state('checking');return
        folder=out/label;folder.mkdir();active=[];started=time.monotonic();peak_rss=0;min_available=available;min_gpu=freegpu;reason=None
        try:
            for i in range(n):
                if psutil.virtual_memory().available<2*GiB+ram_each:reason='RAM reserve prevented next worker startup';break
                log=(folder/f'{i}.log').open('x')
                child=subprocess.Popen([sys.executable,'-u',str(ROOT/'benchmark_worker.py'),'--out',str(folder),'--index',str(i)],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                active.append((child,log))
                deadline=time.monotonic()+120
                while not(folder/f'{i}_ready.json').exists():
                    if child.poll()is not None:reason='Worker failed setup; inspect preserved log';break
                    if psutil.virtual_memory().available<2*GiB or gpu_free()<GiB:reason='Measured reserve reached during startup';break
                    if time.monotonic()>deadline:reason='Worker startup exceeded120s';break
                    time.sleep(.2)
                if reason:break
            if not reason:
                ready=[json.loads((folder/f'{i}_ready.json').read_text()) for i in range(n)]
                ram_used=max(x['rss'] for x in ready);free_started=gpu_free()
                if n==1:profile=dict(ram_each=max(.5*GiB,ram_used*1.15),gpu_each=max(.12*GiB,(freegpu-free_started)*1.15))
                (folder/'GO.json').write_text(json.dumps(dict(finish_unix=time.time()+a.seconds)))
                while any(c.poll()is None for c,_ in active):
                    mem=psutil.virtual_memory().available;min_available=min(min_available,mem)
                    gf=gpu_free();min_gpu=min(min_gpu,gf)
                    if mem<2*GiB or gf<GiB:reason='Measured resource reserve reached during timed phase';break
                    if time.monotonic()-started>n*120+a.seconds+30:reason='Wall watchdog';break
                    time.sleep(.2)
            if reason:(folder/'STOP').write_text(reason)
            for child,_ in active:
                try:child.wait(timeout=8)
                except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=8)
            rows=[json.loads(p.read_text()) for p in folder.glob('*_result.json')]
            valid=not reason and len(rows)==n and all(c.returncode==0 for c,_ in active)
            entry.update(status='completed' if valid else 'failed_or_resource_stopped',reason=reason,actual_started_workers=len(active),completed_worker_reports=len(rows),measurement_s=a.seconds,startup_included_in_fps=False,total_wall_s=time.monotonic()-started,frames=sum(x['frames'] for x in rows) if valid else None,fps=sum(x['frames'] for x in rows)/a.seconds if valid else None,minimum_ram_available=min_available,minimum_vram_available=min_gpu,rows=rows)
        finally:
            for child,log in active:
                if child.poll()is None:child.terminate();child.wait(timeout=8)
                log.close()
        results.append(entry);state('checking');time.sleep(1)
    state('starting')
    cohort(1,'profile_1')
    if profile:
        for n in [8,12,16,24]:cohort(n,f'requested_{n}')
        # Establish a usable smaller baseline only if requested cohorts cannot fit.
        if not any(x['status']=='completed' and x['workers']>=8 for x in results):
            for n in [2,4]:cohort(n,f'fallback_{n}')
    else:
        for n in [8,12,16,24]:
            results.append(dict(workers=n,status='not_started_no_safe_profile',fps=None,reason='Single-worker actual scene did not complete within resource/setup gates.'))
    valid=[x for x in results if x['status']=='completed'];best=max(valid,key=lambda x:x['fps']) if valid else None
    state('completed' if best else 'blocked');report=json.loads((out/'state.json').read_text());report['best_measured_workers']=best['workers'] if best else None;report['best_measured_fps']=best['fps'] if best else None;report['profile']=profile;(out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
