from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent;out=root/'curriculum_v23'
assert not(out/'training_v24_launch.json').exists()
with(out/'training_v24_queue.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_verifier_training_v24.py')],cwd=root,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,scope='new admitted perception negatives; separate cache and bounded fine-tune; no promotion')
(out/'training_v24_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
