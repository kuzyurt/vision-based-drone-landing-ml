"""One bounded VM flight after audited native gates; event wait, no polling."""
from pathlib import Path
import datetime, hashlib, json, os, select, subprocess, sys

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'r11_browser_gate_state.json'

def save(value):
    value['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(STATE)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

try:
    assert not STATE.exists(), 'An existing browser gate must be inspected first'
    save(dict(status='waiting_for_owned_native_coordinator',pid=428179))
    try:
        fd = os.pidfd_open(428179)
    except ProcessLookupError:
        fd = None
    if fd is not None:
        ready, _, _ = select.select([fd], [], [], 7200)
        os.close(fd)
        assert ready, 'Native coordinator exceeded the bounded two-hour event wait'
    native = json.loads((ROOT/'r11_limited_state.json').read_text())
    if native['status'] != 'limited_native_checks_passed_not_qualified_requires_browser':
        save(dict(status='not_run_native_gate_needs_review',native_state=native))
        sys.exit(0)
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime(2026,10,18,11,8,tzinfo=datetime.timezone.utc), 'Work window ending'
    assert sha(ROOT/'candidate_r11/policy.json') == 'e9abb801c6fb1b38ce4a090ff732cd3417c64afc1f3ce1834b26d10aea9edfc1'
    for cohort in ['r11_pilot5','r11_limited_E20','r11_safety_E10']:
        assert (ROOT/cohort/'hardening_audit.json').is_file()
        assert (ROOT/cohort/'nearfield_veto_audit.json').is_file()
    fresh = json.loads((ROOT/'r11_limited_E20/hardening_audit.json').read_text())
    safety = json.loads((ROOT/'r11_safety_E10/hardening_audit.json').read_text())
    assert fresh['outcomes'].get('landed',0) == 20 and fresh['faults_triggered'] >= 5
    assert safety['outcomes'] == {'home_landed':10} and safety['faults_triggered'] == 5
    receipt = json.loads((ROOT/'vm_r11_browser_stage_receipt.json').read_text())
    app = ROOT/'tidewater_runtime/app'
    for relative, expected in receipt['files'].items():
        assert sha(app/relative) == expected, relative
    portability = json.loads((ROOT/'browser_r11_controller_portability.json').read_text())
    assert portability['status'] == 'passed'
    runtime = ROOT/'tidewater_runtime'
    adapter = json.loads((runtime/'adapter_verified.json').read_text())
    command = [adapter['loader'],'--library-path',adapter['library_path'],str(runtime/'node-v22.23.2-linux-x64/bin/node'),str(app/'test/tidewater_landing_r11_browser.mjs')]
    env = dict(os.environ,TIDEWATER_GPU_BACKEND='vulkan',XDG_RUNTIME_DIR='/tmp',POLICY_PYTHON=sys.executable)
    save(dict(status='running_one_production_browser_stack_flight'))
    with (ROOT/'tidewater_stationary_r11_browser.log').open('x') as log:
        subprocess.run(command,cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=360,check=True)
    report = json.loads((ROOT/'tidewater_stationary_r11_browser/report.json').read_text())
    assert report['physical_assessment']['landed'] and not report['gpu_errors'], report
    assert report['policy']['policy_sha256'] == 'e9abb801c6fb1b38ce4a090ff732cd3417c64afc1f3ce1834b26d10aea9edfc1'
    save(dict(status='limited_browser_flight_passed_not_qualified',flight_seconds=report['flight_seconds'],physical_assessment=report['physical_assessment']))
except BaseException as error:
    if isinstance(error,SystemExit) and error.code == 0:
        raise
    save(dict(status='needs_specific_issue_review',error=repr(error)))
    raise
