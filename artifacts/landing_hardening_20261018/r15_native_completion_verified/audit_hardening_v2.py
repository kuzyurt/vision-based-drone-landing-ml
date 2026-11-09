"""Read-only audit of completed flights; truth is used here for scoring only."""
from pathlib import Path
import argparse, collections, hashlib, json, math, statistics

ROOT = Path(__file__).resolve().parent
BASE = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
PARENT = BASE/'landing_training/outputs/vision_first_fusion_20261017T184307Z/candidate'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def audit(cohort):
    folder = ROOT/cohort
    report = json.loads((folder/'report.json').read_text())
    assert report['status'] == 'completed'
    plan = json.loads((folder/'plan.json').read_text())
    bundle = Path(report['bundle'])
    config = json.loads((bundle/'policy.json').read_text())
    assert sha(bundle/'pose.pt') == config['checkpoint_sha256']
    assert sha(bundle/'spatial_acquisition.pt') == config['spatial_checkpoint_sha256']
    for name, expected in config['file_hashes'].items():
        if '__pycache__' not in name:
            assert sha(bundle/name) == expected, name
    for name, expected in json.loads((ROOT/'parent_hashes.json').read_text()).items():
        assert sha(PARENT/name) == expected, ('changed parent', name)
    for name, expected in json.loads((ROOT/'baseline_source_hashes.json').read_text()).items():
        assert sha(BASE/name) == expected, ('changed original source', name)
    details = []
    for result in report['results']:
        assert result.get('infrastructure_error') is None, result
        case = Path(result['directory'])
        job = next(j for j in plan['cases'] if j['source_case'] == result['name'])
        controller = json.loads((case/'controller.json').read_text())
        assert controller['policy_sha256'] == sha(bundle/'policy.json')
        for name, expected in controller['mission_source_sha256'].items():
            assert sha(folder/'mission_sources'/name) == expected, name
        summary = json.loads((case/'summary.json').read_text())
        assert summary['scenario'] == job['scenario']
        assert summary['physics_timestep_s'] == .001
        assert summary['role'] == 'review' and not summary['training_eligible']
        assert summary['scenario']['wave_height'] <= .05
        assert summary['outcome'] == result['outcome']
        assert summary['outcome'] not in ['collision_failure', 'water_strike']
        events = [e['kind'] for e in summary['events']]
        assert not any('collision' in k or 'water_strike' in k for k in events)
        loss_frames = recovered_frames = climbs = height_vetoes = 0
        max_attempts = 0
        last = None
        for line in (case/'steps.jsonl').open():
            row = json.loads(line)
            if row.get('terminal'):
                continue
            o, output = row['observation'], row['output']
            d, p = output['learner_diagnostics'], o['px4']
            assert d.get('entire_radio_input_removed') is True
            assert not o['beacon'].get('valid') and not d.get('radio_position_available')
            assert not d.get('radio_controller_trusted')
            if d.get('mission_fallback_active'):
                assert o['mission']['home_authorized_for_landing']
                assert d['mission_home_source'] == 'own PX4 observations on declared launch pad before takeoff'
                assert not d.get('boat_truth_used', False)
            else:
                assert d.get('direct_radio_controller_bypass_disabled')
            assert all(abs(float(v)) < 1e-12 for v in output['expert_raw_action'])
            assert all(math.isfinite(float(v)) for v in output['executed_action'])
            max_attempts = max(max_attempts, d.get('recovery_attempts', 0))
            assert max_attempts <= 2
            phase = d['control_phase']
            if d.get('recovery_active'):
                recovered_frames += 1
                assert output['executed_action'][2] <= 1e-9
            if phase == 'recovery_climb':
                climbs += 1
                c = o['mission']['recovery_clearance']
                assert c['valid'] and c['no_dynamic_boat_state']
                assert d['recovery_goal_altitude_enu_m'] + .2 <= c['max_altitude_enu_m'] + 1e-9
                assert d['recovery_goal_altitude_enu_m'] <= 10.0 + 1e-9
            eligible_loss = (d.get('visual_memory_established') and d.get('metric_age_s', 0) > .160001
                and p.get('valid') and p.get('armed') and not p.get('landed')
                and not d.get('mission_fallback_active') and not d.get('intervention')
                and phase not in ['touchdown_commit', 'confirm', 'disarmed'])
            if eligible_loss:
                loss_frames += 1
                assert d.get('recovery_active'), (result['name'], row['frame_index'], 'unprotected metric loss')
            context = d.get('metric_physical_height_context', {})
            if context.get('available') and not context.get('compatible', True):
                height_vetoes += 1
                assert not d.get('metric_valid')
            last = row
        assert last is not None
        p = last['observation']['px4']
        if result['outcome'] == 'landed':
            assert all(k in events for k in ['touchdown', 'stable_contact', 'landed'])
            assert p['landed'] and not p['armed']
        elif result['outcome'] == 'home_landed':
            assert 'home_landed' in events and p['landed'] and not p['armed']
        details.append(dict(name=result['name'], map=job['scenario']['kind'], outcome=result['outcome'],
            flight_s=result['task_seconds'], protected_metric_loss_frames=loss_frames,
            recovery_s=recovered_frames*.04, climb_s=climbs*.04, maximum_climbs=max_attempts,
            physically_incompatible_fits_rejected=height_vetoes,
            optical_fault_triggered=result.get('camera_fault_triggered',False),
            optical_fault_trigger_count=result.get('camera_fault_trigger_count',0),
            trace_sha256=sha(case/'steps.jsonl'), summary_sha256=sha(case/'summary.json')))
    bymap = {}
    for d in details:
        bymap.setdefault(d['map'], collections.Counter())[d['outcome']] += 1
    times = [d['flight_s'] for d in details if d['outcome'] == 'landed']
    result = dict(status='audited', cohort=cohort, role=plan['role'], candidate_sha256=sha(bundle/'policy.json'),
        outcomes=dict(collections.Counter(d['outcome'] for d in details)), maps={k:dict(v) for k,v in bymap.items()},
        faults_triggered=sum(d['optical_fault_triggered'] for d in details),
        median_boat_flight_s=statistics.median(times) if times else None,
        range_boat_flight_s=[min(times),max(times)] if times else None,
        details=details, original_sources_and_parent_unchanged=True,
        neural_weights_unchanged=True, radio_task_inputs=False, teacher_task_actions=False,
        physical_outcome_scoring=True, new_training=False,
        limitations=['Simulation only; finite tested scenes.',
            'Own navigation and declared static map/datum are available; camera-only does not mean no own telemetry.',
            'Static upward corridor is a veto, not full dynamic obstacle avoidance.',
            'No unconditional crash-proof or hardware reliability claim.'])
    path = folder/'hardening_audit.json'
    assert not path.exists()
    path.write_text(json.dumps(result,indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='details'}))

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('cohort'); audit(p.parse_args().cohort)
