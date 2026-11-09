from pathlib import Path
import hashlib,json,psutil,subprocess
subprocess.run(['whoami']);subprocess.run(['hostname'])
r=Path(__file__).resolve().parent;root=r.parent
assert json.loads((r/'state.json').read_text())['status']=='completed'
assert hashlib.sha256((root/'candidate_r15/policy.json').read_bytes()).hexdigest()=='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
owned=[]
for p in psutil.process_iter(['pid','cmdline']):
    cmd=p.info['cmdline']or[]
    if any(a.endswith('/tidewater_speed_suite_20261018.mjs')or a==str(r/'run_suite_v2.py')for a in cmd):owned.append(p.info)
print(json.dumps(dict(status='completed',owned_experiment_processes=owned)))
assert not owned
