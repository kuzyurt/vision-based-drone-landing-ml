from pathlib import Path
import json,os,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'v13c_packaging_launch.json').exists()
with(root/'v13c_packaging.log').open('x')as log:
 p=subprocess.Popen([sys.executable,str(root/'package_review_v13c.py')],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,purpose='Wait for closed review recording, inspect actual command/phase evidence and encode at most30s actual camera preview; no simulation or collection')
(root/'v13c_packaging_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
