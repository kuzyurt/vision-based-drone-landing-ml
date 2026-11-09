from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'expert_v21_launch.json').exists()
with(root/'expert_v21_pipeline.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_v21.py')],cwd=root,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,bulk_collection=False,scope='actual terminal and recovery corrections, no promotion')
(root/'expert_v21_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
