"""Resume validated features/epoch1; repair NumPy JSON scalar serialization.

The old optimizer was not checkpointed. This is an explicitly recorded AdamW
warm restart from epoch1 weights, not an exact optimizer-state continuation.
"""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import hashlib,json,time
import numpy as np,torch
import train_discriminator as core
from target_learning.discriminator import Discriminator
ROOT=Path(__file__).resolve().parent

def clean(v):
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,np.ndarray):return v.tolist()
    if isinstance(v,dict):return {str(k):clean(x)for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [clean(x)for x in v]
    return v

def save(p,v):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(clean(v),indent=2,allow_nan=False));tmp.replace(p)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    torch.set_num_threads(2);torch.manual_seed(910422);out=ROOT/'perception_training_v4';out.mkdir(exist_ok=False)
    cache=ROOT/'perception_training_v3';parent=cache/'epoch_001.pt';begin=time.monotonic()
    checkpoint=torch.load(parent,map_location='cuda',weights_only=False)
    assert checkpoint['epoch']==1 and checkpoint['schema']=='mujoco.target_discriminator.v1'
    model=Discriminator().cuda();model.load_state_dict(checkpoint['model']);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4)
    data={}
    for role in ['training','validation']:
        data[role]=dict(fine=np.load(cache/(role+'_fine.npy'),mmap_mode='r'),context=np.load(cache/(role+'_context.npy'),mmap_mode='r'),
                        labels=json.loads((cache/(role+'_labels.json')).read_text()))
        assert len(data[role]['fine'])==len(data[role]['context'])==len(data[role]['labels'])
    source=json.loads((cache/'consumed_sources.json').read_text());assert not source['heldout_images_used']and not source['tidewater_images_used']
    save(out/'provenance.json',dict(resumed_checkpoint=str(parent),resumed_checkpoint_sha256=sha(parent),
        feature_cache=str(cache),feature_cache_sources=source,optimizer_state='Warm-restarted AdamW because previous checkpoint did not save optimizer; epoch1 weights preserved.',
        previous_failure='np.bool_ in calibration sample JSON; loss/model checkpoint completed successfully before serialization failure.',
        no_recollection=True,heldout_images_used=False,tidewater_images_used=False,
        source_hashes={n:sha(ROOT/n)for n in ['train_discriminator.py','train_discriminator_v4.py','target_learning/discriminator.py']}))
    # Restore the epoch1 data-order generator's consumed permutation.
    rng=np.random.default_rng(910422);rng.permutation(len(data['training']['labels']))
    best=float(checkpoint['validation']['score']);stale=0;history=[dict(epoch=1,source='preserved epoch1 before JSON failure',**clean(checkpoint['validation']))]
    torch.save(checkpoint,out/'best.pt')
    save(out/'state.json',dict(stage='training',resume_epoch=1,started_wall_s=time.time()))
    for epoch in range(2,31):
        model.train();order=rng.permutation(len(data['training']['labels']));losses=[];conflicts=0
        for start in range(0,len(order),32):
            ix=order[start:start+32];heat,points,n=core.targets([data['training']['labels'][i]for i in ix]);conflicts+=n
            fine=torch.from_numpy(np.array(data['training']['fine'][ix])).cuda().float()
            context=torch.from_numpy(np.array(data['training']['context'][ix])).cuda().float()
            loss=core.loss(model(fine,context),torch.from_numpy(heat).cuda(),torch.from_numpy(points).cuda())
            assert torch.isfinite(loss),'Nonfinite head loss'
            optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3.);optimizer.step();losses.append(float(loss.detach()))
        metrics=core.evaluate(model,data['validation']);calibration=metrics.pop('calibration_samples');metrics=clean(metrics)
        item=dict(epoch=epoch,loss=float(np.mean(losses)),wall_s=time.monotonic()-begin,unresolved_cell_conflicts=conflicts,**metrics);history.append(item)
        checkpoint=dict(schema='mujoco.target_discriminator.v1',model=model.state_dict(),epoch=epoch,validation=metrics,
            parent_pose_sha256=source['pose_checkpoint_sha256'],parent_spatial_sha256=source['parent_spatial_sha256'],
            tidewater_images_used=False,heldout_images_used=False,teacher_actions_used=False,
            optimizer=optimizer.state_dict(),numpy_rng_state=rng.bit_generator.state,torch_rng_state=torch.get_rng_state(),
            resume_provenance_sha256=sha(out/'provenance.json'))
        torch.save(checkpoint,out/f'epoch_{epoch:03d}.pt')
        if metrics['score']<best:
            best=metrics['score'];stale=0;torch.save(checkpoint,out/'best.pt');save(out/'best_calibration_samples.json',calibration)
        else:stale+=1
        save(out/'history.json',history);save(out/'state.json',dict(stage='training',**item));print('EPOCH',json.dumps(clean(item)),flush=True)
        if epoch>=12 and stale>=6:break
    selected=torch.load(out/'best.pt',map_location='cpu',weights_only=False)
    result=dict(status='completed',epochs=history[-1]['epoch'],selected_epoch=selected['epoch'],validation=clean(selected['validation']),
        checkpoint_sha256=sha(out/'best.pt'),wall_s=time.monotonic()-begin,
        scope='Perception-only bootstrap, not promoted and not a teacher-flight dataset',resume='epoch1 weights, warm-restarted optimizer')
    save(out/'result.json',result);save(out/'state.json',dict(stage='completed',**result));print('RESULT',json.dumps(result),flush=True)

if __name__=='__main__':main()
