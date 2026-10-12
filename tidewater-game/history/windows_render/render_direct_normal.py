import gzip,json,time,subprocess,hashlib,urllib.request
from pathlib import Path
import imageio_ffmpeg,cv2
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'policy_tidewater_1521_1080p_windows_normal_canvas.mp4';WEBM=ROOT/'normal_canvas_capture.webm';PKTS=ROOT/'packets.jsonl.gz';BASE='http://127.0.0.1:5192/'
def rpc(path,payload=None,timeout=900):
 data=json.dumps(payload or {},separators=(',',':')).encode();req=urllib.request.Request(BASE+path,data=data,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
if OUT.exists():raise FileExistsError(OUT)
summary=json.loads((ROOT/'saved_flight'/'summary.json').read_text(encoding='utf-8'));start=time.monotonic()
print('INSTALL_START',flush=True);print('INSTALL_DONE',rpc('install',{'url':'http://127.0.0.1:5191/landing/vehicles.json'}).decode(),flush=True)
print('RECORDER',rpc('record_start').decode(),flush=True);frames=0;render_start=time.monotonic()
with gzip.open(PKTS,'rt',encoding='utf-8') as f:
 for line in f:
  rpc('render_canvas',json.loads(line));frames+=1
  if frames%50==0 or frames==1511:
   elapsed=time.monotonic()-render_start;fps=frames/max(elapsed,1e-6);remaining=max(0,1511-frames)/max(fps,1e-6);progress={'frames':frames,'total':1511,'render_elapsed_seconds':round(elapsed,1),'fps':round(fps,2),'remaining_seconds':round(remaining,1),'resolution':[1920,1080],'render_scale':1,'time_of_day':'15:21','aa':'SMAA normal','shadows':False,'water_reflections':False};(ROOT/'direct_normal_progress.json').write_text(json.dumps(progress,indent=2));print('DIRECT_NORMAL_PROGRESS',json.dumps(progress),flush=True)
print('RECORDER_STOP',rpc('record_stop',timeout=300).decode(),flush=True)
cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-i',str(WEBM),'-vf','setpts=N/(25*TB)','-r','25','-an','-c:v','libx264','-preset','ultrafast','-crf','18','-threads','8','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT)]
subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
cap=cv2.VideoCapture(str(OUT));count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));cap.release()
h=hashlib.sha256()
with OUT.open('rb') as f:
 for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
receipt={'frames_rendered':frames,'frames_encoded':count,'fps':25,'seconds':count/25,'resolution':[width,height],'render_scale':1,'time_of_day':'15:21','antialiasing':'SMAA normal','shadows':False,'water_reflections':False,'render_host':'Windows PC NVIDIA RTX 2060','encoding':'H.264 ultrafast CRF18; direct GPU canvas capture then constant 25fps encode','bytes':OUT.stat().st_size,'sha256':h.hexdigest(),'wall_seconds':round(time.monotonic()-start,2),'flight_outcome':summary['outcome'],'policy_bundle_sha256':summary['policy_bundle_sha256'],'source':'saved policy episode replay; no policy rerun'}
(ROOT/'direct_normal_receipt.json').write_text(json.dumps(receipt,indent=2));print('DIRECT_NORMAL_COMPLETE',json.dumps(receipt),flush=True)


