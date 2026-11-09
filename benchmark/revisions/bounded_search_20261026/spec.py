"""The old 20-case suite plus exactly three explicitly versioned replacements."""
import copy
from pathlib import Path
from benchmark.common import ROOT, read, write, sha, fingerprint, utc

HERE=Path(__file__).resolve().parent
REPLACEMENTS=('acquisition-far-visual-traffic-city-r0',
              'acquisition-far-visual-traffic-rock-r1',
              'combined-stress-visual-traffic-rock-r0')


def build_plan():
    original=read(ROOT/'environments/suite.json')
    calibration=read(HERE/'visibility_calibration.json')
    bound=next(b for b in calibration['bins'] if b['distance_m']==60)
    if not bound['all_detectable']:raise ValueError('60 m must pass the actual rendered calibration')
    config=dict(radius_m=12.,waypoint_spacing_m=.5,cross_track_limit_m=3.,shore_buffer_m=1.,
        navigation_lookahead_m=9.,navigation_lookahead_s=5.,turn_boost_below_speed_m_s=.25,
        decoy_ring_radius_m=20.,decoy_angles_from_outward_deg=[-120.,-72.,-24.,24.,72.,120.],
        minimum_decoy_separation_m=5.,maximum_nearest_decoy_m=20.,
        inspection_standoff_m=24.,safe_detection_range_m=60.,
        reference_search_range_m=[15.,60.],
        detection_threshold=dict(minimum_visible_pixels=24,minimum_extent_px=8),
        observation_condition='Target inside the actual camera without occlusion; under 15 m the existing inspection gimbal must aim down.',
        calibration_sha256=sha(HERE/'visibility_calibration.json'))
    plan=copy.deepcopy(original)
    plan.pop('plan_sha256')
    plan.update(schema='aerodock.benchmark.mission.v4-bounded-search',
        revision='bounded_search_20261026',parent_plan_sha256=original['plan_sha256'],
        calibration_sha256=config['calibration_sha256'],
        design_note='Only the three specified zero-radio decoy cases have fixed moving orbits and safe nearby static decoys. Other seventeen cases are unchanged. Historical results cannot be relabelled as this suite.',
        visibility_scope='Geometry feasibility around a local decoy inspection area; not guaranteed visibility outside the FOV or from an arbitrary drone path.')
    for case in plan['cases']:
        if case['id'] in REPLACEMENTS:
            original=case['id']
            case['supersedes_case_id']=original;case['id']=original+'-bounded-v1'
            case['scenario']['name']=case['id'];case['bounded_route']=copy.deepcopy(config)
    plan['plan_sha256']=fingerprint(plan)
    return plan


def prepare():
    plan=build_plan();write(HERE/'suite.json',plan)
    write(HERE/'source_receipts.json',dict(created_utc=utc(),original_runtime_sha256=sha(ROOT/'environments/runtime.json'),
        sources=[dict(path=str(p.relative_to(ROOT.parent)).replace('\\','/'),sha256=sha(p)) for p in sorted(HERE.glob('*.py'))],
        suite_sha256=sha(HERE/'suite.json'),calibration_sha256=sha(HERE/'visibility_calibration.json')))
    print('Prepared 20-case revision; exactly three cases replaced. No flight or policy inference launched.')
    return plan


def verify():
    from benchmark.common import REPO
    receipt=read(HERE/'source_receipts.json')
    if read(HERE/'suite.json')!=build_plan():raise ValueError('Revision suite differs from its source specification')
    if sha(ROOT/'environments/runtime.json')!=receipt['original_runtime_sha256']:raise ValueError('Original runtime changed')
    for item in receipt['sources']:
        if sha(REPO/item['path'])!=item['sha256']:raise ValueError('Revision source changed: '+item['path'])
    if sha(HERE/'visibility_calibration.json')!=receipt['calibration_sha256']:raise ValueError('Visibility measurement changed')
    if sha(HERE/'suite.json')!=receipt['suite_sha256']:raise ValueError('Suite receipt changed')
    return read(HERE/'suite.json')
