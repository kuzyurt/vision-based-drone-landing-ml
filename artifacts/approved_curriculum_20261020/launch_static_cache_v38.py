from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent;assert not(ROOT/'static_cache_v38_launch.json').exists()
with(ROOT/'static_cache_v38.log').open('x')as f:p=subprocess.Popen([sys.executable,str(ROOT/'queue_static_cache_v38.py')],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(ROOT/'static_cache_v38_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
