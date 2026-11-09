"""One five-flight development cohort, then unchanged full fresh gates."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
r=Path(__file__).resolve().parent
SHA='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
assert hashlib.sha256((r/'candidate_r15/policy.json').read_bytes()).hexdigest()==SHA
probe=json.loads((r/'r15_runtime_terminal_motion_probe.json').read_text())
assert probe['status']=='passed'and probe['actual_terminal_motion_veto_frames']>=12
processes=subprocess.run(['ps','-eo','pid,ppid,etime,args'],capture_output=True,text=True).stdout
active=[s for s in processes.splitlines()if 'evaluate_hardening_v7.py'in s];assert not active,active
for name in ['r15_pilot5','r15_fresh_E60','r15_safety_E10']:assert not(r/name).exists(),name
assert not(r/'r14_fresh_E60/report.json').exists()
(r/'r15_pilot5_plan.json').write_bytes((r/'r14_pilot5_plan.json').read_bytes())
with(r/'r15_pilot5.log').open('x')as log:
    pilot=subprocess.Popen([sys.executable,str(r/'evaluate_hardening_v7.py'),'--bundle','candidate_r15','--cohort','r15_pilot5','--workers','5','--full-budget','--mission-safety','--instance-base','190','--plan',str(r/'r15_pilot5_plan.json')],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
s=(r/'continue_r14_native.py').read_text().replace('34845b34dc9490fddcc411738bd25b83e0d52bf4ab3564bf4aa22c931004c473',SHA).replace('439794',str(pilot.pid)).replace('r14','r15')
a="    assert close_exercised>=100,'Persistent near velocity not exercised'";assert s.count(a)==1
b=a+"""
    terminal_frames=0
    for case in report['results']:
        for line in (Path(case['directory'])/'steps.jsonl').open():
            row=json.loads(line)
            if row.get('terminal'):continue
            plan=row['output']['learner_diagnostics'].get('nearfield_visibility_plan',{})
            if 'visibility_speed_limit_m_s'in plan:
                assert 0<plan['visibility_speed_limit_m_s']<=.08
                terminal_frames+=1
    assert terminal_frames>=100,'Calibrated terminal-motion envelope not exercised'
    assert not (ROOT/'r14_fresh_E60/report.json').exists()
"""
s=s.replace(a,b);out=r/'continue_r15_native.py';assert not out.exists();compile(s,str(out),'exec');out.write_text(s)
assert "'--record-all-rgb'"in s
with(r/'continue_r15_native.log').open('x')as log:
    coordinator=subprocess.Popen([sys.executable,str(out)],cwd=r,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
receipt=dict(status='running_five_targeted_cases_then_full_unchanged_gates',candidate_sha256=SHA,pilot_pid=pilot.pid,coordinator_pid=coordinator.pid,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Five concurrent checks include pairedgravel plus four necessary regressioncases; avoids repeating gravel in a separate one-flight then identical five-flight cohort.',qualification_unestablished=True,E60_untouched_before_launch=True,record_actual_rgb_in_fresh_and_safety=True)
(r/'r15_pipeline_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
