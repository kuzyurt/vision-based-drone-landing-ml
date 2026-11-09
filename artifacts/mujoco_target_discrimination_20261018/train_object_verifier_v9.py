"""Exact-CAD marker pairs and a measured conservative visibility envelope."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,time,types
import numpy as np,torch
from torch.nn import functional as F
import train_discriminator as core
from train_discriminator_v4 import save,sha
from train_object_verifier_v8 import prepare,evaluate
from target_learning.discriminator_v5 import Discriminator
from target_learning.object_verifier import ObjectVerifier
from target_learning.expert_adapter import load_parent
ROOT=Path(__file__).resolve().parent


def main():
    torch.set_num_threads(2);torch.manual_seed(990425);begin=time.monotonic();out=ROOT/'perception_training_v9';out.mkdir(exist_ok=False)
    manifest=json.loads((ROOT/'perception_paired_dataset_v9/manifest.json').read_text());assert manifest['status']=='completed'
    module=load_parent(core.BUNDLE,'paired_feature_parent');config=json.loads((core.BUNDLE/'policy.json').read_text())
    runtime=module.RadioRobustRuntime(core.BUNDLE/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
    save(out/'state.json',dict(stage='paired_image_feature_cache'))
    extra=core.prepare(manifest,out,types.SimpleNamespace(__package__=module.__package__,model=runtime.model))
    del runtime;torch.cuda.empty_cache()
    old=ROOT/'perception_training_v3';v6=ROOT/'perception_training_v6';parent=v6/'best.pt'
    saved=torch.load(parent,map_location='cuda',weights_only=False);head=Discriminator().cuda();head.load_state_dict(saved['model']);head.eval()
    rng=np.random.default_rng(990425);data={};unscored={}
    for role in ['training','validation']:
        count=len(np.load(old/(role+'_fine.npy'),mmap_mode='r'))
        labels=json.loads((v6/(role+'_effective_labels.json')).read_text())[:count]
        unscored[role]=0
        for frame in labels:
            for inst in frame['instances']:
                if inst['annotation_instance']=='target':
                    # Old files lack paired contrast/context masks. Retain only
                    # clear, previously supported marker views. Explicitly
                    # report the remaining old true-target views as unscored.
                    clear=inst['identity']==1 and (inst.get('visible_marker_evidence_pixels_annotation_only')or 0)>=32
                    if not clear:inst['identity']=-2;unscored[role]+=1
        labels+=extra[role]['labels'];save(out/(role+'_effective_labels.json'),labels)
        source=dict(labels=labels,fine=np.concatenate([np.load(old/(role+'_fine.npy'),mmap_mode='r'),extra[role]['fine']]),
            context=np.concatenate([np.load(old/(role+'_context.npy'),mmap_mode='r'),extra[role]['context']]))
        data[role]=prepare(head,source,role,out,rng);del source
    save(out/'provenance.json',dict(frozen_detector_sha256=sha(parent),source_sha256=sha(__file__),
        verifier_source_sha256=sha(ROOT/'target_learning/object_verifier.py'),
        label_sha256={r:sha(out/(r+'_effective_labels.json'))for r in data},
        paired_manifest_sha256=sha(ROOT/'perception_paired_dataset_v9/manifest.json'),
        old_unscored_true_target_instances=unscored,teacher_actions_used=False,tidewater_used=False,heldout_used=False,
        visibility_rule='Both exact-CAD identities unknown below32 changed pixels above20levels or insufficient visible structure; no universal distance claim.',
        validation_true_boxes_added=False,training_true_boxes_added=True,
        classes={r:np.bincount(d['classes'][d['classes']>=0],minlength=3).tolist()for r,d in data.items()}))
    del head,extra;torch.cuda.empty_cache();model=ObjectVerifier().cuda()
    warm=torch.load(ROOT/'perception_training_v8/best.pt',map_location='cuda',weights_only=False);model.load_state_dict(warm['verifier'])
    optimizer=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=1e-3);train=data['training']
    counts=np.bincount(train['classes'][train['classes']>=0],minlength=3);weights=np.sqrt(counts.sum()/np.maximum(counts,1));weights/=weights.mean()
    weights=torch.tensor(weights,dtype=torch.float32,device='cuda');best=float('inf');stale=0;history=[]
    for epoch in range(1,51):
        model.train();order=rng.permutation(len(train['classes']));losses=[]
        for start in range(0,len(order),256):
            ix=order[start:start+256];x=torch.from_numpy(train['features'][ix]).cuda().float();m=torch.from_numpy(train['meta'][ix]).cuda().float();y=torch.from_numpy(train['classes'][ix]).cuda()
            if not(y>=0).any():continue
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
        save(out/'history.json',history);save(out/'state.json',dict(stage='training',**history[-1]))
        print(json.dumps(dict(epoch=epoch,loss=history[-1]['loss'],selected=metrics['selected_operating_point'],diagnostic=metrics['diagnostic_best_effort'])),flush=True)
        if epoch>=20 and stale>=10:break
    ck=torch.load(out/'best.pt',map_location='cpu',weights_only=False)
    result=dict(status='completed',checkpoint_sha256=sha(out/'best.pt'),selected_epoch=ck['epoch'],validation=ck['validation'],wall_s=time.monotonic()-begin)
    save(out/'result.json',result);save(out/'state.json',dict(stage='completed',**result));print(json.dumps({k:v for k,v in result.items()if k!='validation'}),flush=True)

if __name__=='__main__':main()
