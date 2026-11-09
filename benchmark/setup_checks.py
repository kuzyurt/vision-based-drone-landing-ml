"""Exercise real physical takeoff and camera/range contracts, with no timed actor."""
import argparse
from datetime import datetime, timezone
from .common import ROOT,read,sha,write
from .runner import run_trial


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all',action='store_true',help='Check all cases rather than six wind/wave starts')
    args=parser.parse_args()
    plan=read(ROOT/'environments/suite.json')
    policy=next(p for p in read(ROOT/'models/inventory.json')['policies'] if p['actor']=='privileged_teacher')
    cases=[c for c in plan['cases'] if args.all or c['scenario']['wind_mean_m_s']>0 or c['scenario']['wave_height']>0]
    out=ROOT/'audits'/('physical_setup_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(parents=True,exist_ok=False)
    context=dict(plan_sha256=plan['plan_sha256'],runtime_sha256=sha(ROOT/'environments/runtime.json'),
                 physical_setup_only=True,policy_executed=False)
    rows=[]
    for case in cases:
        dest=out/case['id']
        run_trial(policy,case,dest,context,setup_only=True)
        row=read(dest/'setup_result.json');rows.append(row)
        print(case['id'],row['status'],row.get('actual_start_distance_m'),flush=True)
        write(out/'setup_checks.json',dict(context=context,planned=len(cases),completed=len(rows),
            all_valid=len(rows)==len(cases) and all(r.get('condition_valid') for r in rows),cases=rows))
        if not row.get('condition_valid'):raise SystemExit(2)
    print('PHYSICAL_SETUP_CHECKS',out,flush=True)


if __name__=='__main__':main()
