from pathlib import Path
import subprocess,sys,json
R=Path(__file__).parent;O=R/'search_v48';assert not(O/'launch.json').exists()
with(O/'coordinator.log').open('x')as f:p=subprocess.Popen([sys.executable,str(R/'queue_affected_v48b.py')],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(O/'launch.json').write_text(json.dumps(dict(pid=p.pid)));print(p.pid)
