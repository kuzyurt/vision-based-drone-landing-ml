"""Explicit subcommands: prepare/plan/preflight/report never launch a trial."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from .common import ROOT, fingerprint, read, sha, utc, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ['prepare', 'plan', 'report', 'list']:
        commands.add_parser(command)
    check = commands.add_parser('preflight')
    check.add_argument('--policy', required=True)
    run = commands.add_parser('run', help='LAUNCH real MuJoCo/PX4 flights; never implicit')
    run.add_argument('--policy', nargs='+', required=True)
    run.add_argument('--case', nargs='+', help='Diagnostic subset; cannot produce a complete overall score')
    run.add_argument('--category', choices=['landing','wind','waves','acquisition','combined'])
    run.add_argument('--map', choices=['island','beach','city','gravel','rock'])
    run.add_argument('--name', help='New run directory name; existing results are never overwritten')
    run.add_argument('--device', choices=['cpu','cuda'], default='cpu', help='Same inference device for every learned actor in this run')
    trial = commands.add_parser('_trial', help=argparse.SUPPRESS)
    trial.add_argument('--job', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        from .prepare import prepare
        prepare()
        return
    if args.command == 'plan':
        from .suite import main as plan
        plan()
        return
    if args.command == 'report':
        from .report import build_report
        build_report()
        return
    if args.command == '_trial':
        from .runner import run_trial
        job = read(args.job)
        run_trial(job['policy'], job['case'], job['output'], job['context'])
        return
    inventory = read(ROOT / 'models/inventory.json')
    policies = {p['id']: p for p in inventory['policies']}
    if args.command == 'list':
        for item in policies.values():
            print(item['id'], '|', item['role'], '|', 'available' if item['available'] else 'missing: '+', '.join(item['missing']))
        print(f"\n{len(inventory['weights'])} loose files / {inventory['unique_weight_count']} unique weight hashes; see benchmark/models/INVENTORY.md")
        return
    from .runner import preflight
    selected = [args.policy] if isinstance(args.policy, str) else args.policy
    for policy_id in selected:
        if policy_id not in policies:
            parser.error('Unknown policy id: '+policy_id+'; use python -m benchmark list')
        errors = preflight(policies[policy_id])
        if errors:
            print(policy_id+': preflight failed\n  '+'\n  '.join(errors))
            raise SystemExit(2)
    if args.command == 'preflight':
        print('Receipt/dependency checks passed. No model or simulator executed. Flight compatibility is still untested.')
        return
    if len(set(selected)) != len(selected):
        parser.error('Duplicate policy selection')
    plan = read(ROOT / 'environments/suite.json')
    from .suite import build_plan
    if plan != build_plan():
        parser.error('Suite was edited or is stale; prepare a reviewed snapshot before running')
    requested = set(args.case or [])
    known = {c['id'] for c in plan['cases']}
    if requested-known:
        parser.error('Unknown cases: '+', '.join(sorted(requested-known)))
    cases = [c for c in plan['cases'] if (not requested or c['id'] in requested)
             and (not args.category or c['category'] == args.category) and (not args.map or c['map'] == args.map)]
    if not cases:
        parser.error('No cases selected')
    if len(cases) > plan['max_flights_per_policy']:
        parser.error(f"Suite limit is {plan['max_flights_per_policy']} flights per policy")
    name = args.name or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
        parser.error('Run name must contain only letters, numbers, underscores or hyphens')
    output = ROOT / 'runs' / name
    output.mkdir(parents=True, exist_ok=False)
    awake_requested=False
    if os.name=='nt':
        import ctypes
        import atexit
        awake=ctypes.windll.kernel32.SetThreadExecutionState
        awake.argtypes=[ctypes.c_uint];awake.restype=ctypes.c_uint
        awake_requested=bool(awake(0x80000001))
        atexit.register(awake,0x80000000)
    packages = {}
    for package in ['mujoco','torch','torchvision','numpy','scipy','pymavlink','opencv-python','Pillow']:
        try: packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: packages[package] = 'unknown'
    accelerator = None
    if args.device == 'cuda':
        # Do not retain another Torch/CUDA context alongside the isolated worker.
        info = subprocess.check_output([sys.executable, '-B', '-c',
            "import torch,json; assert torch.cuda.is_available(), 'CUDA unavailable'; "
            "print(json.dumps(dict(name=torch.cuda.get_device_name(0),cuda_version=torch.version.cuda)))"],
            text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        accelerator = json.loads(info)
    context = dict(plan_sha256=plan['plan_sha256'], runtime_sha256=sha(ROOT / 'environments/runtime.json'),
                   machine=platform.node(), platform=platform.platform(), python=sys.version,
                   packages=packages, inference_device=args.device, accelerator=accelerator, control_hz=25, backend='windows_mujoco_px4_wasm',
                   system_awake_requested=awake_requested)
    write(output / 'run.json', dict(id=name, created_utc=utc(), policies=selected,
                                  cases=[c['id'] for c in cases], context=context, training_eligible=False))
    print(f'Launching {len(cases)*len(selected)} sequential flights. Each trial has a 240 s simulated mission budget.', flush=True)
    for policy_id in selected:
        for case in cases:
            destination = output / policy_id / case['id']
            job = output / 'next_job.json'
            write(job, dict(policy=policies[policy_id], case=case, output=str(destination), context=context))
            with (output / 'worker.log').open('a', encoding='utf-8') as log:
                worker = subprocess.Popen([sys.executable, '-B', '-m', 'benchmark', '_trial', '--job', str(job)],
                        cwd=ROOT.parent, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                try:
                    worker.wait(timeout=3600)
                    process = worker
                except subprocess.TimeoutExpired:
                    # A transport/render hang is an infrastructure failure, never a scored timeout.
                    subprocess.run(['taskkill', '/PID', str(worker.pid), '/T', '/F'],
                        stdout=log, stderr=subprocess.STDOUT, check=False,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                    worker.wait(timeout=15)
                    process = None
                except KeyboardInterrupt:
                    subprocess.run(['taskkill', '/PID', str(worker.pid), '/T', '/F'],
                        stdout=log, stderr=subprocess.STDOUT, check=False,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                    worker.wait(timeout=15)
                    raise
            result_path = destination / 'result.json'
            if not result_path.exists():
                write(result_path, dict(schema='aerodock.benchmark.trial.v1', policy_id=policy_id,
                    policy_identity_sha256=policies[policy_id]['identity_sha256'], case_id=case['id'], context=context,
                    status='infrastructure_error', condition_valid=False,
                    error='Worker wall watchdog expired' if process is None else 'Worker exited without a result',
                    training_eligible=False))
            from .report import build_report
            build_report()
            result = read(result_path)
            print(policy_id, case['id'], result.get('outcome', 'infrastructure_error'), flush=True)
            if result.get('status') != 'completed' or result.get('condition_valid') is not True:
                print('Batch stopped: an environment or infrastructure check failed; review the unscored result before continuing.',flush=True)
                raise SystemExit(2)


if __name__ == '__main__':
    main()
