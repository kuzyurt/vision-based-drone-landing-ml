from pathlib import Path
import hashlib,json,shutil,tarfile
r=Path(__file__).resolve().parent;out=r/'vm_r14_browser_stage';assert not out.exists();(out/'test').mkdir(parents=True)
shutil.copytree(r/'browser_r14_staging',out/'public/policy_r14_staging',ignore=shutil.ignore_patterns('__pycache__'))
s=(r/'vm_r12_browser_stage/test/tidewater_landing_r12_browser.mjs').read_text().replace('r12','r14')
(out/'test/tidewater_landing_r14_browser.mjs').write_text(s)
shutil.copytree(r/'vm_r12_browser_stage/test/r12_game',out/'test/r14_game')
shutil.copy2(r/'probe_r14_vm_controller.mjs',out/'test/probe_r14_vm_controller.mjs')
files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()}
archive=r/'vm_r14_browser_stage.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as t:
 for p in out.rglob('*'):
  if p.is_file():t.add(p,arcname=p.relative_to(out))
receipt=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=files,status='staged_unpromoted_not_qualified',scope='Isolated R14 complete controller stage; actual flight requires full native and computational gates.')
(r/'vm_r14_browser_stage_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'bytes':archive.stat().st_size,'sha256':receipt['archive_sha256'],'files':len(files)}))
