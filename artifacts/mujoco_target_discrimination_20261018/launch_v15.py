from pathlib import Path
import datetime,json,os,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'expert_v15_pipeline_state.json').exists()
with(root/'expert_v15_pipeline.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_v15.py')],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bulk_collection=False,review_only=True)
(root/'expert_v15_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
