"""Local independent checkpoint downloads, with verified immutable snapshots."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import time
import zipfile
import transport

HERE = Path(__file__).resolve().parent
DEST = HERE / 'policy_backups'

def utc():
    return datetime.datetime.now(datetime.timezone.utc)

def save(value):
    value.update(pid=os.getpid(), updated_utc=utc().isoformat())
    temporary = HERE / 'backup_watcher_state.json.tmp'
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(temporary, HERE / 'backup_watcher_state.json')

def once():
    receipt = json.loads(transport.run('snapshot_policy.py'))
    DEST.mkdir(exist_ok=True)
    name = receipt['source_digest']
    complete = DEST / (name + '.verified.json')
    if complete.exists():
        return json.loads(complete.read_text())
    archive = DEST / (name + '.zip')
    temporary = archive.with_suffix('.zip.part')
    started = time.monotonic()
    transport.pull(receipt['archive_relative'], temporary)
    assert temporary.stat().st_size == receipt['bytes']
    assert hashlib.sha256(temporary.read_bytes()).hexdigest() == receipt['sha256']
    with zipfile.ZipFile(temporary) as z:
        manifest = json.loads(z.read('BACKUP_MANIFEST.json'))
        for member, expected in manifest['files'].items():
            value = z.read(member)
            assert len(value) == expected['bytes']
            assert hashlib.sha256(value).hexdigest() == expected['sha256'], member
    os.replace(temporary, archive)
    receipt.update(local_archive=str(archive), locally_verified_utc=utc().isoformat(),
                   download_and_verification_s=time.monotonic()-started,
                   files_verified=len(manifest['files']))
    complete.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    (DEST / 'LATEST_VERIFIED.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--until', default='2026-10-20T15:30:00+00:00')
    parser.add_argument('--interval', type=int, default=300)
    args = parser.parse_args()
    deadline = datetime.datetime.fromisoformat(args.until)
    last = None
    while True:
        try:
            last = once()
            save({'status': 'verified' if args.once else 'watching', 'latest': last,
                  'next_check_utc': (utc()+datetime.timedelta(seconds=args.interval)).isoformat(),
                  'deadline_utc': deadline.isoformat()})
            print(json.dumps({'status': 'verified', 'snapshot': last['source_digest'],
                              'utc': utc().isoformat()}), flush=True)
            if args.once:
                return
        except Exception as error:
            save({'status': 'retrying', 'error': str(error), 'latest': last,
                  'deadline_utc': deadline.isoformat()})
            if args.once:
                raise
        if utc() >= deadline:
            save({'status': 'finished_at_deadline', 'latest': last})
            return
        time.sleep(min(args.interval, max(1, (deadline-utc()).total_seconds())))

if __name__ == '__main__':
    main()
