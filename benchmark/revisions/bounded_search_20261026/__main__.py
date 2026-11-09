"""Prepare, audit or explicitly run the separately versioned bounded search suite."""
import argparse
from pathlib import Path
import subprocess
import sys
from benchmark.common import ROOT,read,write,sha,utc
from .spec import HERE,prepare,verify


def trial(job):
    from benchmark import runner
    from .routes import install
    plan=verify()
    if job['context']['plan_sha256']!=plan['plan_sha256']:raise ValueError('Different revision plan')
    expected=next(c for c in plan['cases'] if c['id']==job['case']['id'])
    if expected!=job['case']:raise ValueError('Job case differs from the prepared suite')
    original=runner.setup_scene
    runner.setup_scene=lambda env,case,output:install(env,case,output,original)
    if 'fresh_search_identity' in job['policy']:
        from .student import policy,install as student_install
        expected_policy=policy()
        if expected_policy['identity_sha256']!=job['policy']['identity_sha256']:raise ValueError('Student source or weights changed')
        student_install(runner,dict(job['policy'],device=job['context']['inference_device']),job['output'])
    try:
        runner.run_trial(job['policy'],job['case'],job['output'],job['context'])
    finally:
        output=Path(job['output'])
        if (output/'result.json').exists():
            try:
                from benchmark.rollout_digest import generate_episode_digest
                generate_episode_digest(output,overwrite=True)
            except Exception as exc:
                # A diagnostic sidecar must never turn a valid flight into an
                # infrastructure error, but retain the failure locally.
                (output/'diagnostic_digest_error.txt').write_text(f'{type(exc).__name__}: {exc}\n',encoding='utf-8')
                print('diagnostic_digest_error',exc,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('prepare')
    audit=commands.add_parser('audit')
    audit.add_argument('--output',type=Path,required=True)
    audit.add_argument('--motion-seconds',type=float,default=0.)
    audit.add_argument('--case')
    run=commands.add_parser('run')
    run.add_argument('--policy',nargs='+',required=True)
    run.add_argument('--case',nargs='+')
    run.add_argument('--all-cases',action='store_true')
    run.add_argument('--name',required=True)
    run.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    worker=commands.add_parser('_trial',help=argparse.SUPPRESS);worker.add_argument('--job',required=True)
    args=parser.parse_args()
    if args.command=='prepare':prepare();return
    if args.command=='_trial':trial(read(args.job));return
    plan=verify()
    if args.command=='audit':
        from .validate import audit
        if args.case and args.case not in {c['id'] for c in plan['cases'] if 'bounded_route' in c}:parser.error('Unknown revised case')
        audit(args.output,args.motion_seconds,args.case);return
    inventory=read(ROOT/'models/inventory.json');policies={p['id']:p for p in inventory['policies']}
    if any(key.startswith('fresh-search-') for key in args.policy):
        from .student import policy
        student=policy();policies[student['id']]=student
    if len(set(args.policy))!=len(args.policy):parser.error('Duplicate policies')
    from benchmark.runner import preflight
    for key in args.policy:
        if key not in policies:parser.error('Unknown policy: '+key)
        if 'fresh_search_identity' in policies[key]:
            from .student import BASE
            errors=preflight(policies[BASE])
        else:errors=preflight(policies[key])
        if errors:raise RuntimeError(errors)
    known={c['id'] for c in plan['cases']}
    if args.case and set(args.case)-known:parser.error('Unknown case')
    cases=[c for c in plan['cases'] if c['id'] in args.case] if args.case else [c for c in plan['cases'] if args.all_cases or 'bounded_route' in c]
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.name):parser.error('Unsafe run name')
    out=HERE/'runs'/args.name;out.mkdir(parents=True,exist_ok=False)
    context=dict(plan_sha256=plan['plan_sha256'],runtime_sha256=sha(ROOT/'environments/runtime.json'),
        revision_receipts_sha256=sha(HERE/'source_receipts.json'),inference_device=args.device,
        control_hz=25,backend='windows_mujoco_px4',scenario_revision='bounded_search_20261026')
    write(out/'run.json',dict(created_utc=utc(),context=context,policies=args.policy,cases=[c['id'] for c in cases],training_eligible=False))
    results=[]
    for key in args.policy:
        for case in cases:
            destination=out/key/case['id'];job=out/'next_job.json'
            write(job,dict(policy=policies[key],case=case,output=str(destination),context=context))
            with (out/'worker.log').open('a') as log:
                process=subprocess.Popen([sys.executable,'-B','-u','-m','benchmark.revisions.bounded_search_20261026','_trial','--job',str(job)],
                    cwd=ROOT.parent,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                try:process.wait(timeout=3600)
                except (subprocess.TimeoutExpired,KeyboardInterrupt):
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=log,stderr=subprocess.STDOUT,
                        check=False,creationflags=subprocess.CREATE_NO_WINDOW)
                    process.wait(timeout=15)
                    raise
            path=destination/'result.json'
            if not path.exists():raise RuntimeError('Worker exited without evidence; see worker.log')
            result=read(path);results.append(result)
            write(out/'summary.json',dict(context=context,training_eligible=False,results=results))
            print(key,case['id'],result.get('outcome',result['status']),flush=True)
            if process.returncode or result['status']!='completed' or not result['condition_valid']:
                raise SystemExit('Stopped on infrastructure or scenario-envelope error; evidence retained.')
    print('Finished. Results are a separate revision; old scores were not reused.',flush=True)


if __name__=='__main__':main()
