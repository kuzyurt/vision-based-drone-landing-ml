"""Resume one full evidence-gated iteration after the user's explicit continuation."""
from pathlib import Path
import datetime,hashlib,json,os,select,subprocess,sys,time

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'resumed_r12_state.json'
POLICY_SHA='cfae2590824b63296a370e199b7e832a7eee3c34ae0bdd3dc4c5f5d2515deea4'
PLAN_SHA='5b7840f36870a384adb9c83011f6329effa210b53bea19de900396ed05c5c33a'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(value):
    value['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=STATE.with_suffix('.tmp');p.write_text(json.dumps(value,indent=2)+'\n');p.replace(STATE)
def wait_pid(pid,seconds):
    try:fd=os.pidfd_open(pid)
    except ProcessLookupError:return
    ready,_,_=select.select([fd],[],[],seconds);os.close(fd)
    assert ready,('Owned pilot exceeded bounded wait',pid)
def audit(cohort):
    for script,out in [('audit_hardening_v2.py','hardening_audit.json'),('audit_nearfield_veto.py','nearfield_veto_audit.json')]:
        if not (ROOT/cohort/out).exists():
            with (ROOT/(cohort+'_'+out+'.log')).open('x')as log:
                subprocess.run([sys.executable,str(ROOT/script),cohort],stdout=log,stderr=subprocess.STDOUT,check=True)
    return json.loads((ROOT/cohort/'hardening_audit.json').read_text())
def stop_owned(p):
    import psutil
    try:owned=psutil.Process(p.pid).children(recursive=True)+[psutil.Process(p.pid)]
    except psutil.NoSuchProcess:return
    for child in owned:
        try:child.terminate()
        except psutil.NoSuchProcess:pass
    time.sleep(2.)
    for child in owned:
        try:
            if child.is_running()and child.status()not in [psutil.STATUS_ZOMBIE,psutil.STATUS_DEAD]:child.kill()
        except psutil.NoSuchProcess:pass
def run(cohort,plan,base,timeout):
    save(dict(status='running',phase=cohort))
    cmd=[sys.executable,str(ROOT/'evaluate_hardening_v7.py'),'--bundle','candidate_r12','--cohort',cohort,'--workers','8','--full-budget','--mission-safety','--qualification','--instance-base',str(base),'--plan',str(ROOT/plan)]
    # Observe atomic report updates through filesystem events. A failed
    # acceptance gate must not consume another hour of unnecessary flights.
    import ctypes
    libc=ctypes.CDLL(None,use_errno=True)
    libc.inotify_add_watch.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    events=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC)
    assert events>=0
    mask=0x100|0x80|0x8  # create, moved-to, close-write
    assert libc.inotify_add_watch(events,os.fsencode(ROOT),mask)>=0
    pidfd=None
    with (ROOT/(cohort+'.log')).open('x')as log:
        p=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            pidfd=os.pidfd_open(p.pid);deadline=time.monotonic()+timeout
            watching=False;last_completed=-1
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    stop_owned(p);raise RuntimeError('Owned stage exceeded bounded wall allowance; partial artifacts preserved')
                ready,_,_=select.select([pidfd,events],[],[],remaining)
                if pidfd in ready:break
                if events in ready:
                    try:
                        while os.read(events,65536):pass
                    except BlockingIOError:pass
                folder=ROOT/cohort
                if not watching and folder.exists():
                    assert libc.inotify_add_watch(events,os.fsencode(folder),mask)>=0
                    watching=True
                report_path=folder/'report.json'
                if not report_path.exists():continue
                progress=json.loads(report_path.read_text())
                if progress['completed']==last_completed:continue
                last_completed=progress['completed'];outcomes=progress['outcomes']
                collision=any(outcomes.get(k,0)for k in ['collision_failure','water_strike'])
                infrastructure=any(outcomes.get(k,0)for k in ['worker_error','infrastructure_error'])
                impossible=(last_completed-outcomes.get('landed',0)>3)if 'fresh_E60'in cohort else(last_completed-outcomes.get('home_landed',0)>0)
                if collision or infrastructure or impossible:
                    reason=dict(status='acceptance_unreachable_or_infrastructure_failure',cohort=cohort,completed=last_completed,planned=progress['planned'],outcomes=outcomes,report_preserved=True,retired_before_followup_tuning=True)
                    (ROOT/(cohort+'_stopped_receipt.json')).write_text(json.dumps(reason,indent=2)+'\n')
                    stop_owned(p);raise RuntimeError(json.dumps(reason))
            code=p.wait()
        finally:
            if pidfd is not None:os.close(pidfd)
            os.close(events)
    assert code==0,(cohort,code)
    return audit(cohort)

try:
    assert not STATE.exists()
    save(dict(status='waiting_for_owned_pilot',pilot_pid=430933,scope='New user-authorized continuation; prior expired window does not apply'))
    wait_pid(430933,1800)
    pilot=audit('r12_pilot5')
    assert pilot['outcomes']=={'landed':5},pilot['outcomes']
    exercised=0
    report=json.loads((ROOT/'r12_pilot5/report.json').read_text())
    for case in report['results']:
        for line in (Path(case['directory'])/'steps.jsonl').open():
            row=json.loads(line)
            if not row.get('terminal')and row['output']['learner_diagnostics'].get('coarse_angular_rate_limited'):exercised+=1
    assert exercised>=12,'Angular-rate feedback was not meaningfully exercised'
    assert sha(ROOT/'candidate_r12/policy.json')==POLICY_SHA
    assert sha(ROOT/'fresh_edge_E60.json')==PLAN_SHA
    static=json.loads((ROOT/'E_all_static_preflight/receipt.json').read_text())
    assert static['status']=='passed'and static['independent_worlds']==60
    # No earlier candidate has evaluated E; no failed limited-sample gate is
    # reinterpreted as qualification. This is the first full E evaluation.
    for old in ['r9_fresh_E60','r10_fresh_E60','r11_limited_E20']:
        assert not (ROOT/old/'report.json').exists(),old
    fresh=run('r12_fresh_E60','fresh_edge_E60.json',50,7200)
    assert fresh['outcomes'].get('landed',0)>=57,fresh['outcomes']
    assert fresh['faults_triggered']>=12,fresh['faults_triggered']
    safety=run('r12_safety_E10','safety_E10.json',130,2400)
    assert safety['outcomes']=={'home_landed':10},safety['outcomes']
    assert safety['faults_triggered']==5,safety['faults_triggered']
    save(dict(status='native_gates_passed_requires_actual_browser_flight',fresh_outcomes=fresh['outcomes'],safety_outcomes=safety['outcomes'],candidate_sha256=POLICY_SHA))
except BaseException as error:
    save(dict(status='needs_specific_issue_review',error=repr(error)))
    raise
