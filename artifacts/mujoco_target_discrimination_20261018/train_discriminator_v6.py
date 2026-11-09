"""Consistent image-support labels across preserved MuJoCo datasets.

V5 mixed a nominal 12px marker-span rule with a visible-marker-pixel rule.
Use actual visible cyan marker evidence uniformly; never consume held-out RGB.
Shared-marker distractors have unavailable precise pad labels, not negative ones.
"""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import copy,json,time
import h5py,numpy as np,torch
import train_discriminator_v5 as previous
from train_discriminator_v4 import save,sha
from target_learning.discriminator_v5 import Discriminator
ROOT=Path(__file__).resolve().parent


def normalize(labels,sources):
    result=copy.deepcopy(labels);changes={'unknown_to_target':0,'target_to_unknown':0,'support_changes':0,'shared_marker_pad_labels_ignored':0}
    for frame in result:
        with h5py.File(sources[frame['world_seed']],'r')as h:rgb=np.asarray(h['rgb'][frame['index']])
        for inst in frame['instances']:
            box=inst['bbox'];x0,y0,x1,y1=box;context=x0>=2 and y0>=2 and x1<=638 and y1<=358 and inst['pixels']>=128 and max(x1-x0,y1-y0)>=24
            old=inst['identity'];name=inst['annotation_instance'];pad=inst.get('pad_pixel');evidence=None
            if name=='target':
                # Marker point is an annotation used ONLY to label rendered
                # images. It never reaches an actor/controller observation.
                if pad is not None and 0<=pad[0]<640 and 0<=pad[1]<360:
                    radius=max(3,int(.22*min(x1-x0,y1-y0)))
                    px,py=map(int,pad);patch=rgb[max(0,py-radius):min(360,py+radius+1),max(0,px-radius):min(640,px+radius+1)].astype(float)
                    cyan=(patch[...,1]>70)&(patch[...,2]>70)&(patch[...,1]>1.35*patch[...,0]+10)&(patch[...,2]>1.35*patch[...,0]+10)
                    evidence=int(cyan.sum())
                support=context and evidence is not None and evidence>=4
                identity=1 if support else -1
            elif name=='decoy_blank_clone':
                support=context and inst.get('marker_visible_pixels',0)>=4;identity=0 if support else -1
            else:
                support=context;identity=0 if support else -1
            inst['identity']=identity;inst['identity_support']=float(support);inst['boat']=True
            inst['visible_marker_evidence_pixels_annotation_only']=evidence
            if name in ['decoy_false_cross_boat','decoy_false_cross_board']:
                inst['pad_label_available']=False;changes['shared_marker_pad_labels_ignored']+=1
            else:inst['pad_label_available']=True
            changes['unknown_to_target']+=int(old<0 and identity==1);changes['target_to_unknown']+=int(old==1 and identity<0)
            changes['support_changes']+=int((old>=0)!=support)
    return result,changes


def targets(labels):
    heat,points,support=previous.targets(labels)
    # Core points retain instance order, including invalid same-cell conflicts.
    at=0
    for frame in labels:
        used=set()
        for inst in frame['instances']:
            box=np.array(inst['bbox'],float);center=(box[:2]+box[2:])/2;x,y=np.clip(np.floor(center/8).astype(int),[0,0],[79,44])
            if (x,y)in used:continue
            used.add((x,y))
            if not inst['pad_label_available']:
                points[at,11]=0.;points[at,10]=0.  # Ignore visibility and point loss.
            at+=1
    assert at==len(points)
    return heat,points,support


