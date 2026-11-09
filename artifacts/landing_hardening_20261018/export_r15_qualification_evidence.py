"""Export a separate finite-sample certificate only after every existing gate passes."""
from pathlib import Path
import datetime, hashlib, json, math, os, select, tarfile
r=Path(__file__).resolve().parent
app=r/'tidewater_runtime/app'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
try:
    fd=os.pidfd_open(479009)
except ProcessLookupError:
    fd=None
if fd is not None:
    ready,_,_=select.select([fd],[],[],420)
    os.close(fd)
    assert ready,'Bounded event wait expired; inspect existing game process, do not duplicate'
gate=read(r/'r15_browser_gate_v3_state.json')
assert gate['status']=='native_and_two_actual_game_flights_passed_requires_export_review',gate
policy_sha='5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
assert sha(r/'candidate_r15/policy.json')==policy_sha
native=read(r/'resumed_r15_state.json')
assert native['status']=='native_gates_passed_requires_actual_browser_flight'
fresh=read(r/'r15_fresh_E60/hardening_audit.json')
safety=read(r/'r15_safety_E10/hardening_audit.json')
assert fresh['outcomes']=={'landed':58,'home_landed':2}and fresh['faults_triggered']==15
assert safety['outcomes']=={'home_landed':10}and safety['faults_triggered']==5
for cohort in ['r15_pilot5','r15_fresh_E60','r15_safety_E10']:
    audited=read(r/cohort/'hardening_audit.json')
    assert audited['status']=='audited'and audited['candidate_sha256']==policy_sha
    assert audited['original_sources_and_parent_unchanged']and audited['neural_weights_unchanged']
    assert not audited['radio_task_inputs']and not audited['teacher_task_actions']
    assert read(r/cohort/'nearfield_veto_audit.json')['status']=='passed'
stage=read(r/'vm_r15_browser_stage_v2_receipt.json')
for rel,h in stage['files'].items():assert sha(app/rel)==h,rel
port=read(r/'browser_r15_controller_portability.json')
assert port['status']=='passed'and port['frames']==1810
games=[]
files=['r15_browser_gate_v3_state.json','r15_browser_gate_v3_receipt.json',
    'queue_r15_browser_gate_v3.py','queue_r15_browser_gate_v3.log',
    'r15_browser_gate_v2_state.json','queue_r15_browser_gate_v2.log',
    'resumed_r15_state.json','vm_r15_browser_stage_v2_receipt.json',
    'browser_r15_controller_portability.json','r15_safe_handoff_boundary.json',
    'r15_native_completion_archive_receipt.json']
for folder in ['tidewater_stationary_r15_browser','tidewater_moving_r15_browser']:
    report=read(r/folder/'report.json')
    physical=report['physical_assessment']
    assert physical['landed']and physical['stable']and physical['support_count']>=3
    assert not physical['collision_failure']and physical['disarmed_contact_s']>=2
    assert not report['radio']and not report['gpu_errors']
    assert report['policy']['policy_sha256']==policy_sha
    motion=report.get('boat_motion_assessment')
    if motion:assert motion['displacement_m']>5 and .3<motion['mean_speed_m_s']<1
    games.append(dict(scenario=report['scenario'],flight_seconds=report['flight_seconds'],
        wall_seconds=report['wall_seconds'],frames=report['frames'],physical=physical,boat_motion=motion))
    files.extend(str(p.relative_to(r))for p in(r/folder).glob('*')if p.is_file()and p.suffix in['.json','.png','.jsonl'])
    files.append(folder+'.log')
for name in ['PolicyInference','GpuPolicyModel','MarkerKernel','PolicyLandingResult',
             'BrowserForces','BrowserWorld','BrowserPX4','BrowserGame','PolicyTelemetry']:
    files.append('tidewater_runtime/app/src/landing/'+name+'.js')
files.extend('tidewater_runtime/app/'+p for p in stage['files'])
files.extend(['tidewater_runtime/app/test/tidewater_headless_world.mjs',
    'tidewater_runtime/app/test/PolicyRecoveryClearance.mjs'])
files=sorted(set(files))
for rel in files:assert(r/rel).is_file(),rel
z=1.959963984540054;p=58/60;n=60
center=(p+z*z/(2*n))/(1+z*z/n)
half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
certificate=dict(schema='aerodock.finite_simulation_qualification.v1',
    status='passed_predeclared_simulation_and_two_actual_game_stack_gates',
    created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    native_candidate_policy_sha256=policy_sha,
    native_bundle_unchanged=True,qualification_is_external_to_frozen_bundle=True,
    neural_weights_unchanged=True,new_training=False,new_teacher_collection=False,
    description='Hybrid learned vision, geometric registration and persistent tracking, explicit controller and PX4; no boat radio position or velocity in these flights.',
    fresh_suite=dict(plan_sha256=sha(r/'fresh_edge_E60.json'),independent_worlds=60,
        outcomes=fresh['outcomes'],collision_count=0,water_strike_count=0,
        optical_fault_cases_exercised=15,maps=fresh['maps'],
        median_successful_flight_s=fresh['median_boat_flight_s'],range_successful_flight_s=fresh['range_boat_flight_s'],
        sample_landing_fraction=p,wilson_95_interval=[center-half,center+half]),
    safe_home_suite=dict(plan_sha256=sha(r/'safety_E10.json'),outcomes=safety['outcomes'],
        actual_camera_fault_cases=5,known_launch_home_required=True),
    actual_tidewater_stack_flights=games,
    controller_portability=dict(frames=1810,source='browser_r15_controller_portability.json',
        fixed_observed_nn_outputs_and_fits=True,not_a_new_neural_or_fitter_accuracy_test=True),
    verified_runtime_files={rel:sha(r/rel)for rel in files},
    limitations=[
        'Finite simulation evidence; 58/60 is not a hardware guarantee or proof of 95% population reliability.',
        'Two fresh flights returned to their authorized home instead of landing on the boat.',
        'Native qualification spans five maps, moving boats through0.9m/s,3–60m starts, own telemetry/static map priors, wind and waves<=5cm; not arbitrary sea states or mission geometry.',
        'Actual Tidewater checks use production ONNX-WebGPU/WASM/Pyodide components with Node headless scheduling, not the browser-worker UI scheduler.',
        'Tidewater has no authorized home landing site; bounded exhaustion restores manual altitude hold rather than native home landing.',
        'Static recovery-corridor checks are not full dynamic obstacle avoidance.',
        'Production boat cruise remains2.8m/s; policy horizontal commands cap at2m/s, so arbitrary pursuit at default cruise is not established.',
        'Bounded terminal contact commit may continue from a recent accepted visual motion estimate and own odometry; do not claim vision is freshly measured on every final-centimetre step.',
        'Controller port camera optimizer differs by about1e-9rad/s; documented1e-8camera tolerance, unchanged physical scoring.'])
certificate_path=r/'r15_simulation_qualification_certificate.json'
assert not certificate_path.exists()
certificate_path.write_text(json.dumps(certificate,indent=2)+'\n')
archive=r/'r15_final_game_evidence.tar.gz'
assert sum((r/rel).stat().st_size for rel in files)<75_000_000
with tarfile.open(archive,'x:gz')as t:
    for rel in files:t.add(r/rel,arcname=rel,recursive=False)
    t.add(certificate_path,arcname=certificate_path.name,recursive=False)
receipt=dict(status='qualified_evidence_exported_windows_integration_still_pending',
    archive=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),
    certificate_sha256=sha(certificate_path),games=games)
(r/'r15_final_game_evidence_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
