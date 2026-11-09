"""Offline, read-only audit of closed semantic review pilots.

Consumes simulator truth only for scoring/annotations. None of the output is
fed back to the controller or changes the raw review recordings.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import math
import os
import tempfile
import h5py
import numpy as np

ROOT = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020')
PILOTS = ROOT / os.environ.get('AUDIT_PILOT_RELATIVE','semantic_pilots')
IS_NEW='search_v33' in str(PILOTS)
EXPECTED_ACTOR=hashlib.sha256((ROOT/'search_v33/sources/target_learning/expert_adapter_v33.py').read_bytes()).hexdigest()if IS_NEW else '7548f06f0a192a4090790135fa4d388117223a5ad8f4b0887f35991a99bcbacb'
EXPECTED_HARNESS=hashlib.sha256((ROOT/'search_v33/sources/run_semantic_collection_v33.py' if IS_NEW else ROOT/'run_semantic_collection_v32.py').read_bytes()).hexdigest()
EXPECTED_RECOGNIZER='c87dca7541d361b183ce45da5f7756bdc5a358aaf544fb2bc5c3fc08bad1e0e3'
NAMES = ('search_near','search_mid','search_far','search_distractors')if IS_NEW else ('visible_start','search_near','search_mid','search_far','search_distractors','yaw_resync','tilt_loss','learner_struggle')
EXCLUDED = {'return_home', 'land_home', 'home_landed', 'home_land', 'return_to_home'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha_image(image):
    return hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()


def angle_diff(a, b):
    return abs(math.atan2(math.sin(a-b), math.cos(a-b)))


def check(checks, name, ok, detail):
    checks.append({'name': name, 'passed': bool(ok), 'detail': detail})


def owner_and_diag(row):
    out = row.get('output') or {}
    diag = out.get('learner_diagnostics') or {}
    if not diag:
        return 'missing', {}
    return diag.get('actual_command_owner', 'missing'), diag


def run_case(name):
    case = PILOTS / name
    checks, errors = [], []
    required = ('scenario.json', 'initial_view_receipt.json', 'capture_annotation_receipt.json',
                'native_hook_bindings.json', 'source_receipt.json', 'summary.json',
                'preview_result.json', 'observations.h5', 'capture_annotations.jsonl',
                'semantic_camera_trace.jsonl', 'steps.jsonl')
    missing = [f for f in required if not (case / f).is_file()]
    check(checks, 'closed artifact set present', not missing, f'missing={missing}')
    if missing:
        return {'name': name, 'status': 'failed', 'checks': checks}
    paths = [case / f for f in required]
    before = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in paths}
    scenario = read_json(case / 'scenario.json')
    initial = read_json(case / 'initial_view_receipt.json')
    capture_receipt = read_json(case / 'capture_annotation_receipt.json')
    bindings = read_json(case / 'native_hook_bindings.json')
    source_receipt = read_json(case / 'source_receipt.json')
    summary = read_json(case / 'summary.json')
    result = read_json(case / 'preview_result.json')
    contract_path = PILOTS / (name + '_contract.json')
    contract = read_json(contract_path)
    ann_by_uid = {}
    ann_by_capture = {}
    for line in (case / 'capture_annotations.jsonl').open(encoding='utf-8'):
        ann = json.loads(line)
        uid = ann['capture_uid']
        if uid in ann_by_uid:
            errors.append('duplicate capture_uid in annotations')
            break
        ann_by_uid[uid] = ann
        ann_by_capture[round(float(ann['capture_s']) * 1_000_000)] = ann
    traces = [json.loads(line) for line in (case / 'semantic_camera_trace.jsonl').open(encoding='utf-8')]
    check(checks, 'observer annotations are isolated',
          capture_receipt.get('actor_input') is False and capture_receipt.get('grants_training_eligibility') is False
          and capture_receipt.get('unbound_capture') is False
          and all(x.get('actor_input') is False and x.get('annotations_grant_training_eligibility') is False for x in ann_by_uid.values()),
          f"captures={capture_receipt.get('captures')} annotations={len(ann_by_uid)} unbound={capture_receipt.get('unbound_capture')}")
    check(checks, 'source/actor/checkpoint bindings match frozen review',
          bindings.get('actor_sha256') == EXPECTED_ACTOR
          and result.get('actor_source_sha256') == bindings.get('actor_sha256')
          and result.get('recognizer_sha256') == EXPECTED_RECOGNIZER
          and capture_receipt.get('provenance', {}).get('harness_source_sha256') == EXPECTED_HARNESS,
          f"actor={bindings.get('actor_sha256')} recognizer={result.get('recognizer_sha256')} harness={capture_receipt.get('provenance', {}).get('harness_source_sha256')}")
    check(checks, 'native hooks and no-radio task input',
          bindings.get('native_px4') == 'main.<locals>.OwnCommandsPX4'
          and bindings.get('renderer') == 'main.<locals>.ActualReviewRenderer'
          and bindings.get('radio_class') == 'main.<locals>.NoRadio'
          and bindings.get('home_samples_required') == 5
          and bindings.get('absent_radio_keeps_search_enabled') is True,
          json.dumps(bindings, sort_keys=True))
    check(checks, 'target present and search view is geometric',
          initial.get('target_present') is True and initial.get('target_removed') is False
          and scenario.get('camera_blind_seconds') == 0
          and scenario.get('target_absent') is not True,
          f"target_present={initial.get('target_present')} removed={initial.get('target_removed')} blind={scenario.get('camera_blind_seconds')} target_absent={scenario.get('target_absent')}")
    lo, hi = contract.get('actual_initial_distance_band_m', [0, float('inf')])
    dist = float(initial.get('horizontal_distance_m', -1))
    check(checks, 'actual initial range in contract', lo <= dist <= hi,
          f'actual={dist:.3f}m contract=[{lo},{hi}]')

    rows = []
    owner_counts = {}
    owner_transitions = []
    previous_owner = None
    frame_mismatches = 0
    unsupported_descent = []
    fault_indices = []
    wrong_metric_candidates = []
    interventions = {}
    max_history_error = 0.0
    min_clearance = float('inf')
    bad_clearance_down = 0
    image_hash_mismatches = 0
    missing_annotations = 0
    duplicate_frames = 0
    first_delivered = None
    target_pixel_counts = []
    metric_valid_count = 0
    identity_confirmed_count = 0
    valid_image_count = 0
    with h5py.File(case / 'observations.h5', 'r') as h5:
        attrs = h5.attrs
        count = int(h5['steps'].shape[0])
        image_count = int(h5['rgb'].shape[0])
        check(checks, 'raw H5 remains review-only', str(attrs.get('role')) == 'review'
              and str(attrs.get('training_eligible')) in ('False', 'false', '0'),
              f"role={attrs.get('role')} training_eligible={attrs.get('training_eligible')}")
        check(checks, 'H5 RGB and step counts match', count == image_count == int(summary.get('records', -1)),
              f'steps={count} rgb={image_count} summary={summary.get("records")}')
        for idx in range(count):
            raw = h5['steps'][idx]
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            row = json.loads(raw)
            rows.append(row)
            if row.get('frame_index') != idx or row.get('role') != 'review':
                frame_mismatches += 1
            obs = row['observation']; out = row['output']; diag_owner, diag = owner_and_diag(row)
            owner_counts[diag_owner] = owner_counts.get(diag_owner, 0) + 1
            if previous_owner is not None and diag_owner != previous_owner:
                owner_transitions.append({'frame': idx, 'from': previous_owner, 'to': diag_owner, 'task_s': row.get('task_time_s')})
            previous_owner = diag_owner
            if out.get('intervention'):
                key = str(out['intervention']); interventions[key] = interventions.get(key, 0) + 1
            action = np.asarray(out.get('executed_action') or [], dtype=float)
            prev = np.asarray(obs.get('previous_executed_action') or [], dtype=float)
            if action.shape != (6,) or prev.shape != (6,) or not np.isfinite(action).all() or not np.isfinite(prev).all():
                errors.append(f'invalid action shape/value frame {idx}')
                continue
            if idx and not row.get('terminal'):
                last = np.asarray(rows[idx-1]['output'].get('executed_action') or [], dtype=float)
                if last.shape == (6,):
                    max_history_error = max(max_history_error, float(np.max(np.abs(last-prev))))
            cap_s = float(obs['image_capture_time_s'])
            if obs.get('image_valid'):
                valid_image_count += 1
                image = h5['rgb'][idx]
                digest = sha_image(image)
                key_us = round(cap_s * 1_000_000)
                ann = ann_by_capture.get(key_us)
                if ann is None or abs(float(ann['capture_s']) - cap_s) > 1e-6:
                    missing_annotations += 1
                elif ann.get('rgb_sha256') != digest:
                    image_hash_mismatches += 1
                if first_delivered is None:
                    first_delivered = {'frame': idx, 'capture_s': cap_s, 'task_s': row.get('task_time_s'),
                                       'sha256': digest, 'annotation_uid': ann.get('capture_uid') if ann else None,
                                       'annotation_target_pixels': next((x.get('pixels', 0) for x in (ann or {}).get('instances', []) if x.get('annotation_instance') == 'target'), 0 if ann is not None else None),
                                       'annotation_identity': next((x.get('identity') for x in (ann or {}).get('instances', []) if x.get('annotation_instance') == 'target'), None)}
                if idx and cap_s == float(rows[idx-1]['observation']['image_capture_time_s']):
                    duplicate_frames += 1
                inst = next((x for x in (ann or {}).get('instances', []) if x.get('annotation_instance') == 'target'), None)
                if inst:
                    target_pixel_counts.append((cap_s, int(inst.get('pixels', 0))))
            if diag.get('metric_valid'):
                metric_valid_count += 1
                candidate = diag.get('metric_candidate') or diag.get('selected_object') or diag.get('target_association')
                if candidate is not None:
                    wrong_metric_candidates.append({'frame': idx, 'candidate': candidate})
            if diag.get('expert_observable_target_confirmed'):
                identity_confirmed_count += 1
            if diag.get('evaluation_fault_active') or diag_owner == 'evaluation_fault':
                fault_indices.append(idx)
            zvel = obs.get('px4', {}).get('velocity_enu_m_s', [0,0,0])[2]
            clearance = float(row.get('privileged', {}).get('clearance_m', float('nan')))
            min_clearance = min(min_clearance, clearance)
            age=diag.get('metric_age_s');sigma=diag.get('metric_uncertainty_m')
            bounded=bool(diag.get('metric_confirmed') and age is not None and float(age)<=.16 and sigma is not None and float(sigma)<=.15)
            if action[2] > .02 and not bounded and not diag.get('terminal_commit_active'):
                bad_clearance_down += 1
                if len(unsupported_descent) < 12:
                    unsupported_descent.append({'frame': idx, 'task_s': row.get('task_time_s'), 'clearance_m': clearance,
                                                'vertical_velocity_enu_m_s': zvel, 'guard_reasons': diag.get('guard_reasons'),
                                                'owner': diag_owner})
    check(checks, 'step indices and roles contiguous', frame_mismatches == 0, f'mismatches={frame_mismatches}')
    check(checks, 'all valid delivered RGB frames have exact annotation SHA/time joins',
          missing_annotations == 0 and image_hash_mismatches == 0,
          f'valid_images={valid_image_count} missing_annotation={missing_annotations} sha_mismatch={image_hash_mismatches}; first={first_delivered}')
    check(checks, 'executed-command history continuity', max_history_error <= 1e-6,
          f'max_abs_error={max_history_error:.3g}')
    check(checks, 'no executed down command without current bounded geometry', bad_clearance_down == 0,
          f'count={bad_clearance_down}; examples={unsupported_descent}')
    trace = traces
    first_trace = trace[0] if trace else None
    discovery = next((x for x in trace[1:] if int(x.get('target_pixels', 0)) > 0), None)
    search_turn = None
    if first_trace and discovery:
        search_turn = {'delta_bearing_deg': math.degrees(angle_diff(float(discovery['view_bearing_rad']), float(first_trace['view_bearing_rad']))),
                       'horizontal_ray_norm_initial': first_trace['horizontal_ray_norm'],
                       'horizontal_ray_norm_at_discovery': discovery['horizontal_ray_norm'],
                       'first_positive_capture_s': discovery['capture_s'],
                       'initial_capture_s': first_trace['capture_s']}
    is_search = contract.get('initial_target') == 'outside_camera'
    first_px = first_delivered.get('annotation_target_pixels') if first_delivered else None
    search_ok = (not is_search) or (first_px == 0 and discovery is not None and search_turn is not None
                and search_turn['delta_bearing_deg'] >= 20
                and min(search_turn['horizontal_ray_norm_initial'], search_turn['horizontal_ray_norm_at_discovery']) >= .2)
    check(checks, 'declared visible/search initial-view purpose',
          (first_px > 0 if contract.get('initial_target') == 'visible' else search_ok),
          f"initial_target={contract.get('initial_target')} first_delivered_target_pixels={first_px} first_discovery={discovery} search_motion={search_turn}")
    scenario_sha = hashlib.sha256((PILOTS / (name + '_scenario.json')).read_bytes()).hexdigest()
    contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    check(checks, 'initial receipt binds declared scenario and contract',
          initial.get('scenario_sha256') == scenario_sha and initial.get('contract_sha256') == contract_sha,
          f"scenario_match={initial.get('scenario_sha256') == scenario_sha} contract_match={initial.get('contract_sha256') == contract_sha}")
    check(checks, 'strict physical scoring status recorded',
          (result.get('outcome')=='development_diagnostic_stop' and summary.get('outcome')=='flying') or summary.get('outcome') in ('landed', 'home_landed', 'water_strike', 'collision_failure', 'abort', 'timeout', 'contact_only'),
          f"outcome={summary.get('outcome')} events={summary.get('events')} max_dock_error_m={summary.get('max_dock_error_m')}")
    check(checks, 'no water/collision terminal', summary.get('outcome') not in ('water_strike', 'collision_failure'),
          f"outcome={summary.get('outcome')} events={summary.get('events')}")
    check(checks, 'no forbidden home phase or command owner',
          not any(r.get('phase') in EXCLUDED for r in rows)
          and not any(o in ('home', 'return_home', 'land_home') for o in owner_counts),
          f'phases={sorted(set(r.get("phase") for r in rows))} owners={owner_counts}')
    check(checks, 'actual fault rows match fault ownership',
          (not result.get('fault_triggered') or (result.get('fault_frames', 0) > 0 and len(fault_indices) > 0))
          and (not fault_indices or all(owner_and_diag(rows[i])[0] == 'evaluation_fault' for i in fault_indices)),
          f"triggered={result.get('fault_triggered')} configured_frames={result.get('fault_frames')} audited_rows={len(fault_indices)}")
    check(checks, 'pilot raw data stays ineligible', result.get('training_eligible') is False
          and summary.get('training_eligible') is False,
          f"preview={result.get('training_eligible')} summary={summary.get('training_eligible')}")
    check(checks, 'summary matches physical terminal and completed raw file',
          (summary.get('outcome') == result.get('outcome') or (summary.get('outcome')=='flying' and result.get('outcome')=='development_diagnostic_stop' and owner_and_diag(rows[-1])[0]=='collection_stop_hold' and np.max(np.abs(rows[-1]['output']['executed_action']))<1e-8))
          and int(summary.get('records', -1)) == len(rows)
          and result.get('physical_flight_completed') is (summary.get('outcome') == 'landed'),
          f"summary={summary.get('outcome')} result={result.get('outcome')} records={summary.get('records')} rows={len(rows)} completed={result.get('physical_flight_completed')}")
    check(checks,'intended boat task physically completed',result.get('outcome')=='landed' and result.get('physical_flight_completed') is True and bool(rows[-1]['observation']['px4'].get('landed')) and not rows[-1]['observation']['px4'].get('armed'),str(result.get('outcome')))
    if contract.get('requires_metric_loss'):
        after_fault=rows[min(fault_indices):]if fault_indices else []
        lost=sum(not owner_and_diag(r)[1].get('metric_valid')for r in after_fault)
        recovery=sum(bool(owner_and_diag(r)[1].get('recovery_active'))for r in after_fault)
        check(checks,'actual loss and recovery exercised',bool(fault_indices)and lost>0 and recovery>0,f'fault={len(fault_indices)} loss={lost} recovery={recovery}')
    if contract.get('requires_teacher_rescue'):
        takeover=[i for i,r in enumerate(rows)if owner_and_diag(r)[0]=='expert'and i>0 and owner_and_diag(rows[i-1])[0]=='policy']
        triggers=[owner_and_diag(rows[i])[1].get('dagger')for i in takeover]
        check(checks,'actual learner struggle precedes latched educational takeover',owner_counts.get('policy',0)>0 and bool(takeover),str(triggers))
    # Re-stat every input to detect concurrent writes during auditing.
    after = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in paths}
    stable = before == after
    check(checks, 'all audited files remained closed and stable', stable, f'changed={[k for k in before if before[k] != after[k]]}')
    return {
        'name': name, 'status': 'passed' if all(x['passed'] for x in checks) else 'failed',
        'checks': checks, 'rows': len(rows), 'valid_delivered_images': valid_image_count,
        'unique_annotations': len(ann_by_uid), 'first_delivered': first_delivered,
        'trace_discovery': discovery, 'search_motion': search_turn,
        'owner_counts': owner_counts, 'owner_transitions': owner_transitions,
        'interventions': interventions, 'fault_rows': fault_indices,
        'fault_frames_reported': result.get('fault_frames'), 'fault_triggered': result.get('fault_triggered'),
        'identity_confirmed_rows': identity_confirmed_count, 'metric_valid_rows': metric_valid_count,
        'min_clearance_m': min_clearance if math.isfinite(min_clearance) else None,
        'unsupported_descent_count': bad_clearance_down, 'unsupported_descent_examples': unsupported_descent,
        'wrong_metric_candidates': wrong_metric_candidates,
        'outcome': summary.get('outcome'), 'task_rows': len(rows), 'wall_s': result.get('wall_s'),
        'training_eligible': result.get('training_eligible'), 'raw_files_before_after': {'stable': stable},
        'errors': errors,
    }


def main():
    state = read_json(PILOTS / 'state.json')
    if state.get('status') not in ['closed_needs_semantic_and_physical_audits','closed_needs_audit'] or state.get('active') or state.get('remaining'):
        raise RuntimeError('Pilot batch is not fully closed; refusing to audit partial files')
    by_name = {x['name']: x for x in state.get('results', [])}
    if set(by_name) != set(NAMES):
        raise RuntimeError(f'Unexpected pilot result set: {sorted(by_name)}')
    start = dt.datetime.now(dt.timezone.utc).isoformat()
    results = [run_case(name) for name in NAMES]
    passed = sum(x['status'] == 'passed' for x in results)
    report = {'schema': 'approved.curriculum.semantic-pilot-audit.v3',
              'started_utc': start, 'finished_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'batch_status': state['status'], 'cases_passed': passed, 'cases_total': len(results),
              'promotion_allowed': False, 'bulk_collection_allowed': False,
              'raw_training_eligibility_granted': False,
              'results': results,
              'known_limits': ['These eight cases use one previously known development world; they are not an independent map benchmark.',
                               'No pilot result changes the historical failed cold-static recognition gate.',
                               'Purpose/ownership gates are diagnostic evidence only until the world/data contract is frozen.']}
    out = PILOTS / 'purpose_audit_report_v3.json'
    tmp = out.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    tmp.replace(out)
    hashes = {}
    for name in NAMES:
        case_report = next(x for x in results if x['name'] == name)
        p = PILOTS / name / 'purpose_audit_v3.json'
        t = p.with_suffix('.json.tmp')
        t.write_text(json.dumps(case_report, indent=2, sort_keys=True, allow_nan=False) + '\n')
        t.replace(p)
        hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    print(json.dumps({'report': str(out), 'cases_passed': passed, 'cases_total': len(results),
                      'by_case': {x['name']: x['status'] for x in results},
                      'first_view': {x['name']: x.get('first_delivered') for x in results}}, indent=2))


if __name__ == '__main__':
    main()
