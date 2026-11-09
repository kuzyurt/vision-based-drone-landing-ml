from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'frozen_task_evaluation_v3').exists()
with(root/'frozen_task_evaluation_v3_launcher.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'queue_frozen_task_suite_v3.py')],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(root/'frozen_task_evaluation_v3_launch.json').write_text(json.dumps(dict(pid=p.pid),indent=2));print(json.dumps(dict(pid=p.pid)))


