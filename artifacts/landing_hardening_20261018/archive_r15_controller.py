from pathlib import Path
import hashlib,json,tarfile
r=Path(__file__).resolve().parent;p=r/'candidate_r15_controller.tar.gz';assert not p.exists()
assert hashlib.sha256((r/'candidate_r15/policy.json').read_bytes()).hexdigest()=='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
with tarfile.open(p,'w:gz')as t:
    for f in (r/'candidate_r15').rglob('*'):
        if f.is_file()and f.suffix in ['.py','.json','.so']and '__pycache__'not in str(f):t.add(f,arcname=f.relative_to(r))
print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
