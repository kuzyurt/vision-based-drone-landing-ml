"""Short review from ACTUAL recorded cameras; no reconstruction or new render."""
from pathlib import Path
import argparse,hashlib,json,math,subprocess,time
import h5py,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--episode',required=True);p.add_argument('--name',required=True)
    p.add_argument('--max-seconds',type=float,default=30.);a=p.parse_args();assert 5<=a.max_seconds<=40
    directory=(ROOT/a.episode).resolve();assert directory.is_relative_to(ROOT)
    dest=ROOT/(a.name+'.mp4');assert not dest.exists();begin=time.monotonic()
    rows=[json.loads(line)for line in(directory/'steps.jsonl').open()]
    rows=[r for r in rows if 'observation'in r];assert rows
    start=float(rows[0]['observation']['image_capture_time_s']);end=float(rows[-1]['observation']['image_capture_time_s'])
    duration=end-start;assert duration>0
    speed=max(1.,duration/a.max_seconds);fps=15;frame_count=max(2,int(math.ceil(duration/speed*fps)))
    captures=np.array([r['observation']['image_capture_time_s']for r in rows]);assert np.all(np.diff(captures)>=0)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    title=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',28)
    with h5py.File(directory/'observations.h5','r')as onboard,h5py.File(directory/'actual_overview.h5','r')as overview:
        overview_times=np.asarray(overview['capture_s']);assert len(overview_times)>0
        command=['ffmpeg','-nostdin','-n','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(fps),'-i','pipe:0',
            '-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
        with(ROOT/(a.name+'_encode.log')).open('x')as log:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
            for n in range(frame_count):
                at=start+min(duration,n/fps*speed);idx=int(np.argmin(np.abs(captures-at)));row=rows[idx]
                capture=float(row['observation']['image_capture_time_s']);oi=int(np.argmin(np.abs(overview_times-capture)))
                assert abs(overview_times[oi]-capture)<=.25,'No synchronous actual overview; do not fabricate'
                rgb=np.asarray(onboard['rgb'][row['frame_index']]);external=np.asarray(overview['rgb'][oi])
                im=Image.new('RGB',(1280,720),(14,21,29));draw=ImageDraw.Draw(im)
                draw.text((24,20),'OBSERVABLE EXPERT — REVIEW PREVIEW',font=title,fill='white')
                draw.text((24,63),f'No radio | actual MuJoCo cameras | {speed:.2f}x playback | not a learner success',font=font,fill='#becbd4')
                draw.text((12,116),'RECORDED OVERVIEW (5 Hz)',font=small,fill='#a8c4d6')
                draw.text((652,116),'ACTUAL IMAGE DELIVERED TO CONTROLLER (640 x 360)',font=small,fill='#a8c4d6')
                im.paste(Image.fromarray(external).resize((640,360),Image.Resampling.LANCZOS),(0,148));im.paste(Image.fromarray(rgb),(640,148))
                draw=ImageDraw.Draw(im);diag=row['output'].get('learner_diagnostics')or{};intent=diag.get('expert_intent',diag.get('expert_shadow_intent',{}))
                phase=intent.get('phase',diag.get('control_phase','unknown'));owner=diag.get('dagger',{}).get('ownership',{}).get('owner','expert')
                pos=row['observation']['px4'].get('position_enu_m',[0,0,math.nan]);clearance=row.get('privileged',{}).get('clearance_m')
                draw.text((24,534),f'Task {row["task_time_s"]:.1f}s   Control: {owner}   Phase: {phase}',font=font,fill='white')
                draw.text((24,568),f'Own altitude {pos[2]:.2f}m ENU | image age {row["observation"]["image_age_s"]:.3f}s',font=font,fill='#becbd4')
                if clearance is not None:draw.text((24,601),f'Simulation clearance {clearance:.2f}m — review/scoring only, not expert input',font=small,fill='#becbd4')
                draw.text((24,654),'Check: scan/inspect choices, wrong-object rejection, camera aim, descent and recovery.',font=small,fill='#a8c4d6')
                process.stdin.write(np.asarray(im).tobytes())
            process.stdin.close();code=process.wait(timeout=60);assert code==0,'Inspect preserved encoder log'
    report=dict(source_episode=str(directory),video=str(dest),video_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
        bytes=dest.stat().st_size,actual_cameras=True,reconstructed_camera=False,new_3d_render=False,
        fps=fps,playback_speed=speed,video_duration_s=frame_count/fps,source_duration_s=duration,
        overview_max_timestamp_error_s=.25,learner_success=False,training_approval=False,wall_s=time.monotonic()-begin)
    (ROOT/(a.name+'_video_receipt.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':main()
