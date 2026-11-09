from pathlib import Path
import json,subprocess,sys
R=Path(__file__).parent;assert not(R/'terminal_v46_launch.json').exists()
with(R/'terminal_v46_queue.log').open('x')as log:p=subprocess.Popen([sys.executable,str(R/'queue_terminal_v46.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(R/'terminal_v46_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(p.pid)
