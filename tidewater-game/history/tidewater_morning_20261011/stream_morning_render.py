"""Isolated native-4K replay of committed frames while flight recording continues."""
from landing_training.morning_flight import *
import urllib.request,struct
PORT=5191

def isolated_rpc(endpoint,payload=None):
 req=urllib.request.Request(f'http://127.0.0.1:{PORT}/'+endpoint,data=json.dumps(payload or {}).encode(),headers={'Content-Type':'application/json'})
 return urllib.request.urlopen(req,timeout=300).read()

def committed_frames():
 file=OUTPUT/'flight/steps.jsonl'
 if not file.exists():return 0
 with file.open('rb') as h:h.seek(max(0,file.stat().st_size-70000));lines=h.read().splitlines()
 for line in reversed(lines):
  try:return int(json.loads(line)['frame_index'])+1
  except (ValueError,KeyError):pass
 return 0

def main():
 bridge.rpc=isolated_rpc
 for _ in range(240):
  try:
   if json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/status').read())['ready']:break
  except OSError:pass
  time.sleep(1)
 else:raise RuntimeError('Isolated 4K renderer not ready')
 e=bridge.TidewaterEnvironment(scenario());r=bridge.TidewaterRenderer(e,overview=False,time_of_day=7+7/60)
 video=OUTPUT/'policy_tidewater_breezy_0707_4k.mp4';assert not video.exists()
 log=(OUTPUT/'4k_ffmpeg_stream.log').open('x')
 p=subprocess.Popen(['ffmpeg','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','3840x2160','-r','25','-i','pipe:0','-an','-c:v','libx264','-preset','slow','-crf','15','-pix_fmt','yuv420p','-threads','4','-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stderr=log)
 started=time.monotonic();errors=[];i=0;summary_file=OUTPUT/'flight/summary.json'
 try:
  while True:
   count=committed_frames()
   if summary_file.exists():
    summary=json.loads(summary_file.read_text());assert summary['failure'] is None,summary['failure']
    if i>=summary['records']:break
   if i>=count:time.sleep(.25);continue
   file=OUTPUT/'flight/states'/f'{i:05d}.npz';assert file.exists(),file
   state=np.load(file);e.data.time=float(state['time']);e.data.qpos[:]=state['qpos'];e.data.qvel[:]=state['qvel'];e.data.mocap_pos[:]=state['mocap_pos'];e.data.mocap_quat[:]=state['mocap_quat'];e.wind.velocity[:]=state['wind'];e.boat.navigation.progress=float(state['progress']);mujoco.mj_forward(e.model,e.data)
   packet=r.packet();packet['views']=[frame_camera(e)];packet['wind_speed']=7.
   for warm in range(16 if i==0 else 1):raw=bridge.rpc('render',packet)
   n=struct.unpack('<I',raw[:4])[0];meta=json.loads(raw[4:4+n]);errors+=[x for x in meta['errors'] if x!='Failed to load resource: the server responded with a status of 404 (Not Found)']
   assert not meta['failedResources'],meta['failedResources']
   pixels=np.frombuffer(raw[4+n:],dtype='uint8').reshape(2160,3840,4);assert meta['format']=='rgba8unorm'
   assert meta['views']['external']['width']==3840 and meta['views']['external']['height']==2160
   p.stdin.write(pixels[:,:,:3].copy().tobytes())
   if i in [0,500,1000,1500,2000]:Image.fromarray(pixels[:,:,:3]).save(OUTPUT/f'4k_frame_{i:05d}.jpg',quality=98)
   i+=1
   if i%25==0:
    progress=dict(frame=i,committed_flight_frames=count,video_seconds=i/25,wall_seconds=time.monotonic()-started)
    (OUTPUT/'render_progress.json').write_text(json.dumps(progress));print('NATIVE_4K_STREAM',json.dumps(progress),flush=True)
  Image.fromarray(pixels[:,:,:3]).save(OUTPUT/'4k_terminal.jpg',quality=98)
 finally:
  p.stdin.close();code=p.wait();log.close()
 assert code==0 and not errors,(code,errors)
 read_bundle(BUNDLE)
 receipt=dict(frames=i,fps=25,seconds=i/25,resolution=[3840,2160],native_render=True,render_scale=1,encoding='H264 slow CRF15 yuv420p',bytes=video.stat().st_size,sha256=file_hash(video),render_wall_seconds=time.monotonic()-started,policy_bundle_sha256=file_hash(BUNDLE),flight_outcome=summary['outcome'],radio_enabled=True,quality=meta['views']['external']['quality'],provenance='Actual committed flight states, separate replay renderer on collector port 5191; no flight actions changed.')
 (OUTPUT/'video_receipt.json').write_text(json.dumps(receipt,indent=2));print('VIDEO_COMPLETE',json.dumps(receipt),flush=True)

if __name__=='__main__':main()
