"""One isolated, unaided MuJoCo/PX4 trial. Called only by the explicit run command."""
import copy
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import types
from .common import REPO, ROOT, fingerprint, read, sha, utc, write


def verify_receipts(receipts):
    errors = []
    for item in receipts:
        path = REPO / item['path']
        if not path.is_file() or sha(path) != item['sha256']:
            errors.append(item['path'])
    return errors


def preflight(policy):
    runtime = read(ROOT / 'definition/runtime.json')
    errors = verify_receipts(runtime['source_files'] + runtime['assets'] + runtime['harness_files'])
    errors += verify_receipts(policy['source_files'] + policy['actor_source_files'] + [policy['manifest']])
    snapshot = ROOT / 'policies' / policy['id'] / 'policy.json'
    if not snapshot.exists() or sha(snapshot) != policy['manifest']['sha256']:
        # policy.json is normalized JSON in the inventory, so compare semantic
        # content rather than byte formatting with the preserved original.
        if not snapshot.exists() or read(snapshot) != read(REPO / policy['manifest']['path']):
            errors.append('Changed benchmark policy configuration: '+policy['id'])
    for item in policy['weights'].values():
        path = ROOT / item['path']
        if not path.exists() or sha(path) != item['sha256']:
            errors.append(item['path'])
    if not policy['available']:
        errors += policy['missing']
    if os.name != 'nt':
        errors.append('This adapter requires Windows; do not mix Linux or browser results.')
    elif policy['actor'] != 'privileged_teacher':
        native = REPO/policy['source_root']/'radio_robust_20261015/native_marker.py'
        if native.exists():
            cpp = native.with_name('marker_kernel.cpp')
            if not cpp.is_file():
                errors.append('Missing marker_kernel.cpp required to verify the Windows kernel adapter; use a complete source bundle.')
            elif sha(cpp) != '0b70a9263dfc75ddba3b3771fba17391692d43bc0dbffaafe92aa33de2e58c66':
                errors.append('Marker kernel source is incompatible with the pinned Windows DLL.')
    for package in ['mujoco', 'torch', 'torchvision', 'numpy', 'scipy', 'PIL', 'pymavlink', 'cv2']:
        if importlib.util.find_spec(package) is None:
            errors.append('Missing Python dependency: ' + package)
    if shutil.which('node') is None:
        errors.append('Node.js is missing from PATH')
    return errors


def native_path(path):
    """Keep deep per-case source trees loadable on Windows without OS changes."""
    path = Path(os.path.abspath(path))
    value = str(path)
    if os.name == 'nt' and not value.startswith('\\\\?\\'):
        value = '\\\\?\\UNC\\'+value[2:] if value.startswith('\\\\') else '\\\\?\\'+value
        path = Path(value)
    return path


