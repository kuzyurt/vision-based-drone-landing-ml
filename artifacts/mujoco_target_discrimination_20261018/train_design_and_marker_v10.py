"""Correct the task semantics without recollecting/re-rendering existing data.

Our original CAD remains the same boat design with its marker hidden. Landing
marker visibility is supervised separately. A marker alone is not boat identity.
"""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import copy,json,time
import numpy as np,torch
from torch.nn import functional as F
from target_learning.object_verifier_v10 import ObjectVerifier
from train_object_verifier_v8 import matched,class_label as legacy_class_label,evaluate as evaluate_identity
from train_discriminator_v4 import save,sha
ROOT=Path(__file__).resolve().parent


def design_labels(frame):
    frame=copy.deepcopy(frame)
    for inst in frame['instances']:
        name=inst['annotation_instance']
        if name in ['target','counterfactual_unmarked_full_cad']and 'visible_context_parts'in inst:
            parts=inst['visible_context_parts'];box=inst['bbox']
            visible=(sum(n>=16 for n in parts.values())>=2 and sum(parts.values())>=128 and max(box[2]-box[0],box[3]-box[1])>=24)
            inst['identity']=1 if visible else -1;inst['identity_support']=float(visible)
        elif name=='decoy_blank_clone':
            # This reduced static clone omitted visual hatch meshes. It is not
            # a verified different boat design; never manufacture a wrong-ID
            # label from its missing marker/parts.
            inst['identity']=-2;inst['identity_support']=0.  # Unscored, not a fabricated wrong/unknown design.
    return frame


def class_label(proposal,instance):
    # Design identity needs structural coverage, not the landing marker inside
    # the ROI. Marker containment has a separate supervision path below.
    if instance is None:return 0
    value=dict(instance);value.pop('pad_pixel',None)
    return legacy_class_label(proposal,value)


def marker_label(proposal,inst,frame):
    if inst is None:return 0.
    name=inst['annotation_instance']
    if name in ['counterfactual_unmarked_full_cad','decoy_blank_clone']:return 0.
    if name=='target':
        evidence=inst.get('marker_contrast_pixels_annotation_only',inst.get('visible_marker_evidence_pixels_annotation_only')or 0)
        visible=evidence>=32
    elif name in ['decoy_false_cross_boat','decoy_false_cross_board']:
        visible=inst.get('marker_visible_pixels',0)>=32
    else:visible=False
    if visible and inst.get('pad_pixel')is not None:
        lo=np.asarray(proposal['pixel'])-.75*np.asarray(proposal['size_px']);hi=np.asarray(proposal['pixel'])+.75*np.asarray(proposal['size_px'])
        pixel=np.asarray(inst['pad_pixel']);visible=bool(np.all(pixel>=lo)and np.all(pixel<=hi))
    return float(visible)


def relabel(role,parent,out):
    original=json.loads((parent/(role+'_frames.json')).read_text());metadata=np.load(parent/(role+'_meta.npy'),mmap_mode='r')
    old_classes=np.load(parent/(role+'_classes.npy'),mmap_mode='r');classes=[];markers=[];frames=[];at=0
    for old in original:
        label=design_labels(old['label']);instances=label['instances'];frames.append(dict(label=label,predictions=old['predictions']))
        for p in old['predictions']:
            j=matched(p,instances);inst=instances[j]if j is not None else None
            classes.append(class_label(p,inst));markers.append(marker_label(p,inst,label));at+=1
        if role=='training':
            for j,previous in enumerate(old['label']['instances']):
                # Reuse the EXACT existing jittered boxes and feature order,
                # whose augmentation count was fixed by the earlier labels.
                for repeat in range(2 if previous['identity']==1 else 1):
                    m=metadata[at];p=dict(pixel=(m[:2]*[640.,360.]).tolist(),size_px=(m[2:4]*[640.,360.]).tolist())
                    classes.append(class_label(p,instances[j]));markers.append(marker_label(p,instances[j],label));at+=1
    assert at==len(metadata)==len(old_classes)
    result=dict(features=np.load(parent/(role+'_features.npy'),mmap_mode='r'),meta=metadata,
        classes=np.asarray(classes,dtype=np.int64),marker_labels=np.asarray(markers,dtype=np.float32),frames=frames)
    np.save(out/(role+'_classes.npy'),result['classes']);np.save(out/(role+'_marker_labels.npy'),result['marker_labels']);save(out/(role+'_frames.json'),frames)
    return result


class IdentityOnly(torch.nn.Module):
    def __init__(self,model):super().__init__();self.model=model
    def forward(self,x,m):return self.model(x,m)['identity']


@torch.inference_mode()
def evaluate(model,data):
    metrics=evaluate_identity(IdentityOnly(model),data);marker=[]
    for start in range(0,len(data['features']),512):
        output=model(torch.from_numpy(np.array(data['features'][start:start+512])).cuda().float(),torch.from_numpy(np.array(data['meta'][start:start+512])).cuda().float())
        marker.extend(output['marker'].sigmoid().cpu().tolist())
    marker=np.asarray(marker);scope=data['classes']==1;truth=data['marker_labels']>.5;points=[]
    for threshold in [.8,.9,.95,.98,.99,.995]:
        accepted=marker>=threshold
        points.append(dict(threshold=threshold,present=int(sum(scope&truth)),absent=int(sum(scope&~truth)),
            true_positives=int(sum(scope&truth&accepted)),false_positives=int(sum(scope&~truth&accepted)),
            recall=float(sum(scope&truth&accepted)/max(sum(scope&truth),1))))
    safe=[p for p in points if p['false_positives']==0]
    chosen=max(safe,key=lambda p:p['recall'])if safe else points[-1]
    metrics['marker_operating_points']=points;metrics['selected_marker_operating_point']=chosen
    metrics['marker_scope']='Visible marker in a qualified original-design ROI; separate from design identity.'
    # A weak marker head cannot silently count as a ready landing pad.
    metrics['marker_seed_warning']=chosen['false_positives']>0 or chosen['recall']<.5
    return metrics


