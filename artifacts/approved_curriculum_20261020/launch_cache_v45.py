from pathlib import Path
import subprocess,sys,json
R=Path(__file__).parent
assert not(R/'static_cache_v45_launch.json').exists()
with(R/'static_cache_v45_queue.log').open('x')as log:p=subprocess.Popen([sys.executable,str(R/'queue_cache_v45.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(R/'static_cache_v45_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(p.pid)
