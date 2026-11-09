"""Fly the observable two-stage teacher in the existing six-decoy city model.

Only scenario setup / scoring reads target state. No SearchDirector, true target
position, visibility raycast or segmentation enters the actor. All commands are
from IdentityExpertV60 plus its existing safety wrapper and guards.
"""
from __future__ import annotations

import argparse
import copy
import ctypes
from dataclasses import asdict, dataclass, replace
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CURRICULUM = REPO / 'artifacts/local_curriculum_20261020'
CITY = REPO / 'artifacts/city80_decoys_20261023'
sys.path[:0] = [str(REPO), str(CURRICULUM), str(CURRICULUM/'sources')]
import local_paths
sys.path.insert(0, str(CURRICULUM/'sources'))
import mujoco
import numpy as np
import psutil
import torch
from PIL import Image, ImageDraw, ImageFont
from windows_kernels import install
install()
import fast_physics_windows
from landing_training import environment
from landing_training.config import Scenario
from landing_training.expert import Expert
from landing_training.recording import Recorder
from mission_setup import VerticalLaunchEnvironment
from mission_safety import HomeReference, MissionSafety
from clearance_provider import StaticRecoveryPrior
from windows_px4_v2 import WindowsPX4
from windows_renderer import OnboardRenderer
from radio_link import absent_beacon
from review_helpers import nominal_structure_bound
from target_learning.expert_adapter_v60 import IdentityExpertV60
from usv.boat_sim import quaternion
import disarm_policy


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def reclaim_own_memory(out, reason):
    """Page out only this review process's unused resident pages on Windows.

    The meshes/weights stay intact and can be faulted back in. No other app,
    process, model parameter, observation or simulation clock is changed.
    """
    before=psutil.virtual_memory().available
    gc.collect();trimmed=False
    if os.name == 'nt':
        handle=ctypes.windll.kernel32.GetCurrentProcess
        handle.restype=ctypes.c_void_p
        trim=ctypes.windll.psapi.EmptyWorkingSet
        trim.argtypes=[ctypes.c_void_p];trim.restype=ctypes.c_int
        trimmed=bool(trim(handle()))
    time.sleep(.2)
    with (out/'memory_reclaims.jsonl').open('a') as f:
        f.write(json.dumps(dict(reason=reason,own_process_only=True,trimmed=trimmed,
            available_before_mib=round(before/2**20),
            available_after_mib=round(psutil.virtual_memory().available/2**20)))+'\n')


@dataclass(frozen=True)
class ReviewScenario(Scenario):
    def validate(self):
        if not 80 <= self.distance <= 90:
            raise ValueError('This explicit review requires 80..90 m')
        Scenario.validate(replace(self, distance=60.))


