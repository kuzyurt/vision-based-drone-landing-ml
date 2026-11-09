"""Run preserved development gates before the untouched independent final suite."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
def save(v):
    v['updated']=time.time()
    for name in ['qualification_r5_state.json','qualification_state.json']:
        p=ROOT/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
def run(cohort,plan):
    save(dict(status='running',phase=cohort))
    with (ROOT/(cohort+'.log')).open('x') as log:
        p=subprocess.Popen([sys.executable,'-u',str(ROOT/'evaluate_development.py'),'--bundle','bundle_spatial_r5',
            '--cohort',cohort,'--plan',str(ROOT/plan),'--workers','6','--mission-safety','--record-all-rgb',
            '--qualification','--instance-base','160'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        (ROOT/(cohort+'_launch.json')).write_text(json.dumps(dict(pid=p.pid,log=log.name),indent=2))
        code=p.wait()
    if code:raise RuntimeError(f'{cohort} exit {code}')
    return json.loads((ROOT/cohort/'report.json').read_text())
def main():
    for cohort,plan,expected in [
        ('extended_development_spatial_r5','extended_development_plan.json',{'landed':12}),
        ('target_unavailable_spatial_r5','target_unavailable_plan.json',{'home_landed':6})]:
        report=run(cohort,plan)
        if report['outcomes']!=expected:
            save(dict(status='needs_iteration',phase=cohort,outcomes=report['outcomes']));return
    plan=ROOT/'fresh_holdout_60_v2.json';expected=(ROOT/'fresh_holdout_60_v2.sha256').read_text().split()[0]
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen holdout modified')
    report=run('fresh_holdout_spatial_r5',plan.name);o=report['outcomes']
    collisions=o.get('collision_failure',0)+o.get('water_strike',0)
    passed=report['completed']==60 and o.get('landed',0)>=57 and collisions==0 and all(not x.get('infrastructure_error') for x in report['results'])
    save(dict(status='qualified_pending_evidence_audit' if passed else 'needs_iteration',phase='fresh_holdout_spatial_r5',
        outcomes=o,qualified_on_sample=passed,evidence_caveat='Audit input/scoring/source boundaries and finite-sample uncertainty before reporting completion.'))
if __name__=='__main__':
    try:main()
    except BaseException as e:
        save(dict(status='needs_attention',phase='coordinator_error',error=f'{type(e).__name__}: {e}'));raise
