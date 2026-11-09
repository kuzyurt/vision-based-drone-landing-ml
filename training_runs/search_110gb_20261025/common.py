"""Shared run contract. Importing this module performs no simulations or writes."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LOCAL = REPO/'artifacts/local_curriculum_20261020'
R15 = REPO/'artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15'
PACKAGE = 'search110_r15'
sys.path.insert(0, str(REPO))


def config():
    return json.loads((HERE/'config.json').read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    os.replace(tmp, path)


def utc():
    return datetime.now(timezone.utc).isoformat()


def tree_bytes(path):
    total=0
    for p in Path(path).rglob('*'):
        try:
            if p.is_file():total+=p.stat().st_size
        except FileNotFoundError:
            # SQLite commit journals can disappear while another worker is
            # being measured. Its full episode reservation still covers it.
            continue
    return total


def weight_path(which):
    return REPO/'benchmark/models/weights'/(config()[which+'_sha256']+'.pt')


def r15_module(suffix):
    if PACKAGE not in sys.modules:
        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(R15/'code/landing_training')]
        sys.modules[PACKAGE] = package
    return importlib.import_module(PACKAGE+'.'+suffix)


def configure_simulation_imports():
    sys.path.insert(0, str(LOCAL))
    import local_paths
    sys.path[:0] = [str(REPO), str(LOCAL), str(LOCAL/'sources')]
    return local_paths


def source_receipt():
    # Previous audit pins identify the connected dependencies, not any old data.
    previous = json.loads((HERE.parent/'long_range_no_radio_20261025/run_spec.json').read_text())
    paths = list(previous['source_pins'])
    paths += ['benchmark/runtime/px4_bridge.mjs',
              'tidewater-game/app/public/landing/wasm/px4.mjs',
              'tidewater-game/app/public/landing/wasm/px4.wasm',
              'tidewater-game/app/public/landing/physics/px4-startup.json']
    paths += [str(p.relative_to(REPO)).replace('\\','/') for p in HERE.glob('*.py')]
    paths += [str((HERE/'config.json').relative_to(REPO)).replace('\\','/')]
    return {p: sha(REPO/p) for p in sorted(set(paths))}


def verify_sources(receipt):
    for path, expected in receipt.items():
        if sha(REPO/path) != expected:
            raise ValueError('Source changed since collection: '+path)
    c = config()
    for which in ('pose', 'spatial'):
        if sha(weight_path(which)) != c[which+'_sha256']:
            raise ValueError('Starting weight hash mismatch: '+which)


def make_plan():
    import numpy as np
    from landing_training.config import Scenario
    from dataclasses import asdict
    c = config()
    maps = ('island','beach','city','gravel','rock')
    weather = ((0.,3.,'calm',0.),(.05,3.,'breeze',2.),(.15,4.5,'gusty',4.))
    distances = (60.,80.,80.,80.,100.,100.,100.,100.,100.,100.)
    counts = ((0,0),(0,3),(3,0),(3,3))
    roles = Counter()
    episodes = []
    for i in range(c['episodes']):
        block, slot = divmod(i,10)
        role = 'validation' if slot==block%10 else 'test' if slot==(block+3)%10 else 'training'
        ordinal = roles[role]; roles[role] += 1
        base = {'training':110000000,'validation':210000000,'test':310000000}[role]
        seed = base+ordinal
        rng = np.random.default_rng(seed)
        wave, period, wind, mean = weather[i%3]
        similar, unsimilar = counts[i%4]
        name = f'{i:03d}_{role}_{maps[slot%5]}'
        scenario = Scenario(name=name, kind=maps[slot%5], seed=seed,
            world_seed=seed+10000000, path_seed=seed+20000000,
            reverse=bool((slot//5+block)%2), world_rotation_deg=float(rng.uniform(0,360)),
            distance=distances[(slot+block)%10], bearing_deg=float(rng.uniform(-180,180)),
            height=6., boat_speed=.6 if i%2 else 0., wave_height=wave, wave_period=period,
            wave_direction_deg=float(rng.uniform(0,360)), wind_profile=wind, wind_mean_m_s=mean,
            wind_direction_deg=float(rng.uniform(0,360)), yaw_offset_deg=float(rng.uniform(-180,180)),
            initial_camera_target=False, initial_pan_deg=float(rng.uniform(-90,90)),
            initial_tilt_deg=float(rng.uniform(-10,90)), duration=float(c['duration_s']))
        episodes.append(dict(id=name, ordinal=i, role=role, scenario=asdict(scenario),
            weather_level=i%3, target_boats=1, false_boat_similar=similar,
            false_boat_unsimilar=unsimilar, decoy_yaws=rng.uniform(-3.141592653589793,3.141592653589793,6).tolist()))
    return episodes


def no_radio_observation(own, gimbal, previous, capture, elapsed, budget):
    # Construct by allowlist; never copy a scorer/teacher/environment dictionary.
    keys = ('valid','position_enu_m','velocity_enu_m_s','attitude_ned_rad',
            'angular_rate_frd_rad_s','position_age_s','attitude_age_s',
            'position_source_boot_ms','attitude_source_boot_ms','armed','landed',
            'gimbal_commanded_rad','gimbal_command_source')
    return dict(px4={k:own[k] for k in keys if k in own}, gimbal_rad=list(gimbal),
        gimbal_source='synthetic_own_encoder', previous_executed_action=list(previous),
        image_capture_time_s=float(capture), image_delivery_time_s=float(capture),
        image_age_s=0., image_valid=True, decision_dt_s=.04,
        mission=dict(elapsed_s=float(elapsed),budget_s=float(budget)))


def check_no_radio(observation):
    if 'beacon' in observation:
        raise ValueError('Boat radio must be absent, including invalid packets')
    allowed = {'px4','gimbal_rad','gimbal_source','previous_executed_action',
               'image_capture_time_s','image_delivery_time_s','image_age_s','image_valid',
               'decision_dt_s','mission'}
    if set(observation)-allowed:
        raise ValueError('Unexpected actor input field')
    own_allowed = {'valid','position_enu_m','velocity_enu_m_s','attitude_ned_rad',
        'angular_rate_frd_rad_s','position_age_s','attitude_age_s','position_source_boot_ms',
        'attitude_source_boot_ms','armed','landed','gimbal_commanded_rad','gimbal_command_source'}
    if set(observation['px4'])-own_allowed:
        raise ValueError('Unexpected own-sensor field')
    mission_allowed = {'elapsed_s','budget_s','recovery_clearance'}
    if set(observation['mission'])-mission_allowed:
        raise ValueError('Unexpected mission input; target priors/coordinates are forbidden')


def dataset_root(value=None):
    return Path(value).expanduser().resolve() if value else HERE/config()['data_directory']


def summary_counts(entries):
    return dict(episodes=len(entries), roles=dict(Counter(e['role'] for e in entries)),
        distances=dict(Counter(str(e['scenario']['distance']) for e in entries)),
        maps=dict(Counter(e['scenario']['kind'] for e in entries)))
