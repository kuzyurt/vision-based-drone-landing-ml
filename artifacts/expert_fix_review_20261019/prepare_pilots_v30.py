from pathlib import Path
import hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';SRC=ROOT/'expert_fix_review_20261019/v30/sources'
assert not(SRC.parent/'launch.json').exists()
shutil.copy2(HERE/'queue_pilots_v30.py',SRC/'queue_pilots_v30.py')
s="""from pathlib import Path
import json,subprocess,sys
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z');OUT=ROOT/'expert_fix_review_20261019/v30'
assert not(OUT/'launch.json').exists()
with(OUT/'coordinator.log').open('x')as log:
 p=subprocess.Popen([sys.executable,str(OUT/'sources/queue_pilots_v30.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(OUT/'launch.json').write_text(json.dumps(dict(pid=p.pid)));print(json.dumps(dict(pid=p.pid)))
"""
(SRC/'launch_pilots_v30.py').write_text(s)
for p in SRC.rglob('*.py'):compile(p.read_text(),str(p),'exec')
(SRC/'source_hashes.json').write_text(json.dumps({p.relative_to(SRC).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in SRC.rglob('*.py')},indent=2))
files=[SRC/'queue_pilots_v30.py',SRC/'launch_pilots_v30.py',SRC/'source_hashes.json'];subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*[str(p.relative_to(ROOT))for p in files]],check=True)
