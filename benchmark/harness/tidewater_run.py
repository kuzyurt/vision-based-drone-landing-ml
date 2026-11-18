"""Fly selected canonical cases with the current Tidewater student stack.

    python -B -m benchmark.harness.tidewater_run run --name NAME --case ID [ID ...]

Writes to benchmark/runs/NAME like run.py does (working data, not canonical
evidence) and never touches benchmark.json.  The pinned run.py is imported, not
edited: its student hook is swapped for student_tidewater in this process only.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from .common import REPO, ROOT, read, sha, utc, write
from . import run as bench
from . import student_tidewater


def build(name, case_ids, device):
    plan = bench.canonical_plan()
    known = {c['id'] for c in plan['cases']}
    unknown = set(case_ids) - known
    if unknown:
        raise SystemExit('Unknown cases: ' + ', '.join(sorted(unknown)))
    run_dir = ROOT / 'runs' / name
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / 'jobs').mkdir()
    (run_dir / 'logs').mkdir()
    pol = student_tidewater.policy()
    context = dict(plan_sha256=plan['plan_sha256'], runtime_sha256=sha(ROOT / 'definition/runtime.json'),
                   suite_sha256=sha(ROOT / 'definition/suite.json'), inference_device=device,
                   control_hz=25, backend='windows_mujoco_px4_wasm',
                   benchmark='aerodock-20-wave-gate-3c2b501', workers=len(case_ids))
    jobs = []
    for index, cid in enumerate(case_ids, 1):
        case = next(c for c in plan['cases'] if c['id'] == cid)
        job_path = run_dir / 'jobs' / f'{index:02d}.json'
        write(job_path, dict(policy=pol, case=case, output=str(run_dir / pol['id'] / cid), context=context))
        jobs.append(dict(id=f'{index:02d}', case_id=cid, job=str(job_path),
                         log=str(run_dir / 'logs' / f'{index:02d}.log'), output=str(run_dir / pol['id'] / cid)))
    write(run_dir / 'run.json', dict(id=name, created_utc=utc(), policy=pol['id'], cases=case_ids,
                                     jobs=jobs, training_eligible=False,
                                     note='Tidewater student stack flown natively; working data.'))
    return run_dir, jobs


def trial(job_path):
    bench.student_actor = student_tidewater
    bench.trial(job_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run')
    r.add_argument('--name', required=True)
    r.add_argument('--case', nargs='+', help='canonical case ids; default: all 20')
    r.add_argument('--workers', type=int, default=3, help='flights at the same time')
    r.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    t = sub.add_parser('_trial')
    t.add_argument('--job', required=True)
    args = parser.parse_args(argv)
    if args.command == '_trial':
        trial(args.job)
        return 0
    cases = args.case or [c['id'] for c in bench.canonical_plan()['cases']]
    run_dir, jobs = build(args.name, cases, args.device)
    pending, active, code = list(jobs), [], 0
    while pending or active:
        while pending and len(active) < args.workers:
            job = pending.pop(0)
            log = open(job['log'], 'wb')
            proc = subprocess.Popen(
                [sys.executable, '-B', '-u', '-m', 'benchmark.harness.tidewater_run', '_trial', '--job', job['job']],
                cwd=str(REPO), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            active.append((job, log, proc))
            print('Started', job['id'], job['case_id'], flush=True)
            time.sleep(1)
        for item in list(active):
            job, log, proc = item
            if proc.poll() is None:
                continue
            log.close()
            active.remove(item)
            result = Path(job['output']) / 'result.json'
            row = read(result) if result.exists() else {}
            print('Finished', job['id'], job['case_id'], 'exit', proc.returncode,
                  row.get('outcome', 'no result'), flush=True)
            code = code or proc.returncode
        time.sleep(2)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
