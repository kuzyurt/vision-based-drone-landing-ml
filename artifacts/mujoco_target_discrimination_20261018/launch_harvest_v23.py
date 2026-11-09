from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent;out=root/'curriculum_v23'
assert not(out/'harvest_launch.json').exists()
with(out/'harvest.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'harvest_curriculum_v23.py')],cwd=root,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,scope='filesystem-event-driven exact source/label admission; perception only')
(out/'harvest_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
