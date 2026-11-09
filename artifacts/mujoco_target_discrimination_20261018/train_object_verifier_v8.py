"""Train whole-object verification on preserved MuJoCo data only.

Frozen V6 proposals are used for actual validation; ground-truth jittered boxes
are additional TRAINING-only examples. Final held-out worlds remain untouched.
"""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,time
import numpy as np,torch
from torch.nn import functional as F
from target_learning.discriminator_v5 import Discriminator,decode
from target_learning.object_verifier import ObjectVerifier,regions,verify
from train_discriminator_v4 import save,sha
ROOT=Path(__file__).resolve().parent


def matched(p,instances):
    x,y=p['pixel'];options=[]
    for j,i in enumerate(instances):
        a,b,c,d=i['bbox'];margin=max(2.,.08*max(c-a,d-b))
        if a-margin<=x<=c+margin and b-margin<=y<=d+margin:options.append(((c-a)*(d-b),j))
    return min(options)[1]if options else None


def class_label(p,inst):
    if inst is None:return 0  # Background is not the designated boat.
    identity=inst['identity']
    if identity==-2:return -100
    if identity<0:return 2
    center=np.asarray(p['pixel']);size=np.asarray(p['size_px'])*1.5;lo=center-size/2;hi=center+size/2
    a,b,c,d=inst['bbox'];intersection=max(0.,min(c,hi[0])-max(a,lo[0]))*max(0.,min(d,hi[1])-max(b,lo[1]))
    # Missing structural context cannot inherit the identity of a full-box
    # annotation. This label uses the rendered object extent offline only.
    if intersection/((c-a)*(d-b))<.9:return 2
    if identity==1 and inst.get('pad_pixel')is not None:
        pad=np.asarray(inst['pad_pixel'])
        if np.any(pad<lo)or np.any(pad>hi):return 2
    return int(identity)


@torch.inference_mode()
def prepare(head,data,role,out,rng):
    features=[];metas=[];classes=[];frames=[]
    for start in range(0,len(data['labels']),32):
        fine=torch.from_numpy(np.array(data['fine'][start:start+32])).cuda().float()
        context=torch.from_numpy(np.array(data['context'][start:start+32])).cuda().float()
        predictions=decode({k:v.cpu()for k,v in head(fine,context).items()},minimum_presence=.2,topk=24)
        boxes=[];indices=[];labels=[]
        for b,(frame,pred)in enumerate(zip(data['labels'][start:start+32],predictions)):
            frames.append(dict(label=frame,predictions=pred))
            for p in pred:
                j=matched(p,frame['instances']);inst=frame['instances'][j]if j is not None else None
                boxes.append([*p['pixel'],*p['size_px']]);indices.append(b);labels.append(class_label(p,inst))
            if role=='training':
                for inst in frame['instances']:
                    box=np.asarray(inst['bbox'],float);center=(box[:2]+box[2:])/2;size=box[2:]-box[:2]
                    # Include known true/false/ambiguous objects missed by the
                    # detector, without validation ground-truth proposals.
                    for repeat in range(2 if inst['identity']==1 else 1):
                        p=dict(pixel=(center+rng.uniform(-.08,.08,2)*size).tolist(),size_px=(size*rng.uniform(.9,1.15,2)).tolist())
                        boxes.append([*p['pixel'],*p['size_px']]);indices.append(b);labels.append(class_label(p,inst))
        if boxes:
            f,m=regions(fine,context,boxes,indices);features.append(f.half().cpu().numpy());metas.append(m.cpu().numpy());classes.extend(labels)
    result=dict(features=np.concatenate(features),meta=np.concatenate(metas),classes=np.array(classes,dtype=np.int64),frames=frames)
    for name in ['features','meta','classes']:np.save(out/(role+'_'+name+'.npy'),result[name])
    save(out/(role+'_frames.json'),frames);return result


