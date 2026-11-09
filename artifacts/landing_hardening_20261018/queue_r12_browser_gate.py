"""One bounded VM flight after audited native gates; event wait, no polling."""
from pathlib import Path
import datetime, hashlib, json, os, select, subprocess, sys

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'r12_browser_gate_state.json'

def save(value):
    value['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(STATE)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

try:
    assert not STATE.exists(), 'An existing browser gate must be inspected first'
    save(dict(status='waiting_for_owned_native_coordinator',pid=433276))
    try:
        fd = os.pidfd_open(433276)
    except ProcessLookupError:
        fd = None
    if fd is not None:
        ready, _, _ = select.select([fd], [], [], 14400)
        os.close(fd)
        assert ready, 'Native coordinator exceeded the bounded two-hour event wait'
    native = json.loads((ROOT/'resumed_r12_state.json').read_text())
    if native['status'] != 'native_gates_passed_requires_actual_browser_flight':
        save(dict(status='not_run_native_gate_needs_review',native_state=native))
        sys.exit(0)
    assert sha(ROOT/'candidate_r12/policy.json') == 'cfae2590824b63296a370e199b7e832a7eee3c34ae0bdd3dc4c5f5d2515deea4'
    for cohort in ['r12_pilot5','r12_fresh_E60','r12_safety_E10']:
        assert (ROOT/cohort/'hardening_audit.json').is_file()
        assert (ROOT/cohort/'nearfield_veto_audit.json').is_file()
        checked=json.loads((ROOT/cohort/'hardening_audit.json').read_text())
        assert checked['status']=='audited' and checked['candidate_sha256']==sha(ROOT/'candidate_r12/policy.json')
        assert not checked['outcomes'].get('collision_failure',0) and not checked['outcomes'].get('water_strike',0)
        assert json.loads((ROOT/cohort/'nearfield_veto_audit.json').read_text())['status']=='passed'
    fresh = json.loads((ROOT/'r12_fresh_E60/hardening_audit.json').read_text())
    safety = json.loads((ROOT/'r12_safety_E10/hardening_audit.json').read_text())
    assert sum(fresh['outcomes'].values()) == 60 and fresh['outcomes'].get('landed',0) >= 57 and fresh['faults_triggered'] >= 12
    assert safety['outcomes'] == {'home_landed':10} and safety['faults_triggered'] == 5
    receipt = json.loads((ROOT/'vm_r12_browser_stage_receipt.json').read_text())
    app = ROOT/'tidewater_runtime/app'
    for relative, expected in receipt['files'].items():
        assert sha(app/relative) == expected, relative
    portability = json.loads((ROOT/'browser_r12_controller_portability.json').read_text())
    assert portability['status'] == 'passed'
    runtime = ROOT/'tidewater_runtime'
    adapter = json.loads((runtime/'adapter_verified.json').read_text())
    command = [adapter['loader'],'--library-path',adapter['library_path'],str(runtime/'node-v22.23.2-linux-x64/bin/node'),str(app/'test/tidewater_landing_r12_browser.mjs')]
    env = dict(os.environ,TIDEWATER_GPU_BACKEND='vulkan',XDG_RUNTIME_DIR='/tmp',POLICY_PYTHON=sys.executable)
    save(dict(status='running_one_production_browser_stack_flight'))
    with (ROOT/'tidewater_stationary_r12_browser.log').open('x') as log:
        subprocess.run(command,cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=360,check=True)
    report = json.loads((ROOT/'tidewater_stationary_r12_browser/report.json').read_text())
    assert report['physical_assessment']['landed'] and not report['gpu_errors'], report
    assert report['policy']['policy_sha256'] == 'cfae2590824b63296a370e199b7e832a7eee3c34ae0bdd3dc4c5f5d2515deea4'
    save(dict(status='full_native_and_browser_flight_passed_requires_export_review',flight_seconds=report['flight_seconds'],physical_assessment=report['physical_assessment']))
except BaseException as error:
    if isinstance(error,SystemExit) and error.code == 0:
        raise
    save(dict(status='needs_specific_issue_review',error=repr(error)))
    raise
