"""Build an offline-capable dashboard from this suite's own receipts only."""
from pathlib import Path
from .common import ROOT, fingerprint, read, sha, utc, write
from .scoring import aggregate


def build_report():
    inventory = read(ROOT / 'models/inventory.json')
    plan = read(ROOT / 'environments/suite.json')
    runtime_path = ROOT / 'environments/runtime.json'
    runtime_hash = sha(runtime_path) if runtime_path.exists() else None
    policies = {p['id']: p for p in inventory['policies']}
    runs = []
    rejected = []
    for manifest in sorted((ROOT / 'runs').glob('*/run.json')):
        run = read(manifest)
        if run['context']['plan_sha256'] != plan['plan_sha256'] or run['context']['runtime_sha256'] != runtime_hash:
            rejected.append(dict(run=run['id'], reason='Different suite or runtime snapshot; excluded from this comparison.'))
            continue
        scores = {}
        for policy_id in run['policies']:
            if policy_id not in policies:
                rejected.append(dict(run=run['id'], reason='Policy identity is no longer in inventory: '+policy_id))
                continue
            policy = policies[policy_id]
            rows = []
            for result in sorted((manifest.parent / policy_id).glob('*/result.json')):
                row = read(result)
                reasons = []
                if row.get('context') != run['context']:
                    reasons.append('Run context mismatch')
                if row.get('policy_identity_sha256') != policy['identity_sha256'] or row.get('policy_id') != policy_id:
                    reasons.append('Policy identity mismatch')
                if result.parent.name != row.get('case_id') or row.get('case_id') not in run['cases']:
                    reasons.append('Case receipt mismatch')
                if row.get('status') == 'completed':
                    trace = result.parent / 'steps.jsonl'
                    if not trace.exists() or not row.get('trace_sha256') or sha(trace) != row['trace_sha256']:
                        reasons.append('Missing or changed flight trace')
                if reasons:
                    rejected.append(dict(path=str(result.relative_to(ROOT)), reason='; '.join(reasons)))
                else:
                    rows.append(row)
            scores[policy_id] = aggregate(plan, rows)
            scores[policy_id]['trials'] = rows
        runs.append(dict(id=run['id'], created_utc=run['created_utc'], context=run['context'],
                         selected_cases=len(run['cases']), scores=scores))
    payload = dict(schema='aerodock.benchmark.dashboard.v1', generated_utc=utc(),
                   inventory=inventory, suite=plan, runs=runs, rejected=rejected)
    write(ROOT / 'ui/data.json', payload)
    # Script data works over file:// and offline. Escape script delimiters and
    # use textContent in UI for names from paths/manifests.
    import json
    data = json.dumps(payload, ensure_ascii=True, allow_nan=False).replace('<', '\\u003c')
    (ROOT / 'ui/data.js').write_text('window.BENCHMARK_DATA = '+data+';\n', encoding='utf-8')
    print(f'Dashboard: {len(policies)} policy configurations, {len(runs)} comparable runs, {len(rejected)} excluded receipts.')
    return payload


if __name__ == '__main__':
    build_report()
