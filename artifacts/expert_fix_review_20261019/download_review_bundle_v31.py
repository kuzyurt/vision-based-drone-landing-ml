from pathlib import Path
import hashlib,json,subprocess,sys,time,zipfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018';REMOTE='expert_fix_review_20261019/delivery_v31/'
began=time.monotonic()
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'pull',REMOTE+'corrected_expert_review_v31.zip',REMOTE+'corrected_expert_review_v31_bundle_receipt.json'],check=True,timeout=295)
stage=ROOT/'vm_results';archive=stage/'corrected_expert_review_v31.zip';receipt=json.loads((stage/'corrected_expert_review_v31_bundle_receipt.json').read_text())
assert archive.stat().st_size==receipt['bytes']and hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
out=HERE/'delivery_v31';assert not out.exists()
with zipfile.ZipFile(archive)as z:
    for name in z.namelist():assert(out/name).resolve().is_relative_to(out.resolve())and not name.startswith('/')
    z.extractall(out)
m=json.loads((out/'corrected_expert_review_v31_manifest.json').read_text())
for name,r in m['files'].items():
    p=out/name;assert p.stat().st_size==r['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],name
elapsed=time.monotonic()-began;assert elapsed<300,'Compact download exceeded requested five-minute budget'
(out/'LOCAL_VERIFIED_DOWNLOAD.json').write_text(json.dumps(dict(download_and_verification_seconds=elapsed,archive_sha256=receipt['sha256'],files_verified=len(m['files']),training_eligible=False),indent=2))
print(json.dumps(dict(seconds=elapsed,files=len(m['files']),directory=str(out))),flush=True)
