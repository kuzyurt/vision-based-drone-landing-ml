"""Repair a stale pre-handoff driver receipt check; retain all failed evidence."""
from pathlib import Path
import datetime, difflib, hashlib, json, os, psutil, subprocess, sys

r = Path(__file__).resolve().parent
app = r / 'tidewater_runtime/app'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

state = json.loads((r/'r15_browser_gate_v2_state.json').read_text())
assert state['status'] == 'needs_specific_issue_review', state
log = (r/'queue_r15_browser_gate_v2.log').read_text()
assert "assert sha(app/moving['file'])==moving['sha256']" in log, log
for p in psutil.process_iter(['pid','cmdline']):
    cmd = p.info['cmdline'] or []
    assert not any(str(r/filename) in cmd for filename in [
        'queue_r15_browser_gate_v2.py', 'queue_r15_browser_gate_v3.py',
        'continue_r15_native.py', 'evaluate_hardening_v7.py']), p.info
for folder in ['tidewater_stationary_r15_browser','tidewater_moving_r15_browser']:
    assert not (r/folder).exists(), folder
old = json.loads((r/'vm_r15_moving_driver_receipt.json').read_text())
new = json.loads((r/'vm_r15_browser_stage_v2_receipt.json').read_text())
backup = r/'r15_game_before_safe_handoff'/old['file']
current = app/old['file']
assert sha(backup) == old['sha256']
assert sha(current) == new['files'][old['file']]
before = backup.read_text()
after = current.read_text()
expected = before.replace("../src/landing/BrowserPX4.js", "./r15_game/BrowserPX4.js")
assert expected != before and expected == after, ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True)))
source = (r/'queue_r15_browser_gate_v2.py').read_text()
source = source.replace("STATE = ROOT / 'r15_browser_gate_v2_state.json'", "STATE = ROOT / 'r15_browser_gate_v3_state.json'")
stale = "    assert sha(app/moving['file'])==moving['sha256']"
assert source.count(stale) == 1
source = source.replace(stale, "    assert sha(ROOT/'r15_game_before_safe_handoff'/moving['file'])==moving['sha256']\n    assert sha(app/moving['file'])==receipt['files'][moving['file']]")
script = r/'queue_r15_browser_gate_v3.py'
assert not script.exists()
compile(source, str(script), 'exec')
script.write_text(source)
receipt = dict(status='stale_receipt_gate_repaired_before_any_actual_game_flight',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    reason='V2 correctly verified every updated staging hash, then redundantly compared the new safe-handoff driver against its old pre-handoff receipt. Only the BrowserPX4 import differs; the old receipt matches the preserved backup.',
    old_driver_sha256=sha(backup), current_driver_sha256=sha(current),
    diff=''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True))),
    previous_gate_source_sha256=sha(r/'queue_r15_browser_gate_v2.py'),
    source_sha256=sha(script), controller_and_scenarios_unchanged=True)
with (r/'queue_r15_browser_gate_v3.log').open('x') as stream:
    child = subprocess.Popen([sys.executable,str(script)], cwd=r, stdout=stream,
        stderr=subprocess.STDOUT, start_new_session=True)
receipt['pid'] = child.pid
(r/'r15_browser_gate_v3_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