def main():
    torch.set_num_threads(2);torch.manual_seed(990423);begin=time.monotonic();out=ROOT/'perception_training_v6';out.mkdir(exist_ok=False)
    v5=ROOT/'perception_training_v5';assert(v5/'result.json').exists();old=ROOT/'perception_training_v3'
    sources={}
    for name in ['perception_dataset_v2','perception_hard_dataset_v5']:
        for e in json.loads((ROOT/name/'manifest.json').read_text())['entries']:
            if e['role']in ['training','validation']:sources[e['world_seed']]=e['path']
    data={};counts={}
    for role in ['training','validation']:
        labels=json.loads((old/(role+'_labels.json')).read_text())+json.loads((v5/(role+'_labels.json')).read_text())
        labels,counts[role]=normalize(labels,sources);save(out/(role+'_effective_labels.json'),labels)
        data[role]=dict(labels=labels,fine=np.concatenate([np.load(old/(role+'_fine.npy'),mmap_mode='r'),np.load(v5/(role+'_fine.npy'),mmap_mode='r')]),
            context=np.concatenate([np.load(old/(role+'_context.npy'),mmap_mode='r'),np.load(v5/(role+'_context.npy'),mmap_mode='r')]))
    save(out/'label_revision.json',dict(changes=counts,heldout_read=False,tidewater_read=False,
        rule='Uniform full object context plus >=4 actual cyan pixels near annotated marker. No nominal distance/span identity shortcut.',
        label_caution='Visible support heuristic for development; not a universal recognition range or guaranteed identifiable identity.'))
    parent=v5/'best.pt';saved=torch.load(parent,map_location='cuda',weights_only=False)
    model=Discriminator().cuda();model.load_state_dict(saved['model']);optimizer=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=1e-4)
    rng=np.random.default_rng(990423);best=float('inf');stale=0;history=[]
    save(out/'provenance.json',dict(parent_checkpoint_sha256=sha(parent),source_sha256=sha(__file__),
        model_source_sha256=sha(ROOT/'target_learning/discriminator_v5.py'),feature_cache_reused=True,original_rgb_unchanged=True,
        no_teacher_actions=True,no_tidewater=True,no_heldout=True,optimizer='Explicit warm restart for changed labels'))
    print(json.dumps(dict(label_revision=counts)),flush=True)
    for epoch in range(1,41):
        model.train();order=rng.permutation(len(data['training']['labels']));losses=[]
        for start in range(0,len(order),32):
            ix=order[start:start+32];heat,points,support=targets([data['training']['labels'][i]for i in ix])
            fine=torch.from_numpy(np.array(data['training']['fine'][ix])).cuda().float();context=torch.from_numpy(np.array(data['training']['context'][ix])).cuda().float()
            value=previous.loss(model(fine,context),torch.from_numpy(heat).cuda(),torch.from_numpy(points).cuda(),torch.from_numpy(support).cuda())
            assert torch.isfinite(value);optimizer.zero_grad(set_to_none=True);value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3.);optimizer.step();losses.append(float(value.detach()))
        metrics=previous.evaluate(model,data['validation']);item=dict(epoch=epoch,loss=float(np.mean(losses)),wall_s=time.monotonic()-begin,**metrics);history.append(item)
        ck=dict(schema='mujoco.target_discriminator.v5',model=model.state_dict(),epoch=epoch,validation=metrics,
            optimizer=optimizer.state_dict(),numpy_rng_state=rng.bit_generator.state,torch_rng_state=torch.get_rng_state(),
            parent_pose_sha256=saved['parent_pose_sha256'],parent_spatial_sha256=saved['parent_spatial_sha256'],
            teacher_actions_used=False,tidewater_images_used=False,heldout_images_used=False,provenance_sha256=sha(out/'provenance.json'))
        torch.save(ck,out/f'epoch_{epoch:03d}.pt')
        if metrics['score']<best:best=metrics['score'];stale=0;torch.save(ck,out/'best.pt')
        else:stale+=1
        save(out/'history.json',history);save(out/'state.json',dict(stage='training',**item))
        print(json.dumps(dict(epoch=epoch,loss=item['loss'],score=metrics['score'],selected=metrics['selected_operating_point'],diagnostic=metrics['diagnostic_best_effort'])),flush=True)
        if epoch>=16 and stale>=8:break
    ck=torch.load(out/'best.pt',map_location='cpu',weights_only=False)
    result=dict(status='completed',selected_epoch=ck['epoch'],checkpoint_sha256=sha(out/'best.pt'),validation=ck['validation'],wall_s=time.monotonic()-begin)
    save(out/'result.json',result);save(out/'state.json',dict(stage='completed',**result));print(json.dumps({k:v for k,v in result.items()if k!='validation'}),flush=True)

if __name__=='__main__':main()
