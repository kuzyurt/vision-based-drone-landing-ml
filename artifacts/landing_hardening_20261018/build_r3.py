"""Fix the measured live telemetry contract; preserve every evaluated revision."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'candidate_r2b';dest=ROOT/'candidate_r3'
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__'))
p=dest/'code/landing_training/radio_robust_20261015/controller/action_guard.py'
text=p.read_text();old="observation.get('gimbal_commanded_rad',[])"
assert text.count(old)==1
text=text.replace(old,"observation['px4'].get('gimbal_commanded_rad',[])")
p.write_text(text)
config=json.loads((dest/'policy.json').read_text());config['runtime_revision']='landing_hardening_r3'
config['controller_changes']+=['R3: consume own gimbal-command target from actual px4 telemetry namespace; static recovery swept column covers16s maximum climb/scan horizon']
config['file_hashes']={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file() and p.name!='policy.json' and '__pycache__' not in str(p)}
(dest/'policy.json').write_text(json.dumps(config,indent=2)+'\n')
clearance=(ROOT/'recovery_clearance.py').read_text();assert '.8*8.' in clearance
(ROOT/'recovery_clearance_r3.py').write_text(clearance.replace('.8*8.','.8*16.').replace('horizontal motion for the bounded recovery.','horizontal motion over the full <=16s climb-and-scan horizon.'))
evaluator=(ROOT/'evaluate_hardening_v2.py').read_text()
old="'recovery_clearance.py':ROOT/'recovery_clearance.py'";assert evaluator.count(old)==1
(ROOT/'evaluate_hardening_v3.py').write_text(evaluator.replace(old,"'recovery_clearance.py':ROOT/'recovery_clearance_r3.py'"))
print('R3 frozen',sha(dest/'policy.json'))
