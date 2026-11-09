"""Compact, frozen 20-flight comparison; no MuJoCo/Torch/PX4 imports."""
from .common import ROOT, fingerprint, write

MAPS = ('island', 'beach', 'city', 'gravel', 'rock')
REPEATS = 2
MAX_FLIGHTS_PER_POLICY = 20
VERSION = 'aerodock.benchmark.mission.v3-paired-boats'
CATEGORIES = {
    'landing': {'label': 'Landing / boat speed', 'weight': .20},
    'wind': {'label': 'Wind resilience', 'weight': .15},
    'waves': {'label': 'Wave resilience', 'weight': .15},
    'acquisition': {'label': 'Find the target boat', 'weight': .30},
    'combined': {'label': 'Combined conditions', 'weight': .10},
    'speed': {'label': 'Successful mission speed', 'weight': .10},
}

# Ten deliberate conditions, each repeated once on a second procedural map/seed.
# This is a screening comparison, not a safety qualification or broad statistical study.
CONDITIONS = (
    ('acquisition', 'near-radio-clear', 30., .6, 0., 0., 'on', False, True),
    ('acquisition', 'far-radio-clear', 100., .6, 0., 0., 'on', False, True),
    ('acquisition', 'far-visual-clear', 100., .6, 0., 0., 'off', False, True),
    ('acquisition', 'far-radio-traffic', 100., .6, 0., 0., 'on', True, True),
    ('acquisition', 'far-visual-traffic', 100., .6, 0., 0., 'off', True, True),
    ('landing', 'landing-cruise', 30., .6, 0., 0., 'on', False, False),
    ('landing', 'landing-fast-boat', 30., 1.5, 0., 0., 'on', False, False),
    ('wind', 'wind-crosswind', 30., .6, 4., 0., 'on', False, False),
    ('waves', 'waves-moderate', 30., .6, 0., .15, 'on', False, False),
    ('combined', 'stress-visual-traffic', 100., 1., 4., .15, 'off', True, False),
)


def build_plan():
    cases = []
    for condition_index, (category, label, distance, speed, wind, wave, radio, traffic, outside) in enumerate(CONDITIONS):
        for repeat in range(REPEATS):
            map_index = (condition_index + repeat) % len(MAPS)
            # Hold map, route, weather and spawn seeds fixed across the four
            # far radio x distractor conditions, so their effects are separable.
            if category == 'acquisition' and distance == 100.:
                map_index = (2 + 2*repeat) % len(MAPS)
            kind = MAPS[map_index]
            seed = 826000 + map_index * 100 + repeat
            identifier = f'{category}-{label}-{kind}-r{repeat}'
            scenario = dict(name=identifier, kind=kind, seed=seed, world_seed=seed + 1000,
                            path_seed=seed + 2000, reverse=bool(repeat),
                            world_rotation_deg=(map_index * 43 + repeat * 61) % 360,
                            distance=distance, height=6.,
                            bearing_deg=(270. if repeat==0 else 90.) if distance==100. else 180., boat_speed=speed,
                            wind_profile='calm' if wind == 0 else 'breeze', wind_mean_m_s=wind,
                            wind_direction_deg=(repeat * 120 + 90) % 360, wave_height=wave,
                            wave_period=(2.5, 4.5)[repeat], wave_direction_deg=(repeat * 120 + 35) % 360,
                            yaw_offset_deg=180. if outside else 0., initial_camera_target=not outside,
                            initial_pan_deg=0., initial_tilt_deg=6. if outside else 20.,
                            duration=240., stress_test=speed > 1. or category in ('wind', 'waves', 'combined'))
            cases.append(dict(id=identifier, category=category, map=kind, repeat=repeat,
                              scenario=scenario, radio=radio, decoys=traffic,
                              initial_view='outside' if outside else 'visible',
                              acquisition_deadline_s=120.,
                              speed_reference_s=round(distance / 2 + 6 / .18 + 10, 3),
                              speed_deadline_s=240., extrapolation=distance > 60 or wave > .05 or wind > 4 or speed > 1.,
                              condition_tolerance=dict(start_distance_m=.75,
                                  boat_speed_m_s=max(.15, speed * .20),
                                  maximum_speed_outside_fraction=.20, boat_warmup_s=10.)))

    assert len(cases) == MAX_FLIGHTS_PER_POLICY
    assert len({case['id'] for case in cases}) == MAX_FLIGHTS_PER_POLICY
    plan = dict(schema=VERSION, maps=list(MAPS), repeats=REPEATS, max_flights_per_policy=MAX_FLIGHTS_PER_POLICY,
                design_note='Compact screening comparison: ten representative conditions, each on two matched-seed procedural maps. Not a safety qualification.',
                categories=CATEGORIES, cases=cases,
                speed_source_categories=['landing', 'wind', 'waves', 'acquisition', 'combined'],
                aggregation='Weighted category mean; equal case weights within each category. Speed macro-averages the five mission-condition categories.',
                results_import='Only this plan and exact policy/harness/environment receipts; no legacy scores.')
    plan['plan_sha256'] = fingerprint(plan)
    return plan


def main():
    plan = build_plan()
    write(ROOT / 'environments' / 'suite.json', plan)
    for kind in MAPS:
        selected = [c for c in plan['cases'] if c['map'] == kind]
        worlds = {c['repeat']: dict(world_seed=c['scenario']['world_seed'], path_seed=c['scenario']['path_seed'],
                  world_rotation_deg=c['scenario']['world_rotation_deg'], reverse=c['scenario']['reverse']) for c in selected}
        write(ROOT / 'environments/maps' / (kind + '.json'),
              dict(kind=kind, generator='AERODOCK_MuJoCo/usv/procedural_world.py → BoatSim.new_world',
                   scene_receipt='../runtime.json', worlds=worlds, cases=[c['id'] for c in selected],
                   plan_sha256=plan['plan_sha256'], procedural_not_static_xml=True))
    print(f"Prepared {len(plan['cases'])} cases per policy; no simulator or policy was started.")


if __name__ == '__main__':
    main()
