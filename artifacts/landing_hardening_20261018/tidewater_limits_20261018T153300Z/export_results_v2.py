"""Read-only audit and compact evidence export after the Tidewater tests finish."""
from pathlib import Path
import collections,csv,datetime,hashlib,json,math,tarfile
r=Path(__file__).resolve().parent;root=r.parent;app=root/'tidewater_runtime/app'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=read(r/'state.json');assert state['status']=='completed',state['phase']
plan=read(r/'plan.json');expected=plan['candidate_policy_sha256']
assert sha(root/'candidate_r15/policy.json')==expected
stage=read(root/'vm_r15_browser_stage_v2_receipt.json')
for rel,h in stage['files'].items():assert sha(app/rel)==h,rel
rows=[];files={};source_files=['plan.json','followup_plan.json','launch_receipt.json','predecessor_retirement.json','state.json','coordinator.log','run_suite_v2.py','tidewater_speed_suite.mjs']
files.update({str(r/name):'current/'+name for name in source_files})
previous=root/plan['predecessor']
for name in ['plan.json','state.json','coordinator.log','run_suite.py','tidewater_speed_suite.mjs']:
    files[str(previous/name)]='predecessor/'+name
for record in state['results']:
    case=record['case'];folder=Path(record['directory'])
    if record['status']!='measured':
        rows.append(dict(id=case['id'],group=case['group'],radio=case['radio'],status=record['status'],error=record.get('error')));continue
    report=read(folder/'report.json');assert report['policy']['policy_sha256']==expected
    counts=collections.Counter();metric=available=valid=frames=0;first_metric=last_metric=None
    min_height=math.inf;max_command=0.;faults=[];last=None;image_visibility_max=0.;max_attempts=0
    for line in(folder/'steps.jsonl').open():
        x=json.loads(line);frames+=1;d=x['result']['diagnostics'];o=x['observation'];action=x['result']['action']
        assert len(action)==6 and all(math.isfinite(v)for v in action)
        assert d.get('direct_radio_controller_bypass_disabled')and d.get('independent_visual_recurrence')
        assert o['mission']['recovery_clearance']['no_dynamic_boat_state']
        assert not o['mission']['home_authorized_for_landing']
        valid+=bool(o['beacon']['valid']);available+=bool(d.get('radio_position_available'))
        if not case['radio']:assert not o['beacon']['valid']and not d.get('radio_position_available')
        counts[d['control_phase']]+=1
        if d.get('metric_valid'):
            metric+=1
            if first_metric is None:first_metric=x['time_s']
            last_metric=x['time_s']
        min_height=min(min_height,x['assessment_only']['drone']['position'][1])
        max_command=max(max_command,math.hypot(*action[:2]))
        image_visibility_max=max(image_visibility_max,d.get('pad_visibility_probability')or 0)
        max_attempts=max(max_attempts,d.get('recovery_attempts')or 0)
        if x['assessment_only']['outcome']and x['assessment_only']['outcome'].get('collision_failure'):faults.append(x['time_s'])
        last=x
    assert max(abs(v) for v in action[:2])<=2.000001
    if case['radio']:assert available>0,'Requested radio condition was not exercised'
    motion=report['boat_motion_assessment'];physical=report['physical_assessment'];speed=motion['final_2s_speed_m_s']
    rows.append(dict(id=case['id'],group=case['group'],radio=case['radio'],status='measured',
        landed=physical['landed'],collision_failure=physical['collision_failure']or bool(faults),
        flight_seconds=report['flight_seconds'],requested_speed_m_s=case['speed'],
        actual_mean_boat_speed_m_s=motion['mean_speed_m_s'],final_2s_speed_m_s=speed,
        first_support_speed_m_s=motion['first_support_speed_m_s'],
        requested_speed_demonstrated=bool(physical['landed']and speed['mean']>=.85*case['speed']and speed['min']>=.75*case['speed']),
        start=report['start_assessment'],stop_reason=report['stop_reason'],phase=report['ml']['phase'],
        metric_frames=metric,first_metric_simulation_s=first_metric,last_metric_simulation_s=last_metric,
        minimum_recorded_true_body_height_m=min_height,max_command_xy_m_s=max_command,
        radio_valid_frames=valid,radio_available_frames=available,frames=frames,
        maximum_image_visibility_probability=image_visibility_max,max_recovery_attempts=max_attempts,
        phases=dict(counts),last_diagnostics=last['result']['diagnostics'],
        physical=physical,trace_sha256=sha(folder/'steps.jsonl'),report_sha256=sha(folder/'report.json')))
    prefix='cases/'+case['id']+'/'
    for name in['report.json','policy.json','boat_motion.json']:
        files[str(folder/name)]=prefix+name
    snapshots=sorted(folder.glob('camera-*.png'))
    for p in snapshots[:1]+snapshots[-1:]:files[str(p)]=prefix+p.name
result=dict(status='completed_audited_tidewater_only_evaluation_no_training',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate_sha256=expected,
    new_tests=len(rows),boat_landings=sum(bool(x.get('landed'))for x in rows),
    collisions=sum(bool(x.get('collision_failure'))for x in rows),
    measured=sum(x['status']=='measured'for x in rows),
    no_training=True,policy_and_runtime_hashes_unchanged=True,world_and_physics_unchanged=True,
    caveats=['One actual Tidewater map/coastal route; exploratory sample, not a population reliability estimate.',
        'Headless Node runs production game graphics/ONNX-WebGPU/WASM/Pyodide/MuJoCo/PX4, not UI-worker scheduler.',
        'Observed XY-command norm can slightly exceed nominal2m/s after existing per-axis slew; record actual maximum without changing the policy.',
        'Speed targets and actual contact speeds differ; highest successful sample is not a universal maximum.',
        'Original18tests started with challenging views; separate higher initially visible starts measure pursuit without conflating initial search.',
        'Radio is the game simulated channel with0.25m coordinate standard deviation, not physical SX1262 hardware.',
        'Collision field uses original game contact/rotor scorer. Recorded body-height audit is separate; no new physics or scoring threshold was introduced.'],
    results=rows)
summary=r/'audited_results.json';assert not summary.exists();summary.write_text(json.dumps(result,indent=2)+'\n')
files[str(summary)]='audited_results.json'
manifest={name:sha(Path(path))for path,name in files.items()}
manifest_path=r/'download_manifest.json';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
archive=r/'compact_results.tar.gz'
with tarfile.open(archive,'x:gz')as t:
    for path,name in sorted(files.items()):t.add(path,arcname=name,recursive=False)
    t.add(manifest_path,arcname=manifest_path.name,recursive=False)
receipt=dict(archive=str(archive),bytes=archive.stat().st_size,sha256=sha(archive),tests=result['new_tests'],landed=result['boat_landings'],collisions=result['collisions'],measured=result['measured'])
(r/'download_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
