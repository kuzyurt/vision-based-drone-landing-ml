from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent
assert not(ROOT/'search_v33/launch.json').exists()
with(ROOT/'search_v33/coordinator.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'queue_search_v33.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,source_revision='search_v33',training_started=False)
(ROOT/'search_v33/launch.json').write_text(json.dumps(receipt));print(json.dumps(receipt),flush=True)
