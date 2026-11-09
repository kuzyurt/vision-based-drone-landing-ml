"""Frozen-backbone cache + true consumer mask gradients; no optimizer/training."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import hashlib,importlib,json,sys,time,types,subprocess
import h5py,numpy as np,torch
from torch.nn import functional as F
ROOT=Path(__file__).resolve().parent;BUNDLE=ROOT.parents[1]/'landing_hardening_20261018T011610Z/candidate_r15';DATA=ROOT/'original_rgb_admission/v1';OUT=ROOT/'feature_cache/original_v1'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def classes():
    name='approved_visual_backbone';pkg=types.ModuleType(name);pkg.__path__=[str(BUNDLE/'code/landing_training')];sys.modules[name]=pkg
    return importlib.import_module(name+'.radio_robust_20261015.model').RadioRobustPoseModel,importlib.import_module(name+'.radio_robust_20261015.spatial_acquisition')
def spatial_loss(model,fine,context,labels):
    heat,offset,presence=model(fine,context);visible=labels[:,0]>.5;h,w=heat.shape[-2:];column=(labels[:,1]/640*w).floor().long().clamp(0,w-1);row=(labels[:,2]/360*h).floor().long().clamp(0,h-1);cell=row*w+column
    loss=F.binary_cross_entropy_with_logits(presence,labels[:,0]);local_target=torch.stack((labels[:,1]/640*w-column-.5,labels[:,2]/360*h-row-.5),1);local=offset.flatten(2)[torch.arange(len(labels),device=fine.device),:,cell]
    if visible.any():loss=loss+F.cross_entropy(heat[visible].flatten(1),cell[visible])+4*F.smooth_l1_loss(local[visible],local_target[visible])
    return loss
@torch.inference_mode()
def evaluate(model,spatial,data,labels,role):
    ix=np.flatnonzero((labels[:,3]>.5)==(role=='validation'));pred=[];prob=[]
    for s in range(0,len(ix),96):
        take=ix[s:s+96];a=torch.from_numpy(np.array(data['fine'][take])).cuda().float();b=torch.from_numpy(np.array(data['context'][take])).cuda().float();logit,pixel=spatial.decode_spatial(model(a,b));pred.extend(pixel.cpu().tolist());prob.extend(logit.sigmoid().cpu().tolist())
    lab=labels[ix];visible=lab[:,0]>.5;err=np.linalg.norm(np.asarray(pred)-lab[:,1:3],axis=1);p=np.asarray(prob)
    return dict(frames=len(ix),visible=int(visible.sum()),negative=int((~visible).sum()),pixel_rms=float(np.sqrt(np.mean(err[visible]**2))),median_pixel_error=float(np.median(err[visible])),p90_pixel_error=float(np.percentile(err[visible],90)),recall_at_08=float((p[visible]>=.8).mean()),false_positive_at_08=float((p[~visible]>=.8).mean()),score=float(np.sqrt(np.mean(err[visible]**2)))+100*float((p[~visible]>=.8).mean())+30*(1-float((p[visible]>=.8).mean())))
def main():
    receipt=json.loads((DATA/'receipt.json').read_text());assert receipt['status']=='passed_original_visual_derivatives'and sha(DATA/'data.h5')==receipt['data_sha256'];assert sha(DATA/'records.json')==receipt['records_sha256']
    free=float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0]);assert free>4096
    torch.set_num_threads(1);torch.cuda.set_per_process_memory_fraction(.12);OUT.mkdir(parents=True,exist_ok=False);start=time.monotonic();Pose,spatial=classes();backbone=Pose().cuda();backbone.load_state_dict(torch.load(BUNDLE/'pose.pt',map_location='cuda',weights_only=False)['model']);backbone.eval()
    with h5py.File(DATA/'data.h5','r')as h:
        n=len(h['rgb']);labels=np.asarray(h['labels']);fine=np.lib.format.open_memmap(OUT/'fine.npy',mode='w+',dtype='float16',shape=(n,24,45,80));context=np.lib.format.open_memmap(OUT/'context.npy',mode='w+',dtype='float16',shape=(n,48,23,40))
        with torch.inference_mode():
            for s in range(0,n,16):
                images=torch.from_numpy(h['rgb'][s:s+16]).permute(0,3,1,2).cuda();f,c=spatial.encode_spatial(backbone.backbone,images);fine[s:s+len(images)]=f.half().cpu().numpy();context[s:s+len(images)]=c.half().cpu().numpy()
                if s%320==0:(OUT/'state.json').write_text(json.dumps(dict(status='frozen_feature_extraction',frames=min(n,s+16),total=n,elapsed_s=time.monotonic()-start)))
        fine.flush();context.flush();np.save(OUT/'labels.npy',labels)
    del backbone;torch.cuda.empty_cache();head=spatial.SpatialAcquisition().cuda();head.load_state_dict(torch.load(BUNDLE/'spatial_acquisition.pt',map_location='cuda',weights_only=False)['model']);head.eval();baseline=evaluate(head,spatial,dict(fine=fine,context=context),labels,'validation')
    # Test the actual training loss on admitted real cached examples, not a
    # disconnected helper. Negative locations must never influence gradients.
    pos=np.flatnonzero(labels[:,0]>.5)[:4];neg=np.flatnonzero(labels[:,0]<.5)[:4];ix=np.r_[pos,neg];x=torch.from_numpy(np.array(fine[ix])).cuda().float();c=torch.from_numpy(np.array(context[ix])).cuda().float();y=torch.tensor(labels[ix],device='cuda');head.zero_grad();loss=spatial_loss(head,x,c,y);loss.backward();g=[p.grad.detach().clone()for p in head.parameters()if p.grad is not None]
    y2=y.clone();y2[4:,1:3]=1e6;head.zero_grad();loss2=spatial_loss(head,x,c,y2);loss2.backward();g2=[p.grad.detach().clone()for p in head.parameters()if p.grad is not None];assert torch.equal(loss.detach(),loss2.detach())and all(torch.equal(a,b)for a,b in zip(g,g2));assert sum(v.abs().sum().item()for v in g)>0
    report=dict(status='frozen_original_feature_cache_and_consumer_passed',frames=len(labels),baseline_validation=baseline,parent_pose_sha256=sha(BUNDLE/'pose.pt'),parent_spatial_sha256=sha(BUNDLE/'spatial_acquisition.pt'),raw_rgb_cache_sha256=receipt['data_sha256'],source_sha256=sha(__file__),real_masked_targets_do_not_change_loss_or_gradients=True,valid_visual_targets_produce_gradients=True,optimizer_steps=0,features={name:sha(OUT/(name+'.npy'))for name in ['fine','context','labels']},elapsed_s=time.monotonic()-start)
    (OUT/'receipt.json').write_text(json.dumps(report,indent=2));(OUT/'state.json').write_text(json.dumps(report,indent=2));(ROOT/'original_consumer_validation_receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
