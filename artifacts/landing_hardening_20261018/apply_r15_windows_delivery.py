"""Apply the verified prepared delivery with byte-preserving backups and race checks."""
from pathlib import Path
import datetime,difflib,hashlib,json,shutil,subprocess
r=Path(__file__).resolve().parent;repo=r.parents[1];app=repo/'tidewater-game/app'
delivery=r/'r15_windows_delivery'
receipt=json.loads((r/'r15_windows_prepared_receipt.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for rel,values in receipt['changes'].items():
    source=app/rel
    assert (sha(source)if source.exists()else None)==values['before_sha256'],rel+' changed since review'
    assert sha(delivery/rel)==values['prepared_sha256'],rel+' staging changed'
backup=r/'r15_windows_before_integration';assert not backup.exists();backup.mkdir()
dirty=subprocess.run(['git','diff','--name-only','-z'],cwd=repo,capture_output=True,check=True).stdout.decode('utf-8').split('\0')
prior={rel:sha(repo/rel)for rel in dirty if rel and(repo/rel).is_file()}
for rel,values in receipt['changes'].items():
    source=app/rel
    if source.exists():
        target=backup/'app'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        assert sha(target)==values['before_sha256']
readme=repo/'tidewater-game/README.md';shutil.copy2(readme,backup/'tidewater-game_README.md')
dist=app/'dist';dist_backup=backup/'dist_before'
if dist.exists():
    assert dist.resolve().is_relative_to(repo.resolve())and dist_backup.resolve().is_relative_to(repo.resolve())
    assert not dist.is_symlink() and dist.is_dir() and(dist/'index.html').is_file()
    dist.rename(dist_backup)
for rel,values in receipt['changes'].items():
    target=app/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(delivery/rel,target)
    assert sha(target)==values['prepared_sha256']
allowed={'tidewater-game/app/'+rel for rel in receipt['changes']}
for rel,expected in prior.items():
    if rel not in allowed:assert sha(repo/rel)==expected,rel+' unrelated change'
diff=[]
for name in ['BrowserGame','PolicyTelemetry','BrowserPX4']:
    rel='src/landing/'+name+'.js'
    before=(backup/'app'/rel).read_text(encoding='utf-8')
    after=(app/rel).read_text(encoding='utf-8')
    diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=rel+' before',tofile=rel+' R15'))
(r/'r15_windows_integration.diff').write_text(''.join(diff),encoding='utf-8')
result=dict(**receipt,applied_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    backup_directory=str(backup),preexisting_tracked_changes_sha256=prior,
    previous_dist_preserved=dist_backup.exists(),build_still_required=True)
result['status']='integrated_source_and_policy_build_pending'
(r/'r15_windows_integration_receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],files=len(receipt['changes']),backup_directory=str(backup),unrelated_tracked_changes_preserved=True),indent=2))
