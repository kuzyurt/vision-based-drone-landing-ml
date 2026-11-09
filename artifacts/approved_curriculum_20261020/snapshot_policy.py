"""Export stable, versioned policy packages; excludes videos and raw recordings."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent
BASELINE = OLD.parent / 'landing_hardening_20261018T011610Z/candidate_r15'
SOURCES = OLD / 'expert_fix_review_20261019/v31/sources'
PARENT = OLD / 'perception_training_v12_rgb_only/best.pt'
SUFFIXES = {'.pt', '.pth', '.onnx', '.safetensors', '.bin', '.json', '.py', '.md',
            '.toml', '.yaml', '.yml', '.txt', '.npz'}
EXCLUDED = {'backup_snapshots', 'episodes', 'recordings', 'raw', '__pycache__', '.git',
            'feature_cache', 'roi_cache', 'rgb_cache'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def stable_bytes(path):
    before = path.stat()
    value = path.read_bytes()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), str(path)
    return value

def main():
    groups = [('baseline_r15', BASELINE), ('reviewed_v31_sources', SOURCES),
              ('new_experiment', ROOT)]
    members = {}
    for label, directory in groups:
        assert directory.is_dir(), directory
        for path in sorted(directory.rglob('*')):
            rel = path.relative_to(directory)
            if not path.is_file() or path.suffix not in SUFFIXES or set(rel.parts) & EXCLUDED:
                continue
            if label == 'new_experiment' and path.name.startswith('epoch_'):
                continue  # best/latest include the resumable selected state
            if path.name in {'snapshot_index.json', 'snapshot_policy.py.tmp'}:
                continue
            assert path.stat().st_size <= 256 * 1024**2, ('unexpected policy package file', str(path))
            members[label + '/' + rel.as_posix()] = stable_bytes(path)
    assert PARENT.is_file()
    members['recognizer_parent/best.pt'] = stable_bytes(PARENT)
    assert digest(members['recognizer_parent/best.pt']) == 'c87dca7541d361b183ce45da5f7756bdc5a358aaf544fb2bc5c3fc08bad1e0e3'
    assert sum(map(len, members.values())) < 512 * 1024**2, 'policy snapshot exceeds compact size budget'
    entries = {name: {'sha256': digest(value), 'bytes': len(value)} for name, value in members.items()}
    source_digest = digest(json.dumps(entries, sort_keys=True).encode())
    destination = ROOT / 'backup_snapshots'
    destination.mkdir(exist_ok=True)
    receipt_path = destination / (source_digest + '.json')
    if receipt_path.exists():
        print(receipt_path.read_text(), flush=True)
        return
    manifest = {'schema': 'approved.curriculum.policy.backup.v1',
                'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'purpose': 'Recovery package, not a deployment or qualification certificate',
                'source_digest': source_digest, 'files': entries}
    archive = destination / (source_digest + '.zip')
    temporary = archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for name, value in members.items():
            z.writestr(name, value)
        z.writestr('BACKUP_MANIFEST.json', json.dumps(manifest, indent=2))
    os.replace(temporary, archive)
    receipt = {'archive_relative': archive.relative_to(ROOT).as_posix(),
               'sha256': digest(archive.read_bytes()), 'bytes': archive.stat().st_size,
               'source_digest': source_digest, 'created_utc': manifest['created_utc'],
               'file_count': len(entries)}
    temporary_receipt = receipt_path.with_suffix('.json.tmp')
    temporary_receipt.write_text(json.dumps(receipt, indent=2))
    os.replace(temporary_receipt, receipt_path)
    print(json.dumps(receipt), flush=True)

if __name__ == '__main__':
    main()
