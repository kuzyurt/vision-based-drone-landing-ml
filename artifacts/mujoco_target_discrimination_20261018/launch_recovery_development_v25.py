from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent;out=root/'candidate_recovery_v25';out.mkdir(exist_ok=False)
with(out/'coordinator.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_recovery_development_v25.py')],cwd=root,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(out/'launch.json').write_text(json.dumps(dict(pid=p.pid),indent=2));print(json.dumps(dict(pid=p.pid)))
