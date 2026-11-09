"""Train an image-only acquisition head on existing training data, no test inputs."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import json,sys,time,hashlib,copy
from pathlib import Path
import numpy as np,h5py,torch
from torch import nn
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE));from landing_training.gate import file_hash
from collect_domain import save

class AcquisitionHead(nn.Module):
    def __init__(self):
        super().__init__();self.register_buffer('mean',torch.zeros(1728));self.register_buffer('std',torch.ones(1728))
        self.network=nn.Sequential(nn.Linear(1728,256),nn.ReLU(),nn.Dropout(.1),nn.Linear(256,128),nn.ReLU(),nn.Linear(128,3))
    def forward(self,x):return self.network(((x-self.mean)/self.std).clamp(-12,12))

def load(entries,split):
    features=[];labels=[];groups=[];rng=np.random.default_rng(6151 if split=='training' else 7611)
    for e in entries:
        if e['role']!=split:continue
        t=np.load(e['target']);visible=t[:,0]>.5
        radius=np.linalg.norm(t[:,12:14]*[320.,180.],axis=-1)
        bins=np.where(~visible,0,np.where(radius>80,1,np.where(radius>30,2,3)))
        chosen=[]
        for group,limit in enumerate([160,256,128,96] if split=='training' else [256,384,256,192]):
            indices=np.flatnonzero(bins==group)
            if len(indices)>limit:indices=np.sort(rng.choice(indices,limit,replace=False))
            chosen.extend(indices.tolist())
        selected=np.sort(np.asarray(chosen,dtype=int))
        if not len(selected):continue
        with h5py.File(e['cache']) as f:x=np.asarray(f['features'])[selected]
        y=np.column_stack((visible[selected],t[selected,12:14])).astype('f4')
        features.append(x);labels.append(y);groups.append(bins[selected])
    return np.concatenate(features),np.concatenate(labels),np.concatenate(groups)

@torch.inference_mode()
def metrics(model,x,y,g):
    model.eval();prediction=torch.cat([model(chunk) for chunk in x.split(4096)])
    probability=prediction[:,0].sigmoid();visible=y[:,0]>.5
    error=torch.linalg.vector_norm((prediction[:,1:]-y[:,1:])*x.new_tensor([320.,180.]),dim=-1)
    values=dict(frames=len(x),visible_frames=int(visible.sum()),negative_frames=int((~visible).sum()),
        pixel_rms=float(error[visible].square().mean().sqrt()),
        offcenter_pixel_rms=float(error[g==1].square().mean().sqrt()),
        false_positive_rate=float((probability[~visible]>=.8).float().mean()),
        recall=float((probability[visible]>=.8).float().mean()),
        bce=float(nn.functional.binary_cross_entropy_with_logits(prediction[:,0],y[:,0])))
    values['score']=values['offcenter_pixel_rms']+.25*values['pixel_rms']+100*values['false_positive_rate']+20*(1-values['recall'])
    return values

def main():
    out=ROOT/'acquisition_training';out.mkdir(exist_ok=False);torch.set_num_threads(2);torch.manual_seed(6141)
    old=BASE/'landing_training/outputs/control_iteration_20261010T220632Z/pose_targets/manifest.json';new=ROOT/'features/manifest.json'
    entries=json.loads(old.read_text())['entries']+json.loads(new.read_text())['entries']
    assert all(e['role'] in ('training','validation') for e in entries)
    began=time.monotonic();x,y,g=load(entries,'training');vx,vy,vg=load(entries,'validation')
    save(out/'provenance.json',dict(source_manifests={str(p):file_hash(p) for p in [old,new]},test_frames_used=0,
         purpose='Pure image acquisition without recurrent/telemetry shortcuts; balanced missing and off-centre views',
         input='Unchanged frozen image-encoder spatial features',training_frames=len(x),validation_frames=len(vx),
         training_groups=np.bincount(g,minlength=4).tolist(),validation_groups=np.bincount(vg,minlength=4).tolist()))
    x=torch.from_numpy(x).cuda();y=torch.from_numpy(y).cuda();g=torch.from_numpy(g).cuda()
    vx=torch.from_numpy(vx).cuda();vy=torch.from_numpy(vy).cuda();vg=torch.from_numpy(vg).cuda()
    model=AcquisitionHead().cuda();model.mean.copy_(x.mean(0));model.std.copy_(x.std(0).clamp_min(.02))
    optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
    counts=torch.bincount(g,minlength=4).clamp_min(1);ratios=x.new_tensor([.25,.35,.2,.2]);weights=ratios[g]/counts[g]
    best=float('inf');history=[];stale=0
    for epoch in range(1,101):
        model.train();indices=torch.multinomial(weights,65536,replacement=True)
        for batch in indices.split(2048):
            prediction=model(x[batch]);target=y[batch];positive=target[:,0]>.5
            visibility=nn.functional.binary_cross_entropy_with_logits(prediction[:,0],target[:,0])
            pixel=nn.functional.smooth_l1_loss(prediction[positive,1:]*x.new_tensor([320.,180.]),target[positive,1:]*x.new_tensor([320.,180.]),beta=10.)/40
            loss=visibility+pixel;optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),2.);optimizer.step()
        value=metrics(model,vx,vy,vg);item=dict(epoch=epoch,seconds=time.monotonic()-began,**value);history.append(item)
        if value['score']<best:
            best=value['score'];stale=0;torch.save(dict(schema='aerodock.landing.acquisition_head.v1',model=model.state_dict(),epoch=epoch,validation=value,
                 training_test_images=False,provenance_sha256=file_hash(out/'provenance.json')),out/'best.pt')
        else:stale+=1
        save(out/'history.json',history);save(out/'progress.json',item)
        if epoch%5==0:print('ACQUISITION_EPOCH',json.dumps(item),flush=True)
        if epoch>=25 and stale>=15:break
        if time.monotonic()-began>8*60:break
    selected=torch.load(out/'best.pt',map_location='cpu',weights_only=False)
    save(ROOT/'acquisition_training_result.json',dict(status='completed',epochs=len(history),seconds=time.monotonic()-began,
        selected_epoch=selected['epoch'],validation=selected['validation'],checkpoint_sha256=file_hash(out/'best.pt'),test_images_used=False))
    print('ACQUISITION_DONE',json.dumps(selected['validation']),flush=True)

if __name__=='__main__':main()
