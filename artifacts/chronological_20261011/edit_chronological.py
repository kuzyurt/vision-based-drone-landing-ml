"""Match real drone clearance at every cut; export a README-sized GIF."""
import argparse,concurrent.futures,datetime,json,math,os,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

def command(args):
 subprocess.run(args,check=True)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('output');args=parser.parse_args()
 source=Path(args.source).resolve();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
 plan=json.loads((source/'plan.json').read_text());report=json.loads((source/'report.json').read_text())
 assert report['status']=='completed' and len(report['episodes'])==10 and all(e['outcome']=='landed' for e in report['episodes'])
 clips=out/'clips';clips.mkdir();shots=[];data={}
 for j in plan['jobs']:
  d=Path(j['directory']);rows=[json.loads(x) for x in (d/'steps.jsonl').read_text().splitlines()]
  heights=np.array([r['privileged']['vertical_clearance_m'] for r in rows])
  xy=np.array([math.dist(r['privileged']['drone_position_enu_m'][:2],r['privileged']['pad_position_enu_m'][:2]) for r in rows])
  data[j['id']]=(j,rows,heights,xy)
 # Four complete map cycles, alternating the two real weather takes.
 order=plan['jobs'][::2]+plan['jobs'][1::2]
 boundaries=np.linspace(1.45,.02,21)
 for k in range(20):
  j,rows,h,xy=data[order[k%10]['id']];hi=float(boundaries[k]);lo=float(boundaries[k+1])
  # Find a consecutive source window whose endpoints match the common
  # height timeline. Source frames and their original motion are preserved.
  candidates=[]
  starts=np.flatnonzero((np.abs(h-hi)<.025)&(xy<.25))
  for a in starts:
   for b in range(int(a)+2,min(int(a)+80,len(rows)-26)):
    if abs(h[b]-lo)>.025 or np.max(xy[a:b+1])>.25:continue
    expected=np.linspace(hi,lo,b-a+1)
    cost=30*((h[a]-hi)**2+(h[b]-lo)**2)+float(np.mean((h[a:b+1]-expected)**2))
    # Prefer visually steady descents when more than one crossing exists.
    cost+=float(np.sum(np.maximum(np.diff(h[a:b+1]),0)**2))
    candidates.append((cost,int(a),b))
  assert candidates,(j['id'],hi,lo)
  _,a,b=min(candidates)
  shots.append(dict(index=k,source_id=j['id'],map=j['scenario']['kind'],profile=j['profile'],stage='continuous_descent',
   start_frame=a,end_frame_exclusive=b+1,source_frames=b-a+1,target_start_m=hi,target_end_m=lo,
   actual_start_m=float(h[a]),actual_end_m=float(h[b]),duration_s=1.,playback_rate=(b-a+1)/25))
 # A final cycle shows actual contact confirmation and native disarming.
 for j in plan['jobs'][::2]:
  j,rows,h,xy=data[j['id']];a=len(rows)-25;b=len(rows)-1
  assert rows[-1]['terminal'] and rows[-1]['outcome']=='landed'
  shots.append(dict(index=len(shots),source_id=j['id'],map=j['scenario']['kind'],profile=j['profile'],stage='landed',
   start_frame=a,end_frame_exclusive=b+1,source_frames=25,actual_start_m=float(h[a]),actual_end_m=float(h[b]),duration_s=1.,playback_rate=1.))
 jumps=[shots[k]['actual_start_m']-shots[k-1]['actual_end_m'] for k in range(1,len(shots))]
 assert max(jumps)<.025 and max(abs(x) for x in jumps)<.04,jumps
 assert all(shots[k]['map']!=shots[k-1]['map'] for k in range(1,len(shots)))
 last_source_frame={}
 for s in shots:
  assert s['start_frame']>=last_source_frame.get(s['source_id'],-1)
  last_source_frame[s['source_id']]=s['end_frame_exclusive']-1
 decisions=dict(duration_s=25,cut_duration_s=1.,camera=plan['camera'],height_timeline_m=boundaries.tolist(),
  max_upward_cut_jump_m=max(0,max(jumps)),max_absolute_cut_jump_m=max(abs(x) for x in jumps),
  note='Real consecutive flight frames slowed for a continuous height progression; no policy changes, rendered interpolation or synthetic drone motion.',shots=shots)
 (out/'edit_decisions.json').write_text(json.dumps(decisions,indent=2))
 def encode(s):
  d=Path(data[s['source_id']][0]['directory']);n=s['source_frames'];dest=clips/f'clip_{s["index"]:03d}.mp4'
  # Assign original frames evenly across one second. fps duplicates frames;
  # it does not synthesize or interpolate the drone or the environment.
  filters=f'trim=end_frame={n},setpts=N/({n}*TB),fps=25,tpad=stop_mode=clone:stop_duration=0.2,trim=duration=1,setpts=PTS-STARTPTS,setsar=1'
  command(['ffmpeg','-v','error','-nostdin','-ss',str(s['start_frame']/25),'-i',str(d/'review.mp4'),'-vf',filters,'-frames:v','25','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','1',str(dest)])
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(encode,shots))
 (clips/'concat.txt').write_text(''.join(f"file 'clip_{s['index']:03d}.mp4'\n" for s in shots))
 movie=out/'policy_landing_chronological.mp4'
 command(['ffmpeg','-v','error','-nostdin','-f','concat','-safe','0','-i',str(clips/'concat.txt'),'-c','copy','-movflags','+faststart',str(movie)])
 # A global palette keeps colors stable across cuts and the loop.
 gif=out/'drone-policy-landing.gif';palette=out/'palette.png'
 command(['ffmpeg','-v','error','-nostdin','-i',str(movie),'-vf','fps=10,scale=800:-1:flags=lanczos,palettegen=max_colors=192:stats_mode=diff','-frames:v','1','-threads','1',str(palette)])
 command(['ffmpeg','-v','error','-nostdin','-i',str(movie),'-i',str(palette),'-filter_complex','[0:v]fps=10,scale=800:-1:flags=lanczos[v];[v][1:v]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle','-loop','0','-threads','1',str(gif)])
 # Inspect the actual GIF, including both sides of every scene change.
 with Image.open(gif) as im:
  durations=[];samples=[]
  for k in range(im.n_frames):
   im.seek(k);durations.append(im.info['duration'])
   if k%10==5:samples.append(im.convert('RGB').resize((320,180)))
  assert im.size==(800,450) and im.n_frames==250 and sum(durations)==25000
  assert all(d==100 for d in durations) and im.info.get('loop')==0
 sheet=Image.new('RGB',(1600,900))
 for k,im in enumerate(samples):
  s=shots[k];ImageDraw.Draw(im).text((5,5),f"{k+1:02d} {s['map']} {s['actual_start_m']:.2f}m",fill='white');sheet.paste(im,((k%5)*320,(k//5)*180))
 sheet.save(out/'chronology_qa.jpg',quality=94)
 # Decode the complete video before considering the artifacts finished.
 command(['ffmpeg','-v','error','-i',str(movie),'-f','null','-'])
 from landing_training.gate import file_hash,source_fingerprint
 from landing_training.marker_bundle import read_bundle
 read_bundle('landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json')
 originals=json.loads(Path('landing_training/outputs/control_iteration_20261010T220632Z/preservation.json').read_text())
 assert all(file_hash(p)==h for p,h in originals.items())
 for result in report['episodes']:
  assert file_hash(Path(data[result['id']][0]['directory'])/'review.mp4')==result['video_sha256']
 assert source_fingerprint(runtime_only=True)==plan['base_runtime_sha256']
 audit=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),originals_preserved=True,frozen_policy_verified=True,
  policy_bundle_sha256=plan['policy_bundle_sha256'],base_runtime_sha256=plan['base_runtime_sha256'],
  all_source_flights_landed=True,shots=25,maps=['island','beach','city','gravel','rock'],
  max_upward_cut_jump_m=decisions['max_upward_cut_jump_m'],max_absolute_cut_jump_m=decisions['max_absolute_cut_jump_m'],
  video=dict(path=str(movie),sha256=file_hash(movie),bytes=movie.stat().st_size,duration_s=25),
  gif=dict(path=str(gif),sha256=file_hash(gif),bytes=gif.stat().st_size,duration_s=25,width=800,height=450,frames=250,loop=0))
 (out/'completion_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit),flush=True)

if __name__=='__main__':main()