def main():
    torch.set_num_threads(2);torch.manual_seed(990426);begin=time.monotonic();out=ROOT/'perception_training_v10';out.mkdir(exist_ok=False)
    parent=ROOT/'perception_training_v9';assert(parent/'result.json').exists();data={r:relabel(r,parent,out)for r in ['training','validation']}
    saved=torch.load(parent/'best.pt',map_location='cuda',weights_only=False);model=ObjectVerifier().cuda()
    missing=model.load_state_dict(saved['verifier'],strict=False);assert missing.missing_keys==['marker.weight','marker.bias']and not missing.unexpected_keys
    optimizer=torch.optim.AdamW(model.parameters(),lr=2e-4,weight_decay=1e-3);rng=np.random.default_rng(990426);train=data['training']
    counts=np.bincount(train['classes'][train['classes']>=0],minlength=3);weights=np.sqrt(counts.sum()/np.maximum(counts,1));weights/=weights.mean();weights=torch.tensor(weights,dtype=torch.float32,device='cuda')
    positives=max(float(sum(train['marker_labels']>.5)),1.);marker_weight=torch.tensor(min(6.,((len(train['marker_labels'])-positives)/positives)**.5),device='cuda')
    save(out/'provenance.json',dict(parent_checkpoint_sha256=sha(parent/'best.pt'),parent_features_unchanged=True,source_sha256=sha(__file__),
        verifier_source_sha256=sha(ROOT/'target_learning/object_verifier_v10.py'),
        semantic_correction='Recognizable original boat CAD stays original design when marker hidden; separate marker head. Reduced clone identity unverified/unknown.',
        feature_parent=str(parent),label_hashes={r:sha(out/(r+'_frames.json'))for r in data},
        teacher_actions_used=False,tidewater_used=False,heldout_used=False,
        classes={r:np.bincount(d['classes'][d['classes']>=0],minlength=3).tolist()for r,d in data.items()},
        marker_positives={r:int(sum(d['marker_labels']>.5))for r,d in data.items()}))
    best=float('inf');stale=0;history=[]
    for epoch in range(1,51):
        model.train();order=rng.permutation(len(train['classes']));losses=[]
        for start in range(0,len(order),256):
            ix=order[start:start+256];x=torch.from_numpy(np.array(train['features'][ix])).cuda().float();m=torch.from_numpy(np.array(train['meta'][ix])).cuda().float()
            y=torch.from_numpy(train['classes'][ix]).cuda();marker=torch.from_numpy(train['marker_labels'][ix]).cuda();prediction=model(x,m)
            identity=F.cross_entropy(prediction['identity'],y,weight=weights)if(y>=0).any()else prediction['identity'].sum()*0
            value=identity+.5*F.binary_cross_entropy_with_logits(prediction['marker'],marker,pos_weight=marker_weight);assert torch.isfinite(value)
            optimizer.zero_grad(set_to_none=True);value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3.);optimizer.step();losses.append(float(value.detach()))
        metrics=evaluate(model,data['validation']);history.append(dict(epoch=epoch,loss=float(np.mean(losses)),wall_s=time.monotonic()-begin,**metrics))
        score=metrics['score']+10*metrics['selected_marker_operating_point']['false_positives']+5*(1-metrics['selected_marker_operating_point']['recall'])
        ck=dict(schema='mujoco.target_discriminator.v10',model=saved['model'],verifier=model.state_dict(),epoch=epoch,validation=metrics,
            optimizer=optimizer.state_dict(),numpy_rng_state=rng.bit_generator.state,torch_rng_state=torch.get_rng_state(),
            parent_pose_sha256=saved['parent_pose_sha256'],parent_spatial_sha256=saved['parent_spatial_sha256'],frozen_detector_sha256=saved['frozen_detector_sha256'],
            tidewater_images_used=False,heldout_images_used=False,teacher_actions_used=False,provenance_sha256=sha(out/'provenance.json'))
        torch.save(ck,out/f'epoch_{epoch:03d}.pt')
        if score<best:best=score;stale=0;torch.save(ck,out/'best.pt')
        else:stale+=1
        save(out/'history.json',history);save(out/'state.json',dict(stage='training',**history[-1]))
        print(json.dumps(dict(epoch=epoch,loss=history[-1]['loss'],selected=metrics['selected_operating_point'],marker=metrics['selected_marker_operating_point'],diagnostic=metrics['diagnostic_best_effort'])),flush=True)
        if epoch>=20 and stale>=10:break
    ck=torch.load(out/'best.pt',map_location='cpu',weights_only=False)
    result=dict(status='completed',checkpoint_sha256=sha(out/'best.pt'),selected_epoch=ck['epoch'],validation=ck['validation'],wall_s=time.monotonic()-begin)
    save(out/'result.json',result);save(out/'state.json',dict(stage='completed',**result));print(json.dumps({k:v for k,v in result.items()if k!='validation'}),flush=True)

if __name__=='__main__':main()
