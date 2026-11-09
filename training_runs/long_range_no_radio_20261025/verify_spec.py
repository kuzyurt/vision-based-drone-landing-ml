"""Materialize/audit a proposed run. Never collect, train, or launch PX4."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
POSE_HASH = '2a1cf3a289fb9c3fb50146f949560f63fabcd90a3351d08d5059fe10046619c4'
SPATIAL_HASH = 'b432c1584b778d1959e950e855fcdf78c468d7f5ec7e86b71641f5052a6ce14b'
POLICY_ID = 'r15-archived-export-67a80a63'
R15 = 'artifacts/approved_curriculum_20261020/candidate_exports/experimental_v39/package/base_r15'
MISSION = 'artifacts/landing_hardening_20261018/r15_native_completion_verified/r15_fresh_E60/mission_sources'
MAPS = ('island', 'beach', 'city', 'gravel', 'rock')
WEATHER = (
    dict(id='W0', wave_height=0., wave_period=3., wind_profile='calm', wind_mean_m_s=0.),
    dict(id='W1', wave_height=.05, wave_period=3., wind_profile='breeze', wind_mean_m_s=2.),
    dict(id='W2', wave_height=.15, wave_period=4.5, wind_profile='gusty', wind_mean_m_s=4.),
)
DENSITIES = (
    dict(id='D0', target_boats=1, false_boat_similar=0, false_boat_unsimilar=0),
    dict(id='D1', target_boats=1, false_boat_similar=0, false_boat_unsimilar=3),
    dict(id='D2', target_boats=1, false_boat_similar=3, false_boat_unsimilar=0),
    dict(id='D3', target_boats=1, false_boat_similar=3, false_boat_unsimilar=3),
)
SOURCE_PATHS = [
    'benchmark/__main__.py', 'benchmark/runner.py', 'benchmark/actors.py',
    'benchmark/suite.py', 'benchmark/scoring.py', 'benchmark/teacher_policy.json',
    'benchmark/environments/runtime.json',
    'landing_training/config.py', 'landing_training/environment.py',
    'landing_training/expert.py', 'landing_training/privileged_teacher.py',
    'landing_training/smooth_landing.py', 'landing_training/recording.py',
    'landing_training/rendering.py', 'landing_training/scene.py',
    'landing_training/px4.py', 'landing_training/paths.py',
    'AERODOCK_MuJoCo/usv/procedural_world.py', 'AERODOCK_MuJoCo/usv/boat_sim.py',
    'px4-mujoco-drone-simulation/sim/environment.py',
    'px4-mujoco-drone-simulation/sim/propulsion.py',
    'artifacts/local_curriculum_20261020/local_paths.py',
    'artifacts/local_curriculum_20261020/review_helpers.py',
    'artifacts/local_curriculum_20261020/windows_renderer.py',
    'artifacts/local_curriculum_20261020/windows_px4_v2.py',
    'artifacts/local_curriculum_20261020/windows_kernels.py',
    'artifacts/local_curriculum_20261020/fast_physics_windows.py',
    'artifacts/local_curriculum_20261020/physics_math.dll',
    'artifacts/local_curriculum_20261020/sources/target_learning/scenes.py',
    'artifacts/local_curriculum_20261020/sources/target_learning/label_renderer.py',
    'artifacts/teacher_scan_modes_20261024/run_privileged_review.py',
    'artifacts/city80_decoys_20261023/scene_spec.py',
    'artifacts/city80_decoys_20261023/build_scene.py',
    'artifacts/city80_decoys_20261023/scene.xml',
    'artifacts/city80_decoys_20261023/scene.mjb',
    f'{MISSION}/mission_setup.py', f'{MISSION}/mission_safety.py',
    f'{R15}/policy.json',
    'artifacts/landing_hardening_20261018/candidate_r15/policy.json',
    'tidewater-game/app/public/policy/manifest.json',
    'tidewater-game/app/public/policy/reference/browser_api.py',
    'tidewater-game/app/src/landing/PolicyControl.js',
    'tidewater-game/app/src/landing/PolicyInference.js',
    'tidewater-game/app/src/landing/PolicyInferenceWorker.js',
    'tidewater-game/app/src/landing/PolicyTelemetry.js',
]
MODEL_SOURCES = (
    'runtime.py', 'runtime_fixes.py', 'model.py', 'parent_model.py',
    'spatial_acquisition.py', 'native_marker.py', 'marker_kernel.cpp',
    'controller/marker_policy.py', 'controller/marker_geometry.py',
    'controller/marker_geometry_fast.py', 'controller/hybrid_policy.py',
    'controller/observable_acquisition.py', 'controller/visual_acquisition.py',
    'controller/camera_geometry.py', 'controller/camera_geometry_fast.py',
    'controller/action_guard.py', 'controller/supervision.py',
    'controller/recording.py', 'controller/persistent_target.py',
    'controller/visibility_recovery.py', 'controller/nearfield_visibility.py',
    'controller/approach_envelope.py', 'controller/physical_pose_context.py',
    'controller/camera_obstruction_map.json',
)
SOURCE_PATHS += [f'{R15}/code/landing_training/radio_robust_20261015/{p}' for p in MODEL_SOURCES]
SOURCE_PATHS += [f'{R15}/code/landing_training/{p}' for p in ('policy.py', 'pose_model.py', 'recording.py')]


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def inventory_policy():
    inventory = json.loads((REPO/'benchmark/models/inventory.json').read_text())
    return next(p for p in inventory['policies'] if p['id'] == POLICY_ID)


def proposed_spec():
    policy = inventory_policy()
    weights = {name: dict(path='benchmark/'+policy['weights'][name]['path'],
                         sha256=expected)
               for name, expected in [('pose.pt', POSE_HASH), ('spatial_acquisition.pt', SPATIAL_HASH)]}
    pins = {p: digest(REPO/p) for p in SOURCE_PATHS}
    return dict(
        schema='drone_landing.next_run_spec.v1', date_local='2026-10-25', timezone='Europe/Berlin',
        objective='long-range visual boat discovery and decoy discrimination; no boat telemetry',
        status='specified_requires_new_collector_trainer_and_student_adapter',
        collection_or_training_started=False, pretrained_weights_only_reuse=True,
        old_dataset_records_allowed=0, old_feature_or_crop_records_allowed=0,
        policy_id=POLICY_ID, policy_manifest=policy['manifest']['path'],
        policy_source_root=policy['source_root'], teacher='landing_training/privileged_teacher.py',
        initialization=weights, source_pins=pins,
        maps=list(MAPS), weather=list(WEATHER), density_aliases=list(DENSITIES),
        distance_blocks=[dict(distance=60., blocks=1), dict(distance=80., blocks=3), dict(distance=100., blocks=6)],
        episodes=dict(total=1200, training=960, validation=120, test=120),
        task_duration_s=240., decision_dt_s=.04, control_hz=25, physics_dt_s=.001,
        max_steps_per_episode=6000, max_decision_rgb_pairs=7200000,
        raw_rgb_max_bytes=4976640000000, rgb_storage_with_20_percent_headroom_bytes=5971968000000,
        teacher_control_fraction=1., action_imitation_loss_weight=0., boat_radio_fraction=0.,
        allow_visual_landing=True, identity_supervision='resolved evidence plus 0.16 s sustained support only',
        proposed_search_module=dict(new_module=True, base_frozen=True, evidence_classes=4,
            resolved_identity_classes=2, seed=20261025, epochs=15, batch_frames=64,
            optimizer='AdamW', learning_rate=.0003, weight_decay=.0001, gradient_clip_norm=1.),
        execution_prerequisites=['fresh_training_collector', 'masked_multi_instance_trainer',
            'sensor_only_search_runtime', 'current_source_bound_pilot_and_integration_checks'],
        output_directory='training_runs/long_range_no_radio_20261025/fresh_data',
    )


def planned_episodes():
    import numpy as np
    from landing_training.config import Scenario
    counters = Counter()
    result = []
    serial = 0
    bases = {'training': (10000000, 20000000, 30000000),
             'validation': (40000000, 50000000, 60000000),
             'test': (70000000, 80000000, 90000000)}
    for distance, blocks in ((60., 1), (80., 3), (100., 6)):
        for weather in WEATHER:
            for density in DENSITIES:
                for block in range(blocks):
                    val_slot = serial % 10
                    test_slot = (val_slot+1) % 10
                    for slot in range(10):
                        role = 'validation' if slot == val_slot else 'test' if slot == test_slot else 'training'
                        ordinal = counters[role]
                        counters[role] += 1
                        seed, world_seed, path_seed = (x+ordinal for x in bases[role])
                        rng = np.random.default_rng(seed)
                        identifier = f'{role}_{ordinal:04d}'
                        scenario = Scenario(name=identifier, kind=MAPS[slot//2],
                            seed=seed, world_seed=world_seed, path_seed=path_seed,
                            reverse=bool((slot//2+serial) % 2),
                            world_rotation_deg=float(rng.uniform(0., 360.)),
                            distance=distance, bearing_deg=float(rng.uniform(-180., 180.)),
                            height=6., boat_speed=.6 if slot % 2 else 0.,
                            wave_height=weather['wave_height'], wave_period=weather['wave_period'],
                            wave_direction_deg=float(rng.uniform(0., 360.)),
                            wind_profile=weather['wind_profile'], wind_mean_m_s=weather['wind_mean_m_s'],
                            wind_direction_deg=float(rng.uniform(0., 360.)),
                            yaw_offset_deg=float(rng.uniform(-180., 180.)),
                            initial_camera_target=False, initial_pan_deg=float(rng.uniform(-90., 90.)),
                            initial_tilt_deg=float(rng.uniform(-10., 90.)), duration=240.)
                        result.append(dict(id=identifier, role=role, weather=weather['id'],
                            density=dict(density), curriculum_distance_m=distance,
                            block=serial, scenario=asdict(scenario),
                            decoy_yaw_rad=[float(rng.uniform(-math.pi, math.pi)) for _ in range(6)],
                            radio='off', teacher_controlled=True, fresh_data_required=True))
                    serial += 1
    return result


def manifest_bytes(episodes):
    return (''.join(encoded(e)+'\n' for e in episodes)).encode('utf-8')


def check(spec, episodes):
    from benchmark.runner import make_scenario
    from landing_training import paths  # sibling import roots, no simulator construction
    from usv.procedural_world import KINDS
    from sim.environment import PROFILES
    for key, value in proposed_spec().items():
        assert spec[key] == value, f'Spec differs from reviewed definition: {key}'
    assert tuple(spec['maps']) == MAPS and set(MAPS) == set(KINDS)
    for name, expected in spec['source_pins'].items():
        assert digest(REPO/name) == expected, f'Changed source: {name}'
    assert set(spec['source_pins']) == set(SOURCE_PATHS)
    policy = inventory_policy()
    assert policy['manifest']['path'] == spec['policy_manifest']
    assert policy['source_root'] == spec['policy_source_root']
    assert digest(REPO/spec['policy_manifest']) == '5543ee9eaa419400e5a239d6c2bb1c08e9344fa57cf181811f90e0e4a7a81a35'
    assert digest(REPO/spec['policy_manifest']) == digest(REPO/'artifacts/landing_hardening_20261018/candidate_r15/policy.json')
    runtime = json.loads((REPO/'benchmark/environments/runtime.json').read_text())
    assert runtime['scene'] == 'artifacts/city80_decoys_20261023/scene.mjb'
    for name, item in spec['initialization'].items():
        assert item['sha256'] == policy['weights'][name]['sha256']
        assert digest(REPO/item['path']) == item['sha256']
    assert spec['old_dataset_records_allowed'] == spec['old_feature_or_crop_records_allowed'] == 0
    assert spec['boat_radio_fraction'] == 0 and spec['teacher_control_fraction'] == 1
    assert spec['action_imitation_loss_weight'] == 0
    assert spec['weather'] == list(WEATHER) and spec['density_aliases'] == list(DENSITIES)
    assert len(episodes) == spec['episodes']['total'] == 1200
    by_role = Counter(e['role'] for e in episodes)
    assert by_role == Counter(training=960, validation=120, test=120)
    assert Counter(e['scenario']['distance'] for e in episodes) == Counter({60.:120, 80.:360, 100.:720})
    for key, expected in [('weather', 400)]:
        assert set(Counter(e[key] for e in episodes).values()) == {expected}
    assert set(Counter(e['density']['id'] for e in episodes).values()) == {300}
    assert set(Counter(e['scenario']['kind'] for e in episodes).values()) == {240}
    for role, map_count, weather_count, density_count in [('training',192,320,240), ('validation',24,40,30), ('test',24,40,30)]:
        group = [e for e in episodes if e['role'] == role]
        assert set(Counter(e['scenario']['kind'] for e in group).values()) == {map_count}
        assert set(Counter(e['weather'] for e in group).values()) == {weather_count}
        assert set(Counter(e['density']['id'] for e in group).values()) == {density_count}
        assert Counter(e['scenario']['distance'] for e in group) == Counter({60.:int(len(group)*.1),80.:int(len(group)*.3),100.:int(len(group)*.6)})
    assert Counter(e['scenario']['boat_speed'] for e in episodes) == Counter({0.:600,.6:600})
    assert Counter(e['scenario']['reverse'] for e in episodes) == Counter({False:600,True:600})
    for key in ('seed', 'world_seed', 'path_seed'):
        assert len({e['scenario'][key] for e in episodes}) == len(episodes)
    assert len({e['id'] for e in episodes}) == len(episodes)
    for e in episodes:
        scenario = make_scenario(e)
        scenario.validate()
        assert scenario.initial_camera_target is False and scenario.stress_test is False
        assert scenario.camera_delay_steps == scenario.camera_blind_seconds == 0
        assert e['density']['target_boats'] == 1 and e['radio'] == 'off'
        assert scenario.wind_profile in PROFILES and scenario.duration == 240.
    cells = Counter((e['scenario']['distance'], e['weather'], e['density']['id']) for e in episodes)
    assert len(cells) == 36
    assert all(n == {60.:10,80.:30,100.:60}[d] for (d,_,_),n in cells.items())
    scene = ET.parse(REPO/'artifacts/city80_decoys_20261023/scene.xml').getroot()
    assert len(scene.findall(".//body[@name='boat']")) == 1
    names = [b.get('name','') for b in scene.iter('body')]
    assert sum(n.startswith('decoy_false_boat_similar_') for n in names) == 3
    assert sum(n.startswith('decoy_false_boat_unsimilar_') for n in names) == 3
    assert round(spec['task_duration_s']/spec['decision_dt_s']) == spec['max_steps_per_episode'] == 6000
    assert 1200*6000 == spec['max_decision_rgb_pairs']
    assert 1200*6000*640*360*3 == spec['raw_rgb_max_bytes']
    assert spec['raw_rgb_max_bytes']*12//10 == spec['rgb_storage_with_20_percent_headroom_bytes']
    pilot = []
    for weather in WEATHER:
        for density in DENSITIES:
            pool = [e for e in episodes if e['role']=='training' and e['scenario']['distance']==60.
                    and e['weather']==weather['id'] and e['density']['id']==density['id']]
            first = pool[0]
            second = next(e for e in pool if e['scenario']['kind'] != first['scenario']['kind'])
            pilot.extend([first['id'],second['id']])
    assert len(set(pilot)) == 24
    return dict(specification_checks='passed', episodes=len(episodes), roles=dict(by_role),
        distance_counts={str(k):v for k,v in Counter(e['scenario']['distance'] for e in episodes).items()},
        source_pins_checked=len(spec['source_pins']), scenario_validations=1200,
        physical_model_constructed=False, flights_launched=0, weights_updated=False,
        historical_recordings_admitted=0, pilot_episode_ids=pilot,
        execution_ready=False, remaining_prerequisites=spec['execution_prerequisites'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materialize', action='store_true', help='Create new specification/episode files, never overwrite')
    args = parser.parse_args()
    generated = planned_episodes()
    if args.materialize:
        spec = proposed_spec()
        receipt = check(spec, generated)  # Cross-check before saving.
        spec['episode_manifest'] = 'episodes.jsonl'
        spec['episode_manifest_sha256'] = hashlib.sha256(manifest_bytes(generated)).hexdigest()
        with (HERE/'run_spec.json').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(spec, indent=2, allow_nan=False)+'\n')
        with (HERE/'episodes.jsonl').open('xb') as stream:
            stream.write(manifest_bytes(generated))
    else:
        spec = json.loads((HERE/'run_spec.json').read_text(encoding='utf-8'))
        recorded = (HERE/spec['episode_manifest']).read_bytes()
        assert digest(HERE/spec['episode_manifest']) == spec['episode_manifest_sha256']
        assert recorded == manifest_bytes(generated), 'Manifest differs from deterministic plan'
        receipt = check(spec, generated)
    receipt.update(episode_manifest_sha256=digest(HERE/'episodes.jsonl'),
                   specification_sha256=digest(HERE/'run_spec.json'),
                   specification_document_sha256=digest(HERE/'SPECIFICATION.md'),
                   verifier_sha256=digest(Path(__file__)),
                   generation_package_versions={name: importlib.metadata.version(name)
                       for name in ['numpy', 'mujoco', 'torch']})
    (HERE/'verification.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