@torch.inference_mode()
def evaluate(model,data):
    model.eval();probs=[]
    for start in range(0,len(data['features']),512):
        p=model(torch.from_numpy(data['features'][start:start+512]).cuda().float(),torch.from_numpy(data['meta'][start:start+512]).cuda().float()).softmax(-1)
        probs.extend(p.cpu().tolist())
    at=0;known=sum(i['identity']==1 for f in data['frames']for i in f['label']['instances']);objects=sum(len(f['label']['instances'])for f in data['frames']);matched_count=0
    frame_rows=[]
    for f in data['frames']:
        seen=set();rows=[]
        for p in f['predictions']:
            prob=probs[at];at+=1;j=matched(p,f['label']['instances'])
            if j is not None:seen.add(j)
            rows.append((p,j,prob))
        matched_count+=len(seen);frame_rows.append((f['label']['instances'],rows))
    assert at==len(probs)
    unscored_instances=sum(i['identity']==-2 for f in data['frames']for i in f['label']['instances'])
    unscored_assertions=sum(j is not None and instances[j]['identity']==-2 and prob[1]>=.98 for instances,rows in frame_rows for p,j,prob in rows)
    operating=[]
    for heat in [.2,.3,.4]:
        for threshold in [.9,.95,.98,.99,.995]:
            true=wrong=unknown=background=duplicate=0
            for instances,rows in frame_rows:
                seen=set()
                for p,j,prob in rows:
                    if p['presence']<heat or prob[1]<threshold:continue
                    if j is None:background+=1;continue
                    inst=instances[j]
                    if inst['identity']==0:wrong+=1
                    elif inst['identity']==-2:continue
                    elif inst['identity']<0:unknown+=1
                    elif j not in seen:true+=1;seen.add(j)
                    else:duplicate+=1
            operating.append(dict(heat=heat,identity=threshold,support=.8,target_recall=true/max(known,1),accepted_true_objects=true,
                wrong_object_acceptances=wrong,ambiguous_acceptances=unknown,background_acceptances=background,duplicate_target_peaks=duplicate))
    safe=[p for p in operating if p['identity']>=.98 and p['wrong_object_acceptances']==p['ambiguous_acceptances']==p['background_acceptances']==0]
    best=max(safe,key=lambda p:p['target_recall'])if safe else None
    diagnostic=min(operating,key=lambda p:100*(p['wrong_object_acceptances']+p['background_acceptances'])+10*p['ambiguous_acceptances']+100*(1-p['target_recall']))
    chosen=best or diagnostic
    score=100*(chosen['wrong_object_acceptances']+chosen['background_acceptances'])+10*chosen['ambiguous_acceptances']+100*(1-chosen['target_recall'])
    return dict(known_targets=known,unscored_old_target_instances=unscored_instances,unscored_old_target_assertions_at_point98=unscored_assertions,object_instances=objects,object_recall=matched_count/max(objects,1),operating_points=operating,
        selected_operating_point=best,diagnostic_best_effort=diagnostic,score=score,
        expert_gate_passed=best is not None and best['target_recall']>=.8 and matched_count/max(objects,1)>=.65)


