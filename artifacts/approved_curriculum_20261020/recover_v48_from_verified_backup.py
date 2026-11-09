"""Repackage locally verified VM bytes; no training, rendering or remote writes."""
from pathlib import Path
import datetime, hashlib, json, zipfile

R = Path(__file__).resolve().parent
sha = lambda b: hashlib.sha256(b).hexdigest()

def main():
    receipt = json.loads((R/'policy_backups/LATEST_VERIFIED.json').read_text())
    archive = Path(receipt['local_archive'])
    assert archive.stat().st_size == receipt['bytes']
    assert sha(archive.read_bytes()) == receipt['sha256']
    out = R/'candidate_exports/experimental_v48_local_recovery'
    out.mkdir(exist_ok=False)
    members = {}
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('BACKUP_MANIFEST.json'))
        for name, expected in manifest['files'].items():
            value = z.read(name)
            assert len(value) == expected['bytes'] and sha(value) == expected['sha256'], name
        prefix = 'new_experiment/search_v48/sources/'
        for name in manifest['files']:
            if name.startswith(prefix):
                members['sources/'+name[len(prefix):]] = z.read(name)
            if name.startswith('new_experiment/search_v48/audit/') and name.endswith('.json'):
                members['evidence/audit/'+name.rsplit('/',1)[-1]] = z.read(name)
        for name in ['candidate_binding.json','runtime_probe.json','source_test_receipt.json']:
            members['evidence/'+name] = z.read('new_experiment/search_v48/'+name)
        for name in ['best.pt','latest.pt','result.json','provenance.json','history.json','baseline_validation.json']:
            dest = {'best.pt':'checkpoints/recognizer_best.pt','latest.pt':'checkpoints/recognizer_latest_resume.pt'}.get(name,'training/'+name)
            members[dest] = z.read('new_experiment/perception_training_v47/'+name)
    previous = R/'candidate_exports/experimental_v46/package'
    oldmanifest = json.loads((previous/'MANIFEST.json').read_text())
    for name, expected in oldmanifest['files'].items():
        if name.startswith(('base_r15/','restore_fixture/')):
            value = (previous/name).read_bytes()
            assert len(value) == expected['bytes'] and sha(value) == expected['sha256']
            members[name] = value
    probe = json.loads(members['evidence/runtime_probe.json'])
    oldprobe = json.loads((previous/'evidence/runtime_probe.json').read_text())
    assert probe['source'] == oldprobe['source']
    assert [r['frame'] for r in probe['rows'][:16]] == [r['frame'] for r in oldprobe['rows'][:16]]
    binding = json.loads(members['evidence/candidate_binding.json'])
    assert sha(members['checkpoints/recognizer_best.pt']) == binding['recognizer_sha256']
    assert sha(members['sources/target_learning/expert_adapter_v48.py']) == binding['actor_sha256']
    members['restore_check.py'] = (R/'restore_candidate_v46.py').read_bytes().replace(b'expert_adapter_v46',b'expert_adapter_v48').replace(b'verified_local_recovery_v39',b'verified_local_recovery_v48')
    members['README.md'] = b'''# Experimental V48 recovery\n\nNOT QUALIFIED FOR PRODUCTION. No installation or data eligibility release.\nExact frozen V48 actor, corrected DAgger takeover sources, V47 best and latest\nresume checkpoints, original R15 pose/spatial/runtime, static own-aircraft CAD,\nand closed rescue audits. One genuine assisted rescue landed at 61.20 task\nseconds. Other search and expired-memory purpose gates remain FAILED.\nNo bulk teacher trajectories admitted. Latest rejected V53/V55 are separate\nin the complete backup; V59 was prepared but NOT launched.\n\nRebuilt locally from the SHA-verified 09:04 UTC VM snapshot after strict SSH\nauthentication failed. Base runtime and matching RGB fixture came from the\nearlier verified V46 package. Source files are unchanged. Run restore_check.py\nfor offline CPU inference (Linux native kernel); Windows uses the separate\nexact-source marker_kernel.dll wrapper alongside this package.\n'''
    m = dict(schema='approved.experimental.recovery.v48.local',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),qualification='EXPERIMENTAL_NOT_QUALIFIED',active_recognizer_sha256=binding['recognizer_sha256'],recovered_from_snapshot_sha256=receipt['sha256'],files={n:dict(bytes=len(v),sha256=sha(v)) for n,v in members.items()})
    members['MANIFEST.json'] = json.dumps(m,indent=2).encode()
    package = out/'package'; package.mkdir()
    for name,value in members.items():
        p = package/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(value)
    target = out/'experimental_v48.zip'
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for name,value in members.items(): z.writestr(name,value)
    with zipfile.ZipFile(target) as z:
        for name,value in members.items(): assert sha(z.read(name)) == sha(value)
    proof = dict(status='locally_recovered_and_all_members_verified',archive=str(target),sha256=sha(target.read_bytes()),bytes=target.stat().st_size,files=len(m['files']),active_recognizer_sha256=binding['recognizer_sha256'],snapshot_sha256=receipt['sha256'],qualification='EXPERIMENTAL_NOT_QUALIFIED')
    (out/'LOCAL_VERIFIED.json').write_text(json.dumps(proof,indent=2)); print(json.dumps(proof))

if __name__ == '__main__': main()
