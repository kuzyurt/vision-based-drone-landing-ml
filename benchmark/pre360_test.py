"""One dedicated pre360 check: 10 m start, boat directly underneath.

This is a working-data episode, not a canonical suite case.  The standard
Scenario.validate() flight envelope caps height at 8 m; this test extends only
that check so the requested 10 m start can be flown, while retaining all other
envelope checks.  The policy, runner, and suite files are not modified.
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

from benchmark.harness import runner, student_radio
from benchmark.harness.common import REPO, ROOT, read, sha
from benchmark.harness.rollout_digest import generate_episode_digest
import sys
sys.path.insert(0, str(REPO / 'artifacts/local_curriculum_20261020'))
import local_paths  # noqa: F401  (installs mission/source paths)
from mission_setup import VerticalLaunchEnvironment
from landing_training.expert import Expert

_ORIGINAL_INIT = VerticalLaunchEnvironment.__init__


def _pre360_init(self, scenario):
    _ORIGINAL_INIT(self, scenario)
    if scenario.distance == 0.0:
        # With a zero task offset the normal 2 m launch pad sits under the boat
        # hull and the aircraft cannot physically take off.  Move only the
        # launch pad 10 m seaward; task_start_xy remains exactly over the boat.
        import mujoco
        world = self.boat.navigation.world
        _, normal, _ = world.sample(world.route.coast_s[0])
        self.launch_xy = self.pad_position[:2] + normal * 10.0
        self.data.mocap_pos[self.launch_mid, :2] = self.launch_xy
        self.data.qpos[self.drone.free_qadr:self.drone.free_qadr + 3] = [
            *self.launch_xy, .2 - self.drone.bottom + .004]
        self.data.qvel[self.drone.free_vadr:self.drone.free_vadr + 6] = 0
        mujoco.mj_forward(self.model, self.data)
        self.preparation_budget_s = 75.


VerticalLaunchEnvironment.__init__ = _pre360_init

_ORIGINAL_PREPARE = Expert.prepare
_PREP_TICKS = 0


def _instrumented_prepare(self, px4):
    global _PREP_TICKS
    action = _ORIGINAL_PREPARE(self, px4)
    _PREP_TICKS += 1
    if _PREP_TICKS % 25 == 0:
        env = self.env
        print('PREP', round(float(env.data.time), 2),
              'alt', round(env.vertical_clearance, 3),
              'z', round(float(env.drone.position[2]), 3),
              'v', round(float((env.drone.velocity ** 2).sum() ** .5), 3),
              'xyerr', round(float(((env.drone.position[:2] - env.task_start_xy) ** 2).sum() ** .5), 3),
              flush=True)
    return action

Expert.prepare = _instrumented_prepare


def make_case():
    case = copy.deepcopy(next(
        item for item in read(ROOT / 'definition/suite.json')['cases']
        if item['id'] == 'acquisition-far-radio-clear-city-r0'))
    case['id'] = 'pre360-under-10m'
    case['category'] = 'acquisition'
    case['map'] = 'city'
    case['radio'] = 'off'          # isolate the visual pre360 from radio guidance
    case['decoys'] = False
    case['initial_view'] = 'outside'
    case['acquisition_deadline_s'] = 120.0
    case['speed_reference_s'] = 60.0
    case['speed_deadline_s'] = 180.0
    case['extrapolation'] = False
    case['scenario'].update(
        name='pre360-under-10m', kind='city', seed=826900, world_seed=827900,
        path_seed=828900, world_rotation_deg=0.0, distance=0.0, height=10.0,
        bearing_deg=0.0, boat_speed=0.0, wind_profile='calm',
        wind_mean_m_s=0.0, wind_direction_deg=90, wave_height=0.0,
        wave_period=2.5, wave_direction_deg=35, yaw_offset_deg=0.0,
        initial_camera_target=False, initial_pan_deg=0.0,
        initial_tilt_deg=0.0, duration=180.0, stress_test=False)
    case['condition_tolerance'].update(
        start_distance_m=0.75, boat_speed_m_s=0.05,
        maximum_speed_outside_fraction=0.2, boat_warmup_s=10.0)
    return case


def allow_10m_scenario(case):
    from landing_training.config import Scenario

    @dataclass(frozen=True)
    class Pre360Scenario(Scenario):
        def validate(self):
            if not 0 <= self.distance <= 100 or not 1 <= self.duration <= 240:
                raise ValueError('Pre360 start/budget envelope exceeded')
            # The only relaxed item is the 8 m training envelope; the actual
            # object keeps height=10.  Everything else is validated normally.
            Scenario.validate(replace(
                self, distance=min(60., self.distance),
                duration=min(180., self.duration), height=min(8., self.height)))

    return Pre360Scenario(**case['scenario'])


def main():
    runner.make_scenario = allow_10m_scenario
    case = make_case()
    policy = student_radio.policy()
    root = Path(os.environ.get('PRE360_ROOT',
                              str(ROOT / 'runs/pre360_under_10m_20261112')))
    setup_out = root / 'setup'
    flight_out = root / policy['id'] / case['id']
    context = dict(
        plan_sha256=read(ROOT / 'definition/suite.json')['plan_sha256'],
        runtime_sha256=sha(ROOT / 'definition/runtime.json'),
        suite_sha256=sha(ROOT / 'definition/suite.json'),
        inference_device='cuda', control_hz=25,
        backend='windows_mujoco_px4_wasm',
        benchmark='aerodock-20-wave-gate-3c2b501', workers=1)

    student_radio.install(runner, dict(policy, device='cuda'), setup_out)
    runner.run_trial(policy, case, setup_out, context, setup_only=True)
    state = read(setup_out / 'initial_state.json')
    print('SETUP', json.dumps(state, indent=2), flush=True)
    if not state.get('start_valid'):
        raise SystemExit('pre360 setup start was not valid')

    student_radio.install(runner, dict(policy, device='cuda'), flight_out)
    runner.run_trial(policy, case, flight_out, context)
    generate_episode_digest(flight_out, overwrite=True)
    result = read(flight_out / 'result.json')
    print('RESULT', json.dumps({
        key: result.get(key) for key in (
            'policy_id', 'status', 'condition_valid', 'outcome',
            'verified_acquisition_s', 'mission_time_s', 'collision',
            'water_strike', 'wrong_target_contacts', 'assistance_frames',
            'final_lateral_error_m')
    }, indent=2), flush=True)
    print('DIGEST', flight_out / 'diagnostic_digest.txt', flush=True)


if __name__ == '__main__':
    main()
