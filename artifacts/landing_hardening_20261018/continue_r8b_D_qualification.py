"""Gated untouched-D qualification; no candidate tuning during evaluation."""
from pathlib import Path
import datetime,hashlib,json,os,select,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;STATE=ROOT/'r8b_qualification_state.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(v):
    v['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    t=STATE.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(STATE)
def audit(cohort):
    for script,out in [('audit_hardening_v2.py','hardening_audit.json'),('audit_nearfield_veto.py','nearfield_veto_audit.json')]:
        if not (ROOT/cohort/out).exists():
            with (ROOT/(cohort+'_'+out+'.log')).open('x') as log:
                subprocess.run([sys.executable,str(ROOT/script),cohort],stdout=log,stderr=subprocess.STDOUT,check=True)
    return json.loads((ROOT/cohort/'hardening_audit.json').read_text())
def run(cohort,plan,base):
    save(dict(status='running',phase=cohort))
    cmd=[sys.executable,str(ROOT/'evaluate_hardening_v6.py'),'--bundle','candidate_r8b','--cohort',cohort,'--workers','8','--full-budget','--mission-safety','--qualification','--instance-base',str(base),'--plan',str(ROOT/plan)]
    with (ROOT/(cohort+'.log')).open('x') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    return audit(cohort)
try:
    save(dict(status='waiting_for_pilot5_owned_process',pid=387217))
    try:fd=os.pidfd_open(387217)
    except ProcessLookupError:fd=None
    if fd is not None:
        ready,_,_=select.select([fd],[],[],1500);os.close(fd)
        assert ready,'Pilot did not finish within25min'
    pilot=audit('r8b_pilot5')
    expected={'near_front_low','near_side_low','retired_city08_targeted20m','very_close_occlusion3s'}
    assert all(x['outcome']=='landed' for x in pilot['details'] if x['name'] in expected),pilot['outcomes']
    assert len([x for x in pilot['details'] if x['name'] in expected])==4
    assert all(x['outcome'] in ['landed','home_landed'] for x in pilot['details']),pilot['outcomes']
    veto=json.loads((ROOT/'r8b_pilot5/nearfield_veto_audit.json').read_text())
    assert sum(x['paused_frames'] for x in veto['details'])>=6,'New visibility alignment was not exercised'
    assert sha(ROOT/'candidate_r8b/policy.json')=='1121b2431961760ff36b240e007d9623cb9ade9f5b1b97566b4e421b7b7ecec6'
    assert sha(ROOT/'fresh_edge_D60.json')=='65cbcc24a80f359f2760104e88a3206317de7d98b880ed7054dfb7dda3f4cb25'
    static=json.loads((ROOT/'D_all_static_preflight/receipt.json').read_text());assert static['status']=='passed' and static['independent_worlds']==60
    assert (ROOT/'C_retirement.json').exists()
    fresh=run('r8b_fresh_D60','fresh_edge_D60.json',50)
    assert fresh['outcomes'].get('landed',0)>=57,fresh['outcomes']
    assert fresh['faults_triggered']>=12,fresh['faults_triggered']
    safety=run('r8b_safety10','safety_holdout10.json',130)
    assert safety['outcomes']=={'home_landed':10},safety['outcomes']
    assert safety['faults_triggered']==5,safety['faults_triggered']
    save(dict(status='native_gates_passed_requires_browser_export',fresh_outcomes=fresh['outcomes'],safety_outcomes=safety['outcomes']))
except BaseException as e:
    save(dict(status='needs_specific_issue_review',error=repr(e)));raise
