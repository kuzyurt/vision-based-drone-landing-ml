from pathlib import Path
import hashlib,json,tarfile
r=Path(__file__).resolve().parent;p=r/'r15_pilot_verified_compact.tar.gz';receipt=json.loads((r/'r15_pilot_verified_compact_receipt.json').read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['sha256']
out=r/'r15_pilot_verified_compact';assert not out.exists();out.mkdir()
with tarfile.open(p)as t:
    for m in t.getmembers():assert(out/m.name).resolve().is_relative_to(out.resolve())
    t.extractall(out,filter='data')
print('Verified compact development archive',receipt['bytes'],'bytes; no recordings/checkpoints modified')
