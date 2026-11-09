"""Short normal-speed ACTUAL delivered camera; no new simulator rendering."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--episode',required=True);p.add_argument('--name',required=True);p.add_argument('--start',type=float,required=True);p.add_argument('--end',type=float,required=True);a=p.parse_args()
    assert 0<a.end-a.start<=22.;ep=(ROOT/a.episode).resolve();assert ep.is_relative_to(ROOT)
    dest=ROOT/(a.name+'.mp4');assert not dest.exists();begin=time.monotonic()
    rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];rows=[r for r in rows if a.start<=r['task_time_s']<=a.end];assert len(rows)>2
    times=np.array([r['task_time_s']for r in rows]);assert np.allclose(np.diff(times),.04,atol=1e-6),'Do not silently change playback timing'
    summary=json.loads((ep/'summary.json').read_text());command=['ffmpeg','-nostdin','-n','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','640x420','-r','25','-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
    with(ROOT/(a.name+'_encode.log')).open('x')as log,h5py.File(ep/'observations.h5','r')as h:
        proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        for row in rows:
            im=Image.new('RGB',(640,420),(15,20,25));im.paste(Image.fromarray(np.asarray(h['rgb'][row['frame_index']])),(0,0));draw=ImageDraw.Draw(im)
            d=row['output'].get('learner_diagnostics')or{};own=row['observation']['px4']
            draw.text((8,366),f"Actual camera | 1x simulation time | no radio | task {row['task_time_s']:.2f}s",fill='white')
            draw.text((8,383),f"{d.get('control_phase')} | own height {own['position_enu_m'][2]:.2f}m | metric {bool(d.get('metric_valid'))}",fill='white')
            draw.text((8,400),f"Full-flight outcome: {summary['outcome']} | experimental evidence, not qualification",fill='#bccbd7')
            proc.stdin.write(np.asarray(im).tobytes())
        proc.stdin.close();assert proc.wait(timeout=60)==0
    receipt=dict(path=str(dest),bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
        frames=len(rows),fps=25,video_seconds=len(rows)/25.,task_start_s=float(times[0]),task_end_s=float(times[-1]),
        actual_delivered_camera=True,reconstructed_camera=False,new_render=False,normal_simulation_speed=True,
        full_flight_outcome=summary['outcome'],wall_s=time.monotonic()-begin)
    (ROOT/(a.name+'_receipt.json')).write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':main()
