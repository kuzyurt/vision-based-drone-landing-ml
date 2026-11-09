"""Pack selected exact recorded onboard RGB frames for offline review only."""
from pathlib import Path
import json
import h5py
from PIL import Image,ImageDraw

ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020/semantic_pilots')
OUT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z/approved_curriculum_20261020/search_geometry_sheets_v2');OUT.mkdir(exist_ok=False)

def main():
  for name in ('search_near','search_mid','search_far','search_distractors'):
    case=ROOT/name
    with h5py.File(case/'observations.h5','r') as h:
      rows=[json.loads(b.decode() if isinstance(b,bytes) else b) for b in h['steps']]
      wanted=[0,125,250,375,500,625,len(rows)-2]
      frames=[]
      for idx in sorted(set(i for i in wanted if 0<=i<len(rows))):
        r=rows[idx];im=Image.fromarray(h['rgb'][idx]); im.thumbnail((320,180))
        canvas=Image.new('RGB',(320,205),'white');canvas.paste(im,(0,25));d=ImageDraw.Draw(canvas)
        dg=r['output'].get('learner_diagnostics',{});tr=dg.get('expert_visual_tracks') or []
        label=f"{name} frame={idx} t={r.get('task_time_s',0):.1f}s phase={dg.get('control_phase','?')}"
        label+=f" candidates={len(tr)} down={r['output']['executed_action'][2]:.2f}"
        d.text((3,3),label,fill='black')
        frames.append(canvas)
    sheet=Image.new('RGB',(320*2,205*((len(frames)+1)//2)),'#444')
    for j,im in enumerate(frames):sheet.paste(im,((j%2)*320,(j//2)*205))
    sheet.save(OUT/(name+'.jpg'),quality=82,optimize=True)
  print(json.dumps({p.name:{'bytes':p.stat().st_size} for p in OUT.glob('*.jpg')},indent=2))

if __name__=='__main__':main()
