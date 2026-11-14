"""Build benchmark.json from recorded episodes. Never starts MuJoCo, PX4 or a policy."""
from __future__ import annotations

import math
from pathlib import Path

from .common import ROOT, read, sha, utc, write
from .scoring import aggregate, case_credit, strict_landing
from . import student as student_policy

SCHEMA = 'aerodock.benchmark.track.v1'
TEACHER = 'privileged-teacher-wave-gate-74cfb67e'
STUDENT = 'fresh-search-f62c10a2'
R15 = 'r15-archived-export-67a80a63'
RADIO = 'radio-robust-20261015-policy-bundle-44826e5a'
MODEL_IDS = (TEACHER, STUDENT, R15, RADIO)

MODEL_KIND = {
    TEACHER: 'teacher',
    STUDENT: 'student',
    R15: 'learned',
    RADIO: 'learned',
}

MODEL_NOTE = {
    TEACHER: 'Canonical-plan full-20 evidence from the 9 November wave-gate run.',
    STUDENT: 'Existing 8 November 20-case test plus a canonical combined-rock rerun on 11 November: 18/20 strict landings, 20/20 valid. The 6/6 and 12/14 handoff runs are unioned; the canonical rerun completes the combined category.',
    R15: 'Rerun on the canonical plan.',
    RADIO: 'Rerun on the canonical plan.',
}

MODEL_LABEL = {
    R15: 'R15 / archived export',
    RADIO: 'Radio-robust / 15 October',
}


def canonical_plan():
    return read(ROOT / 'definition/suite.json')


def _inventory():
    return {row['id']: row for row in read(ROOT / 'policies/inventory.json')['policies']}


def _student_row():
    try:
        return student_policy.policy()
    except Exception:
        return dict(id=STUDENT, label='Fresh search student / frozen R15',
                    role='unprivileged learned search policy', identity_sha256=None,
                    architecture='radio_robust', weights={}, available=False, missing=['student source'])


def _models(inventory):
    rows = {}
    for identifier in MODEL_IDS:
        if identifier == STUDENT:
            rows[identifier] = _student_row()
        else:
            rows[identifier] = inventory.get(identifier, dict(
                id=identifier, label=identifier, role='flight policy',
                identity_sha256=None, architecture='unknown', weights={},
                available=False, missing=['model not in inventory']))
    return rows


def _episode_candidates():
    for base in (ROOT / 'evidence', ROOT / 'runs'):
        if base.is_dir():
            for result_path in sorted(base.rglob('result.json')):
                yield result_path


def _episode(result_path, case, expected_identity, plan_sha256):
    result_path = Path(result_path)
    result = read(result_path)
    case_path = result_path.parent / 'case.json'
    steps = result_path.parent / 'steps.jsonl'
    recorded_case = read(case_path) if case_path.exists() else None
    case_match = recorded_case == case
    context = result.get('context') or {}
    source_plan = context.get('plan_sha256')
    canonical = source_plan == plan_sha256
    status = result.get('status')
    trace_ok = None
    if status == 'completed':
        trace_ok = bool(steps.exists() and result.get('trace_sha256')
                        and sha(steps) == result['trace_sha256'])
    identity_ok = expected_identity is None or result.get('policy_identity_sha256') == expected_identity
    scoreable = bool(case_match and identity_ok and status == 'completed'
                     and result.get('condition_valid') is True and trace_ok)
    stamp = str(result.get('completed_utc') or result.get('started_utc') or '')
    return dict(path=result_path, result=result, case_match=case_match, canonical=canonical,
                source_plan=source_plan, trace_ok=trace_ok, identity_ok=identity_ok,
                scoreable=scoreable, timestamp=stamp)


def _rank(episode):
    # Prefer a result that can actually be scored, then a canonical-plan result,
    # then the most recently recorded one.
    return (1 if episode['scoreable'] else 0, 1 if episode['canonical'] else 0,
            episode['timestamp'])


