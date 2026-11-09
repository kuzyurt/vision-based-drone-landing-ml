from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent;out=root/'candidate_development_v25'
assert not(out/'audit_launch.json').exists()
with(out/'audit.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'audit_candidate_development_v25.py')],cwd=root,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(out/'audit_launch.json').write_text(json.dumps(dict(pid=p.pid),indent=2));print(json.dumps(dict(pid=p.pid)))
