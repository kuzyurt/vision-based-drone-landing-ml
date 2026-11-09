from pathlib import Path
import inspect,json,subprocess,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/home/hxhshsh7gyg/vision-based-drone-landing-ml')
from landing_training import paths,run_episode
print('CAMERA_INTERFACE',run_episode.camera_image.__module__,inspect.signature(run_episode.camera_image),flush=True)
assert not(ROOT/'static_repair_v44_launch.json').exists()
with(ROOT/'static_repair_v44.log').open('x')as log:p=subprocess.Popen([sys.executable,str(ROOT/'queue_static_repair_v44.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(ROOT/'static_repair_v44_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
