"""Collect eight qualified replacements, then build the curated view. Never trains."""
import argparse
import json
import os
import subprocess
import sys
import psutil
from common import HERE, config, verify_sources, write_json, utc


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--launch',action='store_true')
    p.add_argument('--workers',type=int,default=3)
    p.add_argument('--_run',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args()
    if not 1<=args.workers<=3:p.error('workers must be 1..3')
    receipt=HERE/'process.json'
    if not args._run and receipt.exists():
        r=json.loads(receipt.read_text())
        try:
            existing=psutil.Process(r['pid'])
            if abs(existing.create_time()-r['process_create_time'])<.01:
                raise RuntimeError('Revision coordinator is already running')
        except psutil.NoSuchProcess:pass
    validation=json.loads((HERE/'validation.json').read_text())
    if validation['status']!='passed':raise RuntimeError('Revision validation has not passed')
    verify_sources(validation['source_receipt'])
    c=config()
    if args._run:
        write_json(HERE/'status.json',dict(status='collecting',workers=args.workers,updated_utc=utc(),training_started=False))
        code=subprocess.call([sys.executable,'-B',str(HERE/'collect.py'),'--workers',str(args.workers)],cwd=HERE)
        if code:
            write_json(HERE/'status.json',dict(status='collection_failed_review_required',returncode=code,updated_utc=utc(),training_started=False))
            raise RuntimeError('Collection failed; recordings/logs preserved')
        write_json(HERE/'status.json',dict(status='verifying_curated_view',updated_utc=utc(),training_started=False))
        code=subprocess.call([sys.executable,'-B',str(HERE/'curate.py'),'build'],cwd=HERE)
        write_json(HERE/'status.json',dict(status='ready_for_training' if code==0 else 'curation_requires_review',returncode=code,updated_utc=utc(),training_started=False))
        if code:raise RuntimeError('Curation rejected the results; inspect revision.log')
        return
    available=psutil.virtual_memory().available
    workers=min(args.workers,max(0,int((available-c['worker_ram_headroom_bytes'])//c['worker_ram_estimate_bytes'])))
    if workers<1 or available<c['minimum_free_ram_bytes']:raise RuntimeError('Insufficient available RAM')
    if not args.launch:
        print(json.dumps(dict(eligible_workers=workers,available_ram_bytes=available,launched=False)));return
    lock=HERE/'launch.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        with (HERE/'revision.log').open('ab',buffering=0) as log:
            flags=(subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP) if os.name=='nt' else 0
            child=subprocess.Popen([sys.executable,'-B',str(HERE/'run_revision.py'),'--_run','--workers',str(workers)],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=HERE,
                creationflags=flags,close_fds=True,start_new_session=os.name!='nt')
        write_json(receipt,dict(pid=child.pid,process_create_time=psutil.Process(child.pid).create_time(),workers=workers,started_utc=utc()))
        print(json.dumps(dict(started=True,pid=child.pid,workers=workers,available_ram_bytes=available)))
    finally:lock.unlink(missing_ok=True)


if __name__=='__main__':main()
