from pathlib import Path
import hashlib,json
import h5py,numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).parent;D=R/'static_repair_v52';m=json.loads((D/'manifest.json').read_text());assert m['frames']==6400;sheet=Image.new('RGB',(1600,1260));draw=ImageDraw.Draw(sheet);shown=0;used=set();contacts=0;near=0;counts={};scenes=set()
for e in m['entries']:
 j=e['job'];scenes.add(j['model_scope'])
 with h5py.File(D/j['name']/'data.h5','r')as h:
  labels=[json.loads(x)for x in h['labels']];contacts+=sum(x['static_view_contact_excluded']for x in labels);near+=sum(x['near_view']and not x['static_view_contact_excluded']for x in labels)
  for x in labels:
   if x['static_view_contact_excluded']:continue
   for i in x['instances']:counts[str(i['identity'])]=counts.get(str(i['identity']),0)+1
  key=(j['kind'],j['model_scope'])
  if j['role']!='validation'or key in used:continue
  used.add(key)
  for subject in ['target','decoy_dark','background']:
   matches=[i for i,x in enumerate(labels)if x['view_subject']==subject and not x['static_view_contact_excluded']]
   if not matches:raise RuntimeError('Expected coverage missing '+str(key)+subject)
   at=matches[0];l=labels[at];im=Image.fromarray(h['rgb'][at]);d=ImageDraw.Draw(im)
   for i in l['instances']:d.rectangle(i['bbox'],outline='lime'if i['identity']==1 else'orange',width=2);d.text(tuple(i['bbox'][:2]),str(i['identity']),fill='white')
   x=shown%5*320;y=shown//5*210;sheet.paste(im.resize((320,180)),(x,y));draw.text((x+2,y+181),f"{j['kind']} {j['model_scope']} {subject}\nrange{l['view_distance_m']:.2f}m",fill='white');shown+=1
assert len(used)==10 and scenes=={'basic','hard'}and shown==30
sheet.save(D/'basic_hard_actual_labels.jpg',quality=88);r=dict(total=6400,valid_near=near,contact_excluded=contacts,identity_instance_counts=counts,validation_model_map_pairs=sorted(used),sheet_frames=shown);(D/'coverage.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
