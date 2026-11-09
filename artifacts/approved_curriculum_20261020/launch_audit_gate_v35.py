from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent
assert not(ROOT/'search_v35/audit_launch.json').exists()
with(ROOT/'search_v35/audit.log').open('x')as log:p=subprocess.Popen([sys.executable,str(ROOT/'audit_gate_v35.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(ROOT/'search_v35/audit_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
