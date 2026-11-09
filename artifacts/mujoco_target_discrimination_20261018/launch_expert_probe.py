from pathlib import Path
import datetime,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
assert not(ROOT/'expert_probe_queue_v1_state.json').exists()
with(ROOT/'expert_probe_queue_v1.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'queue_expert_probe.py')],cwd=ROOT,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),teacher_collection=False,
             stages='wait training process exit; recognition gate; read-only full runtime probe; ONE actual native expert-review flight if all gates pass')
(ROOT/'expert_probe_queue_v1_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
