from pathlib import Path
import datetime,json,os,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'expert_v10_pipeline_state.json').exists()
assert not(root/'expert_v10_launch.json').exists()
with(root/'expert_v10_pipeline.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_v10.py')],cwd=root,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),teacher_collection=False,
    stages='cached design/marker relabeling; two-task whole-object verifier; strict recognition gate; full actual-RGB hook probe; ONE bounded native review flight')
(root/'expert_v10_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))

