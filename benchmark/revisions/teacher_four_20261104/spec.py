"""A targeted four-case teacher rerun on the 2026-10-26 revision.

The plan is the bounded-search v4 plan with one geometry change in the
combined case only. The wave gate is a policy change, not a scenario change,
and lives in a new teacher policy identity.
"""
import copy
import importlib
from pathlib import Path

from benchmark.common import ROOT, read, write, sha, fingerprint, utc

HERE = Path(__file__).resolve().parent
BASE = importlib.import_module('benchmark.revisions.bounded_search_20261026.spec')
COMBINED = 'combined-stress-visual-traffic-rock-r0-bounded-v1'
RUN_CASES = (
    'acquisition-far-visual-traffic-city-r0-bounded-v1',
    'acquisition-far-visual-traffic-rock-r1-bounded-v1',
    COMBINED,
    'waves-waves-moderate-gravel-r0',
)


def build_plan():
    base = BASE.build_plan()
    plan = copy.deepcopy(base)
    plan.pop('plan_sha256')
    plan.update(
        schema='aerodock.benchmark.mission.v4-bounded-search',
        revision='teacher_four_20261104',
        parent_plan_sha256=base['plan_sha256'],
        design_note=(
            'Targeted teacher rerun on the four cases the frozen teacher failed. '
            'Only the combined bounded case changes geometry: orbit radius 14 m, '
            'decoy ring 22 m, inspection standoff 20.5 m. The wave case is '
            'unchanged and the wave-aware gate is a separate teacher policy. '
            'The other sixteen bounded-search cases and all historical results '
            'are unchanged.'
        ),
        visibility_scope=(
            'The combined-case local inspection range is 20.5 + 22 + 14 + 3 m '
            'plus the target pad offset, below the measured 60 m detection limit.'
        ),
    )
    case = next(c for c in plan['cases'] if c['id'] == COMBINED)
    case['bounded_route'].update(
        radius_m=14.0,
        decoy_ring_radius_m=22.0,
        inspection_standoff_m=20.5,
    )
    plan['plan_sha256'] = fingerprint(plan)
    return plan


def prepare():
    plan = build_plan()
    write(HERE / 'suite.json', plan)
    write(HERE / 'source_receipts.json', dict(
        created_utc=utc(),
        original_runtime_sha256=sha(ROOT / 'environments/runtime.json'),
        sources=[dict(path=str(p.relative_to(ROOT.parent)).replace('\\', '/'), sha256=sha(p))
                 for p in sorted(HERE.glob('*.py'))],
        suite_sha256=sha(HERE / 'suite.json'),
        calibration_sha256=sha(HERE / 'visibility_calibration.json'),
    ))
    print('Prepared the targeted 4-case revision; no flight or policy inference launched.')
    return plan


def verify():
    from benchmark.common import REPO
    receipt = read(HERE / 'source_receipts.json')
    if read(HERE / 'suite.json') != build_plan():
        raise ValueError('Revision suite differs from its source specification')
    if sha(ROOT / 'environments/runtime.json') != receipt['original_runtime_sha256']:
        raise ValueError('Original runtime changed')
    for item in receipt['sources']:
        if sha(REPO / item['path']) != item['sha256']:
            raise ValueError('Revision source changed: ' + item['path'])
    if sha(HERE / 'visibility_calibration.json') != receipt['calibration_sha256']:
        raise ValueError('Visibility measurement changed')
    if sha(HERE / 'suite.json') != receipt['suite_sha256']:
        raise ValueError('Suite receipt changed')
    return read(HERE / 'suite.json')
