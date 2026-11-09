"""A single VM game flight after qualification, not repeated token polling."""
from pathlib import Path
import datetime, json, os, subprocess, sys, time
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'r7_browser_gate_state.json'
def save(v):
    v['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    t=STATE.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(STATE)
try:
    while True:
        s=json.loads((ROOT/'r7_qualification_state.json').read_text())
        if s['status']=='needs_specific_issue_review':
            save(dict(status='not_run_native_gate_needs_review',native_state=s));sys.exit(0)
        if s['status']=='evaluation_completed_requires_final_audit':break
        if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime(2026,10,18,11,8,tzinfo=datetime.timezone.utc):
            save(dict(status='not_run_work_window_ending'));sys.exit(0)
        save(dict(status='waiting_for_native_gate',native_phase=s.get('phase')))
        time.sleep(1200)
    for cohort in ['r7_remaining8','r7_fresh_C60','r7_safety10']:
        if not (ROOT/cohort/'hardening_audit.json').exists():
            subprocess.run([sys.executable,str(ROOT/'audit_hardening.py'),cohort],check=True)
    fresh=json.loads((ROOT/'r7_fresh_C60/hardening_audit.json').read_text())
    safety=json.loads((ROOT/'r7_safety10/hardening_audit.json').read_text())
    assert fresh['outcomes'].get('landed',0)>=57, fresh['outcomes']
    assert fresh['faults_triggered']>=12, fresh['faults_triggered']
    assert safety['outcomes']=={'home_landed':10}, safety['outcomes']
    assert safety['faults_triggered']==5
    save(dict(status='running_one_production_browser_stack_flight'))
    runtime=ROOT/'tidewater_runtime'
    config=json.loads((runtime/'adapter_verified.json').read_text())
    cmd=[config['loader'],'--library-path',config['library_path'],str(runtime/'node-v22.23.2-linux-x64/bin/node'),str(runtime/'app/test/tidewater_landing_r7_browser.mjs')]
    env=os.environ.copy();env.update(TIDEWATER_GPU_BACKEND='vulkan',XDG_RUNTIME_DIR='/tmp',POLICY_PYTHON=str(ROOT.parents[1]/'.venv/bin/python'))
    with (ROOT/'tidewater_stationary_r7_browser.log').open('x') as log:
        subprocess.run(cmd,cwd=runtime/'app',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=360,check=True)
    report=json.loads((ROOT/'tidewater_stationary_r7_browser/report.json').read_text())
    assert report['physical_assessment']['landed'] and not report['gpu_errors'], report
    save(dict(status='browser_flight_passed_requires_final_export',flight_seconds=report['flight_seconds'],physical_assessment=report['physical_assessment']))
except BaseException as e:
    save(dict(status='needs_specific_issue_review',error=repr(e)));raise
