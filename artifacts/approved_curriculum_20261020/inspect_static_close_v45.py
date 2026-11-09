from pathlib import Path
import hashlib,json,sys
import h5py,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).parent;D=R/'static_repair_v44b';manifest=json.loads((D/'manifest.json').read_text());sheet=Image.new('RGB',(1280,1260));draw=ImageDraw.Draw(sheet);count=0;contacts=0;near=0;classes={}
for entry in manifest['entries']:
 j=entry['job']
 with h5py.File(D/j['name']/'data.h5','r')as h:
  labels=[json.loads(v)for v in h['labels']]
  contacts+=sum(x['static_view_contact_excluded']for x in labels);near+=sum(x['near_view']and not x['static_view_contact_excluded']for x in labels)
  for x in labels:
   if x['static_view_contact_excluded']:continue
   for i in x['instances']:classes[str(i['identity'])]=classes.get(str(i['identity']),0)+1
  if j['role']!='validation':continue
  selections=[]
  for predicate in [lambda x:x['near_view']and x['view_subject']=='target',lambda x:x['near_view']and 'board'in x['view_subject'],lambda x:x['view_subject']=='background']:
   options=[i for i,x in enumerate(labels)if predicate(x)and not x['static_view_contact_excluded']]
   if options:selections.append(options[0])
  for at in selections:
   if count>=24:break
   label=labels[at];im=Image.fromarray(h['rgb'][at]);d=ImageDraw.Draw(im)
   for i in label['instances']:d.rectangle(i['bbox'],outline='lime'if i['identity']==1 else'orange',width=2);d.text(tuple(i['bbox'][:2]),str(i['identity']),fill='white')
   x=(count%4)*320;y=(count//4)*210;sheet.paste(im.resize((320,180)),(x,y));draw.text((x+2,y+181),f"{j['kind']} {label['view_subject']}\n{label['view_distance_m']:.2f}m pan{label['view_pan_rad']:.2f}",fill='white');count+=1
sheet.save(D/'near_and_background_actual_labels.jpg',quality=88);report=dict(total=manifest['frames'],contact_excluded=contacts,valid_near=near,instance_identity_counts=classes,sheet_frames=count);(D/'close_view_coverage.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
