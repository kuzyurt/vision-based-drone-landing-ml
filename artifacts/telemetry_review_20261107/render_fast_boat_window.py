"""Render a labelled telemetry reconstruction of one recorded episode.

This is media review only. It uses recorded positions and logged attitude/gimbal;
it does not run PX4, physics, a policy, or a scorer. The episode has no original
RGB video, so the images are reconstructed and must not be described as original
policy input frames.
"""
from pathlib import Path
import hashlib
import html
import json
import math
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO), str(REPO / 'artifacts/local_curriculum_20261020')]

import local_paths  # noqa: F401
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation

from benchmark import runner
from benchmark.common import read, sha, write
from landing_training import environment
from usv.boat_sim import quaternion
from usv.world_render import WorldRenderer
from sim.server import C, D

SOURCE = REPO / (
    'benchmark/revisions/bounded_search_20261026/runs/guard_support_b_rest/'
    'fresh-search-f62c10a2/landing-landing-fast-boat-city-r1'
)
START_S = 35.0
REQUESTED_END_S = 75.0
FPS = 12.5
VIDEO = HERE / 'fast_boat_35_69.mp4'
PARTIAL = HERE / 'fast_boat_35_69.partial.mp4'
POSTER = HERE / 'fast_boat_51_52.png'
RECEIPT = HERE / 'fast_boat_render_receipt.json'
PAGE = HERE / 'fast_boat_window.html'


