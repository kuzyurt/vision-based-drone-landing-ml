from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent;assert not(ROOT/'search_v39/postmortem_launch.json').exists()
with(ROOT/'search_v39/postmortem.log').open('x')as log:p=subprocess.Popen([sys.executable,str(ROOT/'queue_postmortem_v39.py')],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(ROOT/'search_v39/postmortem_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
