"""Current teacher on the existing MuJoCo/PX4 backend; no old recordings."""
from __future__ import annotations
import json
import math
from pathlib import Path
import subprocess
import threading
import queue
import time
import numpy as np
from common import (REPO, LOCAL, canonical, config, configure_simulation_imports,
                    no_radio_observation, check_no_radio, write_json, utc)


def run_episode(job):
    configure_simulation_imports()
    import mujoco
    from landing_training import environment, rendering
    from landing_training.expert import Expert
    from landing_training.privileged_teacher import PrivilegedTeacher, VisibleBoatOracle
    from benchmark.runner import make_scenario
    from mission_setup import VerticalLaunchEnvironment
    from windows_px4_v2 import WindowsPX4
    from windows_renderer import OnboardRenderer
    from review_helpers import place_distractors
    from target_learning.scenes import annotation_groups
    from target_learning.label_renderer import install, identify_water
    import fast_physics_windows
    from storage import EpisodeWriter

    class PX4(WindowsPX4):
        def start(self):
            params = json.loads((self.runtime/'parameters.json').read_text())
            params['MAV_SYS_ID'] = 1
            self.log = (self.runtime/'px4.log').open('xb')
            self.process = subprocess.Popen(['node',str(REPO/'benchmark/runtime/px4_bridge.mjs')],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,bufsize=1,creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess,'CREATE_NO_WINDOW') else 0)
            self._responses = queue.Queue()
            def receive():
                try:
                    for line in self.process.stdout:
                        self._responses.put(line)
                finally:
                    self._responses.put('')
            def log():
                written = 0
                for line in self.process.stderr:
                    raw = line.encode('utf-8',errors='replace')
                    if written < 1000000:
                        self.log.write(raw[:1000000-written]); written += len(raw)
            self._reader = threading.Thread(target=receive,daemon=True); self._reader.start()
            self._log_reader = threading.Thread(target=log,daemon=True); self._log_reader.start()
            hello = json.loads(self._responses.get(timeout=30))
            if hello.get('status')!='bridge_ready':
                raise RuntimeError('PX4 did not initialize')
            self.rpc('initialize',parameters=params)

        def close(self):
            try:
                if self.process and self.process.poll() is None:
                    try:
                        self.rpc('dispose'); self.process.wait(timeout=10)
                    except Exception:
                        self.process.kill(); self.process.wait(timeout=10)
                for name in ('_reader','_log_reader'):
                    if hasattr(self,name):getattr(self,name).join(timeout=5)
            finally:
                if self.process:
                    for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
                        if stream:stream.close()
                if self.log:self.log.close()

    install(rendering)
    class Renderer(OnboardRenderer):
        def append_water(self, scene):
            super().append_water(scene); identify_water(scene,self.env)

    entry = job['entry']; c = config()
    output = Path(job['output']); output.mkdir(parents=True,exist_ok=False)
    px4 = renderer = writer = None
    scenario = make_scenario(entry)
    started = time.monotonic()
    try:
        scene = REPO/'artifacts/city80_decoys_20261023/scene.mjb'
        model = mujoco.MjModel.from_binary_path(str(scene))
        environment.compile_scene = lambda *a,**kw:model
        fast_physics_windows.install()
        VerticalLaunchEnvironment.audit_directory = output
        env = VerticalLaunchEnvironment(scenario)
        env.boat.navigation.manual()
        groups = place_distractors(env, output)
        decoys = sorted(k for k in groups if k!='target')
        for index, name in enumerate(decoys):
            yaw = entry['decoy_yaws'][index]
            mid = int(model.body_mocapid[model.body(name).id])
            env.data.mocap_quat[mid] = [math.cos(yaw/2),0,0,math.sin(yaw/2)]
            retain = entry['false_boat_unsimilar'] if 'unsimilar' in name else entry['false_boat_similar']
            if retain == 0:
                gids = groups.pop(name)
                model.geom_group[gids] = 5
                model.geom_contype[gids] = 0; model.geom_conaffinity[gids] = 0
        mujoco.mj_forward(model,env.data)
        expected = 1+entry['false_boat_similar']+entry['false_boat_unsimilar']
        if len(groups)!=expected:raise ValueError('Delivered boat density differs')
        prep = Expert(env)
        px4 = PX4(env,output/'px4',instance=100+job['slot'])
        px4.start()
        if job.get('disarmed_backend_probe'):
            import psutil
            own_process=psutil.Process()
            peak=0
            renderer=Renderer(env)
            renderer.onboard_image()
            for tick in range(100):
                px4.send_action(np.zeros(6));px4.advance()
                if px4.armed:raise AssertionError('A disarmed backend probe armed the aircraft')
                processes=[own_process]+own_process.children(recursive=True)
                peak=max(peak,sum(p.memory_info().rss for p in processes if p.is_running()))
            result=dict(status='disarmed_backend_probe_passed',physics_steps=4000,
                simulated_seconds=float(env.data.time),armed=False,task_started=False,
                dataset_created=False,px4_startup_complete=px4.startup_complete,
                own_estimator_valid=bool(px4.observation().get('valid')),process_tree_peak_rss_bytes=peak,
                camera_initialized=True)
            if not px4.startup_complete:raise RuntimeError('PX4 startup did not complete')
            return result
        start_offset = env.task_start_xy-env.pad_position[:2]
        previous = np.zeros(6)
        for tick in range(math.ceil(env.preparation_budget_s*25)):
            env.task_start_xy[:] = env.pad_position[:2]+start_offset
            if tick>125 and tick%50==0 and not px4.armed:px4.arm_offboard()
            previous = prep.prepare(px4); px4.send_action(previous); px4.advance()
            if (px4.was_airborne and px4.armed and abs(env.vertical_clearance-scenario.height)<.15
                and np.linalg.norm(env.drone.velocity)<.3
                and np.linalg.norm(env.drone.position[:2]-env.task_start_xy)<.15):
                break
        else:
            raise RuntimeError('Physical preparation failed')
        distance = float(np.linalg.norm(env.drone.position[:2]-env.pad_position[:2]))
        if abs(distance-scenario.distance)>.75:raise ValueError('Delivered start range differs')
        teacher = PrivilegedTeacher(env)
        oracle = VisibleBoatOracle(env,groups)
        renderer = Renderer(env)
        writer = EpisodeWriter(output/'episode.sqlite',dict(
            schema='drone.search.fresh_episode.v1',entry=entry,
            source_fingerprint=job['source_fingerprint'],created_utc=utc(),
            teacher='landing_training.privileged_teacher.PrivilegedTeacher',
            radio=False,annotation_inputs=False,rgb_shape=[360,640,3],control_hz=25))
        env.task_start_time = float(env.data.time); env.recording=True
        env.boat.navigation.mode='automatic'
        encoders = np.random.default_rng(scenario.seed+50)
        outcome = 'timeout'; phases = {}; identity_counts = {'target':0,'different':0}
        speeds = []; last_disarm = -100.
        for index in range(round(scenario.duration*25)):
            capture = float(env.data.time); elapsed = capture-env.task_start_time
            if env.outcome in ('landed','water_strike','collision_failure'):
                outcome=env.outcome;break
            rgb = renderer.onboard_image()
            renderer.onboard.enable_segmentation_rendering()
            try:segmentation=renderer.onboard.render().copy()
            finally:renderer.onboard.disable_segmentation_rendering()
            views = oracle.observe(segmentation)
            own = px4.observation()
            if not own.get('valid'):raise RuntimeError('PX4 unavailable in task')
            own.update(gimbal_commanded_rad=[float(env.drone.pan),float(env.drone.tilt)],
                       gimbal_command_source='own_last_issued_setpoint')
            observation = no_radio_observation(own,
                (env.data.qpos[env.drone.camera_qpos]+encoders.normal(0,math.radians(.1),2)).tolist(),
                previous.tolist(),capture,elapsed,scenario.duration)
            check_no_radio(observation)
            action, diagnostics = teacher.act(px4,observation,views)
            if diagnostics.get('radio_coarse_guidance'):raise ValueError('Teacher used radio')
            action = prep.bounded(action)
            annotations = []
            for view in views:
                a = view.annotation()
                support = elapsed-teacher.search.support_start.get(view.key,elapsed)
                a['identity_supervision_valid'] &= support+1e-7>=c['identity_support_s']
                a['support_s'] = max(0.,float(support))
                if a['identity_supervision_valid']:
                    identity_counts['target' if a['evidence']=='target_boat' else 'different'] += 1
                annotations.append(a)
            row = dict(frame=index,observation=observation,
                supervision=dict(boats=annotations,teacher_diagnostics=diagnostics,
                    teacher_action=action.tolist(),action_loss_valid=False,student_input=False),
                action_owner='newest_privileged_teacher',outcome=env.outcome)
            writer.append(rgb,row)
            phase=diagnostics['control_phase'];phases[phase]=phases.get(phase,0)+1
            if elapsed>=10:speeds.append(float(np.linalg.norm(env.pad_velocity[:2])))
            if px4.armed and px4.was_airborne and px4.landed and capture-last_disarm>=1.:
                px4.request_disarm();last_disarm=capture
            px4.send_action(action);px4.advance();previous=action
            if index%250==0:
                print(canonical(dict(id=entry['id'],task_s=round(elapsed,2),frames=writer.count,phase=phase)),flush=True)
        if env.outcome in ('landed','water_strike','collision_failure'):outcome=env.outcome
        tolerance=max(.15,.2*scenario.boat_speed)
        outside=sum(abs(v-scenario.boat_speed)>tolerance for v in speeds)/len(speeds) if speeds else None
        motion_valid = (outside is not None and outside<=.2) or (not speeds and outcome!='landed')
        # These are training observations, not speed-qualification trials. Wind-
        # driven drift is valid experience: keep it and report achieved motion.
        # Never filter perception training data based on whether the pilot won.
        condition_valid = bool(not env.boat.navigation.complete)
        result = dict(id=entry['id'],role=entry['role'],status='completed',outcome=outcome,
            condition_valid=condition_valid,actual_start_distance_m=distance,
            boat_speed_outside_fraction=outside,identity_labels=identity_counts,phase_counts=phases,
            motion_matches_requested_speed=bool(motion_valid),
            actual_boat_speed_mean_m_s=float(np.mean(speeds)) if speeds else None,
            radio=False,teacher_control_fraction=1.,forced_disarm=False,wall_s=time.monotonic()-started,
            source_fingerprint=job['source_fingerprint'],scenario=entry['scenario'])
        result = writer.finish(result);writer=None
        if not condition_valid:
            write_json(output/'invalid_condition.json',result)
            raise RuntimeError('Route completed during the task; planned scenario not delivered')
        write_json(output/'result.json',result)
        return result
    except BaseException as exc:
        import traceback
        write_json(output/'error.json',dict(error=repr(exc),traceback=traceback.format_exc()))
        raise
    finally:
        if writer is not None:writer.close()
        if renderer is not None:renderer.close()
        if px4 is not None:px4.close()
