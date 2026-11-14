"""Run the canonical 20-case benchmark and keep benchmark.json current."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .common import REPO, ROOT, read, sha, utc, write
from . import student as student_actor

TEACHER = 'privileged-teacher-wave-gate-74cfb67e'
STUDENT = 'fresh-search-f62c10a2'
R15 = 'r15-archived-export-67a80a63'
RADIO = 'radio-robust-20261015-policy-bundle-44826e5a'
DEFAULT_POLICIES = (R15, RADIO)
RAM_PER_FLIGHT_GIB = 1.5


def canonical_plan():
    return read(ROOT / 'environments/suite.json')


def _inventory():
    return {row['id']: row for row in read(ROOT / 'models/inventory.json')['policies']}


def _policies():
    inventory = _inventory()
    rows = {identifier: inventory[identifier] for identifier in (R15, RADIO)}
    rows[STUDENT] = student_actor.policy()
    if TEACHER in inventory:
        rows[TEACHER] = inventory[TEACHER]
    return rows


def _ram_gib():
    try:
        import psutil
        memory = psutil.virtual_memory()
        return round(memory.available / 2**30, 2), round(memory.total / 2**30, 2)
    except Exception:
        return None, None


def _workers(requested, device):
    available, total = _ram_gib()
    by_ram = max(1, int(available // RAM_PER_FLIGHT_GIB)) if available is not None else 1
    cap = 4
    count = requested if requested else min(cap, by_ram)
    count = max(1, min(count, cap, by_ram))
    reason = (f'{available:.1f} GiB available of {total:.1f} GiB; '
              f'~{RAM_PER_FLIGHT_GIB} GiB per flight; {cap}-worker cap for {device}')
    return count, available, total, reason


def _selected_cases(plan, args):
    cases = list(plan['cases'])
    if args.case:
        wanted = set(args.case)
        cases = [case for case in cases if case['id'] in wanted]
    return cases


def _write_progress(run_dir, status, jobs, active, started, ram, problem=None):
    write(run_dir / 'progress.json', dict(
        status=status, updated_utc=utc(), elapsed_s=time.monotonic() - started,
        workers=len(active), completed=sum(job['status'] == 'completed' for job in jobs),
        planned=len(jobs), active=len(active),
        queued=sum(job['status'] == 'pending' for job in jobs),
        jobs=jobs, problem=problem, available_ram_gib=ram,
    ))


def _kill(process):
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    else:
        process.kill()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        pass


def _track():
    try:
        from .track import build as build_track
        build_track()
    except Exception as exc:
        print(f'track_error {type(exc).__name__}: {exc}', flush=True)


def _valid_result(path):
    try:
        row = read(path)
    except Exception:
        return None
    if row.get('status') == 'completed' and row.get('condition_valid') is True:
        return row
    return None


def _prepare_resume(run_dir):
    """Keep valid completed results and make every unfinished job pending again."""
    progress = read(run_dir / 'progress.json')
    record = read(run_dir / 'run.json')
    jobs = progress['jobs']
    recovery = run_dir / 'recovery' / utc().replace(':', '').replace('+', '_')
    moved = []
    completed = 0
    pending = 0
    for job in jobs:
        output = Path(job['output'])
        result = _valid_result(output / 'result.json')
        if result is not None:
            job['status'] = 'completed'
            job['outcome'] = result.get('outcome', job.get('outcome'))
            for key in ('pid', 'started_utc', 'finished_utc', 'exit_code', 'watchdog', 'error'):
                job.pop(key, None)
            completed += 1
            continue
        if output.exists():
            recovery.mkdir(parents=True, exist_ok=True)
            destination = recovery / job['id']
            if destination.exists():
                destination = recovery / f"{job['id']}-{int(time.time())}"
            shutil.move(str(output), str(destination))
            moved.append(job['id'])
        job['status'] = 'pending'
        for key in ('pid', 'started_utc', 'finished_utc', 'exit_code', 'wall_s',
                    'outcome', 'watchdog', 'error'):
            job.pop(key, None)
        pending += 1
    return record, jobs, completed, pending, moved


def run_batch(name, selected=None, cases=None, device='cuda', requested_workers=None,
              resume=False):
    if not name or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for char in name):
        raise ValueError('Run name must contain only letters, numbers, underscores or hyphens')
    plan = canonical_plan()
    known = {case['id'] for case in plan['cases']}
    unknown = set(cases or []) - known
    if unknown:
        raise ValueError('Unknown cases: ' + ', '.join(sorted(unknown)))
    run_dir = ROOT / 'runs' / name
    if resume:
        if selected or cases:
            raise ValueError('Resume uses the saved job list; do not pass --policy or --case')
        if not (run_dir / 'progress.json').exists() or not (run_dir / 'run.json').exists():
            raise ValueError(f'Cannot resume {name}: progress.json or run.json is missing')
        resume_record = read(run_dir / 'run.json')
        if resume_record.get('plan_sha256') != plan['plan_sha256']:
            raise ValueError('Saved run uses a different canonical plan')
        device = resume_record.get('inference_device', device)
        policies = _policies()
        selected = list(resume_record['policies'])
        all_cases = list(resume_record['cases'])
        workers, available, total, reason = _workers(requested_workers, device)
        context = dict(
            plan_sha256=resume_record['plan_sha256'],
            runtime_sha256=resume_record['runtime_sha256'],
            suite_sha256=resume_record['suite_sha256'],
            inference_device=device,
            control_hz=resume_record.get('control_hz', 25),
            backend=resume_record.get('backend', 'windows_mujoco_px4_wasm'),
            benchmark=resume_record.get('benchmark', 'aerodock-20-wave-gate-3c2b501'),
            workers=workers,
        )
        resume_record, jobs, completed_count, pending_count, moved = _prepare_resume(run_dir)
    else:
        if run_dir.exists():
            raise ValueError(f'Run already exists: {name}; pass --resume to continue it')
        policies = _policies()
        selected = selected or list(DEFAULT_POLICIES)
        if len(set(selected)) != len(selected):
            raise ValueError('Duplicate policy selection')
        for identifier in selected:
            if identifier not in policies:
                raise ValueError('Unknown policy: ' + identifier)
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / 'jobs').mkdir()
        (run_dir / 'logs').mkdir()

        class Args:
            pass
        args = Args()
        args.case = cases

        workers, available, total, reason = _workers(requested_workers, device)
        context = dict(
            plan_sha256=plan['plan_sha256'],
            runtime_sha256=sha(ROOT / 'environments/runtime.json'),
            suite_sha256=sha(ROOT / 'environments/suite.json'),
            inference_device=device,
            control_hz=25,
            backend='windows_mujoco_px4_wasm',
            benchmark='aerodock-20-wave-gate-3c2b501',
            workers=workers,
        )

        jobs = []
        all_cases = []
        index = 0
        for identifier in selected:
            for case in _selected_cases(plan, args):
                index += 1
                destination = run_dir / identifier / case['id']
                job_path = run_dir / 'jobs' / f'{index:02d}.json'
                job = dict(id=f'{index:02d}', policy_id=identifier, case_id=case['id'],
                           output=str(destination), job=str(job_path),
                           log=str(run_dir / 'logs' / f'{index:02d}.log'), status='pending')
                write(job_path, dict(policy=policies[identifier], case=case,
                                     output=str(destination), context=context))
                jobs.append(job)
                if case['id'] not in all_cases:
                    all_cases.append(case['id'])
        if not jobs:
            raise ValueError('No cases selected')
        completed_count = 0
        pending_count = len(jobs)
        moved = []

    run_record = dict(
        id=name, created_utc=resume_record.get('created_utc') if resume else utc(),
        plan_sha256=context['plan_sha256'],
        runtime_sha256=context['runtime_sha256'], suite_sha256=context['suite_sha256'],
        inference_device=device, workers=workers, available_ram_gib=available,
        total_ram_gib=total, workers_reason=reason, policies=selected,
        cases=all_cases, jobs=jobs, training_eligible=False, status='running',
        evidence_reuse='teacher 20/20 and student 18/20 already recorded; this run adds the R15 and radio-robust canonical-plan flights.',
    )
    if resume:
        run_record['resumed_utc'] = utc()
        run_record['resume_count'] = int(resume_record.get('resume_count', 0)) + 1
    write(run_dir / 'run.json', run_record)
    write(run_dir / 'progress.json', dict(
        status='running', updated_utc=utc(), elapsed_s=0., workers=workers,
        completed=completed_count, planned=len(jobs), active=0, queued=pending_count,
        jobs=jobs, problem=None, available_ram_gib=available,
    ))
    if resume:
        print(f'Resuming {name}: {completed_count} completed, {pending_count} pending; '
              f'{workers} workers ({reason}).', flush=True)
        if moved:
            print('Quarantined partial outputs: ' + ', '.join(moved), flush=True)
    else:
        print(f'{len(jobs)} flights, {workers} workers ({reason}).', flush=True)

    active = {}
    trouble = None
    started = time.monotonic()
    last_update = 0.
    try:
        while any(job['status'] == 'pending' for job in jobs) or active:
            for key, item in list(active.items()):
                process, job = item['process'], item['job']
                if process.poll() is None:
                    if time.monotonic() - item['began'] > 3600:
                        _kill(process)
                        job['watchdog'] = 'Owned flight exceeded one hour wall time'
                    else:
                        continue
                item['log'].close()
                job['finished_utc'] = utc()
                job['exit_code'] = process.returncode
                job['wall_s'] = time.monotonic() - item['began']
                result_path = Path(job['output']) / 'result.json'
                row = read(result_path) if result_path.exists() else {}
                good = (process.returncode == 0 and row.get('status') == 'completed'
                        and row.get('condition_valid') is True)
                job['status'] = 'completed' if good else 'needs_attention'
                job['outcome'] = row.get('outcome', row.get('error', 'Missing result; see log'))
                if not good:
                    trouble = dict(job=job['id'], case=job['case_id'],
                                   error=job['outcome'])
                del active[key]
                print('Finished', job['id'], job['case_id'], job['status'], job['outcome'], flush=True)
                _write_progress(run_dir, 'needs_attention' if trouble else 'running',
                                jobs, active, started, _ram_gib()[0], trouble)
                _track()

            if trouble is None:
                while len(active) < workers:
                    job = next((item for item in jobs if item['status'] == 'pending'), None)
                    if job is None:
                        break
                    available_now = _ram_gib()[0]
                    if available_now is not None and available_now < 1.5:
                        trouble = dict(error='Less than 1.5 GiB RAM free; evidence preserved')
                        break
                    log = open(job['log'], 'wb')
                    process = subprocess.Popen(
                        [sys.executable, '-B', '-u', '-m', 'benchmark', '_trial',
                         '--job', job['job']],
                        cwd=str(REPO), stdin=subprocess.DEVNULL, stdout=log,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    job.update(status='running', pid=process.pid, started_utc=utc())
                    active[job['id']] = dict(process=process, job=job, began=time.monotonic(), log=log)
                    print('Started', job['id'], job['policy_id'], job['case_id'], flush=True)
                    _write_progress(run_dir, 'running', jobs, active, started, _ram_gib()[0])
                    time.sleep(1)

            now = time.monotonic()
            if now - last_update >= 10 or not active:
                _write_progress(run_dir, 'needs_attention' if trouble else 'running',
                                jobs, active, started, _ram_gib()[0], trouble)
                last_update = now
            if trouble and not active:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        for item in list(active.values()):
            _kill(item['process'])
            try:
                item['log'].close()
            except Exception:
                pass
        _write_progress(run_dir, 'interrupted', jobs, {}, started, _ram_gib()[0],
                        dict(error='Interrupted by user'))
        raise

    status = 'needs_attention' if trouble else 'completed'
    previous_record = read(run_dir / 'run.json')
    final_record = dict(
        id=name, created_utc=previous_record['created_utc'],
        plan_sha256=plan['plan_sha256'], runtime_sha256=context['runtime_sha256'],
        suite_sha256=context['suite_sha256'], inference_device=device, workers=workers,
        available_ram_gib=available, total_ram_gib=total, workers_reason=reason,
        policies=selected, cases=all_cases, jobs=jobs, training_eligible=False,
        status=status, evidence_reuse='teacher 20/20 and student 18/20 already recorded; '
                                      'this run adds the R15 and radio-robust canonical-plan flights.',
    )
    for key in ('resumed_utc', 'resume_count'):
        if key in previous_record:
            final_record[key] = previous_record[key]
    write(run_dir / 'run.json', final_record)
    _write_progress(run_dir, status, jobs, {}, started, _ram_gib()[0], trouble)
    _track()
    print('Batch finished:', status, flush=True)
    return 0 if trouble is None else 2


def trial(job_path):
    job = read(job_path)
    plan = canonical_plan()
    expected = next(case for case in plan['cases'] if case['id'] == job['case']['id'])
    if expected != job['case']:
        raise ValueError('Job case differs from the canonical suite')
    from . import runner
    from . import routes
    import benchmark.actors as actors

    original_setup = runner.setup_scene
    runner.setup_scene = lambda env, case, output: routes.install(env, case, output, original_setup)
    try:
        if job['policy']['id'] == TEACHER:
            from landing_training.privileged_teacher import VisibleBoatOracle
            from landing_training.wave_teacher import WavePrivilegedTeacher

            class WaveReference(actors.PrivilegedReference):
                def reset(self):
                    self.teacher = WavePrivilegedTeacher(self.env)
                    self.oracle = VisibleBoatOracle(self.env, self.groups)

            actors.PrivilegedReference = WaveReference
        if 'fresh_search_identity' in job['policy']:
            student_actor.install(runner, dict(job['policy'],
                                               device=job['context'].get('inference_device', 'cpu')),
                                  job['output'])
        runner.run_trial(job['policy'], job['case'], job['output'], job['context'])
    finally:
        output = Path(job['output'])
        if (output / 'result.json').exists():
            try:
                from .rollout_digest import generate_episode_digest
                generate_episode_digest(output, overwrite=True)
            except Exception as exc:
                (output / 'diagnostic_digest_error.txt').write_text(
                    f'{type(exc).__name__}: {exc}\n', encoding='utf-8')
                print('diagnostic_digest_error', exc, flush=True)
        runner.setup_scene = original_setup


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run', help='Launch real MuJoCo/PX4 flights')
    run.add_argument('--name', required=True, help='New run directory name')
    run.add_argument('--workers', type=int, help='Worker cap; defaults to a RAM-based value')
    run.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    run.add_argument('--policy', nargs='+', help='Policy ids; defaults to R15 and radio-robust')
    run.add_argument('--case', nargs='+', help='Optional canonical case ids')
    run.add_argument('--resume', action='store_true',
                     help='Continue a paused/interrupted --name, keeping completed results')
    track = commands.add_parser('track', help='Rebuild benchmark.json from recorded evidence')
    digest = commands.add_parser('digest', help='Rebuild diagnostic digests for recorded episodes')
    digest.add_argument('paths', nargs='+')
    digest.add_argument('--overwrite', action='store_true')
    digest.add_argument('--quiet', action='store_true')
    worker = commands.add_parser('_trial', help=argparse.SUPPRESS)
    worker.add_argument('--job', required=True)
    args = parser.parse_args(argv)

    if args.command == 'track':
        from .track import main as track_main
        return track_main()
    if args.command == 'digest':
        from .rollout_digest import main as digest_main
        return digest_main(args.paths + (['--overwrite'] if args.overwrite else [])
                           + (['--quiet'] if args.quiet else []))
    if args.command == '_trial':
        trial(args.job)
        return 0
    return run_batch(args.name, args.policy, args.case, args.device, args.workers,
                     resume=args.resume)


if __name__ == '__main__':
    raise SystemExit(main())
