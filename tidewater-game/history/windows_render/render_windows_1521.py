import gzip,json,struct,time,subprocess,hashlib,urllib.request,urllib.error
from pathlib import Path
import numpy as np
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'policy_tidewater_1521_1080p_windows_4x.mp4'
PKTS=ROOT/'packets.jsonl.gz'
SERVER='http://127.0.0.1:5192/'
def rpc(path,payload=None,timeout=300):
 data=json.dumps(payload or {},separators=(',',':')).encode();req=urllib.request.Request(SERVER+path,data=data,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
if OUT.exists():raise FileExistsError(OUT)
for _ in range(240):
 try:
  status=json.loads(urllib.request.urlopen(SERVER+'status',timeout=2).read())
  if status.get('ready'):break
 except OSError:pass
 time.sleep(1)
else:raise TimeoutError('Windows renderer did not become ready')
summary=json.loads((ROOT/'saved_flight'/'summary.json').read_text(encoding='utf-8'))
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();log=(ROOT/'ffmpeg_windows.log').open('wb')
cmd=[ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','25','-i','pipe:0','-an','-c:v','libx264','-preset','ultrafast','-crf','17','-threads','8','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT)]
enc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log);beg=time.monotonic();frames=0
try:
 print('INSTALL_START',flush=True)
 installation=json.loads(rpc('install',{'url':'http://127.0.0.1:5191/landing/vehicles.json'},timeout=900))
 print('INSTALL_DONE',json.dumps(installation),flush=True)
 with gzip.open(PKTS,'rt',encoding='utf-8') as f:
  for i,line in enumerate(f):
   packet=json.loads(line);raw=rpc('render',packet)
   n=struct.unpack('<I',raw[:4])[0];meta=json.loads(raw[4:4+n]);payload=raw[4+n:]
   if meta.get('failedResources'):raise RuntimeError(f'render resources failed: {meta["failedResources"][:3]}')
   if meta['format']=='bgra8unorm':pixels=np.frombuffer(payload,dtype=np.uint8).reshape(1080,1920,4)[:,:,[2,1,0]]
   elif meta['format']=='rgba8unorm':pixels=np.frombuffer(payload,dtype=np.uint8).reshape(1080,1920,4)[:,:,:3]
   else:raise RuntimeError(f'unsupported GPU format {meta["format"]}')
   enc.stdin.write(pixels.copy().tobytes());frames+=1
   if frames%25==0 or frames==1511:
    elapsed=time.monotonic()-beg;fps=frames/max(elapsed,1e-6);remaining=max(0,1511-frames)/max(fps,1e-6)
    p={'frames':frames,'total':1511,'elapsed_seconds':round(elapsed,1),'fps':round(fps,3),'remaining_seconds':round(remaining,1),'resolution':[1920,1080],'render_scale':1,'time_of_day':'15:21','aa':'TAA4x','shadows':True,'water_reflections':True}
    (ROOT/'windows_render_progress.json').write_text(json.dumps(p,indent=2));print('WINDOWS_EXPORT_PROGRESS',json.dumps(p),flush=True)
finally:
 enc.stdin.close();code=enc.wait();log.close()
if code:raise RuntimeError(f'ffmpeg exited {code}; see {ROOT/"ffmpeg_windows.log"}')
h=hashlib.sha256();
with OUT.open('rb') as f:
 for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
receipt={'frames':frames,'fps':25,'seconds':frames/25,'resolution':[1920,1080],'render_scale':1,'time_of_day':'15:21','antialiasing':'TAA 4x','shadows':True,'water_reflections':True,'render_host':'Windows PC, NVIDIA GeForce RTX 2060','encoding':'H.264 ultrafast CRF17 yuv420p','bytes':OUT.stat().st_size,'sha256':h.hexdigest(),'render_wall_seconds':round(time.monotonic()-beg,2),'flight_outcome':summary['outcome'],'policy_bundle_sha256':summary['policy_bundle_sha256'],'source':'1511 saved poses from the actual Tidewater policy flight; no controller rerun'}
(ROOT/'windows_render_receipt.json').write_text(json.dumps(receipt,indent=2));print('WINDOWS_EXPORT_COMPLETE',json.dumps(receipt),flush=True)
