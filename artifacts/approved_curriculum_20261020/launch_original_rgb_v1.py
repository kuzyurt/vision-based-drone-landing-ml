from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent
assert not(ROOT/'original_rgb_launch.json').exists()
with(ROOT/'original_rgb_v1.log').open('x')as log:p=subprocess.Popen([sys.executable,str(ROOT/'prepare_original_rgb_v1.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(ROOT/'original_rgb_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
