"""Advance only through predefined evidence gates; do not tune on the final suite."""
from pathlib import Path
import collections,hashlib,json,subprocess,sys,time

ROOT=Path(__file__).resolve().parent


def save(value):
    p=ROOT/'qualification_state.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)
def await_file(path):
    while not path.exists():time.sleep(60)
    return json.loads(path.read_text())
def run(cohort,plan,workers):
    save(dict(status='running',phase=cohort))
    with (ROOT/(cohort+'.log')).open('x') as log:
        p=subprocess.Popen([sys.executable,'-u',str(ROOT/'evaluate_development.py'),'--bundle','bundle_spatial_r3',
            '--cohort',cohort,'--plan',str(ROOT/plan),'--workers',str(workers),'--mission-safety','--record-all-rgb',
            '--instance-base','160'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        (ROOT/(cohort+'_launch.json')).write_text(json.dumps(dict(pid=p.pid,log=str(ROOT/(cohort+'.log'))),indent=2))
        code=p.wait()
    if code:raise RuntimeError(cohort+' exited '+str(code))
    report=json.loads((ROOT/cohort/'report.json').read_text())
    return report


def main():
    save(dict(status='running',phase='waiting_for_spatial_development_and_home_fallback'))
    report=await_file(ROOT/'development_spatial_r3/report.json')
    while report['status']!='completed':
        time.sleep(60);report=json.loads((ROOT/'development_spatial_r3/report.json').read_text())
    if report['outcomes']!={'landed':4}:
        stopped=[r for r in report['results'] if r['outcome']!='landed']
        if len(stopped)==1 and stopped[0]['name']=='test_gravel_14_1' and stopped[0]['outcome']=='development_stop_no_tracking':
            save(dict(status='running',phase='waiting_for_full_budget_far_case',initial_outcomes=report['outcomes']))
            far=await_file(ROOT/'far_full_budget_r3/report.json')
            while far['status']!='completed':
                time.sleep(60);far=json.loads((ROOT/'far_full_budget_r3/report.json').read_text())
            if far['outcomes']!={'landed':1}:
                save(dict(status='needs_iteration',phase='far_full_budget_case_failed',outcomes=far['outcomes']));return
        else:
            save(dict(status='needs_iteration',phase='initial_development_failed',outcomes=report['outcomes']));return
    home=await_file(ROOT/'fallback_development_v2/report.json')
    while home['status']!='completed':
        time.sleep(60);home=json.loads((ROOT/'fallback_development_v2/report.json').read_text())
    if home['outcomes']!={'home_landed':1}:
        save(dict(status='needs_iteration',phase='home_fallback_not_qualified',outcomes=home['outcomes']));return
    report=run('extended_development_spatial_r3','extended_development_plan.json',6)
    if report['outcomes']!={'landed':12}:
        save(dict(status='needs_iteration',phase='extended_development_failed',outcomes=report['outcomes']));return
    report=run('target_unavailable_spatial_r3','target_unavailable_plan.json',6)
    if report['outcomes']!={'home_landed':6}:
        save(dict(status='needs_iteration',phase='target_unavailable_fallback_failed',outcomes=report['outcomes']));return
    plan=ROOT/'fresh_holdout_60_v2.json';expected=(ROOT/'fresh_holdout_60_v2.sha256').read_text().split()[0]
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen holdout changed')
    report=run('fresh_holdout_spatial_r3','fresh_holdout_60_v2.json',6)
    outcomes=report['outcomes'];landed=outcomes.get('landed',0)
    collisions=outcomes.get('collision_failure',0)+outcomes.get('water_strike',0)
    qualified=landed>=57 and collisions==0 and report['completed']==60 and all(not r.get('infrastructure_error') for r in report['results'])
    save(dict(status='qualified_pending_evidence_audit' if qualified else 'needs_iteration',phase='fresh_holdout_complete',
        outcomes=outcomes,landed=landed,planned=60,collisions=collisions,qualified_on_sample=qualified,
        evidence_caveat='Agent must audit outcomes, radio/input boundaries and unchanged physical criteria before reporting completion. Finite sample is not universal reliability.'))


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        save(dict(status='needs_attention',phase='coordinator_error',error=f'{type(exc).__name__}: {exc}'));raise
