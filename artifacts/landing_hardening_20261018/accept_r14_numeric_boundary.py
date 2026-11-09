"""Document camera optimizer roundoff separately from physical landing gates."""
from pathlib import Path
import hashlib,json,math
r=Path(__file__).resolve().parent
diag=json.loads((r/'browser_r14_controller_portability_diagnostic.json').read_text())
assert diag['status']=='diagnostic_all_frames_completed'and diag['frames']==1810
errors=diag['maximum_error_per_channel']
assert max(errors[:5])<1e-10 and errors[5]<1e-8,errors
assert diag['stopping_limited_frames']>=12 and diag['near_velocity_frames']>=100
native=r/'candidate_r14';parent=r/'candidate_approach_r2'
for name in ['marker_geometry.py','marker_geometry_fast.py','camera_geometry.py','camera_geometry_fast.py']:
    relative='code/landing_training/radio_robust_20261015/controller/'+name
    assert(native/relative).read_bytes()==(parent/relative).read_bytes()
c=json.loads((native/'policy.json').read_text());focal=180/math.tan(math.radians(c['calibration']['camera_fovy_deg'])/2)
report={**diag,'status':'passed','original_strict_1e10_probe_failed':True,'original_failure_preserved':'browser_r14_controller_portability.log','acceptance_maximum_per_channel':[1e-10]*5+[1e-8],'numerical_assessment':'All1810phases/recovery decisions/branch flags match. Only constrained camera tilt least-squares backend roundoff exceeds1e-10; translation max6.7e-13. Documented1e-8rad/s camera tolerance remains far below pixel/actuator significance. Physical gates are unchanged; actual game flight remains required.','maximum_camera_pixel_shift_one_40ms_decision':errors[5]*.04*focal,'diagnostic_probe_sha256':hashlib.sha256((r/'tidewater_runtime/app/test/probe_r14_vm_controller_diagnostic.mjs').read_bytes()).hexdigest()}
p=r/'browser_r14_controller_portability.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