def main():
    torch.set_num_threads(2);torch.manual_seed(990424);begin=time.monotonic();out=ROOT/'perception_training_v8';out.mkdir(exist_ok=False)
    v6=ROOT/'perception_training_v6';v5=ROOT/'perception_training_v5';old=ROOT/'perception_training_v3';parent=v6/'best.pt'
    saved=torch.load(parent,map_location='cuda',weights_only=False);head=Discriminator().cuda();head.load_state_dict(saved['model']);head.eval();rng=np.random.default_rng(990424);data={}
    save(out/'state.json',dict(stage='proposal_feature_cache'))
    for role in ['training','validation']:
        old_labels=json.loads((v6/(role+'_effective_labels.json')).read_text())
        old_count=len(np.load(old/(role+'_fine.npy'),mmap_mode='r'))
        old_labels=old_labels[:old_count]
        # Old images lack preserved visible-part segmentation. Do not pretend
        # their conservative 'unknown' labels prove a partial view is blind.
        # Keep clear positive/negative labels; score uncertain old TRUE targets
        # explicitly as unscored. New semantic visibility labels remain scored.
        for frame in old_labels:
            for inst in frame['instances']:
                if inst['annotation_instance']=='target'and inst['identity']<0:inst['identity']=-2
        import h5py
        context_manifest=json.loads((ROOT/'perception_context_dataset_v8/manifest.json').read_text())
        new_by_seed={}
        for entry in context_manifest['entries']:
            if entry['role']!=role:continue
            with h5py.File(entry['path'],'r')as h:new_by_seed[entry['world_seed']]=[json.loads(v)for v in h['labels']]
        prior_new=json.loads((v5/(role+'_labels.json')).read_text())
        new_labels=[new_by_seed[frame['world_seed']][frame['index']]for frame in prior_new]
        labels=old_labels+new_labels
        save(out/(role+'_effective_labels.json'),labels)
        source=dict(labels=labels,
            fine=np.concatenate([np.load(old/(role+'_fine.npy'),mmap_mode='r'),np.load(v5/(role+'_fine.npy'),mmap_mode='r')]),
            context=np.concatenate([np.load(old/(role+'_context.npy'),mmap_mode='r'),np.load(v5/(role+'_context.npy'),mmap_mode='r')]))
        data[role]=prepare(head,source,role,out,rng);del source
    save(out/'provenance.json',dict(frozen_detector_sha256=sha(parent),source_sha256=sha(__file__),verifier_source_sha256=sha(ROOT/'target_learning/object_verifier.py'),
        normalized_labels_sha256={role:sha(out/(role+'_effective_labels.json'))for role in data},semantic_dataset_manifest_sha256=sha(ROOT/'perception_context_dataset_v8/manifest.json'),old_uncertain_true_target_proposals_ignored=True,unscored_training_proposals=int(sum(data['training']['classes']<0)),unscored_validation_proposals=int(sum(data['validation']['classes']<0)),
        teacher_actions_used=False,tidewater_used=False,heldout_used=False,training_true_boxes_added=True,validation_true_boxes_added=False,
        samples={r:len(d['classes'])for r,d in data.items()},classes={r:np.bincount(d['classes'][d['classes']>=0],minlength=3).tolist()for r,d in data.items()}))
    del head;torch.cuda.empty_cache();model=ObjectVerifier().cuda();warm=torch.load(ROOT/'perception_training_v7/best.pt',map_location='cuda',weights_only=False);model.load_state_dict(warm['verifier']);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-3)
    train=data['training'];counts=np.bincount(train['classes'][train['classes']>=0],minlength=3);weights=np.sqrt(counts.sum()/np.maximum(counts,1));weights/=weights.mean();weights=torch.tensor(weights,dtype=torch.float32,device='cuda')
    best=float('inf');stale=0;history=[]
    for epoch in range(1,51):
        model.train();order=rng.permutation(len(train['classes']));losses=[]
        for start in range(0,len(order),256):
            ix=order[start:start+256];x=torch.from_numpy(train['features'][ix]).cuda().float();m=torch.from_numpy(train['meta'][ix]).cuda().float();y=torch.from_numpy(train['classes'][ix]).cuda()
            value=F.cross_entropy(model(x,m),y,weight=weights);assert torch.isfinite(value)
            optimizer.zero_grad(set_to_none=True);value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3.);optimizer.step();losses.append(float(value.detach()))
        metrics=evaluate(model,data['validation']);history.append(dict(epoch=epoch,loss=float(np.mean(losses)),wall_s=time.monotonic()-begin,**metrics))
        ck=dict(schema='mujoco.target_discriminator.v7',model=saved['model'],verifier=model.state_dict(),epoch=epoch,validation=metrics,
            optimizer=optimizer.state_dict(),numpy_rng_state=rng.bit_generator.state,torch_rng_state=torch.get_rng_state(),
            parent_pose_sha256=saved['parent_pose_sha256'],parent_spatial_sha256=saved['parent_spatial_sha256'],frozen_detector_sha256=sha(parent),
            tidewater_images_used=False,heldout_images_used=False,teacher_actions_used=False,provenance_sha256=sha(out/'provenance.json'))
        torch.save(ck,out/f'epoch_{epoch:03d}.pt')
        if metrics['score']<best:best=metrics['score'];stale=0;torch.save(ck,out/'best.pt')
        else:stale+=1
        save(out/'history.json',history);save(out/'state.json',dict(stage='training',**history[-1]));print(json.dumps(dict(epoch=epoch,loss=history[-1]['loss'],selected=metrics['selected_operating_point'],diagnostic=metrics['diagnostic_best_effort'])),flush=True)
        if epoch>=20 and stale>=10:break
    ck=torch.load(out/'best.pt',map_location='cpu',weights_only=False);result=dict(status='completed',checkpoint_sha256=sha(out/'best.pt'),selected_epoch=ck['epoch'],validation=ck['validation'],wall_s=time.monotonic()-begin)
    save(out/'result.json',result);save(out/'state.json',dict(stage='completed',**result));print(json.dumps({k:v for k,v in result.items()if k!='validation'}),flush=True)

if __name__=='__main__':main()
