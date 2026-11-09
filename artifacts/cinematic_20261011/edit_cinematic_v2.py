"""Stage-matched cuts from completed, physically landed policy flights."""
import json,subprocess,concurrent.futures,argparse,math
from pathlib import Path

def probe(path):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)]))

def main():
 p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();out=Path(a.output).resolve()
 plan=json.loads((out/'plan.json').read_text());report=json.loads((out/'report.json').read_text())
 assert report['status']=='completed'
 assert len(report['episodes'])==10 and all(e['outcome']=='landed' for e in report['episodes']),report
 edit=out/'edit_v2';edit.mkdir(exist_ok=False)
 sources={};cuts=[]
 for j in plan['jobs']:
  directory=Path(j['directory']);rows=[json.loads(x) for x in (directory/'steps.jsonl').read_text().splitlines()]
  info=probe(directory/'review.mp4');stream=next(s for s in info['streams'] if s['codec_type']=='video')
  n=int(stream['nb_read_frames']);assert n==len(rows),(j['id'],n,len(rows))
  assert stream['width']==1280 and stream['height']==720 and stream['r_frame_rate']=='25/1'
  sources[j['id']]=(j,rows,n)
 for stage,target in [('approach',1.45),('descent',1.1),('near_deck',.38),('landed',None)]:
  for j in plan['jobs'][::2]+plan['jobs'][1::2]:
   job,rows,n=sources[j['id']]
   if target is None:start=n-20
   else:
    candidates=[]
    for i,r in enumerate(rows[:-20]):
     v=r['privileged'];c=v['vertical_clearance_m'];d=v['drone_position_enu_m'];b=v['pad_position_enu_m']
     horizontal=math.hypot(d[0]-b[0],d[1]-b[1])
     # Use measured flight state only for editing. It never enters the actor.
     if c<=target and c>=max(0,target-.35) and horizontal<.38:candidates.append(i)
    if not candidates:raise RuntimeError(f'No stage-aligned frame for {j["id"]}/{stage}')
    start=candidates[0]
   assert 0<=start<=n-20
   c=dict(index=len(cuts),source_id=j['id'],map=j['scenario']['kind'],profile=j['profile'],stage=stage,
          source_start_frame=start,source_end_frame_exclusive=start+20,source_start_s=start/25,duration_s=.8,
          actual_start_clearance_m=rows[start]['privileged']['vertical_clearance_m'],scenario=j['scenario'])
   cuts.append(c)
 assert len(cuts)==40 and all(cuts[i]['map']!=cuts[i-1]['map'] for i in range(1,len(cuts)))
 (edit/'edit_decisions.json').write_text(json.dumps(dict(fps=25,cut_duration_s=.8,total_duration_s=32,camera=plan['camera'],cuts=cuts),indent=2))
 def encode(c):
  source=Path(sources[c['source_id']][0]['directory'])/'review.mp4';dest=edit/f'clip_{c["index"]:03d}.mp4'
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-ss',str(c['source_start_s']),'-i',str(source),'-frames:v','20','-an','-c:v','libx264','-preset','fast','-crf','18','-threads','1','-pix_fmt','yuv420p','-vf','setsar=1','-r','25',str(dest)],check=True)
  assert int(probe(dest)['streams'][0]['nb_read_frames'])==20
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(encode,cuts))
 concat=edit/'concat.txt';concat.write_text(''.join(f"file 'clip_{i:03d}.mp4'\n" for i in range(len(cuts))))
 dest=out/'policy_five_maps_cinematic_v2.mp4'
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(dest)],check=True)
 info=probe(dest);assert int(info['streams'][0]['nb_read_frames'])==800 and abs(float(info['format']['duration'])-32)<.01
 (edit/'ffprobe.json').write_text(json.dumps(info,indent=2))
 from PIL import Image,ImageDraw,ImageFont
 sheet=Image.new('RGB',(1280,1440))
 for row,stage in enumerate(['approach','descent','near_deck','landed']):
  for col,kind in enumerate(['island','beach','city','gravel','rock']):
   c=next(c for c in cuts if c['stage']==stage and c['map']==kind)
   imagepath=edit/f'qa_{stage}_{kind}.png';source=Path(sources[c['source_id']][0]['directory'])/'review.mp4'
   subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-ss',str((c['source_start_frame']+10)/25),'-i',str(source),'-frames:v','1',str(imagepath)],check=True)
   im=Image.open(imagepath).convert('RGB');im=im.resize((256,144));ImageDraw.Draw(im).text((3,3),kind+' '+stage,fill='white');sheet.paste(im,(col*256,row*144))
 sheet=sheet.crop((0,0,1280,576));sheet.save(out/'montage_qa_v2.jpg',quality=94)
 print(json.dumps(dict(video=str(dest),bytes=dest.stat().st_size,duration_s=32,cuts=40)),flush=True)
if __name__=='__main__':main()

