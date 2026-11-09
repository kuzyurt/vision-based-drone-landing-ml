import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import argparse,json,numpy as np,torch,h5py
from PIL import Image,ImageDraw,ImageFont
from target_learning.object_verifier_v12 import ObjectVerifier
from train_object_verifier_v8 import matched
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--mode',required=True);args=parser.parse_args()
out=ROOT/('perception_training_v12_'+args.mode);parent=ROOT/'perception_training_v9'
saved=torch.load(out/'best.pt',map_location='cuda',weights_only=False);model=ObjectVerifier(mode=args.mode).cuda();model.load_state_dict(saved['verifier']);model.eval();torch.set_num_threads(1)
features=np.load(parent/'validation_features.npy',mmap_mode='r');meta=np.load(parent/'validation_meta.npy',mmap_mode='r');frames=json.loads((out/'validation_frames.json').read_text())
probs=[];markers=[];raw=np.load(ROOT/'perception_rgb_cache_v12/validation_rgb.npy',mmap_mode='r')
with torch.inference_mode():
 for at in range(0,len(features),512):
  v=model(torch.tensor(np.array(features[at:at+512]),device='cuda').float(),torch.tensor(np.array(meta[at:at+512]),device='cuda').float(),torch.tensor(np.array(raw[at:at+512]),device='cuda').float())
  probs.extend(v['identity'].softmax(-1).cpu().tolist());markers.extend(v['marker'].sigmoid().cpu().tolist())
point=saved['validation']['diagnostic_best_effort'];at=0;errors=[]
for index,f in enumerate(frames):
 rows=[];accepted=set();false=[]
 for proposal in f['predictions']:
  prob=probs[at];marker=markers[at];at+=1;j=matched(proposal,f['label']['instances']);inst=f['label']['instances'][j]if j is not None else None
  hit=proposal['presence']>=point['heat']and prob[1]>=point['identity']
  row=dict(proposal=proposal,probability=prob,marker=marker,instance=inst,accepted=hit);rows.append(row)
  if hit and inst and inst['identity']==1:accepted.add(j)
  elif hit and (inst is None or inst['identity']not in[1,-2]):false.append(row)
 missed=[i for j,i in enumerate(f['label']['instances'])if i['identity']==1 and j not in accepted]
 if missed or false:errors.append(dict(index=index,frame=f['label'],false=false,missed=missed,predictions=rows))
assert at==len(probs)
history=json.loads((out/'history.json').read_text());brief=[dict(epoch=r['epoch'],loss=r['loss'],diagnostic=r['diagnostic_best_effort'],marker=r['selected_marker_operating_point'],score=r['score'],passed=r['expert_gate_passed'])for r in history]
summary=dict(selected_epoch=saved['epoch'],validation=saved['validation'],history=brief,false_frames=[e for e in errors if e['false']],sample_misses=[e for e in errors if not e['false']][:10],error_frames=len(errors),first_label_keys=list(frames[0]['label']))
(ROOT/('v12_'+args.mode+'_diagnosis.json')).write_text(json.dumps(summary,indent=2))
sources={}
for dataset in ['perception_dataset_v2','perception_hard_dataset_v5','perception_paired_dataset_v9']:
 path=ROOT/dataset/'manifest.json'
 if not path.exists():continue
 manifest=json.loads(path.read_text())
 for e in manifest['entries']:
  if e['role']=='validation':sources[e['world_seed']]=e['path']
chosen=[e for e in errors if e['false']];world_counts={}
for e in errors:
 if e['false']:continue
 world=e['frame']['world_seed']
 if world_counts.get(world,0)>=2:continue
 chosen.append(e);world_counts[world]=world_counts.get(world,0)+1
 if len(chosen)>=10:break
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
sheet=Image.new('RGB',(1280,390*((len(chosen)+1)//2)),(15,20,26))
for n,e in enumerate(chosen):
 frame=e['frame'];path=sources[frame['world_seed']]
 with h5py.File(path,'r')as h:im=Image.fromarray(h['rgb'][frame['index']])
 draw=ImageDraw.Draw(im)
 for inst in frame['instances']:
  color='lime'if inst['identity']==1 else'red'if inst['identity']==0 else'cyan'
  draw.rectangle(inst['bbox'],outline=color,width=1);draw.text(inst['bbox'][:2],inst['annotation_instance'],font=font,fill=color)
 for row in e['predictions']:
  p=row['proposal']
  if p['presence']<point['heat']:continue
  draw.text(tuple(p['pixel']),f"I{row['probability'][1]:.3f} M{row['marker']:.2f}",font=font,fill='yellow')
 x=n%2*640;y=n//2*390;sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text((x+3,y+364),f"world{frame['world_seed']} f{frame['index']} {frame.get('variant','old')} false{len(e['false'])} miss{len(e['missed'])}",font=font,fill='white')
sheet.save(ROOT/('v12_'+args.mode+'_validation_errors.jpg'),quality=94)
print(json.dumps(dict(selected_epoch=saved['epoch'],error_frames=len(errors),false_frames=len(summary['false_frames']),marker=saved['validation']['selected_marker_operating_point'],first_label_keys=summary['first_label_keys'],last_epochs=brief[-5:]),indent=2))
