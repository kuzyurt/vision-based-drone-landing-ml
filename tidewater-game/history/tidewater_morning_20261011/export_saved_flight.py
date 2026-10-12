"""Render one existing recorded flight; never run or retrain a controller."""
from landing_training.morning_flight import *
import struct,urllib.request

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,required=True);p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True);p.add_argument('--day',type=float,required=True);p.add_argument('--name',required=True);a=p.parse_args()
 def rpc(endpoint,payload=None):
  req=urllib.request.Request(f'http://127.0.0.1:{a.port}/'+endpoint,data=json.dumps(payload or {}).encode(),headers={'Content-Type':'application/json'})
  return urllib.request.urlopen(req,timeout=300).read()
 bridge.rpc=rpc
 summary=json.loads((OUTPUT/'flight/summary.json').read_text());count=summary['records']
 e=bridge.TidewaterEnvironment(scenario());r=bridge.TidewaterRenderer(e,overview=False,time_of_day=a.day)
 video=OUTPUT/(a.name+'.mp4');assert not video.exists()
 log=(OUTPUT/(a.name+'.ffmpeg.log')).open('x')
 cmd=['ffmpeg','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{a.width}x{a.height}','-r','25','-i','pipe:0','-an','-c:v','libx264','-preset','slow','-crf','15','-pix_fmt','yuv420p','-threads','3','-movflags','+faststart',str(video)]
 encoder=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log);began=time.monotonic();first_ready=None
 try:
  for i in range(count):
   state=np.load(OUTPUT/'flight/states'/f'{i:05d}.npz');e.data.time=float(state['time']);e.data.qpos[:]=state['qpos'];e.data.qvel[:]=state['qvel'];e.data.mocap_pos[:]=state['mocap_pos'];e.data.mocap_quat[:]=state['mocap_quat'];e.wind.velocity[:]=state['wind'];e.boat.navigation.progress=float(state['progress']);mujoco.mj_forward(e.model,e.data)
   packet=r.packet();view=frame_camera(e);view.update(width=a.width,height=a.height);packet['views']=[view];packet['wind_speed']=7.;packet['time_of_day']=a.day
   for warm in range(16 if i==0 else 1):raw=rpc('render',packet)
   n=struct.unpack('<I',raw[:4])[0];meta=json.loads(raw[4:4+n]);pixels=np.frombuffer(raw[4+n:],dtype='uint8').reshape(a.height,a.width,4)
   rgb=(pixels[:,:,:3] if meta['format']=='rgba8unorm' else pixels[:,:,[2,1,0]]).copy();encoder.stdin.write(rgb.tobytes())
   if i==0:first_ready=time.monotonic();Image.fromarray(rgb).save(OUTPUT/(a.name+'_first.jpg'),quality=98)
   if i in [count//2,count-1]:Image.fromarray(rgb).save(OUTPUT/(a.name+f'_frame_{i:05d}.jpg'),quality=98)
   if (i+1)%25==0 or i==count-1:
    elapsed=time.monotonic()-began;fps=(i/max(.001,time.monotonic()-first_ready)) if i else 0.
    progress=dict(name=a.name,frames=i+1,total=count,elapsed_seconds=elapsed,steady_render_fps=fps,remaining_seconds=(count-i-1)/fps if fps else None,resolution=[a.width,a.height],time_of_day=a.day)
    (OUTPUT/(a.name+'_progress.json')).write_text(json.dumps(progress));print('EXPORT_PROGRESS',json.dumps(progress),flush=True)
 finally:
  encoder.stdin.close();code=encoder.wait();log.close()
 if code:raise RuntimeError('Video encoder failed')
 receipt=dict(name=a.name,frames=count,fps=25,seconds=count/25,resolution=[a.width,a.height],native_render=True,render_scale=1,encoding='H264 slow CRF15 yuv420p',bytes=video.stat().st_size,sha256=file_hash(video),render_wall_seconds=time.monotonic()-began,flight_outcome=summary['outcome'],policy_bundle_sha256=summary['policy_bundle_sha256'],radio_enabled=True,time_of_day=a.day,cloud_cover=.62,sea_state='Breezy',scope='Spectator replay of the same real 07:07 hybrid-policy flight; afternoon export changes rendering only. No new policy evaluation.')
 (OUTPUT/(a.name+'_receipt.json')).write_text(json.dumps(receipt,indent=2));print('EXPORT_COMPLETE',json.dumps(receipt),flush=True)

if __name__=='__main__':main()
