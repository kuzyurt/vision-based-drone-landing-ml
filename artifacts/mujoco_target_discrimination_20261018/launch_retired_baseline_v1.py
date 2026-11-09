from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'retired_matched_baseline_v1').exists()
with(root/'retired_matched_baseline_v1_launcher.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_retired_baseline_v1.py')],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(root/'retired_matched_baseline_v1_launch.json').write_text(json.dumps(dict(pid=p.pid),indent=2));print(json.dumps(dict(pid=p.pid)))
