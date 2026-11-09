"""No-NN, visibility-gated teacher; native PX4 and the existing six-decoy scene."""
from __future__ import annotations
import argparse
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
CITY = REPO/'artifacts/city80_decoys_20261023'
CURRICULUM = REPO/'artifacts/local_curriculum_20261020'
sys.path[:0] = [str(REPO), str(CURRICULUM)]
import local_paths
sys.path.insert(0, str(CURRICULUM/'sources'))
import mujoco
import numpy as np
import psutil
from PIL import Image, ImageDraw, ImageFont
import fast_physics_windows
from landing_training import environment, rendering
from landing_training.config import Scenario
from landing_training.expert import Expert
from landing_training.privileged_teacher import PrivilegedTeacher, VisibleBoatOracle
from landing_training.recording import Recorder
from mission_setup import VerticalLaunchEnvironment
from windows_px4_v2 import WindowsPX4
from windows_renderer import OnboardRenderer
from radio_link import absent_beacon
from target_learning.scenes import annotation_groups
from target_learning.label_renderer import install, identify_water
from usv.boat_sim import quaternion
import disarm_policy

install(rendering)

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

class LabelRenderer(OnboardRenderer):
    def append_water(self, scene):
        super().append_water(scene)
        identify_water(scene, self.env)

@dataclass(frozen=True)
class ReviewScenario(Scenario):
    def validate(self):
        if not 80 <= self.distance <= 90 or not 1 <= self.duration <= 300:
            raise ValueError('Explicit review envelope: 80..90 m, <=300 s')
        Scenario.validate(replace(self, distance=60., duration=min(180., self.duration)))

