from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent;out=root/'curriculum_v23'
assert not(out/'training_queue_launch.json').exists()
with(out/'training_queue.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_verifier_training_v23.py')],cwd=root,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,scope='wait for closed admitted perception, cache and bounded separate RGB verifier fine-tune; no promotion')
(out/'training_queue_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
