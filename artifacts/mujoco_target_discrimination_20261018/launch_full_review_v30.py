from pathlib import Path
import json,subprocess,sys
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z');OUT=ROOT/'expert_fix_review_20261019/v30_full'
OUT.mkdir(exist_ok=True);assert not(OUT/'launch.json').exists()
with(OUT/'coordinator.log').open('x')as log:
    p=subprocess.Popen([sys.executable,str(ROOT/'queue_full_review_v30.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(OUT/'launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)))
