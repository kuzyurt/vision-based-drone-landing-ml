"""Sample this benchmark's process tree and device-wide NVIDIA telemetry."""
import csv
import io
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

import psutil

GIB=1024**3

def number(value):
    try:return float(value)
    except (ValueError,TypeError):return None

def nvidia_snapshot():
    """Return unknown counters as null, rather than implying zero utilization."""
    executable=shutil.which('nvidia-smi')
    if not executable:return [],'nvidia-smi unavailable; AMD/Intel GPUs can still render'
    fields=('index','uuid','name','memory.total','memory.used','memory.free',
            'utilization.gpu','utilization.memory','driver_version')
    try:
        result=subprocess.run([executable,'--query-gpu='+','.join(fields),
                               '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3)
        if result.returncode:return [],result.stderr.strip() or 'nvidia-smi query failed'
        devices=[]
        for row in csv.reader(io.StringIO(result.stdout)):
            if len(row)!=len(fields):continue
            row=[value.strip() for value in row]
            devices.append({'index':int(row[0]),'uuid':row[1],'name':row[2],
                'vram_total_MiB':number(row[3]),'vram_used_MiB':number(row[4]),
                'vram_free_MiB':number(row[5]),'gpu_utilization_percent':number(row[6]),
                'memory_utilization_percent':number(row[7]),'driver_version':row[8]})
        return devices,None
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:return [],str(exc)

def available_memory():
    available=psutil.virtual_memory().available
    try:
        limit=int(Path('/sys/fs/cgroup/memory.max').read_text())
        current=int(Path('/sys/fs/cgroup/memory.current').read_text())
        stats=dict(line.split() for line in Path('/sys/fs/cgroup/memory.stat').read_text().splitlines())
        available=min(available,max(0,limit-current+int(stats.get('inactive_file',0))))
    except (OSError,ValueError):
        try:
            limit=int(Path('/sys/fs/cgroup/memory/memory.limit_in_bytes').read_text())
            current=int(Path('/sys/fs/cgroup/memory/memory.usage_in_bytes').read_text())
            available=min(available,max(0,limit-current))
        except (OSError,ValueError):pass
    return available

def cpu_topology():
    process=psutil.Process()
    try:affinity=process.cpu_affinity()
    except (AttributeError,psutil.Error):affinity=list(range(psutil.cpu_count() or 1))
    cores=set()
    for cpu in affinity:
        folder=Path('/sys/devices/system/cpu')/f'cpu{cpu}'/'topology'
        try:cores.add((int((folder/'physical_package_id').read_text()),int((folder/'core_id').read_text())))
        except (OSError,ValueError):pass
    return {'host_physical_cores':psutil.cpu_count(logical=False),
            'host_logical_cpus':psutil.cpu_count(), 'allowed_logical_cpu_ids':affinity,
            'physical_cores_in_affinity':len(cores) if cores else None,'psutil_version':psutil.__version__}

def renderer_gpu_indices(renderer,devices):
    def normalized(value):return ''.join(c for c in value.lower() if c.isalnum())
    name=normalized(renderer)
    matches=[d['index'] for d in devices if normalized(d['name']) in name]
    # Identical GPU names do not identify which physical device EGL selected.
    return matches if len(matches)==1 else []

class ResourceMonitor:
    def __init__(self,cancel_event,*,ram_budget_bytes,reserve_bytes,deadline,
                 gpu_indices=(),vram_fraction=.9,interval=.5):
        self.cancel=cancel_event;self.ram_budget=ram_budget_bytes;self.reserve=reserve_bytes
        self.deadline=deadline;self.gpu_indices=set(gpu_indices);self.vram_fraction=vram_fraction
        self.interval=interval;self.stop=threading.Event();self.thread=None;self.reason=None
        self.root=psutil.Process();self.samples=0;self.peak_rss=0;self.minimum_available=None
        self.cpu_seconds=0.;self.peak_cpu_cores=0.;self.last_cpu={};self.gpus={};self.errors=[]
        self.observed_cpu_ids=set();self.started=None;self.ended=None

    def reject(self,reason):
        if self.reason is None:self.reason=reason;self.cancel.set()

    def sample(self,elapsed,include_gpu=False):
        processes=[self.root]
        try:processes+=self.root.children(recursive=True)
        except psutil.Error:pass
        rss=0;delta=0.
        for process in processes:
            try:
                with process.oneshot():
                    key=(process.pid,process.create_time());times=process.cpu_times()
                    cpu=times.user+times.system;rss+=process.memory_info().rss
                    if hasattr(process,'cpu_num'):self.observed_cpu_ids.add(process.cpu_num())
                previous=self.last_cpu.get(key,cpu if process.pid==self.root.pid else 0.)
                delta+=max(0,cpu-previous);self.last_cpu[key]=cpu
            except psutil.Error:continue
        self.cpu_seconds+=delta
        if elapsed>0:self.peak_cpu_cores=max(self.peak_cpu_cores,delta/elapsed)
        self.peak_rss=max(self.peak_rss,rss);self.samples+=1
        free=available_memory()
        self.minimum_available=free if self.minimum_available is None else min(self.minimum_available,free)
        if rss>self.ram_budget:self.reject('process-tree RAM budget exceeded')
        if free<self.reserve:self.reject('available RAM fell below reserved headroom')
        if time.monotonic()>=self.deadline:self.reject('tuning time budget reached')
        if include_gpu:
            devices,error=nvidia_snapshot()
            if error and error not in self.errors:self.errors.append(error)
            for device in devices:
                stats=self.gpus.setdefault(device['index'],{'name':device['name'],'uuid':device['uuid'],
                    'vram_total_MiB':device['vram_total_MiB'],'baseline_vram_used_MiB':device['vram_used_MiB'],
                    'peak_vram_used_MiB':None,'utilization_sum':0.,'utilization_samples':0,'peak_utilization_percent':None})
                used=device['vram_used_MiB'];util=device['gpu_utilization_percent']
                if used is not None:stats['peak_vram_used_MiB']=max(stats['peak_vram_used_MiB'] or 0,used)
                if util is not None:
                    stats['utilization_sum']+=util;stats['utilization_samples']+=1
                    stats['peak_utilization_percent']=max(stats['peak_utilization_percent'] or 0,util)
                total=device['vram_total_MiB']
                if device['index'] in self.gpu_indices and used is not None and total and used>total*self.vram_fraction:
                    self.reject('selected GPU VRAM headroom exhausted (device-wide measurement)')

    def loop(self):
        previous=time.monotonic();next_gpu=previous+2
        while not self.stop.wait(self.interval):
            now=time.monotonic()
            try:self.sample(now-previous,include_gpu=now>=next_gpu)
            except Exception as exc:
                self.errors.append(str(exc));self.reject('resource monitoring failed');break
            previous=now
            if now>=next_gpu:next_gpu=now+2

    def __enter__(self):
        self.started=time.monotonic();self.sample(0,include_gpu=True)
        self.cpu_seconds=0.;self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
        return self

    def __exit__(self,*args):
        self.stop.set();self.thread.join(timeout=5);self.ended=time.monotonic()

    def report(self):
        duration=(self.ended or time.monotonic())-self.started
        gpu=[]
        for index,stats in self.gpus.items():
            item=dict(stats);count=item.pop('utilization_samples');total=item.pop('utilization_sum')
            item.update(index=index,mean_utilization_percent=total/count if count else None,samples=count)
            gpu.append(item)
        return {'samples':self.samples,'sample_interval_s':self.interval,
                'mean_cpu_cores_sampled':self.cpu_seconds/duration if duration else None,
                'peak_cpu_cores_sampled':self.peak_cpu_cores,'observed_main_thread_cpu_ids':sorted(self.observed_cpu_ids),
                'peak_process_tree_rss_GiB':self.peak_rss/GIB,
                'minimum_available_ram_GiB':self.minimum_available/GIB if self.minimum_available is not None else None,
                'gpus':gpu,'stop_reason':self.reason,'errors':self.errors,
                'scope':'RAM is summed process-tree RSS (shared pages can be counted twice). CPU peaks are sampled logical core equivalents. GPU/VRAM counters are device-wide and include other workloads. Windows excludes Linux PX4 processes inside WSL.'}
