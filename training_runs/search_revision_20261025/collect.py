"""Start/resume only fresh teacher collection; --workers controls isolated simulators."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from common import (HERE, canonical, config, dataset_root, fingerprint, make_plan,
                    sha, source_receipt, summary_counts, tree_bytes, utc, verify_sources, write_json)


def reserve_fits(used, reservations, budget, reservation, free, free_reserve):
    return used+reservations+reservation<=budget and free-reservations-reservation>=free_reserve


def admitted(root, plan, source_hash):
    entries=[]
    for e in plan:
        folder=root/'episodes'/e['id'];p=folder/'result.json'
        if not p.exists():continue
        result=json.loads(p.read_text())
        if result['source_fingerprint']!=source_hash:raise ValueError('Foreign episode')
        db=folder/'episode.sqlite'
        if sha(db)!=result['database_sha256']:raise ValueError('Episode changed: '+e['id'])
        if not result['condition_valid']:raise ValueError('Invalid physical condition')
        entries.append(dict(e,frames=result['frames'],database=str(db.relative_to(root)),
            database_sha256=result['database_sha256'],outcome=result['outcome'],
            identity_labels=result['identity_labels']))
    return entries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--data-dir',help='Dataset volume/directory; default is this run/data')
    parser.add_argument('--preflight',action='store_true',help='Read-only validation; no flight')
    parser.add_argument('--_job',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args._job:
        from simulation import run_episode
        run_episode(json.loads(args._job.read_text()));return
    if not 1<=args.workers<=32:parser.error('--workers must be 1..32')
    from preflight import check
    check(physics=False)
    if args.preflight:return
    import psutil
    c=config()
    required=max(c['minimum_free_ram_bytes'],c['worker_ram_headroom_bytes']+args.workers*c['worker_ram_estimate_bytes'])
    if psutil.virtual_memory().available < required:
        raise RuntimeError(f'Requested workers require {required/1e9:.2f} GB currently available RAM; reduce --workers')
    root=dataset_root(args.data_dir)
    root.mkdir(parents=True,exist_ok=True)
    lock=root/'collection.lock'
    # PID is evidence; never silently steal a possibly active collection lock.
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(f'Collection lock exists: {lock}. Check its PID before removing a stale lock.')
    os.write(fd,canonical(dict(pid=os.getpid(),started=utc())).encode());os.close(fd)
    active={};handles=[]
    try:
        plan=make_plan();sources=source_receipt();verify_sources(sources);source_hash=fingerprint(sources)
        contract=dict(schema='drone.search.collection.v1',configuration=c,plan=plan,
                      sources=sources,source_fingerprint=source_hash)
        path=root/'collection.json'
        if path.exists():
            if json.loads(path.read_text())!=contract:raise ValueError('Data directory belongs to another source/configuration')
        else:
            if any(p.name!='collection.lock' for p in root.iterdir()):raise ValueError('New dataset directory must be empty')
            write_json(path,contract)
        (root/'episodes').mkdir(exist_ok=True)
        entries=admitted(root,plan,source_hash);completed={e['id'] for e in entries}
        pending=[e for e in plan if e['id'] not in completed]
        for e in pending:
            if (root/'episodes'/e['id']).exists():
                raise RuntimeError('Incomplete episode preserved: '+e['id']+'. Move its folder outside this data directory after inspection, then resume.')
        used=tree_bytes(root);free=shutil.disk_usage(root).free
        # Freeze available capacity at launch; do not count external free-space changes as new authorization.
        budget=min(c['dataset_budget_bytes'],used+max(0,free-c['disk_free_reserve_bytes']))
        print(canonical(dict(dataset_budget_bytes=budget,hard_total_limit=c['total_budget_bytes'],
            requested_workers=args.workers,existing_episodes=len(entries),planned=len(plan))),flush=True)
        stop_for_budget=False;failed=[]
        def save(status):
            write_json(root/'manifest.json',dict(schema='drone.search.dataset.v1',status=status,
                source_fingerprint=source_hash,source_contract_sha256=sha(path),entries=entries,
                planned_episodes=len(plan),actual=summary_counts(entries),dataset_bytes=tree_bytes(root),
                effective_dataset_budget_bytes=budget,hard_total_budget_bytes=c['total_budget_bytes'],
                old_records_admitted=0,lossless=True,all_task_frames_retained=True,updated_utc=utc(),failures=failed))
        while pending or active:
            launched=False
            for slot in range(args.workers):
                if not pending or slot in active or stop_for_budget or failed:continue
                used=tree_bytes(root)
                # Active folders already consume bytes; counting full reservations too is conservative.
                reservations=len(active)*c['episode_reservation_bytes']
                if not reserve_fits(used,reservations,budget,c['episode_reservation_bytes'],
                                    shutil.disk_usage(root).free,c['disk_free_reserve_bytes']):
                    if not active:stop_for_budget=True
                    continue
                e=pending.pop(0)
                job=root/f'job_{slot}.json'
                write_json(job,dict(entry=e,output=str(root/'episodes'/e['id']),slot=slot,source_fingerprint=source_hash))
                log=(root/f'worker_{slot}.log').open('w',encoding='utf-8');handles.append(log)
                process=subprocess.Popen([sys.executable,'-B',str(HERE/'collect.py'),'--_job',str(job)],
                    stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                active[slot]=(process,e,log);launched=True
            for slot,(process,e,log) in list(active.items()):
                code=process.poll()
                if code is None:continue
                log.close();del active[slot]
                if code:failed.append(dict(id=e['id'],returncode=code,log=f'worker_{slot}.log'))
                else:
                    result=json.loads((root/'episodes'/e['id']/'result.json').read_text())
                    entries.append(dict(e,frames=result['frames'],database=f"episodes/{e['id']}/episode.sqlite",
                        database_sha256=result['database_sha256'],outcome=result['outcome'],identity_labels=result['identity_labels']))
                    print(canonical(dict(completed=len(entries),planned=len(plan),id=e['id'],
                        outcome=result['outcome'],dataset_bytes=tree_bytes(root))),flush=True)
                save('collecting')
            if failed and not active:break
            if stop_for_budget and not active:break
            if not launched:time.sleep(.5)
        entries.sort(key=lambda e:e['ordinal'])
        status='failed' if failed else 'budget_complete' if pending else 'complete'
        save(status)
        print(canonical(dict(status=status,**summary_counts(entries))),flush=True)
        if failed:raise RuntimeError('Collection failed; inspect retained episode/error.json and worker log')
        if not entries:raise RuntimeError('No complete episode fits available capacity')
    finally:
        for process,e,log in active.values():
            if process.poll() is None:
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
                else:process.terminate()
                process.wait(timeout=15)
            log.close()
        for log in handles:
            if not log.closed:log.close()
        lock.unlink(missing_ok=True)


if __name__=='__main__':main()
