"""Freeze valid untouched E worlds; development gates precede any E flight."""
from pathlib import Path
import datetime, hashlib, json, os, select, subprocess, sys, time

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'r10_qualification_state_v2.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(value):
    value['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=STATE.with_suffix('.tmp');p.write_text(json.dumps(value,indent=2)+'\n');p.replace(STATE)
def wait_pid(pid,seconds):
    try:fd=os.pidfd_open(pid)
    except ProcessLookupError:return
    ready,_,_=select.select([fd],[],[],seconds);os.close(fd);assert ready,('Owned process exceeded bounded wait',pid)
def audit(cohort):
    for script,out in [('audit_hardening_v2.py','hardening_audit.json'),('audit_nearfield_veto.py','nearfield_veto_audit.json')]:
        if not (ROOT/cohort/out).exists():
            with (ROOT/(cohort+'_'+out+'.log')).open('x') as log:
                subprocess.run([sys.executable,str(ROOT/script),cohort],stdout=log,stderr=subprocess.STDOUT,check=True)
    return json.loads((ROOT/cohort/'hardening_audit.json').read_text())
def run(cohort,plan,base):
    now=datetime.datetime.now(datetime.timezone.utc)
    deadline=datetime.datetime(2026,10,18,11,8,tzinfo=datetime.timezone.utc)
    assert now<deadline,'Insufficient window for another stage'
    save(dict(status='running',phase=cohort))
    cmd=[sys.executable,str(ROOT/'evaluate_hardening_v7.py'),'--bundle','candidate_r10','--cohort',cohort,'--workers','8','--full-budget','--mission-safety','--qualification','--instance-base',str(base),'--plan',str(ROOT/plan)]
    with (ROOT/(cohort+'.log')).open('x') as log:
        p=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=p.wait(timeout=(deadline-now).total_seconds())
        except subprocess.TimeoutExpired:
            import psutil
            owned=psutil.Process(p.pid).children(recursive=True)+[psutil.Process(p.pid)]
            for child in owned:
                try:child.terminate()
                except psutil.NoSuchProcess:pass
            time.sleep(2.)
            for child in owned:
                try:
                    if child.is_running() and child.status() not in [psutil.STATUS_ZOMBIE,psutil.STATUS_DEAD]:child.kill()
                except psutil.NoSuchProcess:pass
            raise RuntimeError('Window ending; owned unfinished cohort stopped and all partial artifacts preserved')
        assert code==0,(cohort,code)
    return audit(cohort)

try:
    assert not STATE.exists()
    save(dict(status='resuming_completed_static_setup_for_V7_scoring',static_setup_already_completed=True))
    final=ROOT/'fresh_edge_E60.json';h=sha(final)
    assert json.loads((ROOT/'E_all_static_preflight/receipt.json').read_text())['status']=='passed'
    save(dict(status='waiting_for_owned_development_pilot',queue_pid=423197))
    wait_pid(423197,2400)
    pilot=audit('r10_pilot4')
    assert pilot['outcomes']=={'landed':4},pilot['outcomes']
    assert sha(ROOT/'candidate_r10/policy.json')=='d8868f20b07b494713d6d1ab08c4d977e56ef5b4622fa251e6cfd7b62175b174'
    exercised=0
    report=json.loads((ROOT/'r10_pilot4/report.json').read_text())
    for case in report['results']:
        for line in (Path(case['directory'])/'steps.jsonl').open():
            row=json.loads(line)
            if not row.get('terminal') and row['output']['learner_diagnostics'].get('far_recovery_reuses_aircraft_clear_view'):exercised+=1
    assert exercised>=12,'Far recovery change was not exercised'
    assert sha(final)==h
    fresh=run('r10_fresh_E60','fresh_edge_E60.json',50)
    assert fresh['outcomes'].get('landed',0)>=57 and fresh['faults_triggered']>=12,fresh['outcomes']
    safety=run('r10_safety_E10','safety_E10.json',130)
    assert safety['outcomes']=={'home_landed':10} and safety['faults_triggered']==5,safety['outcomes']
    save(dict(status='native_gates_passed_requires_browser_export',fresh_outcomes=fresh['outcomes'],safety_outcomes=safety['outcomes']))
except BaseException as error:
    save(dict(status='needs_specific_issue_review',error=repr(error)))
    raise
