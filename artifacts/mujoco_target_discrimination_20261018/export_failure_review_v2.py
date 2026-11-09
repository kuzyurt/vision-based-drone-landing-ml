"""Short actual-camera review clips, full failure at declared accelerated speed."""
from pathlib import Path
import hashlib,json,math,subprocess,time
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'failure_review_20261019_v2'
def main():
    OUT.mkdir(exist_ok=False);receipts=[]
    cases=[('candidate_'+n,'frozen_task_evaluation_v3/'+n,'CANDIDATE ALONE - no expert takeover',None,None)for n in ['fresh_boat_03_1','fresh_boat_00_1','fresh_boat_01_0','fresh_boat_01_1']]

    for name,path,title,start,end in cases:
        ep=ROOT/path;rows=[json.loads(l)for l in(ep/'steps.jsonl').open()]
        if start is not None:rows=[r for r in rows if start<=r['task_time_s']<=end]
        assert rows;times=np.array([r['task_time_s']for r in rows]);duration=float(times[-1]-times[0]);speed=max(1.,duration/26.);fps=15;frames=math.ceil(duration/speed*fps)
        dest=OUT/(name+'.mp4');cmd=['ffmpeg','-nostdin','-n','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','640x440','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
        begin=time.monotonic();summary=json.loads((ep/'summary.json').read_text());origin=np.array(rows[0]['observation']['px4']['position_enu_m'][:2])
        with h5py.File(ep/'observations.h5','r')as h,(OUT/(name+'_encode.log')).open('x')as log:
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
            for n in range(frames):
                t=times[0]+min(duration,n/fps*speed);i=int(np.argmin(np.abs(times-t)));row=rows[i];d=row['output'].get('learner_diagnostics')or{};own=row['observation']['px4']
                im=Image.new('RGB',(640,440),(15,21,27));im.paste(Image.fromarray(np.asarray(h['rgb'][row['frame_index']])),(0,0));draw=ImageDraw.Draw(im)
                owner='candidate alone'
                draw.text((8,366),title,fill='white');draw.text((8,382),f"ACTUAL delivered camera | {speed:.2f}x | task {row['task_time_s']:.2f}s | owner: {owner}",fill='white')
                move=float(np.linalg.norm(np.array(own['position_enu_m'][:2])-origin))
                draw.text((8,398),f"{d.get('control_phase')} | height {own['position_enu_m'][2]:.2f}m | XY displacement {move:.2f}m",fill='white')
                draw.text((8,414),f"Full-flight outcome: {summary['outcome']} | historical recording; no new simulation",fill='#bdcbd6')
                proc.stdin.write(np.asarray(im).tobytes())
            proc.stdin.close();assert proc.wait(timeout=60)==0
        receipts.append(dict(name=name,path=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size,
            video_s=frames/fps,source_task_start_s=float(times[0]),source_task_end_s=float(times[-1]),playback_speed=speed,
            outcome=summary['outcome'],actual_camera=True,new_simulation=False,source_episode=path,wall_s=time.monotonic()-begin))
        (OUT/'receipts.json').write_text(json.dumps(receipts,indent=2));print(json.dumps(receipts[-1]),flush=True)
if __name__=='__main__':main()

