from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'frozen_task_postmortem_v1').exists()
with(root/'frozen_task_postmortem_v1_launcher.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'postmortem_frozen_suite_v1.py')],cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(root/'frozen_task_postmortem_v1_launch.json').write_text(json.dumps(dict(pid=p.pid),indent=2));print(json.dumps(dict(pid=p.pid)))
