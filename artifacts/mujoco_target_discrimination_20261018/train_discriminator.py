"""Frozen-backbone candidate/identity head; MuJoCo-only train/validation splits."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import argparse,datetime,hashlib,importlib,json,math,sys,time,types
import h5py,numpy as np,torch
from torch.nn import functional as F
from target_learning.discriminator import Discriminator,decode
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
BUNDLE=BASE/'landing_training/outputs/landing_hardening_20261018T011610Z/candidate_r15'
sys.path.insert(0,str(BASE))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,indent=2,allow_nan=False));tmp.replace(p)

def targets(labels):
    heat=np.zeros((len(labels),2,45,80),np.float32);points=[]
    yy,xx=np.mgrid[:45,:80]
    conflicts=0
    for b,frame in enumerate(labels):
        used={}
        for inst in frame['instances']:
            box=np.array(inst['bbox'],float);size=box[2:]-box[:2];center=(box[:2]+box[2:])/2
            cell=np.floor(center/[8.,8.]).astype(int);cell=np.clip(cell,[0,0],[79,44]);x,y=cell
            channel=0 if inst['boat'] else 1
            gaussian=np.exp(-((xx-x)**2+(yy-y)**2)/(2*1.2**2))
            heat[b,channel]=np.maximum(heat[b,channel],gaussian)
            if (x,y)in used:
                # Two objects unresolved in the same feature cell cannot have
                # contradictory identity or offset/size regression targets.
                points[used[x,y]][-1]=0.;conflicts+=1;continue
            pad=inst.get('pad_pixel');pad_valid=bool(pad is not None and 0<=pad[0]<640 and 0<=pad[1]<360)
            pad_delta=(np.asarray(pad)-center)/size if pad_valid else [0.,0.]
            values=[b,y,x,*((center/[8.,8.])-cell-.5),*np.log(np.maximum(size/[640.,360.],1e-4)),
                    inst['identity'] if inst['boat'] else -1,*pad_delta,float(pad_valid),float(inst['boat']),1.]
            used[x,y]=len(points);points.append(values)
    return heat,np.asarray(points,dtype=np.float32).reshape(-1,13),conflicts

def loss(output,heat,points):
    probability=output['heat'].sigmoid().clamp(1e-5,1-1e-5)
    positive=heat.eq(1);negative=~positive
    focal=-(probability.log()*(1-probability)**2*positive+(1-probability).log()*probability**2*(1-heat)**4*negative).sum()/positive.sum().clamp_min(1)
    if not len(points):return focal
    p=points;valid=p[:,-1]>.5;p=p[valid]
    if not len(p):return focal
    batch,y,x=p[:,:3].long().T
    regression=F.smooth_l1_loss(output['offset'][batch,:,y,x],p[:,3:5])
    size=F.smooth_l1_loss(output['size'][batch,:,y,x],p[:,5:7])
    known=p[:,7]>=0
    identity=F.binary_cross_entropy_with_logits(output['identity'][batch,0,y,x][known],p[known,7]) if known.any()else output['identity'].sum()*0
    boats=p[:,11]>.5;pad_valid=p[:,10]>.5
    visibility=F.binary_cross_entropy_with_logits(output['pad_visible'][batch,0,y,x][boats],p[boats,10]) if boats.any()else output['pad_visible'].sum()*0
    pad=F.smooth_l1_loss(output['pad'][batch,:,y,x][pad_valid],p[pad_valid,8:10])if pad_valid.any()else output['pad'].sum()*0
    return focal+2*regression+size+identity+visibility+4*pad

def prepare(manifest,out,runtime):
    import copy
    pkg=runtime.__package__
    spatial=importlib.import_module(pkg+'.spatial_acquisition')
    entries=[e for e in manifest['entries']if e['role']in ['training','validation']]
    assert entries and not any('tidewater'in e['path'].lower()for e in entries)
    result={};provenance=[]
    for role in ['training','validation']:
        sources=[e for e in entries if e['role']==role];n=sum(e['frames']for e in sources);assert n>0
        arrays=dict(fine=np.lib.format.open_memmap(out/(role+'_fine.npy'),mode='w+',dtype='float16',shape=(n,24,45,80)),
                    context=np.lib.format.open_memmap(out/(role+'_context.npy'),mode='w+',dtype='float16',shape=(n,48,23,40)),labels=[])
        at=0
        with torch.inference_mode():
            for source in sources:
                assert sha(source['path'])==source['sha256'],'Changed generated source'
                with h5py.File(source['path'],'r')as h:
                    assert h.attrs['role']==role and not bool(h.attrs['teacher_actions'])
                    for start in range(0,len(h['rgb']),24):
                        rgb=np.asarray(h['rgb'][start:start+24]);image=torch.from_numpy(rgb).permute(0,3,1,2).cuda()
                        fine,context=spatial.encode_spatial(runtime.model.backbone,image);end=at+len(rgb)
                        arrays['fine'][at:end]=fine.half().cpu().numpy();arrays['context'][at:end]=context.half().cpu().numpy();at=end
                    arrays['labels'].extend(json.loads(s)for s in h['labels'])
                provenance.append(dict(path=source['path'],sha256=source['sha256'],role=role,world_seed=source['world_seed']))
        assert at==n
        for k in ['fine','context']:arrays[k].flush()
        save(out/(role+'_labels.json'),arrays['labels']);result[role]=arrays
    save(out/'consumed_sources.json',dict(entries=provenance,heldout_images_used=False,tidewater_images_used=False,
        pose_checkpoint_sha256=sha(BUNDLE/'pose.pt'),parent_spatial_sha256=sha(BUNDLE/'spatial_acquisition.pt')))
    return result

@torch.inference_mode()
def evaluate(model,data):
    model.eval();matched=0;total=0;targets_known=0;wrong_known=0
    samples=[];candidate_predictions=0;unmatched_high_identity=[]
    for start in range(0,len(data['labels']),32):
        fine=torch.from_numpy(np.array(data['fine'][start:start+32])).cuda().float()
        context=torch.from_numpy(np.array(data['context'][start:start+32])).cuda().float()
        output={k:v.cpu()for k,v in model(fine,context).items()};decoded=decode(output,minimum_presence=.7)
        for frame,predictions in zip(data['labels'][start:start+32],decoded):
            boats=[p for p in predictions if p['boat']];candidate_predictions+=len(boats);used=set()
            for inst in frame['instances']:
                if not inst['boat']:continue
                box=np.array(inst['bbox'],float);center=(box[:2]+box[2:])/2;diag=np.linalg.norm(box[2:]-box[:2])
                total+=1
                candidates=[(np.linalg.norm(np.array(p['pixel'])-center),i,p)for i,p in enumerate(boats)if i not in used]
                best=min(candidates,key=lambda r:r[0])if candidates else None
                good=best is not None and best[0]<=max(8.,.25*diag)
                if good:matched+=1;used.add(best[1])
                if inst['identity']>=0:
                    targets_known+=int(inst['identity']==1);wrong_known+=int(inst['identity']==0)
                    samples.append(dict(truth=inst['identity'],matched=good,
                        probability=best[2]['target_probability']if good else 0.,
                        visible_pixels=inst['pixels'],bbox_long_px=float(max(box[2:]-box[:2]))))
            unmatched_high_identity.extend(p['target_probability']for i,p in enumerate(boats)if i not in used)
    operating=[]
    for threshold in [.8,.9,.95,.98,.99,.995]:
        accepted=sum(s['truth']==1 and s['matched']and s['probability']>=threshold for s in samples)
        wrong=sum(s['truth']==0 and s['matched']and s['probability']>=threshold for s in samples)
        background=sum(p>=threshold for p in unmatched_high_identity)
        operating.append(dict(threshold=threshold,target_recall=accepted/max(targets_known,1),
            wrong_boat_acceptances=wrong,unmatched_target_acceptances=background))
    usable=[p for p in operating if p['threshold']>=.98 and p['wrong_boat_acceptances']==0 and p['unmatched_target_acceptances']==0]
    best=max(usable,key=lambda p:p['target_recall'])if usable else None
    value=dict(boat_instances=total,matched_boats=matched,boat_recall=matched/max(total,1),
        known_target_instances=targets_known,known_wrong_boat_instances=wrong_known,candidate_predictions=candidate_predictions,
        operating_points=operating,selected_operating_point=best,
        expert_gate_passed=best is not None and best['target_recall']>=.8 and matched/max(total,1)>=.65)
    value['score']=(1-value['boat_recall'])*100+(1-(best['target_recall']if best else 0))*100
    value['calibration_samples']=samples
    return value

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);p.add_argument('--epochs',type=int,default=30);a=p.parse_args()
    out=ROOT/a.output;out.mkdir(exist_ok=False);begin=time.monotonic();torch.set_num_threads(2);torch.manual_seed(910422)
    manifest=json.loads((ROOT/a.manifest).read_text());assert manifest['status']=='completed'
    pkg=types.ModuleType('discrimination_training_parent');pkg.__path__=[str(BUNDLE/'code/landing_training')];sys.modules[pkg.__name__]=pkg
    r=importlib.import_module(pkg.__name__+'.radio_robust_20261015.runtime');config=json.loads((BUNDLE/'policy.json').read_text())
    runtime=r.RadioRobustRuntime(BUNDLE/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
    save(out/'state.json',dict(stage='feature_cache',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    data=prepare(manifest,out,runtime);model=Discriminator().cuda();model.initialize_shared(runtime.acquisition)
    del runtime;torch.cuda.empty_cache();optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
    rng=np.random.default_rng(910422);best=float('inf');stale=0;history=[]
    for epoch in range(1,a.epochs+1):
        model.train();order=rng.permutation(len(data['training']['labels']));losses=[];conflicts=0
        for start in range(0,len(order),32):
            ix=order[start:start+32];labels=[data['training']['labels'][i]for i in ix]
            heat,points,n=targets(labels);conflicts+=n
            fine=torch.from_numpy(np.array(data['training']['fine'][ix])).cuda().float()
            context=torch.from_numpy(np.array(data['training']['context'][ix])).cuda().float()
            value=loss(model(fine,context),torch.from_numpy(heat).cuda(),torch.from_numpy(points).cuda())
            assert torch.isfinite(value),'Nonfinite training loss'
            optimizer.zero_grad(set_to_none=True);value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3.);optimizer.step();losses.append(float(value.detach()))
        metrics=evaluate(model,data['validation']);calibration=metrics.pop('calibration_samples')
        item=dict(epoch=epoch,loss=float(np.mean(losses)),wall_s=time.monotonic()-begin,unresolved_cell_conflicts=conflicts,**metrics)
        history.append(item);checkpoint=dict(schema='mujoco.target_discriminator.v1',model=model.state_dict(),epoch=epoch,validation=metrics,
            parent_pose_sha256=sha(BUNDLE/'pose.pt'),parent_spatial_sha256=sha(BUNDLE/'spatial_acquisition.pt'),
            tidewater_images_used=False,heldout_images_used=False,teacher_actions_used=False)
        path=out/f'epoch_{epoch:03d}.pt';torch.save(checkpoint,path)
        if metrics['score']<best:
            best=metrics['score'];stale=0;torch.save(checkpoint,out/'best.pt');save(out/'best_calibration_samples.json',calibration)
        else:stale+=1
        save(out/'history.json',history);save(out/'state.json',dict(stage='training',**item));print('EPOCH',json.dumps(item),flush=True)
        if epoch>=12 and stale>=6:break
    saved=torch.load(out/'best.pt',map_location='cpu',weights_only=False)
    result=dict(status='completed',epochs=len(history),selected_epoch=saved['epoch'],validation=saved['validation'],
        checkpoint_sha256=sha(out/'best.pt'),wall_s=time.monotonic()-begin,
        scope='Perception-only bootstrap for observable expert; not a promoted policy or a teacher-flight dataset.')
    save(out/'result.json',result);save(out/'state.json',dict(stage='completed',**result));print('RESULT',json.dumps(result),flush=True)

if __name__=='__main__':main()
