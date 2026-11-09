"""Retain started flights, cancel only the confounded queued plan, then launch revised tests."""
from pathlib import Path
import datetime,json,psutil,subprocess,sys
r=Path(__file__).resolve().parent;old=r.parent/'tidewater_speed_20261018T152500Z'
assert not(r/'state.json').exists()
try:p=psutil.Process(480645)
except psutil.NoSuchProcess:p=None
if p is not None:assert str(old/'run_suite.py')in p.cmdline()
nodes=[]if p is None else[c for c in p.children(recursive=True)if any(a.endswith('/test/tidewater_speed_suite_20261018.mjs')for a in c.cmdline())]
old_state=json.loads((old/'state.json').read_text())
if p is None:assert old_state['status']=='completed_requires_review_and_boundary_confirmation'
receipt=dict(status='completed_predecessor_retained_no_cases_repeated'if p is None else'queued_confounded_speed_cases_cancelled_started_flights_continue_unchanged',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),old_pid=480645,
    active_node_pids=[c.pid for c in nodes],old_state=json.loads((old/'state.json').read_text()),
    reason=json.loads((r/'plan.json').read_text())['reason'],original_plan_and_sources_preserved=True)
(r/'predecessor_retirement.json').write_text(json.dumps(receipt,indent=2)+'\n')
if p is not None:p.terminate();p.wait(timeout=5)
for c in psutil.process_iter(['pid','cmdline']):
    if str(old/'watch_completion.py')in(c.info['cmdline']or[]):c.terminate()
with(r/'coordinator.log').open('x')as log:
    child=subprocess.Popen([sys.executable,str(r/'run_suite_v2.py')],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(r/'launch_receipt.json').write_text(json.dumps(dict(pid=child.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),active_prior_flights=[c.pid for c in nodes]),indent=2)+'\n')
print(json.dumps(dict(pid=child.pid,prior_node_pids=[c.pid for c in nodes],started_flights_not_interrupted=True)))