def _source_path(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _case_view(case, categories):
    scenario = case.get('scenario') or {}
    bounded = case.get('bounded_route')
    keys = ('name', 'kind', 'seed', 'world_seed', 'path_seed', 'reverse',
            'world_rotation_deg', 'distance', 'height', 'bearing_deg', 'boat_speed',
            'wind_profile', 'wind_mean_m_s', 'wind_direction_deg', 'wave_height',
            'wave_period', 'wave_direction_deg', 'initial_view', 'initial_tilt_deg',
            'initial_pan_deg', 'initial_camera_target', 'duration', 'stress_test')
    return dict(
        id=case['id'], category=case['category'], map=case['map'], repeat=case['repeat'],
        radio=case['radio'], decoys=case['decoys'], initial_view=case['initial_view'],
        acquisition_deadline_s=case.get('acquisition_deadline_s'),
        speed_reference_s=case.get('speed_reference_s'),
        speed_deadline_s=case.get('speed_deadline_s'),
        extrapolation=case.get('extrapolation'),
        weight=(categories.get(case['category']) or {}).get('weight'),
        condition_tolerance=case.get('condition_tolerance'),
        scenario={key: scenario.get(key) for key in keys},
        bounded_route=(dict(radius_m=bounded.get('radius_m'),
                            decoy_ring_radius_m=bounded.get('decoy_ring_radius_m'),
                            inspection_standoff_m=bounded.get('inspection_standoff_m'))
                       if bounded else None),
    )


def _result_view(episode, case):
    result = episode['result']
    credit = case_credit(case, result) if episode['scoreable'] else None
    landing = strict_landing(result) if episode['scoreable'] else False
    return dict(
        case_id=result.get('case_id'), category=case['category'],
        status=result.get('status'), condition_valid=result.get('condition_valid'),
        outcome=result.get('outcome'), strict_landing=bool(landing),
        verified_acquisition_s=result.get('verified_acquisition_s'),
        mission_time_s=result.get('mission_time_s'),
        final_lateral_error_m=result.get('final_lateral_error_m'),
        touchdown_relative_velocity_m_s=result.get('touchdown_relative_velocity_m_s'),
        task_credit=(credit or {}).get('task'), speed_credit=(credit or {}).get('speed'),
        source=dict(
            path=_source_path(episode['path']),
            result_sha256=sha(episode['path']),
            trace_sha256=result.get('trace_sha256'),
            trace_verified=episode['trace_ok'],
            plan_sha256=episode['source_plan'],
            carried_forward=not episode['canonical'],
            case_definition_match=episode['case_match'],
            policy_identity_match=episode['identity_ok'],
            scoreable=episode['scoreable'],
        ),
    )


def _not_run(case):
    return dict(case_id=case['id'], category=case['category'], status='not_run',
                condition_valid=None, outcome=None, strict_landing=False,
                verified_acquisition_s=None, mission_time_s=None,
                final_lateral_error_m=None, touchdown_relative_velocity_m_s=None,
                task_credit=None, speed_credit=None, source=None)


def _runs():
    runs = []
    for manifest in sorted((ROOT / 'runs').glob('*/run.json')):
        run = read(manifest)
        progress_path = manifest.parent / 'progress.json'
        progress = read(progress_path) if progress_path.exists() else None
        runs.append(dict(
            id=run.get('id') or manifest.parent.name,
            created_utc=run.get('created_utc'),
            plan_sha256=run.get('plan_sha256') or (run.get('context') or {}).get('plan_sha256'),
            runtime_sha256=run.get('runtime_sha256') or (run.get('context') or {}).get('runtime_sha256'),
            device=run.get('inference_device') or (run.get('context') or {}).get('inference_device'),
            workers=run.get('workers'),
            policies=run.get('policies'),
            cases=run.get('cases'),
            progress=(dict(status=progress.get('status'), completed=progress.get('completed'),
                           planned=progress.get('planned'), active=progress.get('active'),
                           updated_utc=progress.get('updated_utc'))
                      if progress else None),
        ))
    return runs


def build():
    plan = canonical_plan()
    cases = {case['id']: case for case in plan['cases']}
    categories = plan['categories']
    inventory = _inventory()
    models = _models(inventory)
    expected = {identifier: row.get('identity_sha256') for identifier, row in models.items()}

    candidates = {}
    warnings = []
    for result_path in _episode_candidates():
        try:
            result = read(result_path)
        except Exception as exc:
            warnings.append(f'Unreadable result {result_path}: {type(exc).__name__}')
            continue
        identifier = result.get('policy_id')
        case_id = result.get('case_id')
        if identifier not in MODEL_IDS or case_id not in cases:
            continue
        episode = _episode(result_path, cases[case_id], expected.get(identifier), plan['plan_sha256'])
        if not episode['case_match']:
            warnings.append(f'Case definition mismatch: {_source_path(result_path)}')
        if not episode['identity_ok']:
            warnings.append(f'Policy identity mismatch: {_source_path(result_path)}')
        if episode['trace_ok'] is False:
            warnings.append(f'Trace hash mismatch: {_source_path(result_path)}')
        key = (identifier, case_id)
        current = candidates.get(key)
        if current is None:
            candidates[key] = episode
        else:
            warnings.append(f'Duplicate result for {identifier} / {case_id}; kept the best receipt.')
            if _rank(episode) > _rank(current):
                candidates[key] = episode

    model_payloads = []
    for identifier in MODEL_IDS:
        model = models[identifier]
        chosen = {case_id: episode for (policy_id, case_id), episode in candidates.items()
                  if policy_id == identifier}
        rows = [episode['result'] for episode in chosen.values() if episode['scoreable']]
        try:
            summary = aggregate(plan, rows)
        except Exception as exc:
            summary = dict(total=None, complete=False, categories={}, valid_cases=0,
                           planned_cases=len(cases), invalid_cases=0, error=f'{type(exc).__name__}: {exc}')
        results = []
        for case in plan['cases']:
            episode = chosen.get(case['id'])
            results.append(_result_view(episode, case) if episode else _not_run(case))
        summary['landings'] = sum(1 for result in results if result['strict_landing'])
        model_payloads.append(dict(
            id=identifier,
            label=MODEL_LABEL.get(identifier) or model.get('label') or identifier,
            role=model.get('role') or MODEL_KIND[identifier],
            kind=MODEL_KIND[identifier],
            identity_sha256=model.get('identity_sha256'),
            architecture=model.get('architecture'),
            actor=model.get('actor'),
            available=model.get('available'),
            missing=model.get('missing') or [],
            weights=len(model.get('weights') or {}),
            note=MODEL_NOTE[identifier],
            coverage=dict(recorded=len(chosen), valid=summary.get('valid_cases'),
                          planned=len(cases)),
            summary=summary,
            results=results,
            sources=[_source_path(episode['path']) for episode in chosen.values()],
        ))

    benchmark = dict(
        id='aerodock-20-wave-gate-3c2b501',
        label='AeroDock 20-case landing benchmark',
        description='Twenty matched MuJoCo/PX4 missions: landing, wind, waves, target acquisition and combined stress.',
        schema=plan['schema'],
        plan_sha256=plan['plan_sha256'],
        suite_path='benchmark/definition/suite.json',
        runtime_sha256=sha(ROOT / 'definition/runtime.json'),
        case_count=len(plan['cases']),
        categories=categories,
        speed_source_categories=plan.get('speed_source_categories'),
        aggregation=plan.get('aggregation'),
        design_note=plan.get('design_note'),
        cases=[_case_view(case, categories) for case in plan['cases']],
    )

    payload = dict(
        schema=SCHEMA,
        updated_utc=utc(),
        benchmark=benchmark,
        models=model_payloads,
        runs=_runs(),
        warnings=warnings[:100],
        notes=[
            'Teacher evidence is the existing verified full-20 run; it is not rerun.',
            'Student evidence is the existing 8 November 20-case test plus the canonical combined-rock rerun on 11 November: 18/20 strict landings, 20/20 valid.',
            'All four models now have canonical-plan coverage; carried-forward evidence is marked per episode.',
            'benchmark/policies is read-only and untouched by the tracker.',
            'Carried-forward results are marked in each result source and are never silently relabelled.',
        ],
    )
    write(ROOT / 'benchmark.json', payload)
    return payload


def main():
    payload = build()
    print('Wrote benchmark/benchmark.json')
    for model in payload['models']:
        total = model['summary'].get('total')
        landings = model['summary'].get('landings', 0)
        print(f"  {model['label']}: {'pending' if total is None else f'{total:.2f}/100'} "
              f"({landings}/{model['coverage']['planned']} landings, "
              f"{model['coverage']['valid']}/{model['coverage']['planned']} valid)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
