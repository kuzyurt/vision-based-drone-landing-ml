from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent;assert not(ROOT/'spatial_training_v3_launch.json').exists()
with(ROOT/'spatial_training_v3.log').open('x')as f:p=subprocess.Popen([sys.executable,str(ROOT/'train_original_spatial_v3.py')],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
(ROOT/'spatial_training_v3_launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)),flush=True)
