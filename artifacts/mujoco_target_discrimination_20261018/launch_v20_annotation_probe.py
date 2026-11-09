from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'v20_annotation_probe_launch.json').exists()
with(root/'v20_annotation_probe_coordinator.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'run_v20_annotation_probe.py')],cwd=root,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,bulk_collection=False,task_seconds=2)
(root/'v20_annotation_probe_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
