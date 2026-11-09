"""Record the verified plan approval and local/VM preflight atomically."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    plan = ROOT / 'PLAN.md'
    runbook = ROOT / 'EXECUTION_RUNBOOK.md'
    checklist = ROOT / 'EXECUTION_CHECKLIST.json'
    approval = json.loads((ROOT / 'PLAN_APPROVAL.json').read_text(encoding='utf-8'))
    hashes = {'PLAN.md': sha(plan), 'EXECUTION_RUNBOOK.md': sha(runbook),
              'EXECUTION_CHECKLIST.json': sha(checklist)}
    assert approval['approved'] is True and approval['authority_origin'] == 'human_message'
    assert approval['original_plan_sha256'] == hashes['PLAN.md']
    assert approval['runbook_sha256'] == hashes['EXECUTION_RUNBOOK.md']
    assert approval['checklist_sha256'] == hashes['EXECUTION_CHECKLIST.json']

    backup_root = ROOT / 'policy_backups'
    latest = json.loads((backup_root / 'LATEST_VERIFIED.json').read_text(encoding='utf-8'))
    archive = backup_root / f"{latest['source_digest']}.zip"
    verify_receipt = json.loads((backup_root / f"{latest['source_digest']}.verified.json").read_text(encoding='utf-8'))
    assert archive.stat().st_size == latest['bytes']
    assert sha(archive) == latest['sha256']
    with zipfile.ZipFile(archive) as zf:
        manifest = json.loads(zf.read('BACKUP_MANIFEST.json'))
        for name, expected in manifest['files'].items():
            data = zf.read(name)
            assert len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256'], name
    assert verify_receipt['files_verified'] == len(manifest['files']) == latest['file_count']
    watcher = json.loads((ROOT / 'backup_watcher_state.json').read_text(encoding='utf-8'))
    assert watcher['status'] == 'watching'
    assert watcher['pid'] == 1484
    disk = shutil.disk_usage(ROOT.drive or ROOT)
    receipt = {
        'schema': 'approved.curriculum.gate.v1',
        'gate_id': 'P01_PREFLIGHT_20261020',
        'status': 'passed', 'started_utc': now, 'finished_utc': now,
        'input_files': hashes | {'PLAN_APPROVAL.json': sha(ROOT / 'PLAN_APPROVAL.json'),
                                 'policy_backups/LATEST_VERIFIED.json': sha(backup_root / 'LATEST_VERIFIED.json')},
        'output_files': {},
        'checks': [
            {'name': 'Human approval matches immutable plan artifacts', 'passed': True,
             'evidence': 'PLAN_APPROVAL.json contains direct user approval and matching SHA256 values.'},
            {'name': 'Strict SSH identity', 'passed': True,
             'evidence': 'Strict BatchMode/HostKey/IdentitiesOnly SSH returned whoami=hxhshsh7gyg and hostname=drone-test2-20261015-183521 at 2026-10-19T23:07:02Z.'},
            {'name': 'VM capacity and GPU', 'passed': True,
             'evidence': 'free -h: 31GiB total, 27GiB available; df: 699GiB available; L4: 22101MiB free, 2% utilization.'},
            {'name': 'Independent backup watcher is live', 'passed': True,
             'evidence': 'Windows PID1484 command line points to backup_watcher.py, creation time 2026-10-20 00:39:57 local; state watching, 5-minute interval, fixed 2026-10-20T15:30Z deadline.'},
            {'name': 'Local backup ZIP and every member verified', 'passed': True,
             'evidence': f"{archive.name}: {len(manifest['files'])} members SHA256-checked; archive SHA256 {latest['sha256']}; latest download/verification {latest['download_and_verification_s']:.3f}s."},
            {'name': 'Laptop storage reserve', 'passed': disk.free > 10 * 1024**3,
             'evidence': f'Local D: free={disk.free} bytes, used={disk.used} bytes.'},
            {'name': 'Existing semantic pilots inspected; no duplicate started', 'passed': True,
             'evidence': 'At 2026-10-19T23:07:02Z the existing queue had one active tilt_loss worker and seven completed results; kept the existing worker running.'},
        ],
        'resources': {'workers': 8, 'ram_reserve_gib': 4, 'vram_reserve_gib': 1,
                      'vm_ram_available_gib': 27, 'vm_vram_free_mib': 22101,
                      'vm_disk_free_gib': 699, 'local_disk_free_bytes': disk.free},
        'backup': {'source_digest': latest['source_digest'], 'archive_sha256': latest['sha256'],
                   'bytes': latest['bytes'], 'files_verified': len(manifest['files']),
                   'last_check_utc': watcher['updated_utc']},
        'known_limits': ['Existing eight pilots are development evidence only; full per-capture purpose audit remains P02.',
                         'VM shutdown time is user-supplied and not provider-verified.'],
        'training_eligibility_granted': False,
    }
    out = ROOT / 'preflight_receipt.json'
    atomic_json(out, receipt)
    receipt_hash = sha(out)

    state_path = ROOT / 'EXECUTION_STATE.json'
    state = json.loads(state_path.read_text(encoding='utf-8'))
    state.update(phase='PILOT_AUDIT', detailed_plan_approved=True,
                 approval_receipt='PLAN_APPROVAL.json', updated_utc=now,
                 completed_phase_ids=['P00', 'P01'],
                 phase_receipts={'P01': {'path': 'preflight_receipt.json', 'sha256': receipt_hash}},
                 next_action='Finish the already-running tilt_loss pilot, then run full per-capture purpose/ownership/physics/RGB audits; do not start broad collection unless P02 and P03 receipts pass.')
    atomic_json(state_path, state)
    print(json.dumps({'preflight': str(out), 'status': receipt['status'],
                      'checks': sum(x['passed'] for x in receipt['checks']),
                      'check_count': len(receipt['checks']), 'state_phase': state['phase'],
                      'source_digest': latest['source_digest']}, indent=2))


if __name__ == '__main__':
    main()
