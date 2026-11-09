"""Read-only review of existing teacher RGB; no simulation, training or new flights."""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
import tarfile
import time

import h5py
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
SOURCE = REPO / 'landing_training/outputs/domain_training_20261016T134939Z'
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from landing_training import paths
from landing_training.rendering import VideoWriter

CASES = [
    dict(number=1, name='training_beach_00_0', start=0., end=None, speed=2.,
         title='Visible approach and touchdown',
         watch='Watch when descent starts and whether alignment stays steady.'),
    dict(number=2, name='training_beach_01_0', start=0., end=18., speed=1.,
         title='Search switches to hidden-position assistance',
         watch='At 7.76 s the expert translates before the pad is visible.'),
    dict(number=3, name='training_beach_02_0', start=0., end=18., speed=1.,
         title='Far target: a brief sighting is swept past',
         watch='Look for a tiny pad, then the timed scan and privileged recovery.'),
    dict(number=4, name='training_city_07_1', start=5., end=17., speed=1.,
         title='Reacquisition with information the learner lacks',
         watch='Watch reacquire: pad visibility is false while movement continues.'),
]


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False))


def render(case):
    directory = SOURCE / 'dataset' / case['name']
    rows = [json.loads(line) for line in (directory / 'steps.jsonl').read_text().splitlines()]
    rows = [row for row in rows if not row.get('terminal', False)]
    times = np.array([row['task_time_s'] for row in rows])
    end = float(times[-1]) if case['end'] is None else min(case['end'], float(times[-1]))
    duration = (end - case['start']) / case['speed']
    fps = 12
    name = f"{case['number']:02d}_{case['name']}.mp4"
    target = OUTPUT / name
    if target.exists():
        raise FileExistsError(target)
    writer = VideoWriter(target, fps=fps)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 18)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 15)
    title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
    drone = np.array([r['privileged']['drone_position_enu_m'][:2] for r in rows])
    boat = np.array([r['privileged']['pad_position_enu_m'][:2] for r in rows])
    low = np.minimum(drone.min(0), boat.min(0))
    high = np.maximum(drone.max(0), boat.max(0))
    centre = (high + low) / 2
    span = max(9., float(np.max(high - low)) * 1.25)

    def point(p):
        q = (np.asarray(p) - centre) / span
        return tuple(np.rint([955 + q[0] * 280, 244 - q[1] * 280]).astype(int))

    preview_done = False
    started = time.monotonic()
    with h5py.File(directory / 'observations.h5', 'r') as data:
        try:
            for n in range(math.ceil(duration * fps)):
                t = min(end, case['start'] + n * case['speed'] / fps)
                i = int(np.argmin(abs(times - t)))
                row = rows[i]
                frame_index = row['frame_index']
                # One essential alignment check: never pair RGB with another step.
                saved_row = json.loads(data['steps'][frame_index])
                assert saved_row['frame_index'] == frame_index
                assert saved_row['time_s'] == row['time_s']
                rgb = data['rgb'][frame_index]
                image = Image.new('RGB', (1280, 720), '#0e1622')
                image.paste(Image.fromarray(rgb), (0, 80))
                draw = ImageDraw.Draw(image)
                draw.text((16, 9), f"EXISTING EXPERT AUDIT {case['number']}/4 | {case['title']}", font=title, fill='white')
                draw.text((16, 48), 'SAVED RGB 640 x 360 | camera frame recorded for learning', font=small, fill='#9ed7ff')
                draw.text((667, 48), 'SIMULATOR TRUTH MAP - AUDIT ONLY', font=small, fill='#ffd17b')
                draw.rectangle((658, 80, 1262, 439), outline='#3a4d65', width=2)
                if i > 0:
                    draw.line([point(p) for p in drone[:i+1:3]], fill='#deae4f', width=3)
                    draw.line([point(p) for p in boat[:i+1:3]], fill='#3b8d92', width=3)
                dp, bp = point(drone[i]), point(boat[i])
                draw.ellipse((dp[0]-6, dp[1]-6, dp[0]+6, dp[1]+6), fill='#ffdf7e')
                draw.ellipse((bp[0]-6, bp[1]-6, bp[0]+6, bp[1]+6), fill='#54e6db')
                obs, truth = row['observation'], row['privileged']
                heading = math.pi / 2 - obs['px4']['attitude_ned_rad'][2]
                pan, tilt = obs['gimbal_rad']
                gaze = heading + pan
                ray = (dp[0]+55*math.cos(gaze), dp[1]-55*math.sin(gaze))
                draw.line([dp, ray], fill='#d7e5ff', width=2)
                draw.text((675, 91), f'Flight t={times[i]:.2f} s | playback {case["speed"]:g}x', font=font, fill='white')
                draw.text((675, 119), f'Map width {span:.1f} m', font=small, fill='#c3cddd')
                draw.text((675, 390), 'Yellow: drone | turquoise: boat', font=small, fill='#dce8f5')
                draw.text((675, 414), 'White ray: camera heading (encoder)', font=small, fill='#dce8f5')
                visible = bool(truth['pad_visible'])
                a = row['output']['executed_action']
                movement = math.hypot(*a[:2])
                assisted = row['phase'] in ('search', 'reacquire') and not visible
                badge = 'HIDDEN-POSITION ASSISTANCE' if assisted else ('FIXED TIMER CAMERA SWEEP' if row['phase']=='search_demonstration' else 'PRIVILEGED EXPERT CONTROL')
                color = '#ffb273' if assisted else '#d2e0f0'
                draw.text((18, 456), badge, font=title, fill=color)
                visible_points = np.array(truth['pad_keypoints_px'])
                px_width = float(np.ptp(visible_points[:, 0]))
                px_height = float(np.ptp(visible_points[:, 1]))
                pixel_label = f'{px_width:.1f} x {px_height:.1f} px' if visible else 'unavailable / pad not visible'
                lines = [
                    f"Phase {row['phase']} | pad visible label: {visible} | camera tilt {math.degrees(tilt):.1f} deg",
                    f'Forward/right/down commands: {a[0]:+.2f} / {a[1]:+.2f} / {a[2]:+.2f} m/s | XY command {movement:.2f}',
                    f'Projected PAD size (truth, not boat box): {pixel_label}',
                    f"Recorded student radio: ABSENT | expert: radio-assisted search + simulator pose",
                    f"{case['watch']}",
                    'Pad visibility is not whole-boat visibility. Map and pixel labels use privileged truth.',
                    'Historical expert demonstration; NOT an ML-policy result or the proposed new teacher.',
                ]
                for k, line in enumerate(lines):
                    draw.text((18, 500+k*28), line, font=small if k >= 3 else font, fill='#d6e1ed')
                writer.write(np.asarray(image))
                if not preview_done and ((assisted and case['number'] in (2,4)) or (visible and case['number'] in (1,3))):
                    image.save(OUTPUT / name.replace('.mp4', '.jpg'))
                    preview_done = True
        finally:
            writer.close()
    hidden = [r for r in rows if r['phase'] in ('search','reacquire') and not r['privileged']['pad_visible'] and math.hypot(*r['output']['executed_action'][:2]) > .2]
    result = dict(case, file=name, source=str(directory), end=end, video_seconds=duration,
                  original_outcome=json.loads((directory/'summary.json').read_text())['outcome'],
                  source_trace_sha256=hashlib.sha256((directory/'steps.jsonl').read_bytes()).hexdigest(),
                  actual_saved_rgb=True, physics_rerun=False, new_training=False,
                  hidden_pad_xy_command_frames=len(hidden),
                  timed_search_pad_visible_frames=sum(r['phase']=='search_demonstration' and r['privileged']['pad_visible'] for r in rows),
                  sha256=hashlib.sha256(target.read_bytes()).hexdigest(), bytes=target.stat().st_size,
                  wall_seconds=time.monotonic()-started)
    dump(OUTPUT/name.replace('.mp4', '.json'), result)
    print('REVIEW_READY', json.dumps(result), flush=True)
    return result


def main():
    results = [render(case) for case in CASES]
    dump(OUTPUT/'manifest.json', dict(videos=results, scope='read-only historical teacher audit, not proposed new expert',
         originals_untouched=True, bulk_collection_started=False, training_started=False))
    with tarfile.open(OUTPUT/'expert_audit_videos.tar', 'w') as archive:
        for p in OUTPUT.iterdir():
            if p.suffix in ('.mp4','.jpg','.json'):
                archive.add(p, arcname=p.name)
    print('COMPLETE', json.dumps(dict(bytes=(OUTPUT/'expert_audit_videos.tar').stat().st_size,
          sha256=hashlib.sha256((OUTPUT/'expert_audit_videos.tar').read_bytes()).hexdigest())), flush=True)


if __name__ == '__main__':
    main()
