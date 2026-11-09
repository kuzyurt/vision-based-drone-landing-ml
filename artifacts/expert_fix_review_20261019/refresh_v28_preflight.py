from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';SRC=ROOT/'expert_fix_review_20261019/v28/sources'
assert not(SRC.parent/'launch.json').exists(),'Never change launched sources'
for p in SRC.rglob('*.py'):compile(p.read_text(),str(p),'exec')
(SRC/'source_hashes.json').write_text(json.dumps({p.relative_to(SRC).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in SRC.rglob('*.py')},indent=2))
files=[SRC/'target_learning/camera_continuity.py',SRC/'check_camera_continuity.py',SRC/'source_hashes.json']
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*[str(p.relative_to(ROOT))for p in files]],check=True)