class Video:
    def __init__(self, out):
        self.out = out
        self.frames = 0
        self.font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 14)
        self.log = (out/'video_encode.log').open('x')
        self.proc = subprocess.Popen([
            'ffmpeg','-n','-loglevel','error','-f','rawvideo','-pixel_format','rgb24',
            '-video_size','960x420','-framerate','25','-i','pipe:0','-an',
            '-c:v','libx264','-preset','veryfast','-threads','2','-crf','22',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(out/'review.mp4')],
            stdin=subprocess.PIPE, stderr=self.log, creationflags=subprocess.CREATE_NO_WINDOW)

    def write(self, rgb, row, expert, initial):
        canvas = Image.new('RGB',(960,420),(19,24,32))
        canvas.paste(Image.fromarray(rgb),(0,0))
        draw = ImageDraw.Draw(canvas)
        now = row['time_s']
        # These boxes are predictions. Ground-truth scene labels are never used.
        for track in expert.bank.tracks.values():
            if now-track.measured_s > .25:
                continue
            d = track.detection
            xy = np.asarray(d['pixel']); half = .5*np.asarray(d['size_px'])
            identity = expert.bank._identity(d)
            colour = (72,230,169) if identity == 1 else ((245,104,111) if identity == 0 else (255,205,100))
            draw.rectangle([*(xy-half),*(xy+half)],outline=colour,width=1)
            draw.text(tuple(xy-half-np.array([0,15])),str(track.index),font=self.font,fill=colour)
        d = row['output']['learner_diagnostics']; a = row['output']['executed_action']
        intent = d.get('expert_intent',{})
        lines = [
            'OBSERVABLE TEACHER', 'No boat radio / actual RGB',
            f"Task: {row['task_time_s']:6.2f} s",
            f"Mode: {d.get('expert_scan_mode','-')}",
            f"Phase: {d.get('control_phase','-')}",
            f"Coverage: {math.degrees(d.get('expert_scan_coverage_rad',0)):5.1f} deg",
            f"Tilt band: {d.get('expert_scan_tilt_goal_deg','-')} deg",
            f"Selected track: {intent.get('selected_track')}",
            f"Confirmed target: {d.get('expert_observable_target_confirmed',False)}",
            f"Metric pad: {d.get('metric_confirmed',False)}",
            f"Target range (eval): {row['privileged']['range_m']:.1f} m",
            f"Owner: {d.get('actual_command_owner','-')}",
            f"Outcome: {row['outcome']}",
        ]
        for i,line in enumerate(lines):
            draw.text((650,9+i*25),line,font=self.font,fill=(255,205,100) if i in (0,3) else (226,235,245))
        draw.text((8,367),f"Initial yaw / pan / tilt: {initial['yaw_deg']:.1f} / {initial['pan_deg']:.1f} / {initial['tilt_deg']:.1f} deg; seed {initial['seed']}",font=self.font,fill='white')
        draw.text((8,393),f"fwd/right/down: {a[0]:+.2f} {a[1]:+.2f} {a[2]:+.2f} m/s | boxes = predictions | range = evaluation only",font=self.font,fill=(255,205,100))
        self.proc.stdin.write(np.asarray(canvas).tobytes())
        self.frames += 1

    def close(self):
        self.proc.stdin.close()
        code = self.proc.wait(timeout=60)
        self.log.close()
        if code:
            raise RuntimeError('ffmpeg failed')
        (self.out/'video.receipt.json').write_text(json.dumps(dict(
            frames=self.frames,fps=25,width=960,height=420,seconds=self.frames/25,
            source='actual onboard RGB; prediction overlay added after actor input',
            sha256=sha(self.out/'review.mp4')),indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',default='episode_01')
    parser.add_argument('--seed',type=int,default=20261024)
    parser.add_argument('--distance',type=float,default=85.)
    parser.add_argument('--duration',type=float,default=180.)
    parser.add_argument('--probe-seconds',type=float,default=0.)
    args = parser.parse_args()
    torch.set_num_threads(1)
    source = CURRICULUM/'sources/target_learning'
    checkpoint = CURRICULUM/'models/perception_v61/best.pt'
    gate = json.loads((HERE/'runtime_probe.json').read_text())
    assert gate['status']=='v61_replay_probe_passed' and gate['frames']==16 and gate['finite_actions']
    assert gate['protocol_sha256']==sha(source/'protocol_priority_v60.py')
    assert gate['adapter_sha256']==sha(source/'expert_adapter_v60.py')
    assert gate['recognizer_sha256']==sha(checkpoint)
    rng = np.random.default_rng(args.seed)
    initial = dict(seed=args.seed, yaw_deg=float(rng.uniform(-180,180)),
                   pan_deg=float(rng.uniform(-90,90)), tilt_deg=float(rng.uniform(-10,90)),
                   sampling='independent uniform draws; no target visibility filtering',
                   policy_pan_interval_deg=[-90,90],policy_tilt_interval_deg=[-10,90])
    scenario = ReviewScenario(name='observable_city85_random',kind='city',world_seed=401,
        path_seed=501,seed=701,distance=args.distance,bearing_deg=270.,height=6.,
        boat_speed=0.,wave_height=.02,wave_period=3.,wind_profile='calm',
        initial_camera_target=False,initial_pan_deg=initial['pan_deg'],
        initial_tilt_deg=initial['tilt_deg'],duration=args.duration)
    scenario.validate()
    out = HERE/args.out
    out.mkdir(parents=True,exist_ok=False)
    (out/'scenario.json').write_text(json.dumps(asdict(scenario),indent=2))
    (out/'random_initialization.json').write_text(json.dumps(initial,indent=2))
    (out/'source_receipt.json').write_text(json.dumps(dict(
        harness_sha256=sha(__file__),protocol_sha256=gate['protocol_sha256'],
        adapter_sha256=gate['adapter_sha256'],checkpoint_sha256=gate['recognizer_sha256'],
        scene_xml_sha256=sha(CITY/'scene.xml'), scene_mjb_sha256=sha(CITY/'scene.mjb'),
        gate=gate, no_radio=True,no_truth_actor_input=True,no_scripted_search_director=True,
        initial_distance_review_extension_only=True,physics_and_scoring_unchanged=True,
        review_only=True,training_eligible=False),indent=2))
    (out/'sources').mkdir()
    for path in [Path(__file__),source/'protocol_priority_v60.py',source/'expert_adapter_v60.py']:
        (out/'sources'/path.name).write_bytes(path.read_bytes())
    manifest = json.loads((CITY/'decoys.json').read_text())
    (out/'decoy_scene.json').write_text(json.dumps(dict(labels=manifest['labels'],
        decoys=manifest['decoys'],actor_input=False),indent=2))
    px4 = renderer = recorder = video = None
    started = time.monotonic(); rows = 0; last_diag = {}; stop = None; error = None
    phase_counts = {}; modes = {}; last_home = None; last_disarm = -100.; deck_dwell = 0.; disarm_events=[]
    try:
        model = mujoco.MjModel.from_binary_path(str(CITY/'scene.mjb'))
        environment.compile_scene = lambda *a,**k:model
        fast_physics_windows.install()
        VerticalLaunchEnvironment.audit_directory=out
        env=VerticalLaunchEnvironment(scenario)
        env.boat.navigation.manual()
        q=env.drone.free_qadr
        env.data.qpos[q+3:q+7]=quaternion(0.,0.,math.radians(initial['yaw_deg']))
        angles=np.radians([initial['pan_deg'],initial['tilt_deg']])
        env.data.qpos[env.drone.camera_qpos]=angles
        env.drone.pan,env.drone.tilt=angles
        mujoco.mj_forward(model,env.data)
        structure=nominal_structure_bound(model);gc.collect()
        reclaim_own_memory(out,'scene_loaded')
        static=StaticRecoveryPrior(env,out);home=HomeReference();prep=Expert(env)
        px4=WindowsPX4(env,out/'px4',instance=0);px4.start()
        previous=np.zeros(6)
        for tick in range(int(math.ceil(env.preparation_budget_s*25))):
            own=px4.observation()
            if own.get('valid') and (own.get('armed') or own['position_source_boot_ms']!=last_home):
                home.observe(own);last_home=own['position_source_boot_ms']
            if tick>125 and tick%50==0 and len(home.samples)>=5 and not px4.armed:
                px4.arm_offboard()
            previous=prep.prepare(px4);px4.send_action(previous);px4.advance()
            if tick%125==0:
                print(json.dumps(dict(status='preparation',sim_s=float(env.data.time),
                    free_ram_gib=round(psutil.virtual_memory().available/2**30,2))),flush=True)
            if (px4.was_airborne and px4.armed and abs(env.vertical_clearance-scenario.height)<.15
                and np.linalg.norm(env.drone.velocity)<.3
                and np.linalg.norm(env.drone.position[:2]-env.task_start_xy)<.15):
                break
        else:
            raise RuntimeError('Preparation did not establish the requested airborne state')
        expert=IdentityExpertV60(local_paths.BUNDLE,checkpoint,device='cpu',
            review_only=True,package_name='two_stage_city85_observable')
        safe=MissionSafety(expert,expert.config['slew_limits']);gc.collect()
        reclaim_own_memory(out,'recognizer_loaded')
        renderer=OnboardRenderer(env);recorder=Recorder(out,asdict(scenario),'review');video=Video(out)
        env.task_start_time=float(env.data.time);env.recording=True;env.boat.navigation.mode='automatic'
        task_start=float(env.data.time)
        actual_initial=dict(own=px4.observation(),gimbal_rad=env.data.qpos[env.drone.camera_qpos].tolist(),
            range_m=float(np.linalg.norm(env.pad_position[:2]-env.drone.position[:2])),
            actor_input=False,random_sample=initial)
        assert actual_initial['range_m']>=80.,actual_initial
        (out/'initial_state.json').write_text(json.dumps(actual_initial,indent=2))
        for index in range(round(scenario.duration*25)+1):
            capture=float(env.data.time);task_s=capture-task_start
            rgb=renderer.onboard_image()
            if index==0:Image.fromarray(rgb).save(out/'initial_actual_rgb.png')
            own=px4.observation()
            own.update(gimbal_commanded_rad=[float(env.drone.pan),float(env.drone.tilt)],
                       gimbal_command_source='own last issued setpoint')
            clear=static.certify(own)
            search=max(4.,math.ceil((structure+.75)*2)/2.)
            xy=np.asarray(own['position_enu_m'])[:2]
            ring=xy+2*np.column_stack((np.cos(np.arange(8)*math.pi/4),np.sin(np.arange(8)*math.pi/4)))
            water=bool(np.min(env.boat.navigation.world.distance(ring))>=5.)
            ceiling=min(10.,float(clear['max_altitude_enu_m'])) if clear.get('valid') else 10.
            mission=dict(home.mission(),elapsed_s=task_s,budget_s=scenario.duration,
                search_timeout_s=140.,recovery_clearance=clear)
            mission['target_discrimination']=dict(search_height_enu_m=search,maximum_height_enu_m=10.,
                nominal_boat_plane_enu_m=.45,plane_uncertainty_m=.4,
                static_prior_no_dynamic_boat_state=True,
                search_corridor_valid=bool(water and own['position_enu_m'][2]>=search-.15 and clear.get('valid') and ceiling>=search),
                upward_corridor_valid=bool(clear.get('valid') and own['position_enu_m'][2]>=structure+.1
                    and ceiling-own['position_enu_m'][2]>=max(2.6,search-own['position_enu_m'][2]+.1)),
                nominal_structure_bound_m=structure)
            observation=dict(px4=own,beacon=absent_beacon(),gimbal_rad=env.data.qpos[env.drone.camera_qpos].tolist(),
                gimbal_source='synthetic own encoder',image_capture_time_s=capture,image_delivery_time_s=capture,
                image_age_s=0.,image_valid=True,decision_dt_s=.04,previous_executed_action=previous.tolist(),mission=mission)
            terminal=env.outcome in ('landed','water_strike','collision_failure')
            if terminal:
                action=np.zeros(6);diag=copy.deepcopy(last_diag);owner='terminal_no_command'
            else:
                action,diag=safe.act(rgb,observation);owner='observable_teacher'
                if diag.get('mission_fallback_active'):
                    action=np.zeros(6);owner='stop_before_home_fallback';stop='mission_fallback_requested'
                if expert.protocol.search_exhausted:
                    stop='three_empty_surveys_no_candidate'
            action=prep.bounded(action)
            action,reason=expert.supervise(action,observation,task_s,scenario.duration)
            if reason and not terminal:owner='safety'
            diag.update(actual_command_owner=owner,evaluation_fault_active=False)
            last_diag=copy.deepcopy(diag)
            row=dict(schema='aerodock.landing.step.v1',role='review',frame_index=index,
                time_s=capture,task_time_s=task_s,phase=diag.get('control_phase','unknown'),outcome=env.outcome,
                observation=observation,output=dict(executed_action=action.tolist(),
                    observable_expert_proposal=action.tolist(),learner_diagnostics=diag,intervention=reason,
                    action_supervision_valid=False),privileged=dict(
                    drone_position_enu_m=env.drone.position.tolist(),pad_position_enu_m=env.pad_position.tolist(),
                    range_m=float(np.linalg.norm(env.pad_position[:2]-env.drone.position[:2])),
                    clearance_m=float(env.clearance),annotation_and_scoring_only=True))
            row['terminal']=terminal
            probe=bool(args.probe_seconds and task_s>=args.probe_seconds)
            row['output']['command_was_sent_after_frame']=not (terminal or stop or probe or task_s>=scenario.duration)
            recorder.append(rgb,row);video.write(rgb,row,expert,initial);rows+=1
            phase_counts[row['phase']]=phase_counts.get(row['phase'],0)+1
            mode=diag.get('expert_scan_mode','unknown');modes[mode]=modes.get(mode,0)+1
            if index%100==0:
                state=dict(status='flying',task_s=round(task_s,2),frames=rows,phase=row['phase'],mode=mode,
                    selected=expert.protocol.selected,confirmed=expert.protocol.confirmed,
                    coverage_deg=round(math.degrees(expert.protocol.scan_coverage),1),
                    range_eval_m=round(row['privileged']['range_m'],1),outcome=env.outcome,
                    wall_s=round(time.monotonic()-started,1))
                (out/'state.json').write_text(json.dumps(state,indent=2));print(json.dumps(state),flush=True)
            if terminal or stop or probe or task_s>=scenario.duration:
                stop=stop or ('bounded_probe' if probe else ('task_duration' if not terminal else None))
                Image.fromarray(rgb).save(out/'terminal.png')
                break
            deck_dwell=disarm_policy.dwell(deck_dwell,.04,float(env.clearance))
            disarm_now, disarm_reason=disarm_policy.should_disarm(armed=px4.armed,was_airborne=px4.was_airborne,
                px4_landed=px4.landed,contact_s=float(env.contact_seconds),
                speed_m_s=float(np.linalg.norm(env.drone.velocity)),dwell_s=deck_dwell,
                since_last_disarm_s=capture-last_disarm,clearance_m=float(env.clearance))
            ordinary=px4.armed and px4.was_airborne and px4.landed
            if (ordinary or disarm_now) and capture-last_disarm>=disarm_policy.DISARM_GUARD_S:
                if ordinary:px4.request_disarm();disarm_reason='px4_landed'
                else:px4.request_forced_disarm()
                last_disarm=capture
                disarm_events.append(dict(task_s=task_s,reason=disarm_reason,termination_only=True))
            if psutil.virtual_memory().available < .35*2**30:
                reclaim_own_memory(out,'low_available_memory')
                for _ in range(3):
                    if psutil.virtual_memory().available >= .15*2**30:break
                    time.sleep(.5);reclaim_own_memory(out,'persistent_low_memory')
                if psutil.virtual_memory().available < .15*2**30:
                    raise MemoryError('Review stopped after reclaim below 0.15 GiB available memory')
            px4.send_action(action);px4.advance();previous=action
        result=dict(outcome=env.outcome,stop_reason=stop,frames=rows,phase_counts=phase_counts,scan_modes=modes,
            initial=actual_initial,protocol=expert.protocol.diagnostics(),events=env.events,disarm_events=disarm_events,
            actor='updated observable teacher; v61 recognizer',radio=False,truth_controls=False,
            wall_s=time.monotonic()-started,review_only=True,training_eligible=False)
        (out/'summary.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(dict(status='finished',outcome=env.outcome,stop_reason=stop,frames=rows)),flush=True)
    except BaseException as exc:
        error=repr(exc)
        (out/'error.json').write_text(json.dumps(dict(error=error,traceback=traceback.format_exc(),frames=rows),indent=2))
        raise
    finally:
        errors=[]
        for name,obj in [('video',video),('recorder',recorder),('renderer',renderer),('px4',px4)]:
            if obj is not None:
                try:obj.close()
                except BaseException as exc:errors.append(dict(resource=name,error=repr(exc)))
        (out/'closed.json').write_text(json.dumps(dict(frames=rows,error=error,cleanup_errors=errors),indent=2))


if __name__=='__main__':
    main()
