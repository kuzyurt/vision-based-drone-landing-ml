from pathlib import Path
import datetime,json,subprocess,sys
root=Path(__file__).resolve().parent;out=root/'curriculum_v23'
assert not(out/'launch.json').exists()
with(out/'coordinator.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_curriculum_v23.py')],cwd=root,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='new staged MuJoCo perception curriculum; no action imitation or production promotion',workers=8)
(out/'launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