def stage(policy, folder):
    folder = native_path(folder)
    folder.mkdir()
    shutil.copy2(ROOT / 'policies' / policy['id'] / 'policy.json', folder / 'policy.json')
    if policy['actor'] == 'privileged_teacher':
        code = folder / 'code/landing_training'
        code.mkdir(parents=True)
        for item in policy['source_files']:
            shutil.copy2(REPO/item['path'], code/Path(item['path']).name)
    else:
        shutil.copytree(native_path(REPO / policy['source_root']), folder / 'code/landing_training',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name, item in policy['weights'].items():
        shutil.copy2(ROOT / item['path'], folder / name)
    return folder


def bind_legacy_geometry(package='benchmark_actor'):
    """Resolve the common guard's legacy import to this actor's frozen helper."""
    suffix='radio_robust_20261015.controller.visual_acquisition'
    name=package+'.'+suffix
    if importlib.util.find_spec(name) is None:
        return
    for part in ['radio_robust_20261015','radio_robust_20261015.controller',suffix]:
        sys.modules['landing_training.'+part]=importlib.import_module(package+'.'+part)
    import landing_training
    landing_training.radio_robust_20261015=sys.modules['landing_training.radio_robust_20261015']


def make_scenario(case):
    from dataclasses import dataclass, replace
    from landing_training.config import Scenario
    @dataclass(frozen=True)
    class BenchmarkScenario(Scenario):
        def validate(self):
            if not 0 <= self.distance <= 100 or not 1 <= self.duration <= 240:
                raise ValueError('Benchmark start/budget envelope exceeded')
            Scenario.validate(replace(self, distance=min(60.,self.distance), duration=min(180.,self.duration)))
    return BenchmarkScenario(**case['scenario'])


def setup_scene(env, case, output):
    import mujoco
    from target_learning.scenes import annotation_groups
    from review_helpers import place_distractors
    yaw = math.atan2(*(env.pad_position[:2]-env.task_start_xy)[::-1]) + (math.pi if case['initial_view']=='outside' else 0.)
    q = env.drone.free_qadr
    env.data.qpos[q+3:q+7] = [math.cos(yaw/2),0.,0.,math.sin(yaw/2)]
    mujoco.mj_forward(env.model, env.data)
    groups = annotation_groups(env.model)
    if case['decoys']:
        place_distractors(env, output)
    else:
        for name,gids in groups.items():
            if name != 'target':
                env.model.geom_group[gids] = 5
                env.model.geom_contype[gids] = 0
                env.model.geom_conaffinity[gids] = 0
        write(Path(output)/'scene_spawn_receipt.json', dict(decoys=False,hidden_and_collision_disabled=True))
    return groups


def make_renderer(env):
    from windows_renderer import OnboardRenderer
    from landing_training import rendering
    from target_learning.label_renderer import install, identify_water
    install(rendering)
    class LabelRenderer(OnboardRenderer):
        def append_water(self, scene):
            super().append_water(scene)
            identify_water(scene, self.env)
    return LabelRenderer(env)


def run_trial(policy, case, output, run_context, *, setup_only=False):
    """Policy receives RGB and the declared observation dict, never env/scorer."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    errors = preflight(policy)
    base = dict(schema='aerodock.benchmark.trial.v1', policy_id=policy['id'], case_id=case['id'],
                policy_identity_sha256=policy['identity_sha256'], started_utc=utc(),
                context=run_context, training_eligible=False)
    write(output / 'case.json', case)
    if errors:
        write(output / ('setup_result.json' if setup_only else 'result.json'), dict(base, status='infrastructure_error', condition_valid=False, errors=errors))
        return
    # Imports and side effects below occur only in a deliberately launched trial.
    local = REPO / 'artifacts/local_curriculum_20261020'
    sys.path.insert(0, str(local))
    import local_paths
    import mujoco
    import numpy as np
    import torch
    from landing_training import environment
    from landing_training.expert import Expert
    from windows_kernels import install
    install()
    import fast_physics_windows
    fast_physics_windows.install()
    from windows_px4_v2 import WindowsPX4
    from review_helpers import nominal_structure_bound, place_distractors
    from mission_setup import VerticalLaunchEnvironment
    from mission_safety import HomeReference, MissionSafety
    from clearance_provider import StaticRecoveryPrior
    torch.set_num_threads(1)

    # Reuse transport and sensor code, with a benchmark-specific PX4 bridge.
    class BenchmarkPX4(WindowsPX4):
        def start(self):
            import queue
            import subprocess
            import threading
            parameters = read(self.runtime / 'parameters.json')
            parameters['MAV_SYS_ID'] = 1
            initial_time=float(self.env.data.time)
            attempts=[]
            def receive(process,responses):
                for line in process.stdout:responses.put(line)
                responses.put('')
            for attempt in range(1,4):
                assert float(self.env.data.time)==initial_time, 'A bootstrap retry may not repeat physics'
                began=time.perf_counter()
                try:
                    filename='px4_windows.log' if attempt==1 else f'px4_windows_bootstrap_{attempt}.log'
                    self.log=(self.runtime/filename).open('x')
                    self.process=subprocess.Popen(['node',str(ROOT/'harness/runtime/px4_bridge.mjs')],
                        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,
                        text=True,bufsize=1,creationflags=subprocess.CREATE_NO_WINDOW)
                    self._responses=queue.Queue()
                    self._reader=threading.Thread(target=receive,args=(self.process,self._responses),daemon=True)
                    self._reader.start()
                    hello=json.loads(self._responses.get(timeout=25))
                    if hello.get('status')!='bridge_ready':raise RuntimeError('PX4 bridge did not become ready')
                    receipt=self.rpc('initialize',parameters=parameters)
                    attempts.append(dict(attempt=attempt,status='ready',physics_time_s=initial_time,
                                         wall_s=time.perf_counter()-began))
                    write(self.runtime/'bootstrap_attempts.json',dict(before_physics=True,policy_retried=False,attempts=attempts))
                    write(self.runtime/'runtime_platform.json',dict(backend='Windows real PX4 WASM',
                        px4_revision=receipt['px4_revision'],parity_with_native_linux_claimed=False,bootstrap_attempt=attempt))
                    return
                except Exception as exc:
                    attempts.append(dict(attempt=attempt,status='startup_error',error=repr(exc),
                                         physics_time_s=float(self.env.data.time),wall_s=time.perf_counter()-began))
                    write(self.runtime/'bootstrap_attempts.json',dict(before_physics=True,policy_retried=False,attempts=attempts))
                    process=getattr(self,'process',None)
                    if process is not None:
                        if process.poll() is None:
                            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False,
                                creationflags=subprocess.CREATE_NO_WINDOW)
                        process.wait(timeout=15)
                        if hasattr(self,'_reader'):self._reader.join(timeout=5)
                        if process.stdin:process.stdin.close()
                        if process.stdout:process.stdout.close()
                    self.process=None
                    if getattr(self,'log',None):self.log.close()
                    if attempt==3:raise RuntimeError('PX4 bootstrap failed after three fresh-process attempts') from exc

    renderer = px4 = None
    rows = []
    outcome = 'setup_failure'
    started = time.perf_counter()
    try:
        runtime = read(ROOT / 'definition/runtime.json')
        environment.compile_scene = lambda *args, **kwargs: mujoco.MjModel.from_binary_path(str(REPO / runtime['scene']))
        scenario = make_scenario(case)
        VerticalLaunchEnvironment.audit_directory = output
        env = VerticalLaunchEnvironment(scenario)
        env.boat.navigation.manual()
        groups = setup_scene(env, case, output)
        # Wind/waves can move the manually held boat during physical takeoff.
        # Settle at the prescribed relative start, rather than a stale absolute
        # coordinate. All motion here is flown through PX4 before task time.
        start_offset = env.task_start_xy-env.pad_position[:2]
        structure = nominal_structure_bound(env.model)
        static = StaticRecoveryPrior(env, output)
        prep = Expert(env)  # prepare() and bounded() only. Never call Expert.act().
        home = HomeReference()
        px4 = BenchmarkPX4(env, output / 'px4', instance=0)
        px4.start()
        last_stamp = None
        for tick in range(math.ceil(env.preparation_budget_s * 25)):
            env.task_start_xy[:] = env.pad_position[:2]+start_offset
            own = px4.observation()
            if own.get('valid') and own.get('position_source_boot_ms') != last_stamp:
                home.observe(own)
                last_stamp = own['position_source_boot_ms']
            if tick > 125 and tick % 50 == 0 and len(home.samples) >= 5 and not px4.armed:
                px4.arm_offboard()
            px4.send_action(prep.prepare(px4))
            px4.advance()
            if (px4.was_airborne and px4.armed and abs(env.vertical_clearance-scenario.height) < .15
                    and np.linalg.norm(env.drone.velocity) < .3 and np.linalg.norm(env.drone.position[:2]-env.task_start_xy) < .15):
                break
        else:
            raise RuntimeError('Physical takeoff did not reach the prescribed start')
        renderer = make_renderer(env)
        renderer.onboard.enable_segmentation_rendering()
        try:
            segmentation = renderer.onboard_image()
        finally:
            renderer.onboard.disable_segmentation_rendering()
        visible_pixels = int((np.isin(segmentation[...,0],groups['target']) &
                              (segmentation[...,1]==int(mujoco.mjtObj.mjOBJ_GEOM))).sum())
        distance = float(np.linalg.norm(env.drone.position[:2] - env.pad_position[:2]))
        start_valid = (abs(distance-scenario.distance) <= case['condition_tolerance']['start_distance_m']
                       and ((visible_pixels == 0) if case['initial_view'] == 'outside' else visible_pixels >= 16))
        write(output / 'initial_state.json', dict(actual_start_distance_m=distance, target_pixels=visible_pixels,
              intended_view=case['initial_view'], start_valid=start_valid, achieved_bearing_deg=env.achieved_bearing_deg,
              preparation_reference='physically flown relative offset from current boat; task clock not started',
              drone_position_enu_m=env.drone.position.tolist(),pad_position_enu_m=env.pad_position.tolist(),
              annotation_only=True))
        if not start_valid:
            raise RuntimeError('Actual start violates distance/view contract; trial cannot be scored')
        if setup_only:
            from PIL import Image
            Image.fromarray(renderer.onboard_image()).save(output/'actual_start_rgb.png')
            write(output/'setup_result.json',dict(base,schema='aerodock.benchmark.setup_check.v1',
                status='completed',condition_valid=True,actual_start_distance_m=distance,
                target_pixels=visible_pixels,policy_executed=False,timed_mission_executed=False,
                physical_takeoff=True,wall_seconds=time.perf_counter()-started))
            return
        bundle = stage(policy, output / 'bundle')
        package = types.ModuleType('benchmark_actor')
        package.__path__ = [str(bundle / 'code/landing_training')]
        sys.modules[package.__name__] = package
        config = read(bundle / 'policy.json')
        device = run_context.get('inference_device', 'cpu')
        cuda_actor = device == 'cuda' and policy['actor'] != 'privileged_teacher'
        if policy['actor'] == 'privileged_teacher':
            from .actors import PrivilegedReference
            actor = PrivilegedReference(env, px4, renderer, groups)
        elif policy['actor'] == 'radio_robust':
            module = importlib.import_module('benchmark_actor.radio_robust_20261015.runtime')
            actor = module.RadioRobustRuntime(bundle / 'pose.pt', config['calibration'], config['slew_limits'],
                                              device, allow_visual_landing=True)
            bind_legacy_geometry()
            from .actors import LegacyMetricAdapter
            actor = LegacyMetricAdapter(actor)
        else:
            # Select this actor's own source tree before importing its package.
            source = REPO / policy['actor_source_root']
            for name in list(sys.modules):
                if name == 'target_learning' or name.startswith('target_learning.'):
                    del sys.modules[name]
            sys.path.insert(0, str(source.parent))
            module, cls = policy['actor'].rsplit('.', 1)
            actor = getattr(importlib.import_module(module), cls)(bundle, bundle / 'recognizer.pt',
                     device=device, review_only=True, package_name='benchmark_teacher_parent')
        safe = MissionSafety(actor, config['slew_limits'])
        safe.reset()
        # Independent seeded 1 Hz boat radio. No packet or target coordinates at all
        # in the radio-off observation; own PX4 position remains available.
        radio_rng = np.random.default_rng(scenario.seed + 40)
        encoder_rng = np.random.default_rng(scenario.seed + 50)
        packet = None
        previous = np.zeros(6)
        start_sim = float(env.data.time)
        env.task_start_time = start_sim
        env.recording = True
        env.boat.navigation.mode = 'automatic'
        first_acquisition = None
        consecutive = 0
        false_events = 0
        false_active = False
        last_disarm = -100.
        wrong_contacts = 0
        path_m = 0.
        last_position = env.drone.position.copy()
        outcome = 'timeout'
        with (output / 'steps.jsonl').open('x', encoding='utf-8') as stream:
            for tick in range(round(scenario.duration * 25)):
                capture = float(env.data.time)
                elapsed = capture - start_sim
                rgb = renderer.onboard_image()
                own = px4.observation()
                if not own.get('valid'):
                    raise RuntimeError('PX4 estimator unavailable during task')
                own.update(gimbal_commanded_rad=[float(env.drone.pan), float(env.drone.tilt)],
                           gimbal_command_source='own_last_issued_setpoint')
                clearance = static.certify(own)
                search = max(4., math.ceil((structure+.75)*2)/2)
                xy = np.asarray(own['position_enu_m'])[:2]
                ring = xy + 2*np.column_stack((np.cos(np.arange(8)*math.pi/4), np.sin(np.arange(8)*math.pi/4)))
                water = bool(np.min(env.boat.navigation.world.distance(ring)) >= 5.)
                ceiling = min(10., clearance['max_altitude_enu_m']) if clearance.get('valid') else 10.
                mission = dict(home.mission(), elapsed_s=elapsed, budget_s=scenario.duration,
                    search_timeout_s=120., recovery_clearance=clearance,
                    target_discrimination=dict(search_height_enu_m=search, maximum_height_enu_m=10.,
                        nominal_boat_plane_enu_m=.45, plane_uncertainty_m=.4,
                        static_prior_no_dynamic_boat_state=True, nominal_structure_bound_m=structure,
                        search_corridor_valid=bool(water and own['position_enu_m'][2] >= search-.15 and clearance.get('valid') and ceiling >= search),
                        upward_corridor_valid=bool(clearance.get('valid') and own['position_enu_m'][2] >= structure+.1 and ceiling-own['position_enu_m'][2] >= max(2.6, search-own['position_enu_m'][2]+.1))))
                observation = dict(px4=own, gimbal_rad=(env.data.qpos[env.drone.camera_qpos]+encoder_rng.normal(0, math.radians(.1), 2)).tolist(),
                    gimbal_source='synthetic own encoder', image_capture_time_s=capture, image_delivery_time_s=capture,
                    image_age_s=0., image_valid=True, decision_dt_s=.04,
                    previous_executed_action=previous.tolist(), mission=mission)
                if case['radio'] == 'on':
                    if packet is None or elapsed-packet['capture_s'] >= 1.-1e-8:
                        packet = dict(capture_s=elapsed, position=env.pad_position+radio_rng.normal(0,.25,3),
                                      velocity=env.pad_velocity+radio_rng.normal(0,.025,3))
                    yaw = math.pi/2-own['attitude_ned_rad'][2]
                    c, s = math.cos(yaw), math.sin(yaw)
                    rotation = np.array([[c,-s,0],[s,c,0],[0,0,1.]])
                    observation['beacon'] = dict(valid=True, age_s=elapsed-packet['capture_s'], dock_ready=True,
                        dock_status_valid=True, position_sigma_m=.25, velocity_sigma_m_s=.025,
                        relative_heading_m=((rotation.T@(packet['position']-own['position_enu_m']))*[1,-1,-1]).tolist(),
                        velocity_heading_m_s=((rotation.T@packet['velocity'])*[1,-1,-1]).tolist())
                if cuda_actor:
                    torch.cuda.synchronize()
                infer_start = time.perf_counter()
                try:
                    action, diagnostics = safe.act(rgb, copy.deepcopy(observation))
                    if cuda_actor:
                        torch.cuda.synchronize()
                except Exception as exc:
                    outcome = 'policy_error'
                    stream.write(json.dumps(dict(task_s=elapsed, policy_error=f'{type(exc).__name__}: {exc}'))+'\n')
                    break
                inference_ms = (time.perf_counter()-infer_start)*1000
                action = np.asarray(action, dtype=float)
                if action.shape != (6,) or not np.isfinite(action).all():
                    outcome = 'policy_error'
                    stream.write(json.dumps(dict(task_s=elapsed, policy_error='Malformed/non-finite action'))+'\n')
                    break
                action = prep.bounded(action)
                if diagnostics.get('mission_fallback_active'):
                    outcome = 'mission_fallback'
                    break  # No home/expert command is sent; a boat mission has failed.
                # This block is scoring-only, AFTER the actor's decision.
                estimate = diagnostics.get('estimated_relative_position')
                metric = diagnostics.get('metric_valid') and diagnostics.get('metric_confirmed', diagnostics.get('metric_valid'))
                estimate_error = None
                if metric and estimate is not None:
                    yaw = math.pi/2-own['attitude_ned_rad'][2]
                    c, s = math.cos(yaw), math.sin(yaw)
                    rotation = np.array([[c,-s,0],[s,c,0],[0,0,1.]])
                    predicted = np.asarray(own['position_enu_m']) + rotation@(np.asarray(estimate)*[1,-1,-1])
                    estimate_error = float(np.linalg.norm(predicted-env.pad_position))
                correct = estimate_error is not None and estimate_error <= .75
                consecutive = consecutive + 1 if correct else 0
                if consecutive >= 10 and first_acquisition is None:
                    first_acquisition = elapsed - 9*.04
                false = estimate_error is not None and estimate_error > 2.
                false_events += int(false and not false_active)
                false_active = false
                for contact in env.data.contact[:env.data.ncon]:
                    a, b = int(contact.geom1), int(contact.geom2)
                    if (env.model.geom_bodyid[a] in env.drone.bodies and any(b in gids for n,gids in groups.items() if n != 'target')
                        or env.model.geom_bodyid[b] in env.drone.bodies and any(a in gids for n,gids in groups.items() if n != 'target')):
                        wrong_contacts += 1
                speed = float(np.linalg.norm(env.pad_velocity[:2]))
                path_m += float(np.linalg.norm(env.drone.position-last_position))
                last_position = env.drone.position.copy()
                row = dict(task_s=elapsed, observation=observation, action=action.tolist(), diagnostics=diagnostics,
                    scoring_only=dict(actual_boat_speed_m_s=speed, pad_estimate_error_m=estimate_error,
                        drone_position_enu_m=env.drone.position.tolist(), pad_position_enu_m=env.pad_position.tolist(),
                        wind_m_s=float(np.linalg.norm(env.wind.velocity)), clearance_m=env.vertical_clearance),
                    inference_ms=inference_ms)
                # Some legacy diagnostics use +/-inf for an absent estimate.
                def clean(value):
                    if isinstance(value, dict): return {k:clean(v) for k,v in value.items()}
                    if isinstance(value, (list,tuple)): return [clean(v) for v in value]
                    if isinstance(value, np.ndarray): return clean(value.tolist())
                    if isinstance(value, np.generic): return clean(value.item())
                    if isinstance(value, float) and not math.isfinite(value): return None
                    return value
                stream.write(json.dumps(clean(row), allow_nan=False)+'\n')
                rows.append(dict(t=elapsed, speed=speed, ms=inference_ms))
                if px4.was_airborne and px4.armed and px4.landed and capture-last_disarm >= 1.:
                    px4.request_disarm()
                    last_disarm = capture
                px4.send_action(action)
                px4.advance()
                previous = action
                if env.outcome in ('landed','collision_failure','water_strike'):
                    outcome = env.outcome
                    break
                if tick % 250 == 0:
                    print(json.dumps(dict(case=case['id'], task_s=round(elapsed,2), outcome=env.outcome)), flush=True)
        elapsed = float(env.data.time)-start_sim
        measured = [r['speed'] for r in rows if r['t'] >= case['condition_tolerance']['boat_warmup_s']]
        tolerance = case['condition_tolerance']['boat_speed_m_s']
        outside = sum(abs(s-scenario.boat_speed) > tolerance for s in measured)/len(measured) if measured else None
        # An early policy failure cannot escape the denominator through missing speed samples.
        motion_valid = outside is not None and outside <= case['condition_tolerance']['maximum_speed_outside_fraction']
        if not measured and outcome != 'landed':
            motion_valid = True
        if env.boat.navigation.complete:
            motion_valid = False
        result = dict(base, status='completed', condition_valid=bool(start_valid and motion_valid),
            actor_role=policy['role'], privileged_reference=policy['actor']=='privileged_teacher',
            outcome=outcome, disarmed=not px4.armed, px4_landed=bool(px4.landed),
            stable_disarmed_contact_s=float(env.disarmed_contact_seconds),
            collision=outcome=='collision_failure', water_strike=outcome=='water_strike',
            assistance_frames=0, wrong_target_contacts=wrong_contacts,
            verified_acquisition_s=first_acquisition, false_acquisition_events=false_events,
            mission_time_s=elapsed, path_length_m=path_m, actual_start_distance_m=distance,
            final_lateral_error_m=float(np.linalg.norm((env.pad_rotation.T@(env.drone.position-env.pad_position))[:2])),
            touchdown_relative_velocity_m_s=next((e['relative_velocity'] for e in env.events if e['kind']=='touchdown'),None),
            final_deck_tilt_deg=math.degrees(math.acos(float(np.clip(env.pad_rotation[2,2],-1,1)))),
            requested_boat_speed_m_s=scenario.boat_speed,
            measured_boat_speed_mean_m_s=float(np.mean(measured)) if measured else None,
            speed_outside_tolerance_fraction=outside, route_completed=bool(env.boat.navigation.complete),
            inference_p50_ms=float(np.percentile([r['ms'] for r in rows],50)) if rows else None,
            inference_p95_ms=float(np.percentile([r['ms'] for r in rows],95)) if rows else None,
            control_deadline_miss_fraction=sum(r['ms']>40 for r in rows)/len(rows) if rows else None,
            events=env.events, trace_sha256=sha(output / 'steps.jsonl'),
            wall_seconds=time.perf_counter()-started, completed_utc=utc())
        write(output / 'result.json', result)
    except Exception as exc:
        write(output / ('setup_result.json' if setup_only else 'result.json'), dict(base, status='infrastructure_error', condition_valid=False,
              error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc(),
              frames=len(rows), wall_seconds=time.perf_counter()-started))
        raise
    finally:
        for resource in [renderer, px4]:
            if resource is not None:
                resource.close()
