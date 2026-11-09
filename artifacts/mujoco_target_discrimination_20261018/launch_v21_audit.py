from pathlib import Path
import json,os,subprocess,sys
root=Path(__file__).resolve().parent
assert not(root/'v21_completion_audit_launch.json').exists()
coordinator=json.loads((root/'expert_v21_launch.json').read_text())['pid']
with(root/'v21_completion_audit.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(root/'audit_v21_when_closed.py'),'--coordinator',str(coordinator)],
        cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(pid=p.pid,coordinator=coordinator,wait='Linux process exit event, not token polling')
(root/'v21_completion_audit_launch.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
