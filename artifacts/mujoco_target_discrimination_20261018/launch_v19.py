from pathlib import Path
import datetime,json,os,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'expert_v19_pipeline_state.json').exists()
assert not(root/'expert_v19_launch.json').exists()
with(root/'expert_v19_pipeline.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_v19.py')],cwd=root,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bulk_collection=False,
    purpose='three genuine learner struggle development cases; no automatic success or approval')
(root/'expert_v19_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
