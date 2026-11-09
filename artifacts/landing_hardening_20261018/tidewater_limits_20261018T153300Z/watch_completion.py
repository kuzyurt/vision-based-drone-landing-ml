from pathlib import Path
import ctypes,json,os,select
r=Path(__file__).resolve().parent
lib=ctypes.CDLL(None,use_errno=True);fd=lib.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC);assert fd>=0
assert lib.inotify_add_watch(fd,os.fsencode(r),0x80|0x8)>=0
seen=set();pid=json.loads((r/'launch_receipt.json').read_text())['pid']
try:proc=os.pidfd_open(pid)
except ProcessLookupError:proc=None
while True:
    state=json.loads((r/'state.json').read_text())
    for x in state['results']:
        label=x['case']['id']
        if x.get('predecessor_case')or label in seen:continue
        seen.add(label)
        print(json.dumps(dict(case=label,status=x['status'],landed=x.get('landed'),seconds=x.get('flight_seconds'),
            final_boat_speed=x.get('actual_motion',{}).get('final_2s_speed_m_s'),
            requested_speed_demonstrated=x.get('requested_speed_demonstrated'),phase=x.get('ml_phase'),error=x.get('error'))),flush=True)
    if state['status']!='running':print('FINAL '+state['status'],flush=True);break
    ready,_,_=select.select([fd]+([proc]if proc is not None else[]),[],[])
    if proc is not None and proc in ready:
        print('COORDINATOR_EXITED; read final state and log',flush=True);break
    try:os.read(fd,65536)
    except BlockingIOError:pass
os.close(fd)
if proc is not None:os.close(proc)