class Video:
    def __init__(self, out):
        self.out = out; self.frames = 0
        self.font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 14)
        self.small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 12)
        self.log = (out/'video_encode.log').open('x')
        self.proc = subprocess.Popen(['ffmpeg','-n','-loglevel','error','-f','rawvideo',
            '-pixel_format','rgb24','-video_size','960x420','-framerate','25','-i','pipe:0',
            '-an','-c:v','libx264','-preset','veryfast','-threads','2','-crf','22',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(out/'review.mp4')],
            stdin=subprocess.PIPE,stderr=self.log,creationflags=subprocess.CREATE_NO_WINDOW)

    def write(self, rgb, row, views, initial):
        canvas = Image.new('RGB',(960,420),(19,24,32)); canvas.paste(Image.fromarray(rgb),(0,0))
        draw = ImageDraw.Draw(canvas); d = row['output']['teacher_diagnostics']
        for v in views:
            if not v.detectable: continue
            colour = '#50dfb0' if v.evidence == 'target_boat' else ('#fa8585' if v.evidence == 'different_boat' else '#f1ce71')
            draw.rectangle(v.bbox,outline=colour,width=2)
            label = f"{v.key.replace('decoy_false_boat_', '')}: {v.range_m:.0f}m"
            draw.text((v.bbox[0],max(0,v.bbox[1]-14)),label,font=self.small,fill=colour)
        selected = (d.get('selected') or '-').replace('decoy_false_boat_', '')
        lines = ['SIMULATOR-ASSISTED TEACHER','No neural detector / no radio',
            f"Task: {row['task_time_s']:6.2f} s",f"Mode: {d.get('mode','-')}",
            f"Phase: {d.get('control_phase','-')}",f"Scan: {d.get('coverage_deg',0):5.1f} / 360 deg",
            f"Selected: {selected}",f"Confirmed: {d.get('confirmed',False)}",
            f"Evidence: {d.get('selected_evidence') or '-'}",f"Rejected boats: {len(d.get('rejected',[]))}",
            f"Pad visible: {d.get('metric_confirmed',False)}",
            f"Target range: {row['privileged']['range_m']:.1f} m",f"Outcome: {row['outcome']}"]
        for i,line in enumerate(lines):
            draw.text((650,8+i*26),line,font=self.font,fill='#f1ce71' if i in (0,3) else '#e2ebf5')
        draw.text((8,368),f"Start: 85m | random yaw {initial['yaw_deg']:.1f}, pan {initial['pan_deg']:.1f}, tilt {initial['tilt_deg']:.1f} deg",font=self.font,fill='white')
        draw.text((8,395),'Boxes = exact visible pixels. Yellow: unknown/ambiguous | green: identified target | red: reject',font=self.small,fill='#f1ce71')
        self.proc.stdin.write(np.asarray(canvas).tobytes()); self.frames += 1

    def close(self):
        self.proc.stdin.close(); code = self.proc.wait(timeout=60); self.log.close()
        if code: raise RuntimeError('ffmpeg failed')
        (self.out/'video.receipt.json').write_text(json.dumps(dict(frames=self.frames,fps=25,
            width=960,height=420,seconds=self.frames/25,sha256=sha(self.out/'review.mp4'),
            source='actual onboard RGB; visible segmentation boxes added after actor decision'),indent=2))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',default='privileged_episode_01'); p.add_argument('--seed',type=int,default=20261024)
    p.add_argument('--duration',type=float,default=240.); p.add_argument('--probe-seconds',type=float,default=0.)
    args = p.parse_args()
    rng = np.random.default_rng(args.seed)
    initial = dict(seed=args.seed,yaw_deg=float(rng.uniform(-180,180)),pan_deg=float(rng.uniform(-90,90)),
        tilt_deg=float(rng.uniform(-10,90)),sampling='independent uniform draws; no visibility filtering',
        policy_pan_interval_deg=[-90,90],policy_tilt_interval_deg=[-10,90])
    scenario = ReviewScenario(name='privileged_city85_random',kind='city',world_seed=401,path_seed=501,
        seed=701,distance=85.,bearing_deg=270.,height=6.,boat_speed=0.,wave_height=.02,wave_period=3.,
        wind_profile='calm',initial_camera_target=False,initial_pan_deg=initial['pan_deg'],
        initial_tilt_deg=initial['tilt_deg'],duration=args.duration)
    scenario.validate(); out = HERE/args.out; out.mkdir(parents=True,exist_ok=False)
    (out/'sources').mkdir()
    sources = [Path(__file__),REPO/'landing_training/privileged_teacher.py',REPO/'landing_training/expert.py']
    for source in sources: (out/'sources'/source.name).write_bytes(source.read_bytes())
    (out/'source_receipt.json').write_text(json.dumps(dict(
        sources={str(s.relative_to(REPO)):sha(s) for s in sources},scene_mjb_sha256=sha(CITY/'scene.mjb'),
        actor='privileged_visibility_gated_teacher',neural_network_used=False,no_radio=True,
        truth_labels_separate_from_student_inputs=True,review_only=True,training_eligible=False),indent=2))
    (out/'scenario.json').write_text(json.dumps(asdict(scenario),indent=2))
    (out/'random_initialization.json').write_text(json.dumps(initial,indent=2))
    (out/'decoy_scene.json').write_bytes((CITY/'decoys.json').read_bytes())
    px4 = renderer = recorder = video = None
    started = time.monotonic(); rows = 0; stop = None; error = None
    phase_counts = {}; modes = {}; disarms = []; last_disarm = -100.; deck_dwell = 0.
    try:
        model = mujoco.MjModel.from_binary_path(str(CITY/'scene.mjb'))
        environment.compile_scene = lambda *a,**k:model
        fast_physics_windows.install(); VerticalLaunchEnvironment.audit_directory = out
        env = VerticalLaunchEnvironment(scenario); env.boat.navigation.manual()
        q = env.drone.free_qadr
        env.data.qpos[q+3:q+7] = quaternion(0.,0.,math.radians(initial['yaw_deg']))
        angles = np.radians([initial['pan_deg'],initial['tilt_deg']])
        env.data.qpos[env.drone.camera_qpos] = angles; env.drone.pan, env.drone.tilt = angles
        mujoco.mj_forward(model,env.data); gc.collect()
        prep = Expert(env); px4 = WindowsPX4(env,out/'px4',instance=0); px4.start()
        previous = np.zeros(6)
        for tick in range(int(math.ceil(env.preparation_budget_s*25))):
            if tick > 125 and tick%50 == 0 and not px4.armed: px4.arm_offboard()
            previous = prep.prepare(px4); px4.send_action(previous); px4.advance()
            if tick%125 == 0: print(json.dumps(dict(status='preparation',sim_s=float(env.data.time))),flush=True)
            if (px4.was_airborne and px4.armed and abs(env.vertical_clearance-scenario.height)<.15
                and np.linalg.norm(env.drone.velocity)<.3 and np.linalg.norm(env.drone.position[:2]-env.task_start_xy)<.15): break
        else: raise RuntimeError('Preparation did not establish requested airborne state')
        teacher = PrivilegedTeacher(env)
        oracle = VisibleBoatOracle(env,annotation_groups(model))
        renderer = LabelRenderer(env); recorder = Recorder(out,asdict(scenario),'review'); video = Video(out)
        env.task_start_time = float(env.data.time); env.recording = True; env.boat.navigation.mode = 'automatic'
        actual_initial = dict(own=px4.observation(),gimbal_rad=env.data.qpos[env.drone.camera_qpos].tolist(),
            range_m=float(np.linalg.norm(env.pad_position[:2]-env.drone.position[:2])),random_sample=initial)
        assert actual_initial['range_m'] >= 80.
        (out/'initial_state.json').write_text(json.dumps(actual_initial,indent=2))
        for index in range(round(scenario.duration*25)+1):
            capture = float(env.data.time); task_s = capture-env.task_start_time
            rgb = renderer.onboard_image()
            renderer.onboard.enable_segmentation_rendering()
            # Re-render the identical frozen scene: no second water/scenery
            # rebuild and no physics step between RGB and its visible labels.
            try: segmentation = renderer.onboard.render().copy()
            finally: renderer.onboard.disable_segmentation_rendering()
            views = oracle.observe(segmentation)
            if index == 0: Image.fromarray(rgb).save(out/'initial_actual_rgb.png')
            observation = dict(px4=px4.observation(),beacon=absent_beacon(),
                gimbal_rad=env.data.qpos[env.drone.camera_qpos].tolist(),gimbal_source='synthetic own encoder',
                image_capture_time_s=capture,image_delivery_time_s=capture,image_age_s=0.,image_valid=True,
                decision_dt_s=.04,previous_executed_action=previous.tolist(),
                mission=dict(elapsed_s=task_s,budget_s=scenario.duration))
            terminal = env.outcome in ('landed','water_strike','collision_failure')
            action, diag = teacher.act(px4,observation,views)
            if terminal: action = np.zeros(6)
            row = dict(schema='aerodock.landing.step.v1',role='review',frame_index=index,time_s=capture,
                task_time_s=task_s,phase=diag['control_phase'],outcome=env.outcome,terminal=terminal,
                observation=observation,output=dict(executed_action=action.tolist(),teacher_diagnostics=diag,
                    action_supervision_valid=False,intervention=diag['intervention']),
                privileged=dict(drone_position_enu_m=env.drone.position.tolist(),pad_position_enu_m=env.pad_position.tolist(),
                    range_m=float(np.linalg.norm(env.pad_position[:2]-env.drone.position[:2])),
                    clearance_m=float(env.clearance),boats=[v.annotation() for v in views],
                    student_input=False))
            probe = args.probe_seconds and task_s >= args.probe_seconds
            row['output']['command_was_sent_after_frame'] = not (terminal or probe or task_s >= scenario.duration)
            recorder.append(rgb,row); video.write(rgb,row,views,initial); rows += 1
            phase_counts[row['phase']] = phase_counts.get(row['phase'],0)+1
            modes[diag['mode']] = modes.get(diag['mode'],0)+1
            if index%100 == 0:
                state = dict(status='flying',task_s=round(task_s,2),frames=rows,**diag,
                    range_eval_m=round(row['privileged']['range_m'],1),outcome=env.outcome,
                    wall_s=round(time.monotonic()-started,1),torch_loaded='torch' in sys.modules)
                (out/'state.json').write_text(json.dumps(state,indent=2)); print(json.dumps(state),flush=True)
            if terminal or probe or task_s >= scenario.duration:
                stop = 'bounded_probe' if probe else (None if terminal else 'task_duration')
                Image.fromarray(rgb).save(out/'terminal.png'); break
            deck_dwell = disarm_policy.dwell(deck_dwell,.04,float(env.clearance))
            disarm_now, reason = disarm_policy.should_disarm(armed=px4.armed,was_airborne=px4.was_airborne,
                px4_landed=px4.landed,contact_s=float(env.contact_seconds),speed_m_s=float(np.linalg.norm(env.drone.velocity)),
                dwell_s=deck_dwell,since_last_disarm_s=capture-last_disarm,clearance_m=float(env.clearance))
            ordinary = px4.armed and px4.was_airborne and px4.landed
            if (ordinary or disarm_now) and capture-last_disarm >= disarm_policy.DISARM_GUARD_S:
                if ordinary: px4.request_disarm(); reason = 'px4_landed'
                else: px4.request_forced_disarm()
                last_disarm = capture; disarms.append(dict(task_s=task_s,reason=reason,termination_only=True))
            px4.send_action(action); px4.advance(); previous = action
        result = dict(outcome=env.outcome,stop_reason=stop,frames=rows,phase_counts=phase_counts,scan_modes=modes,
            initial=actual_initial,search=teacher.search.diagnostics(),search_events=teacher.search.events,
            events=env.events,disarm_events=disarms,actor='privileged_visibility_gated_teacher',radio=False,
            neural_network_used=False,torch_loaded='torch' in sys.modules,wall_s=time.monotonic()-started,
            review_only=True,training_eligible=False)
        (out/'summary.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result),flush=True)
    except BaseException as exc:
        error = repr(exc)
        (out/'error.json').write_text(json.dumps(dict(error=error,traceback=traceback.format_exc(),frames=rows),indent=2))
        raise
    finally:
        errors = []
        for name,obj in [('video',video),('recorder',recorder),('renderer',renderer),('px4',px4)]:
            if obj is not None:
                try: obj.close()
                except BaseException as exc: errors.append(dict(resource=name,error=repr(exc)))
        (out/'closed.json').write_text(json.dumps(dict(frames=rows,error=error,cleanup_errors=errors),indent=2))

if __name__ == '__main__': main()
