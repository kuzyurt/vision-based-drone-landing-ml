"""Three isolated workers for the remaining sixteen teacher flights.

This reuses the prepared teacher_four_20261104 plan and the final wave-gate
teacher. The four already-completed targeted flights are not rerun; the full
twenty-case score is assembled separately from those results and this run.
"""
import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

import psutil

from benchmark.common import REPO, ROOT, read, write, sha, utc
from benchmark.scoring import aggregate, strict_landing
from .run import policy
from .spec import HERE, RUN_CASES, verify

WORKERS = 3
MODULE = 'benchmark.revisions.teacher_four_20261104'


def prepare(name):
    from benchmark.runner import preflight

    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
        raise ValueError('Unsafe run name')
    plan = verify()
    teacher = policy()
    errors = preflight(teacher)
    if errors:
        raise RuntimeError(errors)
    selected = [case for case in plan['cases'] if case['id'] not in RUN_CASES]
    if len(selected) != 16:
        raise RuntimeError('Expected 16 remaining cases; got %d' % len(selected))

    run = HERE / 'runs' / name
    run.mkdir(parents=True, exist_ok=False)
    (run / 'jobs').mkdir()
    (run / 'receipts').mkdir()
    for filename in ('suite.json', 'source_receipts.json', 'policy_id.json', 'teacher_policy_wave.json'):
        shutil.copy2(HERE / filename, run / 'receipts' / filename)
    operations = [dict(path=str(p.relative_to(REPO)).replace('\\', '/'), sha256=sha(p))
                  for p in sorted(Path(__file__).parent.glob('*.py'))]
    for item in operations:
        shutil.copy2(REPO / item['path'], run / 'receipts' / Path(item['path']).name)
    context = dict(
        plan_sha256=plan['plan_sha256'],
        runtime_sha256=sha(ROOT / 'environments/runtime.json'),
        revision_receipts_sha256=sha(HERE / 'source_receipts.json'),
        inference_device='cpu',
        control_hz=25,
        backend='windows_mujoco_px4',
        scenario_revision='teacher_four_20261104',
        workers=WORKERS,
        machine=os.environ.get('COMPUTERNAME', ''),
        platform=sys.platform,
        python=sys.version,
        operations_sources=operations,
        reused_cases=list(RUN_CASES),
    )
    jobs = []
    for index, case in enumerate(selected, 1):
        key = f'{index:02d}'
        folder = run / 'teacher' / case['id']
        job_path = run / 'jobs' / (key + '.json')
        write(job_path, dict(policy=teacher, case=case, output=str(folder), context=context))
        jobs.append(dict(id=key, policy_id=teacher['id'], case_id=case['id'],
                         output=str(folder), job=str(job_path),
                         log=str(job_path.with_suffix('.log')), status='pending'))
    write(run / 'run.json', dict(
        id=name, created_utc=utc(), workers=WORKERS, jobs=jobs, context=context,
        policy_id=teacher['id'], policy_identity_sha256=teacher['identity_sha256'],
        planned_cases=len(jobs), reused_cases=list(RUN_CASES), training_eligible=False,
        historical_results_reused=False, operations_sources=operations,
        note='Remaining sixteen teacher_four cases; the four completed targeted cases are reused only in the full-20 aggregation.',
    ))
    write(run / 'progress.json', dict(
        status='prepared', updated_utc=utc(), workers=WORKERS,
        completed=0, planned=len(jobs), active=0, queued=len(jobs), jobs=jobs,
    ))
    print(run, flush=True)


def tail_progress(folder):
    path = Path(folder) / 'steps.jsonl'
    if not path.exists():
        return dict(task_s=0., frames=0, phase='preparing')
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - 120000))
        lines = stream.read().splitlines()
    for line in reversed(lines):
        try:
            import json
            row = json.loads(line)
            if 'observation' in row:
                return dict(task_s=row['task_s'], frames=round(row['task_s'] * 25) + 1,
                            phase=row.get('diagnostics', {}).get('control_phase'))
        except (ValueError, KeyError):
            pass
    return dict(task_s=0., frames=0, phase='preparing')


def report(run, manifest, jobs, status):
    plan = read(run / 'receipts/suite.json')
    results = []
    for job in jobs:
        path = Path(job['output']) / 'result.json'
        if path.exists():
            results.append(read(path))
    score = aggregate(plan, results)
    summary = dict(
        updated_utc=utc(), status=status,
        context=manifest['context'], policy_id=manifest['policy_id'],
        policy_identity_sha256=manifest['policy_identity_sha256'],
        training_eligible=False, historical_results_reused=False,
        planned=len(jobs), completed=sum(j['status'] == 'completed' for j in jobs),
        strict_landings=sum(strict_landing(r) and r.get('condition_valid') is True for r in results),
        results=results, score=score,
    )
    write(run / 'summary.json', summary)
    lines = [
        '# Wave-gate teacher / remaining sixteen flights', '',
        f'Status: **{status}**. {manifest["workers"]} isolated workers; {len(jobs)} planned flights.', '',
        '| Case | Outcome | Mission seconds | Verified acquisition | Landing |',
        '|---|---|---:|---:|---|',
    ]
    for job in jobs:
        row = next((r for r in results if r['case_id'] == job['case_id']), {})
        outcome = row.get('outcome', row.get('error', job['status']))
        if row and not row.get('condition_valid'):
            outcome = 'INVALID: ' + outcome
        lines.append(f"| {job['case_id']} | {outcome} | {row.get('mission_time_s', '')} | "
                     f"{row.get('verified_acquisition_s', '')} | {strict_landing(row)} |")
    lines += ['', f'Strict landings: **{summary["strict_landings"]} / {len(jobs)}** for this sixteen-case run.',
              'This is not the full twenty-case score; the four completed targeted flights are combined separately.']
    temporary = run / 'RESULTS.md.tmp'
    temporary.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    temporary.replace(run / 'RESULTS.md')


