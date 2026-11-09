from pathlib import Path
import datetime,hashlib,json,os,psutil,subprocess,sys
r=Path(__file__).resolve().parent
assert not(r/'state.json').exists()
for p in psutil.process_iter(['pid','cmdline']):
    assert not any(str(r/'run_suite.py')==v for v in(p.info['cmdline']or[])),p.info
with(r/'coordinator.log').open('x')as log:
    child=subprocess.Popen([sys.executable,str(r/'run_suite.py')],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=child.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    run_suite_sha256=hashlib.sha256((r/'run_suite.py').read_bytes()).hexdigest(),
    policy_unchanged=True,no_training=True)
(r/'launch_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
