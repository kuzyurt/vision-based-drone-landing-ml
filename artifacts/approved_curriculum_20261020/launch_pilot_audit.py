"""Start exactly one read-only semantic pilot audit and record its PID."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020')
state_path = ROOT / 'pilot_audit_state.json'
if state_path.exists():
    old = json.loads(state_path.read_text())
    pid = old.get('pid')
    if pid and Path(f'/proc/{pid}/cmdline').exists():
        cmd = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        if 'audit_semantic_pilots.py' in cmd:
            raise SystemExit(f'audit already running as {pid}')
batch = json.loads((ROOT / 'semantic_pilots' / 'state.json').read_text())
if batch.get('status') != 'closed_needs_semantic_and_physical_audits' or batch.get('active') or batch.get('remaining'):
    raise SystemExit('refusing partial/open pilot audit')
log = (ROOT / 'pilot_audit.log').open('ab', buffering=0)
p = subprocess.Popen([sys.executable, str(ROOT / 'audit_semantic_pilots.py')], cwd=ROOT,
                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                     start_new_session=True, close_fds=True)
tmp = state_path.with_suffix('.json.tmp')
tmp.write_text(json.dumps({'status':'running','pid':p.pid,'started_utc':time.time(),'log':'pilot_audit.log'}, indent=2))
os.replace(tmp, state_path)
print(json.dumps({'status':'started','pid':p.pid,'log':str(ROOT/'pilot_audit.log')}))
