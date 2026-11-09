"""Short actual-camera debug clip; VM encoding only, no training data claim."""
from pathlib import Path
import hashlib,json,subprocess
import h5py,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).parent;C=R/'search_v48/pilots/learner_struggle';O=R/'search_v48/debug_delivery';O.mkdir(exist_ok=False);rows=[json.loads(x)for x in(C/'steps.jsonl').open()];indices=[i for i,r in enumerate(rows)if 9.<=r.get('task_time_s',-1)<=29. or 55.<=r.get('task_time_s',-1)<=61.3];indices=[i for i in indices if not rows[i].get('terminal')];assert indices and len(indices)/25<=30
video=O/'actual_learner_to_expert_rescue.mp4';cmd=['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','640x416','-r','25','-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','23','-threads','1','-pix_fmt','yuv420p',str(video)];p=subprocess.Popen(cmd,stdin=subprocess.PIPE);evidence=[];previous=None
with h5py.File(C/'observations.h5','r')as h:
 for i in indices:
  r=rows[i];d=r['output'].get('learner_diagnostics')or{};t=r['task_time_s'];im=Image.new('RGB',(640,416));im.paste(Image.fromarray(h['rgb'][i]),(0,0));draw=ImageDraw.Draw(im);owner=d.get('actual_command_owner');cut=previous is not None and t-previous>.1
  draw.text((8,365),f"ACTUAL MuJoCo camera | task {t:.2f}s | owner: {owner}\n1x playback; time cut 29 -> 55s at final landing segment\nExpert handover14.68s after actual1.46m unqualified learner descent",fill='white');p.stdin.write(np.asarray(im).tobytes());evidence.append(dict(frame=i,task_s=t,owner=owner,capture_s=r['observation']['image_capture_time_s'],time_cut_before=cut));previous=t
p.stdin.close();assert p.wait(timeout=120)==0
receipt=dict(status='actual_camera_debug_clip_closed',sha256=hashlib.sha256(video.read_bytes()).hexdigest(),bytes=video.stat().st_size,frames=len(indices),playback_fps=25.,duration_s=len(indices)/25.,real_time_segments=[[9.,29.],[55.,61.2]],artificial_motion_or_rerendering=False,not_learner_only_success=True,raw_training_eligible=False,source_sha256=hashlib.sha256((C/'observations.h5').read_bytes()).hexdigest(),evidence=evidence);(O/'clip_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items()if k!='evidence'}))
