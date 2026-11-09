from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'expert_fix_review_20261019/v26b'
assert not(OUT/'packaging_launch.json').exists()
with(OUT/'packaging.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'watch_pilot_audit.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(OUT/'packaging_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)))
