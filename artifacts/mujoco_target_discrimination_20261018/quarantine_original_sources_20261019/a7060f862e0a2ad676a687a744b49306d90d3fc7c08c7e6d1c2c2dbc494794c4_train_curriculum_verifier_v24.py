"""Bounded RGB verifier fine-tune; original plus new MuJoCo perception only."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import json,time
import numpy as np,torch
from torch.nn import functional as F
from target_learning.object_verifier_v12 import ObjectVerifier
from train_design_and_marker_v12 import evaluate
from train_discriminator_v4 import save
from cache_curriculum_verifier_v24 import sha
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'perception_training_v24'

def load_new(entry):
    p=Path(entry['path']);assert json.loads((p/'receipt.json').read_text())==entry
    for name,digest in entry['files'].items():assert sha(p/name)==digest
    data={k:np.load(p/(k+'.npy'),mmap_mode='r')for k in ['rgb','meta','classes','marker_labels','marker_mask']}
    data['features']=np.zeros((len(data['classes']),1),np.float32)
    data['frames']=json.loads((p/'frames.json').read_text());return data

def load_old(role):
    parent=ROOT/'perception_training_v12_rgb_only'
    data={k:np.load(parent/(role+'_'+k+'.npy'),mmap_mode='r')for k in ['classes','marker_labels']}
    data['rgb']=np.load(ROOT/'perception_rgb_cache_v12'/(role+'_rgb.npy'),mmap_mode='r')
    data['meta']=np.load(ROOT/'perception_training_v9'/(role+'_meta.npy'),mmap_mode='r')
    data['features']=np.zeros((len(data['classes']),1),np.float32)
    data['marker_mask']=np.ones(len(data['classes']),bool)
    data['frames']=json.loads((parent/(role+'_frames.json')).read_text());return data

def combine(metrics):
    total={k:sum(m[k]for m in metrics)for k in ['known_targets','object_instances','unscored_old_target_instances','unscored_old_target_assertions_at_point98']}
    total['object_recall']=sum(m['object_recall']*m['object_instances']for m in metrics)/max(total['object_instances'],1)
    points=[]
    for i in range(len(metrics[0]['operating_points'])):
        first=metrics[0]['operating_points'][i];point={k:first[k]for k in ['heat','identity','support']}
        for k in ['accepted_true_objects','wrong_object_acceptances','ambiguous_acceptances','background_acceptances','duplicate_target_peaks']:
            point[k]=sum(m['operating_points'][i][k]for m in metrics)
        point['target_recall']=point['accepted_true_objects']/max(total['known_targets'],1);points.append(point)
    total['operating_points']=points;return total

@torch.inference_mode()
def qualify(model,old,new):
    original=evaluate(model,old);fresh=combine([evaluate(model,d)for d in new]);pooled=combine([original,fresh])
    safe=[]
    for i,p in enumerate(pooled['operating_points']):
        if p['identity']<.98 or any(p[k]for k in ['wrong_object_acceptances','ambiguous_acceptances','background_acceptances']):continue
        value=dict(p,original_recall=original['operating_points'][i]['target_recall'],curriculum_recall=fresh['operating_points'][i]['target_recall'])
        value['macro_recall']=(value['original_recall']+value['curriculum_recall'])/2;safe.append(value)
    chosen=max(safe,key=lambda p:p['macro_recall'])if safe else None
    diagnostic=min(pooled['operating_points'],key=lambda p:100*(p['wrong_object_acceptances']+p['background_acceptances'])+10*p['ambiguous_acceptances']+100*(1-p['target_recall']))
    pooled.update(selected_operating_point=chosen,diagnostic_best_effort=diagnostic,
        expert_gate_passed=bool(chosen and min(chosen['original_recall'],chosen['curriculum_recall'])>=.8 and min(original['object_recall'],fresh['object_recall'])>=.65),
        score=100*(1-chosen['macro_recall'])if chosen else 1000+100*(diagnostic['wrong_object_acceptances']+diagnostic['background_acceptances'])+10*diagnostic['ambiguous_acceptances'],
        original_validation=original,curriculum_validation=fresh,
        selected_marker_operating_point=original['selected_marker_operating_point'],
        marker_scope='Marker seed only; unchanged RGB metric geometry/PX4 gates remain mandatory.',
        temporal_frame_samples_are_not_independent_flights=True)
    return pooled

def draw(data_list,rng,n):
    lengths=np.asarray([len(d['classes'])for d in data_list]);indices=rng.integers(int(lengths.sum()),size=n);ends=np.cumsum(lengths)
    result={k:[]for k in ['rgb','meta','classes','marker_labels','marker_mask']}
    for i,data in enumerate(data_list):
        selected=indices[(indices>=(ends[i-1]if i else 0))&(indices<ends[i])]-(ends[i-1]if i else 0)
        if not len(selected):continue
        for k in result:result[k].append(np.asarray(data[k][selected]))
    return {k:np.concatenate(v)for k,v in result.items()}

def main():
    torch.set_num_threads(2);torch.manual_seed(2026101902);rng=np.random.default_rng(2026101902);start=time.monotonic()
    cache=ROOT/'curriculum_v23/verifier_cache_v2';manifest=json.loads((cache/'manifest.json').read_text())
    assert manifest['status']=='completed'and not manifest['heldout_used']and not manifest['tidewater_used']and not manifest['action_targets_used']
    parent=ROOT/'perception_training_v12_rgb_only/best.pt';assert sha(parent)==manifest['parent_sha256']
    OUT.mkdir(exist_ok=False);old={r:load_old(r)for r in ['training','validation']}
    new={r:[load_new(e)for e in manifest['entries']if e['role']==r]for r in old};assert all(new.values())
    saved=torch.load(parent,map_location='cuda',weights_only=False);assert saved['verifier_mode']=='rgb_only'
    model=ObjectVerifier(mode='rgb_only').cuda();model.load_state_dict(saved['verifier'],strict=True)
    baseline=qualify(model,old['validation'],new['validation']);save(OUT/'baseline_validation.json',baseline)
    original_hashes={str(p.relative_to(ROOT)):sha(p)for p in [parent,cache/'manifest.json',ROOT/'target_learning/object_verifier_v12.py',Path(__file__)]}
    for role in old:
        for p in [ROOT/'perception_training_v12_rgb_only'/(role+'_classes.npy'),ROOT/'perception_training_v12_rgb_only'/(role+'_marker_labels.npy'),ROOT/'perception_rgb_cache_v12'/(role+'_rgb.npy')]:original_hashes[str(p.relative_to(ROOT))]=sha(p)
    save(OUT/'provenance.json',dict(parent_sha256=sha(parent),sources=original_hashes,original_failed_gate_preserved=True,
        action_targets_used=False,heldout_used=False,tidewater_used=False,training_mix='equal old/new regions per batch',
        pose_spatial_detector_frozen=True,optimizer='AdamW warm restart, not exact optimizer continuation',max_epochs=12))
    optimizer=torch.optim.AdamW([p for p in model.parameters()if p.requires_grad],lr=5e-5,weight_decay=1e-3)
    counts=sum((np.bincount(d['classes'][d['classes']>=0],minlength=3)for d in [old['training'],*new['training']]),np.zeros(3))
    weights=np.sqrt(counts.sum()/np.maximum(counts,1));weights/=weights.mean();weights=torch.tensor(weights,dtype=torch.float32,device='cuda')
    steps=min(400,max(40,int(np.ceil(max(len(old['training']['classes']),sum(len(d['classes'])for d in new['training']))/256))))
    best=baseline['score'];stale=0;history=[]
    for epoch in range(1,13):
        model.train();losses=[]
        for _ in range(steps):
            a=draw([old['training']],rng,128);b=draw(new['training'],rng,128);batch={k:np.concatenate([a[k],b[k]])for k in a}
            rgb=torch.from_numpy(batch['rgb']).cuda().float();meta=torch.from_numpy(batch['meta']).cuda().float()
            prediction=model(rgb.new_zeros((len(rgb),1)),meta,rgb);y=torch.from_numpy(batch['classes']).cuda()
            valid=y>=0;identity=F.cross_entropy(prediction['identity'][valid],y[valid],weight=weights)if valid.any()else prediction['identity'].sum()*0
            mask=torch.from_numpy(batch['marker_mask']).cuda();labels=torch.from_numpy(batch['marker_labels']).cuda()
            marker=F.binary_cross_entropy_with_logits(prediction['marker'][mask],labels[mask])if mask.any()else prediction['marker'].sum()*0
            value=identity+.5*marker;assert torch.isfinite(value)
            optimizer.zero_grad(set_to_none=True);value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3);optimizer.step();losses.append(float(value.detach()))
        metrics=qualify(model,old['validation'],new['validation']);item=dict(epoch=epoch,loss=float(np.mean(losses)),wall_s=time.monotonic()-start,validation=metrics);history.append(item)
        ck={k:v for k,v in saved.items()if k not in ['optimizer','verifier','validation','epoch']}
        ck.update(verifier=model.state_dict(),validation=metrics,epoch=epoch,optimizer=optimizer.state_dict(),
            provenance_sha256=sha(OUT/'provenance.json'),numpy_rng_state=rng.bit_generator.state,torch_rng_state=torch.get_rng_state(),
            schema='mujoco.target_discriminator.v12',teacher_actions_used=False)
        torch.save(ck,OUT/f'epoch_{epoch:03d}.pt')
        if metrics['score']<best:
            best=metrics['score'];stale=0;torch.save(ck,OUT/'best.pt')
        else:stale+=1
        save(OUT/'history.json',history);save(OUT/'state.json',dict(stage='training',epoch=epoch,score=metrics['score'],wall_s=time.monotonic()-start))
        print(json.dumps(dict(epoch=epoch,score=metrics['score'],selected=metrics['selected_operating_point'])),flush=True)
        if epoch>=5 and stale>=4:break
    result=dict(status='completed',improved_over_parent=(OUT/'best.pt').exists(),baseline_score=baseline['score'],best_score=best,
        candidate_sha256=sha(OUT/'best.pt')if(OUT/'best.pt').exists()else None,wall_s=time.monotonic()-start,
        native_qualification_pending=True,production_promoted=False)
    save(OUT/'result.json',result);save(OUT/'state.json',result)
if __name__=='__main__':main()
