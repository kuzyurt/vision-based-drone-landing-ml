"""A deterministic command/encoder mismatch counterexample, no scene render."""
from pathlib import Path
import importlib,math,sys,types
import numpy as np
folder=Path(__file__).resolve().parents[2]/'tidewater-game/app/public/policy/reference'
p=types.ModuleType('handoff_probe');p.__path__=[str(folder)];sys.modules[p.__name__]=p
module=importlib.import_module('handoff_probe.action_guard')

def run(command_feedback):
    guard=module.ActionGuard();command=math.radians(60);encoder=math.radians(80)
    for _ in range(100):
        o=dict(decision_dt_s=.04,gimbal_rad=[0.,encoder],image_valid=True)
        if command_feedback:guard.tilt_target=command
        action=np.zeros(6);action[5]=math.radians(40)
        actual,_=guard.apply(action,o,dict(pad_visibility_probability=1.))
        command+=actual[5]*.04;encoder=command
    return math.degrees(encoder),math.degrees(guard.tilt_target)
old=run(False);synchronized=run(True)
assert abs(old[0]-70.)<1e-8 and abs(old[1]-90.)<1e-8,old
assert abs(synchronized[0]-90.)<1e-8,synchronized
print('Encoder-initialized guard can latch at actual70deg while believing90deg; own commanded-target feedback reaches90deg:',old,synchronized)
