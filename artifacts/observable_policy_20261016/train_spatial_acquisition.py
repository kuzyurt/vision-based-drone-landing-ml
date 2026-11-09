"""Existing approved training RGB only; spatial feature cache and new image head."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import copy,hashlib,json,sys,time,shutil
import h5py,numpy as np,torch
from torch.nn import functional as F
from spatial_acquisition import SpatialAcquisition,encode_spatial,decode_spatial

ROOT=Path(__file__).resolve().parent
BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
OLD=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
OUT=ROOT/'spatial_acquisition_training'
sys.path.insert(0,str(BASE))
import landing_training
landing_training.__path__.append(str(OLD/'candidate_bundle/code/landing_training'))
from landing_training import paths
from landing_training.radio_robust_20261015.model import RadioRobustPoseModel


def save(path,value):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False));tmp.replace(path)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def select(entries):
    jobs=[]
    for e in entries:
        role=e['role'];assert role in ['training','validation']
        assert not any(v in e['source_path'] for v in ['/evaluation_','/probe_','/spatial_failure_audit_','/observable_policy_'])
        target=Path(e['target']);assert sha(target)==e['target_sha256']
        t=np.load(target);valid=t[:,0]>.5;point=(t[:,12:14]+1)*[320.,180.]
        inside=(point[:,0]>4)&(point[:,0]<636)&(point[:,1]>4)&(point[:,1]<356)
        valid&=inside
        radius=np.linalg.norm(point-[320.,180.],axis=-1)
        groups=np.where(~valid,0,np.where(radius>80,1,np.where(radius>30,2,3)))
        recent='domain_training_20261016' in e['source_path']
        limits=([48,80,32,32] if recent else [12,16,8,8]) if role=='training' else ([64,96,48,48] if recent else [16,20,10,10])
        rng=np.random.default_rng(int.from_bytes(hashlib.sha256(e['source_path'].encode()).digest()[:4],'little'))
        chosen=[]
        for group,limit in enumerate(limits):
            indices=np.flatnonzero(groups==group)
            if len(indices)>limit:indices=np.sort(rng.choice(indices,limit,replace=False))
            chosen.extend(indices.tolist())
        indices=np.sort(np.array(chosen,dtype=np.int64))
        if len(indices):jobs.append(dict(entry=e,indices=indices.tolist(),role=role))
    return jobs


def extract(jobs,backbone):
    totals={role:sum(len(j['indices']) for j in jobs if j['role']==role) for role in ['training','validation']}
    arrays={}
    for role,n in totals.items():
        arrays[role]=dict(fine=np.lib.format.open_memmap(OUT/f'{role}_fine.npy',mode='w+',dtype='float16',shape=(n,24,45,80)),
            context=np.lib.format.open_memmap(OUT/f'{role}_context.npy',mode='w+',dtype='float16',shape=(n,48,23,40)),
            labels=np.lib.format.open_memmap(OUT/f'{role}_labels.npy',mode='w+',dtype='float32',shape=(n,4)))
    offsets=dict(training=0,validation=0);start=time.monotonic();manifest=[]
    with torch.inference_mode():
        for number,job in enumerate(jobs):
            e=job['entry'];role=job['role'];indices=np.array(job['indices']);t=np.load(e['target']);n=len(indices);digest=hashlib.sha256()
            point=(t[indices,12:14]+1)*[320.,180.];valid=(t[indices,0]>.5)&(point[:,0]>4)&(point[:,0]<636)&(point[:,1]>4)&(point[:,1]<356)
            weak_boat_labels=0
            with h5py.File(e['source_path'],'r') as raw:
                assert str(raw.attrs['role'])==role and len(raw['rgb'])==len(t)
                for a in range(0,n,24):
                    selected=indices[a:a+24];rgb=np.stack([raw['rgb'][int(i)] for i in selected])
                    digest.update(rgb.tobytes())
                    # Same existing boat-visibility evidence used by V4. Preserve
                    # pad coordinates as the point label; do not train on test RGB.
                    for k,index in enumerate(range(a,min(n,a+24))):
                        if valid[index]:continue
                        px,py=point[index]
                        if not (4<px<636 and 4<py<356):continue
                        image=rgb[k,max(0,int(py)-100):min(360,int(py)+101),max(0,int(px)-100):min(640,int(px)+101)].astype(np.int16)
                        paint=(np.minimum(image[...,1],image[...,2])-image[...,0]>45)&(image[...,1]>=image[...,2]-12)&(image[...,1]>85)
                        white=(image.min(-1)>110)&(image.max(-1)-image.min(-1)<60)
                        if paint.sum()>=2 and white.sum()>=8:valid[index]=True;weak_boat_labels+=1
                    tensor=torch.from_numpy(rgb).permute(0,3,1,2).cuda()
                    fine,context=encode_spatial(backbone,tensor)
                    begin=offsets[role]+a;end=begin+len(selected)
                    arrays[role]['fine'][begin:end]=fine.half().cpu().numpy()
                    arrays[role]['context'][begin:end]=context.half().cpu().numpy()
            radius=np.linalg.norm(point-[320.,180.],axis=1)
            groups=np.where(~valid,0,np.where(radius>80,1,np.where(radius>30,2,3)))
            begin=offsets[role];arrays[role]['labels'][begin:begin+n]=np.column_stack((valid,point,groups))
            offsets[role]+=n
            manifest.append(dict(source=e['source_path'],role=role,indices=indices.tolist(),selected_rgb_sha256=digest.hexdigest(),target_sha256=e['target_sha256'],weak_boat_labels=weak_boat_labels))
            for array in arrays[role].values():array.flush()
            progress=dict(stage='extracting',episodes=number+1,total_episodes=len(jobs),frames=offsets,planned=totals,seconds=time.monotonic()-start)
            save(OUT/'progress.json',progress)
            if number%25==0:print('SPATIAL_CACHE',json.dumps(progress),flush=True)
    save(OUT/'consumed_sources.json',dict(entries=manifest,totals=totals,development_or_test_rgb_used=False))
    return arrays


@torch.inference_mode()
def metrics(model,data):
    model.eval();labels=np.asarray(data['labels']);visible=labels[:,0]>.5;predictions=[];probabilities=[]
    for start in range(0,len(labels),128):
        a=torch.from_numpy(np.array(data['fine'][start:start+128])).cuda().float();b=torch.from_numpy(np.array(data['context'][start:start+128])).cuda().float()
        logits,pixel=decode_spatial(model(a,b));predictions.append(pixel.cpu().numpy());probabilities.append(logits.sigmoid().cpu().numpy())
    prediction=np.concatenate(predictions);probability=np.concatenate(probabilities);error=np.linalg.norm(prediction-labels[:,1:3],axis=1)
    off=(labels[:,3]==1)&visible;negative=~visible
    value=dict(frames=len(labels),visible_frames=int(visible.sum()),negative_frames=int(negative.sum()),
        pixel_rms=float(np.sqrt(np.mean(error[visible]**2))),offcenter_pixel_rms=float(np.sqrt(np.mean(error[off]**2))),
        median_pixel_error=float(np.median(error[visible])),p90_pixel_error=float(np.percentile(error[visible],90)),
        false_positive_rate=float(np.mean(probability[negative]>=.8)),recall=float(np.mean(probability[visible]>=.8)))
    value['score']=value['offcenter_pixel_rms']+.25*value['pixel_rms']+100*value['false_positive_rate']+30*(1-value['recall'])
    return value


def train(arrays):
    torch.manual_seed(81043);model=SpatialAcquisition().cuda();optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
    data=arrays['training'];labels=np.asarray(data['labels']);groups=[np.flatnonzero(labels[:,3]==i) for i in range(4)]
    assert all(len(g) for g in groups)
    rng=np.random.default_rng(81043);best=float('inf');stale=0;history=[];started=time.monotonic()
    for epoch in range(1,31):
        model.train()
        # Balanced search negatives/off-centre/near-centre points; no sequences
        # or teacher actions are inputs to this image-only perception head.
        indices=np.concatenate([rng.choice(group,10000,replace=True) for group in groups]);rng.shuffle(indices)
        losses=[]
        for start in range(0,len(indices),96):
            ix=indices[start:start+96];target=torch.from_numpy(np.array(labels[ix])).cuda();visible=target[:,0]>.5
            fine=torch.from_numpy(np.array(data['fine'][ix])).cuda().float();context=torch.from_numpy(np.array(data['context'][ix])).cuda().float()
            heat,offset,presence=model(fine,context);h,w=heat.shape[-2:]
            column=(target[:,1]/640*w).floor().long().clamp(0,w-1);row=(target[:,2]/360*h).floor().long().clamp(0,h-1);cell=row*w+column
            classification=F.binary_cross_entropy_with_logits(presence,target[:,0])
            location=F.cross_entropy(heat[visible].flatten(1),cell[visible]) if visible.any() else heat.sum()*0
            local_target=torch.stack((target[:,1]/640*w-column-.5,target[:,2]/360*h-row-.5),1)
            local=offset.flatten(2)[torch.arange(len(ix),device='cuda'),:,cell]
            regression=F.smooth_l1_loss(local[visible],local_target[visible]) if visible.any() else offset.sum()*0
            loss=classification+location+4*regression
            optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3.);optimizer.step();losses.append(float(loss.detach()))
        value=metrics(model,arrays['validation']);item=dict(epoch=epoch,loss=float(np.mean(losses)),seconds=time.monotonic()-started,**value);history.append(item)
        checkpoint=dict(schema='observable_landing.spatial_acquisition.v1',model=model.state_dict(),epoch=epoch,validation=value,
            pose_checkpoint_sha256=sha(OLD/'candidate_bundle/pose.pt'),test_images_used=False,selected_on='existing validation split only')
        epoch_path=OUT/f'epoch_{epoch:03d}.pt';torch.save(checkpoint,epoch_path)
        if value['score']<best:
            best=value['score'];stale=0
            shutil.copy2(epoch_path,OUT/'best.pt')
        else:stale+=1
        save(OUT/'history.json',history);save(OUT/'progress.json',dict(stage='training',**item));print('SPATIAL_EPOCH',json.dumps(item),flush=True)
        if epoch>=12 and stale>=6:break
    selected=torch.load(OUT/'best.pt',map_location='cpu',weights_only=False)
    save(OUT/'result.json',dict(status='completed',epochs=len(history),selected_epoch=selected['epoch'],validation=selected['validation'],checkpoint_sha256=sha(OUT/'best.pt'),test_images_used=False))


def main():
    OUT.mkdir(exist_ok=False);torch.set_num_threads(2)
    manifests=[BASE/'landing_training/outputs/control_iteration_20261010T220632Z/pose_targets/manifest.json',OLD/'features/manifest.json']
    entries=sum((json.loads(p.read_text())['entries'] for p in manifests),[]);jobs=select(entries)
    save(OUT/'plan.json',dict(source_manifests={str(p):sha(p) for p in manifests},jobs=jobs,
        test_or_development_frames_used=False,encoder_frozen=True,new_collection=False,
        purpose='Retain spatial feature maps for image-only target localization instead of regressing centre from globally compressed features'))
    model=RadioRobustPoseModel().cuda();model.load_state_dict(torch.load(OLD/'candidate_bundle/pose.pt',map_location='cuda',weights_only=False)['model']);model.eval()
    arrays=extract(jobs,model.backbone);del model;torch.cuda.empty_cache();train(arrays)


if __name__=='__main__':main()
