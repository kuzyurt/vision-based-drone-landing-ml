"""Wait on file events, emitting only new measured results; no periodic polling."""
from pathlib import Path
import ctypes,json,os,select,sys,time
r=Path(__file__).resolve().parent
lib=ctypes.CDLL(None,use_errno=True)
fd=lib.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC);assert fd>=0
assert lib.inotify_add_watch(fd,os.fsencode(r),0x80|0x8)>=0
seen=set()
while True:
    p=r/'state.json'
    if p.exists():
        state=json.loads(p.read_text())
        for case in state['results']:
            label=case['case']['id']
            if label in seen:continue
            seen.add(label)
            print(json.dumps({k:case.get(k)for k in['status','landed','flight_seconds','actual_motion','radio_observation_audit','ml_phase','error']}|{'case':label,'completed':state['completed'],'planned':state['planned']}),flush=True)
        if state['status']!='running':
            print('FINAL_STATE '+state['status'],flush=True);break
    select.select([fd],[],[])
    try:os.read(fd,65536)
    except BlockingIOError:pass
os.close(fd)
