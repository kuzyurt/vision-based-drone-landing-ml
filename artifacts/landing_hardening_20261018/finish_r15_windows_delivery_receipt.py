"""Finish the receipt after Windows path separators interrupted the post-copy audit."""
from pathlib import Path
import datetime,difflib,hashlib,json,subprocess
r=Path(__file__).resolve().parent;repo=r.parents[1];app=repo/'tidewater-game/app'
receipt=json.loads((r/'r15_windows_prepared_receipt.json').read_text(encoding='utf-8'))
backup=r/'r15_windows_before_integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert backup.is_dir()
for rel,value in receipt['changes'].items():
    assert sha(app/rel)==value['prepared_sha256'],rel
    if value['before_sha256']is not None:
        assert sha(backup/'app'/rel)==value['before_sha256'],rel
assert sha(repo/'tidewater-game/README.md')==sha(backup/'tidewater-game_README.md')
diff=[]
for name in ['BrowserGame','PolicyTelemetry','BrowserPX4']:
    rel='src/landing/'+name+'.js'
    diff.extend(difflib.unified_diff((backup/'app'/rel).read_text(encoding='utf-8').splitlines(True),
        (app/rel).read_text(encoding='utf-8').splitlines(True),fromfile=rel+' before',tofile=rel+' R15'))
(r/'r15_windows_integration.diff').write_text(''.join(diff),encoding='utf-8')
allowed={'tidewater-game/app/'+rel.replace('\\','/')for rel in receipt['changes']}
dirty=subprocess.run(['git','diff','--name-only','-z'],cwd=repo,capture_output=True,check=True).stdout.decode('utf-8').split('\0')
unrelated={rel:sha(repo/rel)for rel in dirty if rel and rel not in allowed and(repo/rel).is_file()}
result=dict(**receipt,applied_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    backup_directory=str(backup),unrelated_tracked_changes_after_integration_sha256=unrelated,
    previous_dist_preserved=(backup/'dist_before/index.html').is_file(),build_still_required=True,
    validation_note='Initial post-copy audit used Windows backslashes against Git forward slashes and misclassified BrowserGame as unrelated. All28installed files and every previous-file backup now verified against the pre-copy receipt; no policy or app correction was needed.')
result['status']='integrated_source_and_policy_build_pending'
(r/'r15_windows_integration_receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],files=len(receipt['changes']),backups_verified=True,previous_dist_preserved=result['previous_dist_preserved']),indent=2))
