import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys
import numpy as np,torch,h5py
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'search_v35/sources'));sys.path.insert(1,str(ROOT.parent))
from target_learning.object_verifier_v12 import ObjectVerifier
from train_object_verifier_v8 import matched
def main():
    q=ROOT/'roi_cache/static_v37/validation';raw=np.load(q/'rgb.npy');meta=np.load(q/'meta.npy');frames=json.loads((q/'frames.json').read_text());m=ObjectVerifier(mode='rgb_only').cuda();m.load_state_dict(torch.load(ROOT/'perception_training_v37/best.pt',map_location='cpu',weights_only=False)['verifier']);m.eval();probs=[]
    with torch.inference_mode():
        for at in range(0,len(raw),128):
            x=torch.tensor(raw[at:at+128],device='cuda').float();p=m(x.new_zeros((len(x),1)),torch.tensor(meta[at:at+128],device='cuda').float(),x)['identity'].softmax(-1);probs.extend(p.cpu().tolist())
    bad=[];sheet=Image.new('RGB',(960,540));manifest=json.loads((ROOT/'static_repair_v37/manifest.json').read_text())
    for f in frames:
        for k,p in enumerate(f['predictions']):
            prob=probs[f['offset']+k][1];j=matched(p,f['label']['instances'])
            if prob<.98 or p['presence']<.3 or(j is not None and f['label']['instances'][j]['identity']in[1,-2]):continue
            label=f['label'];entry=next(e for e in manifest['entries']if e['job']['world_seed']==label['world_seed']);path=ROOT/'static_repair_v37'/entry['job']['name']/'data.h5'
            with h5py.File(path,'r')as h:rgb=np.asarray(h['rgb'][label['index']]);assert hashlib.sha256(rgb.tobytes()).hexdigest()==label['rgb_sha256']
            n=len(bad);im=Image.fromarray(rgb);d=ImageDraw.Draw(im);xy=p['pixel'];sz=p['size_px'];d.rectangle([xy[0]-sz[0]*1.25,xy[1]-sz[1]*1.25,xy[0]+sz[0]*1.25,xy[1]+sz[1]*1.25],outline='red',width=2);sheet.paste(im.resize((640,360)),(0,0));crop=Image.fromarray((np.transpose(raw[f['offset']+k],(1,2,0))*255).clip(0,255).astype('uint8')).resize((288,288));sheet.paste(crop,(650,0));bad.append(dict(probability=prob,proposal=p,instance=f['label']['instances'][j]if j is not None else None,label=label))
    out=ROOT/'perception_training_v37';(out/'false_assertions.json').write_text(json.dumps(bad,indent=2));sheet.save(out/'false_assertion_actual_rgb.jpg');print(json.dumps(dict(false_assertions=len(bad))),flush=True)
if __name__=='__main__':main()
