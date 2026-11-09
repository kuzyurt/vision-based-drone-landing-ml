"""Wait outside the chat token loop for resource availability, then one flight."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;state=ROOT/'tidewater_flight_state.json'
def save(value):
 p=state.with_suffix('.tmp');p.write_text(json.dumps(value,indent=2)+'\n');p.replace(state)
assert not state.exists();save(dict(status='queued',reason='Wait for native8-worker development cohort; no duplicate compute'))
deadline=time.monotonic()+3600
while True:
 p=ROOT/'r4_extended8_development/report.json';report=json.loads(p.read_text()) if p.exists() else {}
 if report.get('status')=='completed':break
 if time.monotonic()>deadline:save(dict(status='not_launched',reason='Native pilot not finished within resource queue bound'));sys.exit(0)
 time.sleep(30)
if report.get('outcomes',{}).get('landed',0)<3:
 save(dict(status='not_launched',reason='Development candidate not sufficiently promising for a graphics-domain flight',development_outcomes=report.get('outcomes')));sys.exit(0)
r=ROOT/'tidewater_runtime';a=json.loads((r/'adapter_verified.json').read_text());assert a['exit_code']==0
log=(ROOT/'tidewater_stationary_r4.log').open('xb')
env=dict(os.environ,TIDEWATER_GPU_BACKEND='vulkan',XDG_RUNTIME_DIR='/tmp',POLICY_PYTHON=sys.executable,POLICY_BUNDLE='candidate_r4')
command=[a['loader'],'--library-path',a['library_path'],str(r/'node-v22.23.2-linux-x64/bin/node'),str(r/'app/test/tidewater_landing_probe.mjs')]
p=subprocess.Popen(command,cwd=r/'app',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
save(dict(status='running',pid=p.pid,started=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='One actual Tidewater scene/physics flight, native frozen policy; no browser or video'))
try:code=p.wait(timeout=1200)
except subprocess.TimeoutExpired:p.terminate();code=p.wait(timeout=20)
save(dict(status='completed' if code==0 else 'failed',exit_code=code,report=str(ROOT/'tidewater_stationary_r4/report.json'),scope='Domain development, not qualification or browser ONNX parity'))
