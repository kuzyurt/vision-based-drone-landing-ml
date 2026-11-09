"""Validation-only object/support errors and hard-scene challenge; no tuning run."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',MUJOCO_GL='egl')
from pathlib import Path
import json,time
import h5py,numpy as np,torch
from PIL import Image,ImageDraw,ImageFont
from target_learning.discriminator_v5 import Discriminator,decode
from train_discriminator_v4 import save
ROOT=Path(__file__).resolve().parent


def main():
    torch.set_num_threads(1);begin=time.monotonic();out=ROOT/'perception_training_v5';assert(out/'result.json').exists()
    labels=json.loads((out/'validation_effective_labels.json').read_text());old=ROOT/'perception_training_v3'
    fine=np.concatenate([np.load(old/'validation_fine.npy',mmap_mode='r'),np.load(out/'validation_fine.npy',mmap_mode='r')])
    context=np.concatenate([np.load(old/'validation_context.npy',mmap_mode='r'),np.load(out/'validation_context.npy',mmap_mode='r')])
    saved=torch.load(out/'best.pt',map_location='cuda',weights_only=False);head=Discriminator().cuda();head.load_state_dict(saved['model']);head.eval()
    point=saved['validation']['selected_operating_point']or saved['validation']['diagnostic_best_effort']
    sources={}
    for dataset in ['perception_dataset_v2','perception_hard_dataset_v5']:
        for e in json.loads((ROOT/dataset/'manifest.json').read_text())['entries']:
            if e['role']=='validation':sources[e['world_seed']]=e['path']
    errors=[];predictions=[];conflicts={'same_glyph_non_target_pad_visibility_zero':0,'ambiguous_same_glyph_crops':0}
    with torch.inference_mode():
        for start in range(0,len(labels),32):
            output=head(torch.from_numpy(np.array(fine[start:start+32])).cuda().float(),torch.from_numpy(np.array(context[start:start+32])).cuda().float())
            decoded=decode({k:v.cpu()for k,v in output.items()},minimum_presence=.2)
            for index,(label,pred)in enumerate(zip(labels[start:start+32],decoded),start):
                accepts=[p for p in pred if p['presence']>=point['heat']and p['target_probability']>=point['identity']and p['identity_support_probability']>=point['support']]
                matches=[];false=[]
                for p in accepts:
                    x,y=p['pixel'];inside=[j for j,i in enumerate(label['instances'])if i['bbox'][0]-2<=x<=i['bbox'][2]+2 and i['bbox'][1]-2<=y<=i['bbox'][3]+2]
                    matches.extend(j for j in inside if label['instances'][j]['identity']==1)
                    if not inside or all(label['instances'][j]['identity']!=1 for j in inside):false.append(p)
                missed=[i for j,i in enumerate(label['instances'])if i['identity']==1 and j not in matches]
                if false or missed:errors.append(dict(index=index,label=label,predictions=pred,false=len(false),missed=len(missed)))
                for inst in label['instances']:
                    if inst['annotation_instance']in ['decoy_false_cross_boat','decoy_false_cross_board']and inst.get('marker_visible_pixels',0)>=4:
                        conflicts['same_glyph_non_target_pad_visibility_zero']+=1
                        conflicts['ambiguous_same_glyph_crops']+=int(inst['identity']<0)
                predictions.append(dict(label=label,predictions=pred))
    # Show false assertions first, then varied missed targets; actual RGB only.
    ordered=sorted(errors,key=lambda e:(-e['false'],-e['missed']))
    chosen=[];world_counts={}
    for e in ordered:
        world=e['label']['world_seed']
        if world_counts.get(world,0)>=3:continue
        chosen.append(e);world_counts[world]=world_counts.get(world,0)+1
        if len(chosen)>=12:break
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13);sheet=Image.new('RGB',(1280,6*390),(15,20,26))
    for n,e in enumerate(chosen):
        frame=e['label']
        with h5py.File(sources[frame['world_seed']],'r')as h:im=Image.fromarray(h['rgb'][frame['index']])
        draw=ImageDraw.Draw(im)
        for inst in frame['instances']:
            color='lime'if inst['identity']==1 else'red'if inst['identity']==0 else'cyan'
            draw.rectangle(inst['bbox'],outline=color,width=1)
        for p in e['predictions']:
            x,y=p['pixel'];draw.text((x,y),f'H{p["presence"]:.2f} I{p["target_probability"]:.2f} S{p["identity_support_probability"]:.2f}',font=font,fill='yellow')
        x=n%2*640;y=n//2*390;sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text((x+3,y+364),f'world{frame["world_seed"]} frame{frame["index"]} misses{e["missed"]} false{e["false"]}',font=font,fill='white')
    sheet.save(ROOT/'v5_validation_errors.jpg',quality=94)
    save(ROOT/'v5_validation_predictions.json',predictions)
    save(ROOT/'v5_diagnosis.json',dict(selected_point=point,errors=len(errors),label_conflicts=conflicts,
        selected_errors=chosen,seconds=time.monotonic()-begin,heldout_used=False,tidewater_used=False))
    print(json.dumps(dict(errors=len(errors),label_conflicts=conflicts,seconds=time.monotonic()-begin)),flush=True)

if __name__=='__main__':main()
