"""Bounded replay of nominal non-landings; originals and split coverage survive."""
from datetime import datetime, timezone
from pathlib import Path

RETRY_LIMIT = 3
MIN_NOMINAL_LANDING_RATE = .98
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
    rates = {}
    for role in ('training', 'validation', 'test'):
        subset = [row for row in nominal if row['role'] == role]
        if subset:
            rates[role] = sum(row['outcome'] == 'landed' for row in subset) / len(subset)
    passed = not failures or (allow_retried_aborts and len(retained) == len(failures)
                             and all(rate >= MIN_NOMINAL_LANDING_RATE for rate in rates.values()))
    return {'nominal_expert_failures': [row['name'] for row in failures],
            'retry_candidates': candidates, 'retry_exhausted': retained,
            'nominal_landing_rates': rates, 'nominal_quality_passed': passed,
            'quality_warnings': ([f'{len(retained)} nominal non-landings retained after '
                                  f'{RETRY_LIMIT} retries; action imitation is masked.']
                                 if retained and passed else []),
            'retry_policy': {'additional_attempts': RETRY_LIMIT,
                             'minimum_nominal_landing_rate_per_split': MIN_NOMINAL_LANDING_RATE}}
