from pathlib import Path
import hashlib,json,tarfile
r=Path(__file__).resolve().parent;p=r/'candidate_r14_controller.tar.gz';assert not p.exists()
assert hashlib.sha256((r/'candidate_r14/policy.json').read_bytes()).hexdigest()=='34845b34dc9490fddcc411738bd25b83e0d52bf4ab3564bf4aa22c931004c473'
with tarfile.open(p,'w:gz')as t:
    for f in (r/'candidate_r14').rglob('*'):
        if f.is_file()and f.suffix in ['.py','.json','.so']and '__pycache__'not in str(f):t.add(f,arcname=f.relative_to(r))
print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
