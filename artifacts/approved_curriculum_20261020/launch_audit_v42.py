from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent;assert(ROOT/'search_v42/launch.json').exists();assert not(ROOT/'search_v42/audit_launch.json').exists()
with(ROOT/'search_v42/audit.log').open('x')as f:p=subprocess.Popen([sys.executable,str(ROOT/'audit_gate_v42.py')],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(ROOT/'search_v42/audit_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
