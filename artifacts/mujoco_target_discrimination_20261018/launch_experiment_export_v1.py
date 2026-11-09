from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'experimental_delivery_v1').exists()
with(root/'experimental_delivery_v1_launcher.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'export_experiment_evidence_v1.py')],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(root/'experimental_delivery_v1_launch.json').write_text(json.dumps(dict(pid=p.pid),indent=2));print(json.dumps(dict(pid=p.pid)))
