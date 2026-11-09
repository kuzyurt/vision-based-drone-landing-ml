"""Expert-only actual onboard clips, no new flights/renders and no learner frames."""
from pathlib import Path
import hashlib,json,math,subprocess
import h5py,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
CASES=[('expert_visible_native_v19_near_deck','late_terminal_takeover','post_takeover'),
       ('expert_visible_native_v19_near_deck_tilt','failed_expert_rescue_v19','post_takeover'),
       ('expert_visible_native_v21_tilt','failed_expert_rescue_v21','post_takeover'),
       ('task_harness_development_v1/full_home','expert_no_target_home_return','all')]
def main():
    output=ROOT/'expert_bug_review_20261019';output.mkdir(exist_ok=True);receipts=[]
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    for relative,name,selection in CASES:
        ep=ROOT/relative;allrows=[json.loads(l)for l in(ep/'steps.jsonl').open()];rows=[];learner_seen=False
        for r in allrows:
            d=r.get('output',{}).get('learner_diagnostics')or{};owner=d.get('actual_command_owner','unknown')
            if owner=='policy':learner_seen=True
            if owner=='expert'and(selection=='all'or learner_seen):rows.append(r)
        assert rows,(relative,'no expert rows after policy control')
        # A single uninterrupted expert block; never concatenate unrelated moments.
        end=next((i for i in range(1,len(rows))if rows[i]['frame_index']!=rows[i-1]['frame_index']+1),len(rows));rows=rows[:end]
        start=rows[0]['task_time_s'];duration=rows[-1]['task_time_s']-start;speed=max(1.,duration/30);fps=15
        times=np.array([r['task_time_s']for r in rows]);count=max(1,math.ceil(duration/speed*fps));dest=output/(name+'.mp4')
        assert not dest.exists();command=['ffmpeg','-nostdin','-n','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','640x450','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
        with h5py.File(ep/'observations.h5','r')as h, (output/(name+'.log')).open('x')as log:
            p=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
            for n in range(count):
                r=rows[int(np.argmin(abs(times-(start+n/fps*speed))))];d=r['output']['learner_diagnostics'];assert d['actual_command_owner']=='expert'
                im=Image.new('RGB',(640,450),(15,20,27));im.paste(Image.fromarray(np.asarray(h['rgb'][r['frame_index']])),(0,0));draw=ImageDraw.Draw(im)
                draw.text((8,365),f'EXPERT ONLY | task {r["task_time_s"]:.2f}s | {speed:.2f}x',font=font,fill='white')
                phase=(d.get('expert_intent')or{}).get('phase',d.get('control_phase','unknown'))
                draw.text((8,393),f'{phase} | REJECTED - DO NOT TRAIN',font=font,fill='#ffbb88')
                draw.text((8,420),'Actual delivered camera; expert segment only',font=font,fill='white');p.stdin.write(np.asarray(im).tobytes())
            p.stdin.close();assert p.wait(timeout=60)==0
        receipt=dict(episode=relative,video=dest.name,selection=selection,first_task_s=start,last_task_s=rows[-1]['task_time_s'],
            expert_only=True,learner_frames=0,playback_speed=speed,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),training_allowed=False)
        receipts.append(receipt);print(json.dumps(receipt),flush=True)
    (output/'manifest.json').write_text(json.dumps(receipts,indent=2))
if __name__=='__main__':main()
