"""Summarize actual supplied channels and unchanged physical flight outcomes."""
import collections,hashlib,json,math,statistics,sys
from pathlib import Path

ROOT=Path(sys.argv[1]);QUAL=ROOT.parent/'observable_policy_20261016T203932Z'
plan=json.loads((ROOT/'flights/plan.json').read_text());report=json.loads((ROOT/'flights/report.json').read_text())
assert report['status']=='completed' and report['completed']==9
assert len({json.dumps(j['scenario'],sort_keys=True) for j in plan['cases']})==1
results=[]
for job in plan['cases']:
    d=Path(job['directory']);result=json.loads((d/'result.json').read_text())
    assert not result['infrastructure_error'],result
    summary=json.loads((d/'summary.json').read_text())
    counts=collections.Counter();first=None;last=None;teacher_nonzero=0
    with (d/'steps.jsonl').open() as f:
        for line in f:
            row=json.loads(line)
            if row.get('terminal'):continue
            if first is None:first=row
            last=row
            out=row['output'];diag=out['learner_diagnostics']
            if any(abs(v)>1e-10 for v in out['expert_raw_action']):teacher_nonzero+=1
            counts['frames']+=1
            for k in ['radio_position_available','radio_controller_trusted','entire_radio_input_removed','metric_valid']:
                counts[k]+=int(bool(diag.get(k)))
            counts['fit_'+str(diag.get('metric_acceptance'))]+=1
            if job['radio_setting']['kind']=='absent':
                assert diag['entire_radio_input_removed'] and not diag['radio_position_available']
                assert 'relative_heading_m' not in row['observation']['beacon']
            else:
                assert not diag['entire_radio_input_removed']
                assert row['observation']['beacon']['valid']
                assert len(row['observation']['beacon']['relative_heading_m'])==3
                counts['supplied_radio_frames']+=1
                # Physical return-home overrides intentionally stop calling the
                # boat controller; the incoming packet still exists in its log.
                if not diag.get('mission_fallback_active',False):
                    assert diag['radio_position_available']
                    assert diag['radio_position_sigma_m']==job['radio_setting']['reported_sigma_m']
                    assert diag['radio_controller_trusted']==(job['radio_setting']['reported_sigma_m']<=1.5)
    assert teacher_nonzero==0
    start=first['time_s']-first['task_time_s']
    events=summary.get('events',[])
    terminal=[e for e in events if e['kind'] in ['landed','home_landed','collision_failure','water_strike']]
    finish=(terminal[-1]['time_s']-start) if terminal else result['task_seconds']
    contact=[e['time_s']-start for e in events if e['kind']=='touchdown']
    noise=[]
    if (d/'radio_packets.jsonl').exists():
        noise=[json.loads(l) for l in (d/'radio_packets.jsonl').read_text().splitlines()]
    measured={}
    if noise:
        errors=[v['error_enu_m'] for v in noise]
        measured=dict(packets=len(noise),mean_error_enu_m=[statistics.mean(e[i] for e in errors) for i in range(3)],
            rms_3d_error_m=math.sqrt(statistics.mean(sum(v*v for v in e) for e in errors)),
            max_abs_coordinate_error_m=max(abs(v) for e in errors for v in e))
        if job['radio_setting']['kind']=='uniform':assert measured['max_abs_coordinate_error_m']<=5
    results.append(dict(condition=job['source_case'],radio_setting=job['radio_setting'],
        outcome=result['outcome'],boat_landed=result['outcome']=='landed',task_seconds_to_outcome=finish,
        touchdown_seconds=contact[0] if contact else None,wall_seconds=result['wall_seconds'],
        first_metric_s=result['first_metric_s'],diagnostic_counts=dict(counts),sensor_error_measurements=measured,
        events=events,teacher_action_frames=teacher_nonzero))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
launch=json.loads((ROOT/'launch.json').read_text())
assert sha(QUAL/'bundle_spatial_r8/policy.json')==launch['qualified_policy_sha256']
helpers=['mission_safety_r8.py','mission_integration.py','mission_setup.py']
assert all(sha(ROOT/n)==sha(QUAL/n) for n in helpers)
qualified=json.loads((QUAL/'bundle_spatial_r8_qualification_sources.json').read_text())
assert qualified['evaluate_development.py']==sha(QUAL/'evaluate_r8.py')
for canonical,actual in [('mission_safety.py','mission_safety_r8.py'),('mission_integration.py','mission_integration.py'),('mission_setup.py','mission_setup.py')]:
    assert qualified[canonical]==sha(QUAL/actual)
receipt=dict(status='completed_and_audited',root=str(ROOT),same_scenario_all_conditions=True,
    results=results,qualified_sources_unchanged=True,teacher_task_actions_used=False,training=False,
    suite_wall_seconds=report['wall_seconds'],source_files={p.name:sha(p) for p in ROOT.glob('*.py')},
    timing='Simulation seconds from policy handover after takeoff to strict physical support/disarm outcome; no boat landing for home_landed/timeout/abort.',
    default_radio='1 Hz Gaussian independent xyz sigma .25m, velocity xyz sigma .025m/s; sigma is not a hard +/- bound.',
    limitations='One flight per condition in one reused beach scene, not a new reliability estimate or qualification. PX4 scheduling can introduce small between-flight variation. Gaussian/uniform uncertainty is reported honestly; bias faults deliberately claim sigma .25m. Runtime discards direct controller radio above reported sigma 1.5m; neural input still receives supplied values and uncertainty. No-radio entire packet removed.')
(ROOT/'audited_report.json').write_text(json.dumps(receipt,indent=2))
lines=['# Radio position characterization','','Same moving-boat beach scene, 20m start, boat 0.6m/s, gusty wind, 3cm waves. Existing R8 weights/controller unchanged.','','Times are simulated policy-flight seconds, excluding takeoff preparation, including stable support and PX4 disarm.','','| Condition | Boat landed? | Outcome | Time (s) | First physical boat contact (s) |','|---|---|---|---:|---:|']
for r in results:
    contact='—' if r['touchdown_seconds'] is None else f"{r['touchdown_seconds']:.1f}"
    lines.append(f"| {r['condition']} | {'Yes' if r['boat_landed'] else 'No'} | {r['outcome']} | {r['task_seconds_to_outcome']:.1f} | {contact} |")
lines+=['',receipt['default_radio'],'',receipt['limitations'],'',f"Batch wall time: {report['wall_seconds']/60:.1f} minutes. Detailed input, noise, event and source audits are in audited_report.json."]
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(status=receipt['status'],results=[{k:r[k] for k in ['condition','outcome','task_seconds_to_outcome','touchdown_seconds','first_metric_s']} for r in results],suite_wall_seconds=report['wall_seconds']),indent=2))
