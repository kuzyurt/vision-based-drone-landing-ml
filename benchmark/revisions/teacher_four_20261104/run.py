"""Run only the four failed teacher cases with the additive wave-aware actor."""
import subprocess
import sys
import time
from pathlib import Path

from benchmark.common import ROOT, read, write, sha, utc
from .spec import HERE, RUN_CASES, verify


def policy():
    identifier = read(HERE / 'policy_id.json')['policy_id']
    inventory = read(ROOT / 'models/inventory.json')
    return next(row for row in inventory['policies'] if row['id'] == identifier)


def cases(plan, selected_ids=None):
    found = {case['id']: case for case in plan['cases']}
    requested = tuple(selected_ids or RUN_CASES)
    missing = [case_id for case_id in requested if case_id not in found]
    if missing:
        raise ValueError('Prepared suite is missing: ' + ', '.join(missing))
    return [found[case_id] for case_id in requested]


def trial(job_path):
    job = read(job_path)
    plan = verify()
    if job['context']['plan_sha256'] != plan['plan_sha256']:
        raise ValueError('Different revision plan')
    expected = next(case for case in plan['cases'] if case['id'] == job['case']['id'])
    if expected != job['case']:
        raise ValueError('Job case differs from the prepared suite')
    if job['policy']['id'] != read(HERE / 'policy_id.json')['policy_id']:
        raise ValueError('Different registered teacher policy')

    import benchmark.actors as actors
    from landing_training.privileged_teacher import VisibleBoatOracle
    from landing_training.wave_teacher import WavePrivilegedTeacher

    class WaveReference(actors.PrivilegedReference):
        def reset(self):
            self.teacher = WavePrivilegedTeacher(self.env)
            self.oracle = VisibleBoatOracle(self.env, self.groups)

    actors.PrivilegedReference = WaveReference
    from benchmark import runner
    from .routes import install

    original = runner.setup_scene
    runner.setup_scene = lambda env, case, output: install(env, case, output, original)
    runner.run_trial(job['policy'], job['case'], job['output'], job['context'])


def run_command(name, selected_ids=None):
    if not name or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for char in name):
        raise ValueError('Unsafe run name')
    plan = verify()
    selected = cases(plan, selected_ids)
    teacher = policy()
    from benchmark.runner import preflight
    errors = preflight(teacher)
    if errors:
        raise RuntimeError(errors)
    output = HERE / 'runs' / name
    output.mkdir(parents=True, exist_ok=False)
    context = dict(
        plan_sha256=plan['plan_sha256'],
        runtime_sha256=sha(ROOT / 'environments/runtime.json'),
        revision_receipts_sha256=sha(HERE / 'source_receipts.json'),
        inference_device='cpu',
        control_hz=25,
        backend='windows_mujoco_px4',
        scenario_revision='teacher_four_20261104',
    )
    write(output / 'run.json', dict(
        created_utc=utc(),
        context=context,
        policy=teacher['id'],
        cases=[case['id'] for case in selected],
        requested_cases=list(selected_ids or RUN_CASES),
        targeted_rerun_of='privileged-teacher-platform-aligned-7ac0a6ff',
        training_eligible=False,
        note='Only the four failed teacher cases. Historical 25/26 October results are not overwritten.',
    ))
    results = []
    for case in selected:
        destination = output / teacher['id'] / case['id']
        job = output / 'next_job.json'
        write(job, dict(policy=teacher, case=case, output=str(destination), context=context))
        began = time.perf_counter()
        with (output / 'worker.log').open('a') as log:
            process = subprocess.Popen(
                [sys.executable, '-B', '-u', '-m',
                 'benchmark.revisions.teacher_four_20261104', '_trial', '--job', str(job)],
                cwd=ROOT.parent, stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                process.wait(timeout=3600)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=log, stderr=subprocess.STDOUT, check=False,
                               creationflags=subprocess.CREATE_NO_WINDOW)
                process.wait(timeout=15)
                raise
        result_path = destination / 'result.json'
        if not result_path.exists():
            raise RuntimeError('Worker exited without evidence; see worker.log')
        result = read(result_path)
        result['wall_s'] = time.perf_counter() - began
        results.append(result)
        write(output / 'summary.json', dict(
            context=context,
            policy=teacher['id'],
            training_eligible=False,
            results=results,
        ))
        print(teacher['id'], case['id'], result.get('outcome', result['status']), flush=True)
        if process.returncode or result['status'] != 'completed' or not result['condition_valid']:
            raise SystemExit('Stopped on infrastructure or scenario-envelope error; evidence retained.')
    print('Finished the four targeted flights; this is a separate revision.', flush=True)
    return results
