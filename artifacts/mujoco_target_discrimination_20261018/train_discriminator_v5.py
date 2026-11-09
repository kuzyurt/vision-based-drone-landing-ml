"""Reuse preserved features, add hard MuJoCo negatives and support supervision."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import copy,importlib,json,sys,time,types
import numpy as np,torch
from torch.nn import functional as F
import train_discriminator as core
from train_discriminator_v4 import save,sha
from target_learning.discriminator_v5 import Discriminator,decode
ROOT=Path(__file__).resolve().parent


def refine(labels):
    labels=copy.deepcopy(labels)
    for frame in labels:
        for inst in frame['instances']:
            b=inst['bbox'];context=b[0]>=2 and b[1]>=2 and b[2]<=638 and b[3]<=358 and inst['pixels']>=128 and max(b[2]-b[0],b[3]-b[1])>=24
            # Original decoys are distinguishable at the declared context size;
            # true target retains its earlier visible-marker support rule.
            support=context and inst['identity']>=0
            if not support:inst['identity']=-1
            inst['identity_support']=float(support)
            inst['boat']=True  # Potential objects; tiny type is not learnable.
    return labels


def targets(labels):
    heat,points,_=core.targets(labels);supports=[]
    for b,frame in enumerate(labels):
        used={}
        for inst in frame['instances']:
            box=np.array(inst['bbox'],float);center=(box[:2]+box[2:])/2;x,y=np.clip(np.floor(center/8).astype(int),[0,0],[79,44])
            if (x,y)in used:supports[used[x,y]][-1]=0.;continue
            used[x,y]=len(supports);supports.append([b,y,x,inst['identity_support'],1.])
    return heat,points,np.array(supports,dtype=np.float32).reshape(-1,5)


def loss(output,heat,points,support):
    value=core.loss(output,heat,points)
    p=support[support[:,-1]>.5]
    if len(p):
        b,y,x=p[:,:3].long().T
        value=value+2*F.binary_cross_entropy_with_logits(output['support'][b,0,y,x],p[:,3])
    background=heat.max(1).values<.05
    if background.any():
        value=value+.1*F.softplus(output['support'][:,0][background]).mean()
    return value


@torch.inference_mode()
def evaluate(model,data):
    model.eval();frames=[];known=0;objects=0;matched=0;predictions=0
    for start in range(0,len(data['labels']),32):
        fine=torch.from_numpy(np.array(data['fine'][start:start+32])).cuda().float()
        context=torch.from_numpy(np.array(data['context'][start:start+32])).cuda().float()
        decoded=decode({k:v.cpu()for k,v in model(fine,context).items()},minimum_presence=.2)
        for label,pred in zip(data['labels'][start:start+32],decoded):
            instances=label['instances'];assign=[];seen=set();known+=sum(p['identity']==1 for p in instances);objects+=len(instances);predictions+=len(pred)
            for p in pred:
                x,y=p['pixel'];choices=[]
                for j,inst in enumerate(instances):
                    a,b,c,d=inst['bbox'];margin=max(2.,.08*max(c-a,d-b))
                    if a-margin<=x<=c+margin and b-margin<=y<=d+margin:
                        choices.append(((c-a)*(d-b),j))
                j=min(choices)[1]if choices else None
                if j is not None:seen.add(j)
                assign.append(j)
            matched+=len(seen);frames.append((instances,pred,assign))
    operating=[]
    for heat in [.2,.3,.4]:
        for identity in [.98,.995]:
            for support in [.8,.9,.95,.98]:
                true=wrong=unknown=background=duplicate=0;pad_errors=[]
                for instances,pred,assign in frames:
                    accepted=set()
                    for p,j in zip(pred,assign):
                        if p['presence']<heat or p['target_probability']<identity or p['identity_support_probability']<support:continue
                        if j is None:background+=1;continue
                        inst=instances[j]
                        if inst['identity']==0:wrong+=1
                        elif inst['identity']<0:unknown+=1
                        elif j not in accepted:
                            true+=1;accepted.add(j)
                            if inst.get('pad_pixel')is not None:pad_errors.append(float(np.linalg.norm(np.array(p['pad_pixel'])-inst['pad_pixel'])))
                        else:duplicate+=1
                operating.append(dict(heat=heat,identity=identity,support=support,target_recall=true/max(known,1),
                    accepted_true_objects=true,wrong_object_acceptances=wrong,ambiguous_acceptances=unknown,
                    background_acceptances=background,duplicate_target_peaks=duplicate,
                    median_pad_error_px=float(np.median(pad_errors))if pad_errors else None))
    # Development calibration only, never a claim of fresh qualification.
    safe=[p for p in operating if p['wrong_object_acceptances']==0 and p['background_acceptances']==0 and p['ambiguous_acceptances']==0]
    best=max(safe,key=lambda p:p['target_recall'])if safe else None
    fallback=min(operating,key=lambda p:100*(p['wrong_object_acceptances']+p['background_acceptances'])+10*p['ambiguous_acceptances']+100*(1-p['target_recall']))
    selected=best or fallback
    score=100*(selected['wrong_object_acceptances']+selected['background_acceptances'])+10*selected['ambiguous_acceptances']+100*(1-selected['target_recall'])+10*(1-matched/max(objects,1))
    return dict(known_targets=known,object_instances=objects,matched_objects=matched,object_recall=matched/max(objects,1),
        candidate_predictions=predictions,operating_points=operating,selected_operating_point=best,
        diagnostic_best_effort=fallback,expert_gate_passed=best is not None and best['target_recall']>=.8 and matched/max(objects,1)>=.65,score=score)


def main():
    torch.set_num_threads(2);torch.manual_seed(990422);begin=time.monotonic();out=ROOT/'perception_training_v5';out.mkdir(exist_ok=False)
    manifest=json.loads((ROOT/'perception_hard_dataset_v5/manifest.json').read_text());assert manifest['status']=='completed'
    from target_learning.expert_adapter import load_parent
    module=load_parent(core.BUNDLE,'hard_perception_parent');c=json.loads((core.BUNDLE/'policy.json').read_text())
    runtime=module.RadioRobustRuntime(core.BUNDLE/'pose.pt',c['calibration'],c['slew_limits'],'cuda',allow_visual_landing=True)
    facade=types.SimpleNamespace(__package__=module.__package__,model=runtime.model)
    extra=core.prepare(manifest,out,facade);del runtime;torch.cuda.empty_cache();data={}
    cache=ROOT/'perception_training_v3'
    for role in ['training','validation']:
        labels=refine(json.loads((cache/(role+'_labels.json')).read_text()))
        data[role]=dict(fine=np.concatenate([np.load(cache/(role+'_fine.npy'),mmap_mode='r'),extra[role]['fine']]),
            context=np.concatenate([np.load(cache/(role+'_context.npy'),mmap_mode='r'),extra[role]['context']]),
            labels=labels+extra[role]['labels'])
        save(out/(role+'_effective_labels.json'),data[role]['labels'])
    parent=ROOT/'perception_training_v4/best.pt';checkpoint=torch.load(parent,map_location='cuda',weights_only=False)
    model=Discriminator().cuda();missing=model.load_state_dict(checkpoint['model'],strict=False)
    assert missing.missing_keys==['support.weight','support.bias']and not missing.unexpected_keys
    optimizer=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=1e-4);rng=np.random.default_rng(990422)
    save(out/'provenance.json',dict(parent_checkpoint_sha256=sha(parent),new_manifest_sha256=sha(ROOT/'perception_hard_dataset_v5/manifest.json'),
        old_cache_sources=json.loads((cache/'consumed_sources.json').read_text()),old_images_unchanged=True,
        hard_negative_images=1920,teacher_actions_used=False,tidewater_used=False,heldout_used=False,
        support_rule='Conservative visible marker plus unclipped object context; ambiguous identity ignored, support supervised zero.',
        source_hashes={name:sha(ROOT/name)for name in ['train_discriminator_v5.py','target_learning/discriminator_v5.py']}))
    best=float('inf');stale=0;history=[]
    for epoch in range(1,41):
        model.train();order=rng.permutation(len(data['training']['labels']));losses=[]
        for start in range(0,len(order),32):
            ix=order[start:start+32];heat,points,support=targets([data['training']['labels'][i]for i in ix])
            fine=torch.from_numpy(np.array(data['training']['fine'][ix])).cuda().float();context=torch.from_numpy(np.array(data['training']['context'][ix])).cuda().float()
            value=loss(model(fine,context),torch.from_numpy(heat).cuda(),torch.from_numpy(points).cuda(),torch.from_numpy(support).cuda())
            assert torch.isfinite(value);optimizer.zero_grad(set_to_none=True);value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3.);optimizer.step();losses.append(float(value.detach()))
        metrics=evaluate(model,data['validation']);item=dict(epoch=epoch,loss=float(np.mean(losses)),wall_s=time.monotonic()-begin,**metrics);history.append(item)
        ck=dict(schema='mujoco.target_discriminator.v5',model=model.state_dict(),epoch=epoch,validation=metrics,
            optimizer=optimizer.state_dict(),numpy_rng_state=rng.bit_generator.state,torch_rng_state=torch.get_rng_state(),
            parent_pose_sha256=checkpoint['parent_pose_sha256'],parent_spatial_sha256=checkpoint['parent_spatial_sha256'],
            teacher_actions_used=False,tidewater_images_used=False,heldout_images_used=False,provenance_sha256=sha(out/'provenance.json'))
        torch.save(ck,out/f'epoch_{epoch:03d}.pt')
        if metrics['score']<best:best=metrics['score'];stale=0;torch.save(ck,out/'best.pt')
        else:stale+=1
        save(out/'history.json',history);save(out/'state.json',dict(stage='training',**item))
        print(json.dumps(dict(epoch=epoch,loss=item['loss'],score=metrics['score'],selected=metrics['selected_operating_point'],diagnostic=metrics['diagnostic_best_effort'])),flush=True)
        if epoch>=16 and stale>=8:break
    ck=torch.load(out/'best.pt',map_location='cpu',weights_only=False)
    result=dict(status='completed',selected_epoch=ck['epoch'],checkpoint_sha256=sha(out/'best.pt'),validation=ck['validation'],wall_s=time.monotonic()-begin)
    save(out/'result.json',result);save(out/'state.json',dict(stage='completed',**result));print(json.dumps(result),flush=True)

if __name__=='__main__':main()
