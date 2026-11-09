"""Stage a deterministic handoff bug fix; deployed game remains unchanged."""
from pathlib import Path
import hashlib,json,tarfile
r=Path(__file__).resolve().parent;repo=r.parents[1];out=r/'r15_safe_handoff_patch';assert not out.exists();(out/'test/r15_game').mkdir(parents=True)
source=repo/'tidewater-game/app/src/landing/BrowserPX4.js';s=source.read_text()
a='manualHold() {this.targetHeight=clamp(.216-this.observation()[3],.205,8);this.landingRequested=false;}'
b='manualHold() {this.targetHeight=Math.max(.205,.216-this.observation()[3]);this.landingRequested=false;}'
assert s.count(a)==1;s=s.replace(a,b)
a="this.targetHeight=clamp(this.targetHeight+((held('KeyR')?1:0)-(held('KeyF')?1:0))*.6*.04,.205,8);";assert s.count(a)==1
s=s.replace(a,a.replace('.205,8);','.205,Math.max(8,this.targetHeight));'))
s=s.replace("from './","from '../../src/landing/")
(out/'test/r15_game/BrowserPX4.js').write_text(s)
for name in ['tidewater_landing_r15_browser.mjs','tidewater_landing_r15_moving_browser.mjs']:
    s=(r/'vm_r15_browser_stage/test'/name).read_text();a="from '../src/landing/BrowserPX4.js'";assert s.count(a)==1
    (out/'test'/name).write_text(s.replace(a,"from './r15_game/BrowserPX4.js'"))
probe=r/'probe_r15_safe_handoff.mjs';assert probe.exists();(out/'test/probe_r15_safe_handoff.mjs').write_bytes(probe.read_bytes())
files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in out.rglob('*')if p.is_file()}
archive=r/'r15_safe_handoff_patch.tar.gz'
with tarfile.open(archive,'w:gz')as t:
    for p in out.rglob('*'):
        if p.is_file():t.add(p,arcname=p.relative_to(out))
receipt=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=files,production_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Current manualHold and following pilot tick both clamp target to8m; policy recovery may reach10m. Retain measured handoff height without changing normal8m manual ceiling or boat controls. Scene/controller/physics unchanged.',staging_only=True)
(r/'r15_safe_handoff_patch_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k!='files'}))
