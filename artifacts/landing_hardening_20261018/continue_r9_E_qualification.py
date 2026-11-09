"""Freeze valid untouched E worlds; development gates precede any E flight."""
from pathlib import Path
import datetime, hashlib, json, os, select, subprocess, sys, time

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'r9_qualification_state.json'
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
    cmd=[sys.executable,str(ROOT/'evaluate_hardening_v6.py'),'--bundle','candidate_r9','--cohort',cohort,'--workers','8','--full-budget','--mission-safety','--qualification','--instance-base',str(base),'--plan',str(ROOT/plan)]
    with (ROOT/(cohort+'.log')).open('x') as log:
        p=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=p.wait(timeout=(deadline-now).total_seconds())
        except subprocess.TimeoutExpired:
            import psutil
            owned=psutil.Process(p.pid).children(recursive=True)+[psutil.Process(p.pid)]
            for child in owned:
                try:child.terminate()
                except psutil.NoSuchProcess:pass
            _,alive=psutil.wait_procs(owned,timeout=6)
            for child in alive:
                try:child.kill()
                except psutil.NoSuchProcess:pass
            raise RuntimeError('Window ending; owned unfinished cohort stopped and all partial artifacts preserved')
        assert code==0,(cohort,code)
    return audit(cohort)

try:
    assert not STATE.exists()
    save(dict(status='waiting_for_static_phase_preflight'))
    wait_pid(419757,900)
    receipt=json.loads((ROOT/'inland_phase_preflight_E/receipt.json').read_text())
    assert receipt['no_policy_evaluated']
    plan=json.loads((ROOT/'fresh_edge_E60_source.json').read_text())
    for replacement in receipt['replacements']:
        j=next(x for x in plan['cases'] if x['name']==replacement['original_case'])
        j['scenario']['boat_start_fraction']=replacement['job']['scenario']['boat_start_fraction']
    final=ROOT/'fresh_edge_E60.json';assert not final.exists()
    final.write_text(json.dumps(plan,indent=2)+'\n')
    h=sha(final)
    source=(ROOT/'preflight_D_all_static.py').read_text()
    source=source.replace('fresh_edge_D60.json','fresh_edge_E60.json').replace('65cbcc24a80f359f2760104e88a3206317de7d98b880ed7054dfb7dda3f4cb25',h).replace('D_all_static_preflight','E_all_static_preflight')
    source=source.replace("assert len(D)==60 and not D&trained and not D&C", "retired_D={(j['scenario']['kind'],j['scenario']['world_seed']) for j in json.loads((ROOT/'fresh_edge_D60.json').read_text())['cases']}\nassert len(D)==60 and not D&trained and not D&C and not D&retired_D")
    p=ROOT/'preflight_E_all_static.py';assert not p.exists();p.write_text(source)
    save(dict(status='running_static_constructor_checks',frozen_E_sha256=h))
    with (ROOT/'preflight_E_all_static.log').open('x') as log:
        subprocess.run([sys.executable,str(p)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert json.loads((ROOT/'E_all_static_preflight/receipt.json').read_text())['status']=='passed'
    save(dict(status='waiting_for_owned_development_pilot',queue_pid=419758))
    wait_pid(419758,2400)
    pilot=audit('r9_pilot4')
    assert pilot['outcomes']=={'landed':4},pilot['outcomes']
    assert sha(ROOT/'candidate_r9/policy.json')=='bf2b1c696dd4c5ff5524a8b467ce72f3df081656fda0f950936cb861fc87f380'
    exercised=0
    report=json.loads((ROOT/'r9_pilot4/report.json').read_text())
    for case in report['results']:
        for line in (Path(case['directory'])/'steps.jsonl').open():
            row=json.loads(line)
            if not row.get('terminal') and row['output']['learner_diagnostics'].get('recovery_far_bearing_fresh'):exercised+=1
    assert exercised>=12,'Far recovery change was not exercised'
    assert sha(final)==h
    fresh=run('r9_fresh_E60','fresh_edge_E60.json',50)
    assert fresh['outcomes'].get('landed',0)>=57 and fresh['faults_triggered']>=12,fresh['outcomes']
    safety=run('r9_safety_E10','safety_E10.json',130)
    assert safety['outcomes']=={'home_landed':10} and safety['faults_triggered']==5,safety['outcomes']
    save(dict(status='native_gates_passed_requires_browser_export',fresh_outcomes=fresh['outcomes'],safety_outcomes=safety['outcomes']))
except BaseException as error:
    save(dict(status='needs_specific_issue_review',error=repr(error)))
    raise
