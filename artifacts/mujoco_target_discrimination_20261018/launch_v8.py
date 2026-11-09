from pathlib import Path
import datetime,json,os,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'expert_v8_pipeline_state.json').exists()
assert not(root/'expert_v8_launch.json').exists()
with(root/'expert_v8_pipeline.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_v8.py')],cwd=root,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),teacher_collection=False,
    stages='visible-part annotation with exact RGB reuse proof; whole-object verifier; strict recognition gate; full actual-RGB hook probe; ONE bounded native review flight')
(root/'expert_v8_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