def execute(run):
    manifest = read(run / 'run.json')
    verify()
    with (run / 'pool.lock').open('x') as lock:
        lock.write(str(os.getpid()))
    jobs = manifest['jobs']
    active = {}
    trouble = None
    started = time.monotonic()
    last_update = 0.
    python = str(Path(sys.executable).with_name('python.exe'))
    awake = ctypes.windll.kernel32.SetThreadExecutionState
    awake(0x80000001)
    try:
        while any(j['status'] == 'pending' for j in jobs) or active:
            for key, item in list(active.items()):
                child, job = item['process'], item['job']
                if child.poll() is None:
                    if time.monotonic() - item['began'] > 3600:
                        subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW, check=False)
                        child.wait(timeout=15)
                        job['watchdog'] = 'Owned flight exceeded one hour wall time'
                    else:
                        continue
                job['finished_utc'] = utc()
                job['exit_code'] = child.returncode
                job['wall_s'] = time.monotonic() - item['began']
                result = Path(job['output']) / 'result.json'
                row = read(result) if result.exists() else {}
                good = child.returncode == 0 and row.get('status') == 'completed' and row.get('condition_valid') is True
                job['status'] = 'completed' if good else 'needs_attention'
                job['outcome'] = row.get('outcome', row.get('error', 'Missing result; see log'))
                if not good:
                    trouble = dict(job=job['id'], error=job['outcome'])
                del active[key]
                print('Finished', job['id'], job['status'], job['outcome'], flush=True)
                report(run, manifest, jobs, 'needs_attention' if trouble else 'running')
            if trouble is None:
                while len(active) < manifest['workers']:
                    job = next((j for j in jobs if j['status'] == 'pending'), None)
                    if job is None:
                        break
                    if psutil.virtual_memory().available < 1.5 * 2**30:
                        trouble = dict(error='Less than 1.5 GiB RAM free; evidence preserved')
                        break
                    if Path(job['output']).exists():
                        raise RuntimeError('Refusing to overwrite existing flight: ' + job['output'])
                    with Path(job['log']).open('xb') as log:
                        child = subprocess.Popen(
                            [python, '-B', '-u', '-m', MODULE, '_trial', '--job', job['job']],
                            cwd=ROOT.parent, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW)
                    job.update(status='running', pid=child.pid,
                               created=psutil.Process(child.pid).create_time(), started_utc=utc())
                    active[job['id']] = dict(process=child, job=job, began=time.monotonic())
                    print('Started', job['id'], job['policy_id'], job['case_id'], flush=True)
                    time.sleep(3)
            now = time.monotonic()
            if now - last_update >= 15 or not active:
                for item in active.values():
                    item['job'].update(tail_progress(item['job']['output']))
                    item['job']['wall_s'] = now - item['began']
                completed = sum(j['status'] == 'completed' for j in jobs)
                status = 'needs_attention' if trouble else 'completed' if completed == len(jobs) else 'running'
                write(run / 'progress.json', dict(
                    status=status, updated_utc=utc(), elapsed_s=now - started,
                    workers=manifest['workers'], completed=completed, planned=len(jobs),
                    active=len(active), queued=sum(j['status'] == 'pending' for j in jobs),
                    jobs=jobs, problem=trouble,
                    available_ram_gib=psutil.virtual_memory().available / 2**30,
                    disk_free_gib=psutil.disk_usage(str(REPO)).free / 2**30,
                ))
                report(run, manifest, jobs, status)
                last_update = now
            if trouble and not active:
                break
            time.sleep(1)
    except BaseException:
        write(run / 'pool_failure.json', dict(
            utc=utc(), traceback=traceback.format_exc(),
            active_pids=[x['process'].pid for x in active.values()], evidence_preserved=True))
        raise
    finally:
        awake(0x80000000)
    print('Batch finished:', 'needs_attention' if trouble else 'completed', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'execute'])
    parser.add_argument('--name')
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.name)
    else:
        args.run.mkdir(exist_ok=True)
        with (args.run / 'pool.log').open('a', encoding='utf-8', buffering=1) as log:
            sys.stdout = sys.stderr = log
            execute(args.run)


if __name__ == '__main__':
    main()
