"""Bounded replay of nominal non-landings; originals and split coverage survive."""
from datetime import datetime, timezone
from pathlib import Path

RETRY_LIMIT = 3
MIN_NOMINAL_LANDING_RATE = .98
LANDING_RATE_GATED_SPLITS = ('training', 'validation')
RETRYABLE_OUTCOMES = {'abort', 'timeout', 'contact_only'}


def fault(scenario):
    return any(scenario.get(key, 0) > 0 for key in
               ('camera_blind_seconds', 'beacon_dropout_duration_s', 'dock_unavailable_seconds'))


def prepare_attempt(manifest, root, item):
    """Journal before launching. A pending interrupted attempt keeps its slot."""
    name = item['scenario']['name']
    history = manifest.setdefault('outcome_retries', {}).setdefault(name, [])
    if history and history[-1]['status'] == 'pending':
        attempt = history[-1]
    else:
        if len(history) >= RETRY_LIMIT:
            return None
        attempt = {'number': len(history) + 1, 'status': 'pending',
                   'directory': f'retry_attempts/{name}/attempt_{len(history)+1:03d}',
                   'started_utc': datetime.now(timezone.utc).isoformat()}
        original=next((entry for entry in manifest.get('episodes',[]) if entry['name']==name),None)
        if original:attempt.update(original_path=original['path'],original_outcome=original['outcome'])
        history.append(attempt)
    directory = (Path(root) / attempt['directory']).resolve()
    if not directory.is_relative_to(Path(root).resolve()):
        raise ValueError('Retry directory escapes dataset')
    return attempt, directory


def exhausted(manifest, name):
    history = manifest.get('outcome_retries', {}).get(name, [])
    return len(history) == RETRY_LIMIT and all(
        item['status'] == 'completed' and item['outcome'] in RETRYABLE_OUTCOMES
        for item in history)


def quality(rows, manifest, allow_retried_aborts):
    nominal = [row for row in rows if not row['fault_case']]
    failures = [row for row in nominal if row['outcome'] != 'landed']
    candidates = [row['name'] for row in failures
                  if row['outcome'] in RETRYABLE_OUTCOMES and not exhausted(manifest, row['name'])]
    retained = [row['name'] for row in failures
                if row['outcome'] in RETRYABLE_OUTCOMES and exhausted(manifest, row['name'])]
    rates = {}; counts = {}
    for role in ('training', 'validation', 'test'):
        subset = [row for row in nominal if row['role'] == role]
        if subset:
            landed = sum(row['outcome'] == 'landed' for row in subset)
            rates[role] = landed / len(subset)
            counts[role] = {'episodes': len(subset), 'landed': landed,
                            'non_landings': len(subset) - landed}
    # Test trajectories never provide optimization targets or choose weights.
    # Keep their full scenario coverage and report expert limitations rather
    # than conditioning permission to fit a model on held-out test successes.
    blocking = [role for role in LANDING_RATE_GATED_SPLITS
                if role in rates and rates[role] < MIN_NOMINAL_LANDING_RATE]
    passed = not failures or (allow_retried_aborts and len(retained) == len(failures)
                             and not blocking)
    warnings = ([f'{len(retained)} nominal non-landings retained after '
                 f'{RETRY_LIMIT} retries; action imitation is masked.']
                if retained and passed else [])
    if 'test' in rates and rates['test'] < MIN_NOMINAL_LANDING_RATE:
        warnings.append(f"Held-out test expert landed {counts['test']['landed']}/"
                        f"{counts['test']['episodes']} nominal flights ({rates['test']:.2%}). "
                        'Reported limitation; test expert success does not gate training. '
                        'All test scenarios remain in final policy evaluation.')
    return {'nominal_expert_failures': [row['name'] for row in failures],
            'retry_candidates': candidates, 'retry_exhausted': retained,
            'nominal_landing_rates': rates, 'nominal_outcome_counts': counts,
            'landing_rate_blocking_splits': blocking, 'nominal_quality_passed': passed,
            'quality_warnings': warnings,
            'retry_policy': {'additional_attempts': RETRY_LIMIT,
                             'minimum_nominal_landing_rate_per_split': MIN_NOMINAL_LANDING_RATE,
                             'landing_rate_gated_splits': list(LANDING_RATE_GATED_SPLITS),
                             'test_expert_landing_rate': 'reported, not used to gate fitting or select weights'}}
