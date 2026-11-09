"""Prepare, audit or run the targeted four-case teacher revision."""
import argparse
from pathlib import Path

from .spec import prepare, verify
from .register import register_policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('prepare')
    commands.add_parser('register')
    audit = commands.add_parser('audit')
    audit.add_argument('--output', type=Path, required=True)
    audit.add_argument('--motion-seconds', type=float, default=0.)
    audit.add_argument('--case')
    run = commands.add_parser('run')
    run.add_argument('--name', required=True)
    run.add_argument('--case', nargs='+')
    worker = commands.add_parser('_trial', help=argparse.SUPPRESS)
    worker.add_argument('--job', required=True)
    args = parser.parse_args()

    if args.command == 'prepare':
        prepare()
        return
    if args.command == 'register':
        prepare()
        register_policy()
        return
    if args.command == '_trial':
        from .run import trial
        trial(args.job)
        return
    plan = verify()
    if args.command == 'audit':
        from .validate import audit
        known = {case['id'] for case in plan['cases'] if 'bounded_route' in case}
        if args.case and args.case not in known:
            parser.error('Unknown revised case')
        audit(args.output, args.motion_seconds, args.case)
        return
    if args.command == 'run':
        from .run import run_command
        run_command(args.name, args.case)
        return


if __name__ == '__main__':
    main()
