"""One scheduled check, at most one detached collector; never auto-trains."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
import subprocess
import sys
import time
import psutil
from common import HERE, canonical, config, dataset_root, sha, utc, write_json,verify_sources


def choose_workers(available, c=None):
    c=config() if c is None else c
    if available<c['minimum_free_ram_bytes']:return 0
    capacity=int((available-c['worker_ram_headroom_bytes'])//c['worker_ram_estimate_bytes'])
    return max(0,min(3,capacity))


def owned_alive(receipt):
    try:
        process=psutil.Process(receipt['pid'])
        return (abs(process.create_time()-receipt['process_create_time'])<.01
                and any(str(HERE/'collect.py').lower() in arg.lower() for arg in process.cmdline()))
    except (psutil.NoSuchProcess,psutil.AccessDenied,KeyError):return False


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--launch',action='store_true',help='Launch only within the authorized morning window')
    p.add_argument('--data-dir')
    args=p.parse_args()
    c=config();root=dataset_root(args.data_dir)
    available=psutil.virtual_memory().available
    workers=choose_workers(available)
    report=dict(checked_utc=utc(),available_ram_bytes=available,selected_workers=workers,
                started=False,data_directory=str(root))
    process_file=HERE/'collector_process.json'
    if process_file.exists() and owned_alive(json.loads(process_file.read_text())):
        report['status']='already_running'
    elif (root/'collection.lock').exists():
        report['status']='collection_lock_present'
    elif (root/'manifest.json').exists() and json.loads((root/'manifest.json').read_text())['status'] in ('complete','budget_complete','failed'):
        report['status']='existing_collection_'+json.loads((root/'manifest.json').read_text())['status']
    elif workers==0:
        report['status']='waiting_for_ram'
    else:
        report['status']='eligible'
    if args.launch and report['status']=='eligible':
        local=datetime.now().astimezone()
        if local.strftime('%Y-%m-%d')!='2026-10-25' or not 6<=local.hour<=8:
            raise RuntimeError('Automatic launch is authorized only on 25 October 2026 at the morning checks (06–08 local)')
        validation=json.loads((HERE/'validation.json').read_text())
        if validation['status']!='passed':raise RuntimeError('Pipeline has not passed validation')
        verify_sources(validation['source_receipt'])
        for name,expected in validation['run_file_hashes'].items():
            if sha(HERE/name)!=expected:raise RuntimeError('Run changed since validation: '+name)
        cleanup=json.loads((HERE/'cleanup_receipt.json').read_text())
        if cleanup['status'] not in ('completed','blocked_by_automatic_review'):
            raise RuntimeError('Old-data cleanup has not been audited')
        report['old_data_cleanup_status']=cleanup['status']
        # Exclusive launch reservation closes the race before collection.lock appears.
        launch_lock=HERE/'wake_launch.lock'
        fd=os.open(launch_lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
        os.close(fd)
        try:
            with (HERE/'scheduled_collection.log').open('ab',buffering=0) as log:
                command=[sys.executable,'-B',str(HERE/'collect.py'),'--workers',str(workers),'--data-dir',str(root)]
                flags=(subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP) if os.name=='nt' else 0
                process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                    cwd=HERE,creationflags=flags,close_fds=True,start_new_session=os.name!='nt')
            receipt=dict(pid=process.pid,process_create_time=psutil.Process(process.pid).create_time(),
                command=command,started_utc=utc(),available_ram_bytes=available,workers=workers)
            write_json(process_file,receipt)
            report.update(status='started',started=True,pid=process.pid)
        finally:launch_lock.unlink(missing_ok=True)
    write_json(HERE/'wake_status.json',report)
    print(canonical(report))


if __name__=='__main__':main()
