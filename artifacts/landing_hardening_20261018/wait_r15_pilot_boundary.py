from pathlib import Path
import ctypes,json,os,select,time
r=Path(__file__).resolve().parent
try:fd=os.pidfd_open(443763)
except ProcessLookupError:fd=None
if fd is not None:
    ready,_,_=select.select([fd],[],[],900);os.close(fd)
    if not ready:print(json.dumps({'pilot_still_running':True}));raise SystemExit(0)
libc=ctypes.CDLL(None,use_errno=True);libc.inotify_add_watch.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
event=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC);assert event>=0
assert libc.inotify_add_watch(event,os.fsencode(r),0x100|0x80|0x8)>=0
deadline=time.monotonic()+120
while True:
    state=json.loads((r/'resumed_r15_state.json').read_text())
    if state['status']!='waiting_for_owned_pilot' or time.monotonic()>=deadline:break
    ready,_,_=select.select([event],[],[],max(0.,deadline-time.monotonic()))
    if ready:
        try:
            while os.read(event,65536):pass
        except BlockingIOError:pass
os.close(event)
print('native_state',json.dumps(state))
q=json.loads((r/'r15_pilot5/report.json').read_text());print('pilot',json.dumps({'status':q['status'],'outcomes':q['outcomes'],'results':[{'name':x['name'],'outcome':x['outcome'],'seconds':x['task_seconds']}for x in q['results']]}))
print('game_gate',(r/'r15_browser_gate_state.json').read_text())
