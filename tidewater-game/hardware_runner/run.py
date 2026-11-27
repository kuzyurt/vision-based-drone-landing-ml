"""Fly canonical benchmark cases with the realistic game's policy behind the simulated flight electronics.

    python -B tidewater-game/hardware_runner/run.py run --name hw_try --case <ID> [<ID> ...]
        [--state-of-charge 1.0] [--variant carrier|camera_on_battery] [--camera-latency 0.12]
        [--python-marker]                # model the pure-Python marker fit instead of the C++ kernel
    python -B tidewater-game/hardware_runner/run.py smoke    # no MuJoCo/PX4 needed, plumbing check

Uses the same native flight stack as benchmark.harness.tidewater_run (MuJoCo +
PX4, Windows), writes to benchmark/runs/NAME (working data, not evidence) and
adds hardware_summary.json to every episode.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_electronics.simulation.hil import HilConfig  # noqa: E402


def _config(args) -> HilConfig:
    return HilConfig(seed=args.seed, variant=args.variant, state_of_charge=args.state_of_charge,
                     camera_latency_s=args.camera_latency, native_marker_kernel=not args.python_marker)


def trial(job_path, config: HilConfig | None):
    """One episode. config=None flies without the simulated hardware (baseline)."""
    import linux_compat
    from benchmark.harness import student_tidewater, tidewater_run
    from adapter import HardwareInTheLoopActor

    job = json.loads(Path(job_path).read_text(encoding='utf-8'))
    output = Path(job['output'])
    linux_compat.install(output.parent / (output.name + '_platform'))
    original = student_tidewater.TidewaterActor
    wrappers = []

    def factory(device='cpu'):
        wrapper = HardwareInTheLoopActor(original(device), config, output / 'hardware_summary.json')
        wrappers.append(wrapper)
        return wrapper

    if config is not None:
        student_tidewater.TidewaterActor = factory
    try:
        tidewater_run.trial(job_path)
    finally:
        student_tidewater.TidewaterActor = original
        for wrapper in wrappers:
            output.mkdir(parents=True, exist_ok=True)
            wrapper.write_summary()


def run(args):
    import subprocess
    import time
    from benchmark.harness import tidewater_run, run as bench

    cases = args.case or [c['id'] for c in bench.canonical_plan()['cases']]
    run_dir, jobs = tidewater_run.build(args.name, cases, args.device, args.workers)
    config = None if args.no_hardware else vars(_config(args))
    (run_dir / 'hardware_config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    script = str(Path(__file__).resolve())
    pending, active, code = list(jobs), [], 0
    while pending or active:
        while pending and len(active) < max(1, args.workers):
            job = pending.pop(0)
            log = open(job['log'], 'wb')
            proc = subprocess.Popen([sys.executable, '-B', '-u', script, '_trial', '--job', job['job'],
                                     '--config', str(run_dir / 'hardware_config.json')],
                                    cwd=str(REPO), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            active.append((job, log, proc))
            print('Started', job['case_id'], flush=True)
            time.sleep(1)
        for item in list(active):
            job, log, proc = item
            if proc.poll() is None:
                continue
            log.close()
            active.remove(item)
            result = Path(job['output']) / 'result.json'
            row = json.loads(result.read_text(encoding='utf-8')) if result.exists() else {}
            print('Finished', job['case_id'], row.get('outcome', 'no result'), flush=True)
            code = code or proc.returncode
        time.sleep(2)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run')
    r.add_argument('--name', required=True)
    r.add_argument('--case', nargs='+')
    r.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    r.add_argument('--workers', type=int, default=1, help='flights at the same time')
    r.add_argument('--no-hardware', action='store_true', help='baseline: same flight path without the simulated hardware')
    for p in (r, sub.add_parser('smoke')):
        p.add_argument('--seed', type=int, default=0)
        p.add_argument('--variant', choices=['carrier', 'camera_on_battery'], default='carrier')
        p.add_argument('--state-of-charge', type=float, default=1.0)
        p.add_argument('--camera-latency', type=float, default=0.12)
        p.add_argument('--python-marker', action='store_true')
    t = sub.add_parser('_trial')
    t.add_argument('--job', required=True)
    t.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    if args.command == '_trial':
        stored = json.loads(Path(args.config).read_text(encoding='utf-8'))
        trial(args.job, None if stored is None else HilConfig(**stored))
        return 0
    if args.command == 'smoke':
        from smoke import smoke
        print(json.dumps(smoke(_config(args)), indent=2, default=str))
        return 0
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
