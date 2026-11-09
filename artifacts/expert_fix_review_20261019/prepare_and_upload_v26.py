"""Finalize never-evaluated new sources, then send only namespaced repair files."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';prefix=Path('expert_fix_review_20261019/v26');dest=ROOT/prefix/'sources'
for name in ['check_protocol_repair.py','check_camera_continuity.py']:
    shutil.copy2(HERE/name,dest/name)
for f in dest.rglob('*.py'):compile(f.read_text(),str(f),'exec')
(dest/'source_hashes.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest()for p in dest.rglob('*.py')},indent=2))
files=[str(f.relative_to(ROOT))for f in dest.rglob('*')if f.is_file()and'__pycache__'not in f.parts]
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',*files],check=True)
