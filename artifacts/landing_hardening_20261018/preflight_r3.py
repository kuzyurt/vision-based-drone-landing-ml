"""Exercise the real recorded observation namespace, not a synthetic alternative."""
from pathlib import Path
import copy,hashlib,importlib,json,math,sys,types
import numpy as np
ROOT=Path(__file__).resolve().parent;BUNDLE=ROOT/'candidate_r3'
folder=BUNDLE/'code/landing_training/radio_robust_20261015/controller'
p=types.ModuleType('r3_probe');p.__path__=[str(folder)];sys.modules[p.__name__]=p
ActionGuard=importlib.import_module('r3_probe.action_guard').ActionGuard
line=(ROOT/'r2_development/near_side_low/steps.jsonl').open().readline()
recorded=json.loads(line)['observation'];assert 'gimbal_commanded_rad' in recorded['px4']
assert 'gimbal_commanded_rad' not in recorded
guard=ActionGuard();target=math.radians(60);encoder=math.radians(80)
for _ in range(100):
 o=copy.deepcopy(recorded);o['gimbal_rad']=[0.,encoder];o['px4']['gimbal_commanded_rad']=[0.,target]
 command=np.zeros(6);command[5]=math.radians(40)
 actual,d=guard.apply(command,o,dict(pad_visibility_probability=1.));target+=actual[5]*.04;encoder=target
assert abs(math.degrees(encoder)-90)<1e-8
assert d['guard_target_feedback_source']=='own_issued_command'
config=json.loads((BUNDLE/'policy.json').read_text())
for name,expected in config['file_hashes'].items():assert hashlib.sha256((BUNDLE/name).read_bytes()).hexdigest()==expected,name
value=dict(status='passed',scope='Actual recorded native telemetry namespace and unsettled handoff, candidate source hashes',final_command_deg=math.degrees(target),new_flight=False)
(ROOT/'r3_preflight.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
