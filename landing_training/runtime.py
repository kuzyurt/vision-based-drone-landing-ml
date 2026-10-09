"""Portable host utilities; Windows rendering uses an owned PX4 process in WSL."""
import contextlib
import ctypes
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
WINDOWS=sys.platform=='win32'

def wsl(*args,**kwargs):
    return subprocess.check_output(['wsl','-d',os.environ.get('PX4_WSL_DISTRO','Ubuntu-22.04'),'--',*map(str,args)],text=True,**kwargs).strip()

def wsl_path(path):return wsl('wslpath','-u',Path(path).resolve().as_posix())

def px4_binary():
    vendor=ROOT/'.vendor/PX4-Autopilot'
    if WINDOWS:
        vendor=os.environ.get('LANDING_PX4_WSL_ROOT') or wsl_path(vendor)
        return vendor+'/build/px4_sitl_landing/bin/px4'
    return str(vendor/'build/px4_sitl_landing/bin/px4')

def check_px4():
    binary=px4_binary()
    if WINDOWS:wsl('test','-x',binary)
    elif not Path(binary).is_file():raise FileNotFoundError('Build pinned PX4 using landing_training.setup_px4 in Linux/WSL first')
    return binary

def windows_host():
    # Under WSL NAT, Linux's default gateway is the Windows host.
    address=wsl('sh','-c',"ip -4 route show default | awk 'NR==1 {print $3}'")
    socket.inet_aton(address)
    return address

@contextlib.contextmanager
def cache_lock(name='collection.cache.lock',path=None):
    ROOT.joinpath('build').mkdir(exist_ok=True)
    with (Path(path) if path else ROOT/'build'/name).open('a+b') as stream:
        if WINDOWS:
            import msvcrt
            if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
            stream.seek(0)
            # LK_LOCK retries only ten times; explicitly wait for slow compilation.
            import time
            while True:
                try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1);break
                except OSError:time.sleep(.1)
            try:yield
            finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX)
            try:yield
            finally:fcntl.flock(stream,fcntl.LOCK_UN)

def process_usage():
    if not WINDOWS:
        import resource
        own=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
        return {'max_rss_MiB':own.ru_maxrss/1024,'cpu_seconds':own.ru_utime+own.ru_stime+children.ru_utime+children.ru_stime,'cpu_scope':'worker and exited PX4 children'}
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):raise ctypes.WinError(ctypes.get_last_error())
    t=os.times()
    return {'max_rss_MiB':counters.PeakWorkingSetSize/1024**2,'cpu_seconds':t.user+t.system,'cpu_scope':'Windows worker only; WSL PX4 excluded'}

def windows_memory():
    from ctypes import wintypes
    class Memory(ctypes.Structure):
        _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD)]+[(n,ctypes.c_ulonglong) for n in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
    memory=Memory();memory.length=ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):raise ctypes.WinError()
    return memory.total,memory.available
