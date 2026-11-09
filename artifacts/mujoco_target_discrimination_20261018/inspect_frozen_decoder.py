from pathlib import Path
import sys,json
from target_learning.expert_adapter import load_parent
root=Path(__file__).resolve().parent
bundle=root.parent/'landing_hardening_20261018T011610Z/candidate_r15'
module=load_parent(bundle,'frozen_inspection_only')
import inspect
for name in ['RadioRobustRuntime','decode_spatial']:
 value=getattr(module,name,None)
 if value is not None:
  source=inspect.getsource(value)
  if name=='RadioRobustRuntime':
   print('runtime source lines',*[(i+1,line)for i,line in enumerate(source.splitlines())if'acquisition'in line or'decode_spatial'in line],sep='\n')
  else:print(source)
import importlib
spatial=importlib.import_module(module.__package__+'.spatial_acquisition')
print(inspect.getsource(spatial))
old=bundle.parent
report=json.loads((old/'r15_pilot5/report.json').read_text());source=Path(report['results'][0]['directory'])
rows=[json.loads(s)for s in(source/'steps.jsonl').open()]
metric=[i for i,r in enumerate(rows)if r['output'].get('learner_diagnostics',{}).get('metric_valid')]
chosen=sorted(set([0,metric[0],metric[len(metric)//2],metric[-1]]))
import h5py,numpy as np
from PIL import Image,ImageDraw
sheet=Image.new('RGB',(1280,780),(15,20,26));details=[]
with h5py.File(source/'observations.h5','r')as h:
 for n,i in enumerate(chosen):
  row=rows[i];diag=row['output'].get('learner_diagnostics',{});im=Image.fromarray(h['rgb'][row['frame_index']])
  x=n%2*640;y=n//2*390;sheet.paste(im,(x,y))
  detail=dict(row=i,time=row['task_time_s'],frame=row['frame_index'],own_height=row['observation']['px4']['position_enu_m'][2],metric=diag.get('metric_valid'),clearance=diag.get('estimated_clearance_m'),metric_age=diag.get('metric_age_s'));details.append(detail)
  ImageDraw.Draw(sheet).text((x+2,y+364),str(detail),fill='white')
sheet.save(root/'development_replay_views.jpg',quality=94)
(root/'development_replay_views.json').write_text(json.dumps(dict(source=str(source),rows=len(rows),metric_frames=len(metric),views=details),indent=2))
print(json.dumps(dict(source=str(source),rows=len(rows),metric_frames=len(metric),views=details),indent=2))

