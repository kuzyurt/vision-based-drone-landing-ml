"""Discriminate detection-score calibration versus wrong identity/localization.

Validation only, no training or physical flights. Keep failed gate intact.
"""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import json,time
import h5py,numpy as np,torch
from PIL import Image,ImageDraw,ImageFont
from target_learning.discriminator import Discriminator,decode
from train_discriminator_v4 import clean
ROOT=Path(__file__).resolve().parent

def main():
    torch.set_num_threads(2);dest=ROOT/'v4_diagnosis.json';assert not dest.exists();begin=time.monotonic()
    saved=torch.load(ROOT/'perception_training_v4/best.pt',map_location='cuda',weights_only=False)
    model=Discriminator().cuda();model.load_state_dict(saved['model']);model.eval()
    source=ROOT/'perception_training_v3';fine=np.load(source/'validation_fine.npy',mmap_mode='r');context=np.load(source/'validation_context.npy',mmap_mode='r')
    labels=json.loads((source/'validation_labels.json').read_text());rows=[];examples=[]
    stats={str(th):dict(known_targets=0,target_found=0,target_identified=0,wrong_accept=0,unmatched_target_accept=0,pad_errors=[])for th in [.1,.2,.3,.5,.7]}
    with torch.inference_mode():
        for start in range(0,len(labels),32):
            output=model(torch.from_numpy(np.array(fine[start:start+32])).cuda().float(),torch.from_numpy(np.array(context[start:start+32])).cuda().float())
            predictions=decode({k:v.cpu()for k,v in output.items()},minimum_presence=.05,topk=32)
            for frame,all_predictions in zip(labels[start:start+32],predictions):
                for th,s in stats.items():
                    boats=[p for p in all_predictions if p['boat']and p['presence']>=float(th)];used=set()
                    for inst in frame['instances']:
                        if not inst['boat']:continue
                        box=np.asarray(inst['bbox']);center=(box[:2]+box[2:])/2;diag=np.linalg.norm(box[2:]-box[:2])
                        options=[(np.linalg.norm(np.asarray(p['pixel'])-center),j,p)for j,p in enumerate(boats)if j not in used]
                        best=min(options,key=lambda x:x[0])if options else None
                        hit=bool(best and best[0]<=max(8.,.25*diag))
                        if hit:used.add(best[1])
                        if inst['identity']==1:
                            s['known_targets']+=1;s['target_found']+=int(hit)
                            if hit and best[2]['target_probability']>=.98:
                                s['target_identified']+=1
                                if inst['pad_pixel']is not None:s['pad_errors'].append(float(np.linalg.norm(np.asarray(best[2]['pad_pixel'])-inst['pad_pixel'])))
                            if th=='0.7'and not hit and len(examples)<8:
                                examples.append(dict(frame=frame,predictions=all_predictions))
                        if inst['identity']==0 and hit and best[2]['target_probability']>=.98:s['wrong_accept']+=1
                    s['unmatched_target_accept']+=sum(p['target_probability']>=.98 for j,p in enumerate(boats)if j not in used)
                rows.append(dict(world_seed=frame['world_seed'],index=frame['index'],predictions=all_predictions,
                                 known_target_boxes=[i['bbox']for i in frame['instances']if i['identity']==1]))
    for s in stats.values():
        s['target_detection_recall']=s['target_found']/s['known_targets'];s['target_identity_recall']=s['target_identified']/s['known_targets']
        errors=s.pop('pad_errors');s['pad_pixel_error_median']=float(np.median(errors))if errors else None
    manifest=json.loads((ROOT/'perception_dataset_v2/manifest.json').read_text());paths={e['world_seed']:e['path']for e in manifest['entries']if e['role']=='validation'}
    sheet=Image.new('RGB',(1280,4*396),(15,21,30));font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
    for number,e in enumerate(examples):
        f=e['frame']
        with h5py.File(paths[f['world_seed']],'r')as h:rgb=np.asarray(h['rgb'][f['index']])
        im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
        for inst in f['instances']:
            if inst['identity']==1:draw.rectangle(inst['bbox'],outline='#00ff88',width=2)
        for p in e['predictions']:
            if not p['boat']or p['presence']<.1:continue
            x,y=p['pixel'];draw.ellipse((x-3,y-3,x+3,y+3),fill='#ff9977')
            draw.text((x+4,y),f'{p["presence"]:.2f}/ID{p["target_probability"]:.2f}',font=font,fill='yellow')
        x=(number%2)*640;y=(number//2)*396;sheet.paste(im,(x,y))
        ImageDraw.Draw(sheet).text((x+4,y+363),f'Validation{f["world_seed"]}frame{f["index"]}: green=known target; labels=heat/identity',font=font,fill='white')
    sheet.save(ROOT/'v4_errors.jpg',quality=93)
    result=dict(status='diagnosed',seconds=time.monotonic()-begin,score_sweep=stats,validation_only=True,examples=rows)
    dest.write_text(json.dumps(clean(result),indent=2));print(json.dumps(clean({k:v for k,v in result.items()if k!='examples'}),indent=2),flush=True)

if __name__=='__main__':main()