def font(name, size):
    path = Path('C:/Windows/Fonts') / name
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def main():
    rows = [json.loads(line) for line in (SOURCE / 'steps.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    result = read(SOURCE / 'result.json')
    case = read(SOURCE / 'case.json')
    if sha(SOURCE / 'steps.jsonl') != result['trace_sha256']:
        raise RuntimeError('steps.jsonl does not match result.trace_sha256')

    times = np.asarray([row['task_s'] for row in rows])
    first = int(np.searchsorted(times, START_S, side='left'))
    last = int(np.searchsorted(times, REQUESTED_END_S, side='right')) - 1
    if first >= len(rows) or last < first:
        raise RuntimeError('No recorded rows in requested window')
    indices = list(range(first, last + 1))
    frame_indices = indices[::2]
    if frame_indices[-1] != indices[-1]:
        frame_indices.append(indices[-1])
    # Include the one accepted metric frame exactly so the poster is not a
    # neighbouring no-registration frame.
    key_index = min(indices, key=lambda i: abs(times[i] - 51.52))
    if key_index not in frame_indices:
        frame_indices.append(key_index)
        frame_indices.sort()

    runtime = read(REPO / 'benchmark/environments/runtime.json')
    environment.compile_scene = lambda *args, **kwargs: mujoco.MjModel.from_binary_path(str(REPO / runtime['scene']))
    env = environment.Environment(runner.make_scenario(case))
    runner.setup_scene(env, case, HERE)
    renderer = runner.make_renderer(env)
    external = mujoco.Renderer(env.model, height=450, width=800, max_geom=20000)
    renderer.worlds[id(external)] = WorldRenderer(env.model, radius=250)
    for flag in (mujoco.mjtRndFlag.mjRND_SHADOW, mujoco.mjtRndFlag.mjRND_REFLECTION):
        external.scene.flags[flag] = False

    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    boat_q = env.boat.free_qadr
    drone_q = env.drone.free_qadr
    boat_rotation = env.data.xmat[env.boat.boat].reshape(3, 3)
    pad_local = boat_rotation.T @ (env.pad_position - env.data.xpos[env.boat.boat])
    initial_euler = Rotation.from_matrix(boat_rotation).as_euler('xyz')
    pads = np.asarray([row['scoring_only']['pad_position_enu_m'] for row in rows])

    title_font = font('arialbd.ttf', 29)
    heading_font = font('arialbd.ttf', 22)
    body_font = font('consola.ttf', 18)
    small_font = font('consola.ttf', 16)

    receipt = {
        'schema': 'drone.benchmark.telemetry_video.v1',
        'status': 'rendering',
        'source': str(SOURCE.relative_to(REPO)).replace('\\', '/'),
        'source_trace_sha256': sha(SOURCE / 'steps.jsonl'),
        'source_result_sha256': sha(SOURCE / 'result.json'),
        'policy_inference_executed': False,
        'physics_rerun': False,
        'training_eligible': False,
        'scored_trial': False,
        'reconstructed': True,
        'original_rgb_recording': False,
        'requested_window_s': [START_S, REQUESTED_END_S],
        'actual_window_s': [float(times[first]), float(times[last])],
        'exact_fields': [
            'recorded drone position',
            'recorded pad position',
            'recorded task timeline',
            'recorded diagnostics and actions',
        ],
        'approximate_fields': [
            'drone orientation from PX4 estimate',
            'gimbal pose from own encoder including noise',
            'boat heading from recorded motion',
            'boat roll/pitch use initial static trim; articulated joints use prepared nominal geometry',
        ],
        'frames': 0,
    }
    write(RECEIPT, receipt)

    def compose(row, frame_number):
        s = row['scoring_only']
        obs = row['observation']
        d = row['diagnostics']
        external_img = renderer.view(external, cam)
        onboard_img = renderer.onboard_image()
        canvas = Image.new('RGB', (1440, 810), '#0d1620')
        canvas.paste(Image.fromarray(external_img), (0, 50))
        canvas.paste(Image.fromarray(onboard_img), (800, 50))
        draw = ImageDraw.Draw(canvas)
        draw.text((18, 8), 'FAST BOAT | TELEMETRY RECONSTRUCTION', font=title_font, fill='#eef4fa')
        draw.text((18, 512), 'OUTSIDE VIEW', font=heading_font, fill='#8bd0f5')
        draw.text((818, 426), 'ONBOARD VIEW (reconstructed)', font=heading_font, fill='#8bd0f5')

        horizontal = math.hypot(
            s['drone_position_enu_m'][0] - s['pad_position_enu_m'][0],
            s['drone_position_enu_m'][1] - s['pad_position_enu_m'][1],
        )
        altitude = s['drone_position_enu_m'][2] - s['pad_position_enu_m'][2]
        metric = bool(d.get('metric_valid'))
        confirmed = bool(d.get('metric_confirmed'))
        identity = bool(d.get('search_identity_confirmed'))
        support = bool(d.get('mission_supported_visual_finish'))
        acceptance = str(d.get('metric_acceptance') or 'none')
        phase = str(d.get('control_phase') or 'unknown')
        remaining = result['mission_time_s'] - row['task_s']

        metric_color = '#77dd99' if metric else '#f1ce85'
        support_color = '#77dd99' if support else '#f08d8d'
        left = [
            (f"Window: {START_S:.2f}-{result['mission_time_s']:.2f} s  |  frame {frame_number}/{len(frame_indices)}", '#dce7ee'),
            (f"Mission time: {row['task_s']:.2f} s  |  remaining {remaining:.2f} s", '#dce7ee'),
            (f"Phase: {phase}  |  selected: {d.get('selected') or d.get('selected_visual_track') or 'none'}", '#dce7ee'),
            (f"Horizontal distance: {horizontal:.2f} m  |  altitude above pad: {altitude:.2f} m", '#dce7ee'),
            (f"Identity: {'YES' if identity else 'no'}  |  metric: {'VALID' if metric else 'no'}  |  confirmed: {'yes' if confirmed else 'no'}", metric_color),
            (f"Marker acceptance: {acceptance}  |  fit candidate: {'yes' if d.get('fit_candidate_valid') else 'no'}", '#dce7ee'),
            (f"Visual finish support: {'yes' if support else 'NO'}  |  stalled: {'yes' if d.get('mission_visual_progress_stalled') else 'no'}", support_color),
        ]
        for i, (line, color) in enumerate(left):
            draw.text((18, 548 + i * 27), line, font=small_font, fill=color)

        right = [
            'RECONSTRUCTED VIDEO - NOT ORIGINAL RGB',
            'Recorded positions/timeline: exact',
            'Drone attitude/gimbal: logged estimates',
            'Boat heading/trim: approximate',
            'No policy inference or physics rerun',
        ]
        for i, line in enumerate(right):
            draw.text((818, 458 + i * 25), line, font=small_font,
                      fill='#f1ce85' if i == 0 else '#aebdca')

        # A simple event strip makes the 51.52 s metric flash and the 66.48 s
        # support loss visible without turning the replay into a dashboard.
        y = 770
        draw.rectangle((18, y, 1422, y + 5), fill='#33434f')
        progress = (row['task_s'] - START_S) / max(1e-9, result['mission_time_s'] - START_S)
        draw.rectangle((18, y, 18 + int(1404 * progress), y + 5), fill='#7ac9f3')
        for j, (event_s, label, color) in enumerate([
            (51.52, 'metric flash', '#77dd99'),
            (51.68, 'gap', '#f1ce85'),
            (66.48, 'support lost', '#f08d8d'),
            (69.48, 'fallback', '#f08d8d'),
        ]):
            x = 18 + int(1404 * (event_s - START_S) / max(1e-9, result['mission_time_s'] - START_S))
            draw.line((x, y - 8, x, y + 12), fill=color, width=2)
            text_width = draw.textlength(label, font=small_font)
            text_x = x + 4 if x + text_width + 8 < 1420 else x - text_width - 4
            text_y = y - 24 if j % 2 == 0 else y - 44
            draw.text((text_x, text_y), label, font=small_font, fill=color)
        draw.text((18, 790), f"Recorded episode ends at {result['mission_time_s']:.2f} s (requested window {START_S:.0f}-{REQUESTED_END_S:.0f} s)",
                  font=small_font, fill='#f1ce85')
        return np.asarray(canvas)

    log = (HERE / 'ffmpeg.log').open('w', encoding='utf-8')
    writer = subprocess.Popen([
        'ffmpeg', '-nostdin', '-y', '-loglevel', 'error',
        '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', '1440x810',
        '-framerate', str(FPS), '-i', 'pipe:0', '-an',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(PARTIAL),
    ], stdin=subprocess.PIPE, stderr=log,
       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    max_drone_error = 0.0
    max_pad_error = 0.0
    poster_saved = False
    began = time.perf_counter()
    try:
        for frame_number, i in enumerate(frame_indices, 1):
            row = rows[i]
            s = row['scoring_only']
            obs = row['observation']
            env.data.time = obs['image_capture_time_s']
            env.data.qpos[drone_q:drone_q + 3] = s['drone_position_enu_m']
            r = C.T @ Rotation.from_euler('xyz', obs['px4']['attitude_ned_rad']).as_matrix() @ D
            q = Rotation.from_matrix(r).as_quat()
            env.data.qpos[drone_q + 3:drone_q + 7] = q[[3, 0, 1, 2]]
            env.data.qpos[env.drone.camera_qpos] = obs['gimbal_rad']

            low = max(0, i - 10)
            high = min(len(rows) - 1, i + 10)
            velocity = pads[high, :2] - pads[low, :2]
            yaw = initial_euler[2] if np.linalg.norm(velocity) < .02 else math.atan2(velocity[1], velocity[0])
            boat_r = Rotation.from_euler('xyz', [initial_euler[0], initial_euler[1], yaw]).as_matrix()
            env.data.qpos[boat_q:boat_q + 3] = pads[i] - boat_r @ pad_local
            env.data.qpos[boat_q + 3:boat_q + 7] = quaternion(initial_euler[0], initial_euler[1], yaw)

            # Forward kinematics only: no physics step and no generated actions.
            mujoco.mj_kinematics(env.model, env.data)
            mujoco.mj_comPos(env.model, env.data)
            mujoco.mj_camlight(env.model, env.data)
            max_drone_error = max(max_drone_error, float(np.linalg.norm(env.drone.position - s['drone_position_enu_m'])))
            max_pad_error = max(max_pad_error, float(np.linalg.norm(env.pad_position - pads[i])))

            cam.lookat[:] = (env.pad_position + env.drone.position) / 2
            cam.distance = max(6.0, float(np.linalg.norm(env.pad_position - env.drone.position)) * 1.15 + 3.0)
            cam.azimuth = math.degrees(env.boat_yaw) + 135.0
            cam.elevation = -23.0

            frame = compose(row, frame_number)
            if not poster_saved and i == key_index:
                Image.fromarray(frame).save(POSTER)
                poster_saved = True
            writer.stdin.write(frame.tobytes())
            receipt['frames'] = frame_number
            if frame_number % 100 == 0:
                write(RECEIPT, dict(receipt, last_task_s=row['task_s']))
                print(json.dumps({'frame': frame_number, 'task_s': row['task_s']}), flush=True)

        writer.stdin.close()
        if writer.wait() != 0:
            raise RuntimeError('ffmpeg failed; see ffmpeg.log')
        if max_drone_error > 1e-8 or max_pad_error > 1e-8:
            raise RuntimeError('Reconstructed positions diverged from the recorded trace')
        PARTIAL.replace(VIDEO)
        receipt.update(
            status='completed',
            frames=len(frame_indices),
            last_task_s=float(times[last]),
            video=VIDEO.name,
            video_sha256=sha(VIDEO),
            max_drone_position_error_m=max_drone_error,
            max_pad_position_error_m=max_pad_error,
            duration_s=len(frame_indices) / FPS,
            wall_seconds=time.perf_counter() - began,
            note='The recorded episode ends at 69.48 s; no rows exist for 69.48-75.0 s.',
        )
        write(RECEIPT, receipt)
        write_page(rows, result, frame_indices, receipt)
        print(json.dumps(receipt), flush=True)
    finally:
        if writer.poll() is None:
            try:
                writer.stdin.close()
            except OSError:
                pass
            writer.wait()
        log.close()
        external.close()
        renderer.close()


def write_page(rows, result, frame_indices, receipt):
    mission_end = float(result['mission_time_s'])
    start = float(rows[frame_indices[0]]['task_s'])
    poster = POSTER.name if POSTER.exists() else ''
    events = [
        (40.60, 'identity lock'),
        (51.52, 'one valid metric (0.117 m)'),
        (51.68, 'recovery / metric gap'),
        (66.48, 'support lost'),
        (69.44, 'last logged decision'),
    ]
    buttons = '\n'.join(
        f'<button data-time="{max(0.0, t - start):.2f}">{t:.2f} s · {html.escape(label)}</button>'
        for t, label in events
    )
    page = f'''<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fast boat · 35–69.48 s reconstruction</title>
<style>
:root{{color-scheme:dark;font:16px/1.55 system-ui,sans-serif;background:#0d1620;color:#e6edf3}}
body{{max-width:1440px;margin:32px auto;padding:0 24px}}
h1{{font-size:30px;margin-bottom:6px}} .sub{{color:#aebdca;margin-top:0}}
.id{{font-family:monospace;color:#8bd0f5}}
video{{display:block;width:100%;max-height:76vh;background:#000;border:1px solid #344554;border-radius:8px}}
nav{{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}}
button{{font:inherit;cursor:pointer;background:#203446;color:#e6edf3;border:1px solid #526b80;border-radius:6px;padding:8px 14px}}
button:hover{{background:#31536e}} .note{{padding:14px 18px;background:#162330;border-left:3px solid #8bd0f5}}
.muted{{color:#aebdca}} a{{color:#8bd0f5}} .result{{color:#f1ce85}}
</style>
<h1><span class="id">FAST BOAT</span> · 35–69.48 s telemetry reconstruction</h1>
<p class="sub">City · 30 m start · boat 1.5 m/s · no decoys · mission <span class="id">landing-landing-fast-boat-city-r1</span></p>
<video id="flight" controls preload="metadata" poster="{poster}">
  <source src="{VIDEO.name}" type="video/mp4">
</video>
<nav aria-label="Jump to event">{buttons}<button id="speed">Playback: 1×</button></nav>
<p class="result">Recorded result: mission_fallback at {mission_end:.2f} s. No landing, no verified acquisition; final lateral error 6.686 m.</p>
<p class="note">This is a <strong>telemetry reconstruction</strong>, not original RGB. Recorded positions, timing and diagnostics are exact. Drone attitude and gimbal use logged estimates; boat heading and trim are approximate. The original episode contains no onboard video, so these images are not evidence of actual pixel visibility or marker detection.</p>
<p class="muted">The requested window was 35–75 s, but the recorded episode ends at {mission_end:.2f} s. The video therefore covers {start:.2f}–{mission_end:.2f} s. It performs no policy inference, no physics step and no new scoring. See the <a href="{RECEIPT.name}">render receipt</a>.</p>
<script>
const video=document.querySelector('video');
document.querySelectorAll('[data-time]').forEach(button=>button.addEventListener('click',()=>{{video.currentTime=Number(button.dataset.time);video.play()}}));
const speeds=[1,2,.5];let speed=0;
document.querySelector('#speed').addEventListener('click',event=>{{speed=(speed+1)%speeds.length;video.playbackRate=speeds[speed];event.target.textContent=`Playback: ${{speeds[speed]}}×`}});
</script>
</html>'''
    PAGE.write_text(page, encoding='utf-8')


if __name__ == '__main__':
    main()
