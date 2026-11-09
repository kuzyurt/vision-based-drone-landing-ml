from pathlib import Path
import hashlib,json,shutil,tarfile
r=Path(__file__).resolve().parent;out=r/'vm_r15_browser_stage';assert not out.exists();(out/'test').mkdir(parents=True)
shutil.copytree(r/'browser_r15_staging',out/'public/policy_r15_staging',ignore=shutil.ignore_patterns('__pycache__'))
for name,source in [('tidewater_landing_r15_browser.mjs',r/'vm_r14_browser_stage/test/tidewater_landing_r14_browser.mjs'),('tidewater_landing_r15_moving_browser.mjs',r/'tidewater_landing_r14_moving_browser.mjs')]:
    (out/'test'/name).write_text(source.read_text().replace('r14','r15'))
shutil.copytree(r/'vm_r14_browser_stage/test/r14_game',out/'test/r15_game')
shutil.copy2(r/'probe_r15_vm_controller.mjs',out/'test/probe_r15_vm_controller.mjs')
files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()}
archive=r/'vm_r15_browser_stage.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as t:
    for p in out.rglob('*'):
        if p.is_file():t.add(p,arcname=p.relative_to(out))
receipt=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=files,status='staged_unpromoted_not_qualified',scope='Isolated R15 controller +bounded actual-game scenarios; no production changes. Physical native and actual game gates required.')
(r/'vm_r15_browser_stage_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(r/'vm_r15_moving_driver_receipt.json').write_text(json.dumps(dict(file='test/tidewater_landing_r15_moving_browser.mjs',sha256=files['test/tidewater_landing_r15_moving_browser.mjs'],scope='Independent test boat motor route at.6m/s scenario; production2.8cruise/usercontrols unchanged.'),indent=2)+'\n')
print(json.dumps({'bytes':archive.stat().st_size,'sha256':receipt['archive_sha256'],'files':len(files)}))
