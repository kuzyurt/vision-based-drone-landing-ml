"""Continue the current checkpoint on original plus new, disjoint training data."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import hashlib
import json
from pathlib import Path
import random
import sys
import time
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent;BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
sys.path.insert(0,str(BASE));import landing_training
landing_training.__path__.append(str(ROOT/'policy_bundle/code/landing_training'))
from landing_training.radio_robust_20261015.model import RadioRobustPoseModel
from landing_training.radio_robust_20261015.augmentation import RadioAugmentation
from landing_training.radio_robust_20261015.train import update,Metrics,checkpoint
from landing_training.training_pipeline import ChunkLoader,chunk_plan,frame_counts
from landing_training.gate import file_hash
from collect_domain import save

class Augmentation:
    def __init__(self,epoch,neutral,mode='mixed'):self.epoch=epoch;self.neutral=neutral;self.mode=mode;self.lanes={}
    def apply(self,spec,values):
        token=spec['token']
        if token not in self.lanes:
            mode=self.mode
            if mode=='mixed':
                number=int.from_bytes(hashlib.sha256((str(token)+str(self.epoch)).encode()).digest()[:8],'little')/2**64
                mode='clean' if number<.10 else 'noisy' if number<.25 else 'missing'
            self.lanes[token]=RadioAugmentation(self.epoch,mode)
        numeric,quality,mode=self.lanes[token].apply(spec,values)
        numeric[numeric[:,21]<.5,22]=self.neutral
        if spec['end']:self.lanes.pop(token)
        return numeric,quality,mode

def validate(model,paths,counts,targets,mode):
    model.eval();metrics=Metrics();hidden={};augmentation=Augmentation(0,float(model.backbone.observation_mean[22]),mode)
    with ChunkLoader(chunk_plan(paths,counts,lanes=8,steps=64),cached=True,workers=0,device='cuda') as loader,torch.inference_mode():
        for items in loader.updates():update(model,items,hidden,targets,augmentation,'cuda',metrics=metrics)
    return metrics.result()

def main():
    while not (ROOT/'feature_result.json').exists():time.sleep(20)
    from feature_compatibility import complete
    complete(ROOT,file_hash,save)
    source=ROOT/'policy_bundle/pose.pt';state=torch.load(source,map_location='cpu',weights_only=False)
    old_manifest=BASE/'landing_training/datasets/expert/manifest.json'
    assert file_hash(old_manifest)=='5840294d08b700262cfac01480a8e5ee9c40ba29946747f6942db496642e802e'
    old_targets=BASE/'landing_training/outputs/control_iteration_20261010T220632Z/pose_targets/manifest.json'
    assert file_hash(old_targets)=='a2643723f387ccfb2a26b37c43478ff45f9e7e79bfed99dcd76ab3dd4cb180f5'
    old=json.loads(old_targets.read_text())['entries'];new=json.loads((ROOT/'features/manifest.json').read_text())['entries']
    if sum(e['role']=='training' for e in new)<20:raise RuntimeError('Insufficient usable new training episodes')
    entries=old+new;targets={};splits={'training':[],'validation':[]}
    for e in entries:
        if e['role'] not in splits:raise ValueError('Test data must not enter training or selection')
        if file_hash(e['cache'])!=e['cache_sha256'] or file_hash(e['target'])!=e['target_sha256']:raise ValueError('Feature integrity failed')
        path=Path(e['cache']);splits[e['role']].append(path);targets[str(path)]=np.load(e['target'])
    mixed=dict(original_manifest_sha256=file_hash(old_manifest),supplemental_manifest_sha256=file_hash(ROOT/'dataset/manifest.json'),
               authorization_sha256=file_hash(ROOT/'authorization.json'),training_episodes=len(splits['training']),validation_episodes=len(splits['validation']),test_episodes_used=0,
               source_checkpoint_sha256=file_hash(source),radio_modes={'clean':.10,'noisy':.15,'missing':.75},new_training_entries=sum(e['role']=='training' for e in new))
    save(ROOT/'mixed_dataset.json',mixed)
    out=ROOT/'training';out.mkdir(exist_ok=False);torch.set_num_threads(2);torch.manual_seed(1741);np.random.seed(1741);random.seed(1741)
    model=RadioRobustPoseModel().cuda();model.load_state_dict(state['model'])
    for name,p in model.named_parameters():p.requires_grad=not name.startswith(('backbone.encoder.','backbone.actions.'))
    optimizer=torch.optim.Adam([dict(params=list(model.visual_absolute.parameters())+list(model.quality.parameters()),lr=6e-5),
                               dict(params=[p for n,p in model.backbone.named_parameters() if p.requires_grad],lr=2e-5)])
    counts=frame_counts(splits['training']+splits['validation']);history=[];best=float('inf');stale=0;began=time.monotonic()
    fresh_training=[Path(e['cache']) for e in new if e['role']=='training']
    baseline=validate(model,splits['validation'],counts,targets,'missing')
    save(out/'parent_baseline_missing.json',baseline)
    for epoch in range(1,17):
        started=time.monotonic();model.train();model.backbone.encoder.eval();order=splits['training']+fresh_training*2;random.shuffle(order)
        augmentation=Augmentation(epoch,float(model.backbone.observation_mean[22]));hidden={};frames=losses=lanes=0;mode_counts={}
        with ChunkLoader(chunk_plan(order,counts,lanes=8,steps=64),cached=True,workers=0,device='cuda') as loader:
            for step,items in enumerate(loader.updates(),1):
                n,loss,modes=update(model,items,hidden,targets,augmentation,'cuda',optimizer)
                frames+=n;losses+=loss;lanes+=len(items)
                for key,value in modes.items():mode_counts[key]=mode_counts.get(key,0)+value
                if step%100==0:save(out/'progress.json',dict(status='running',phase='training',epoch=epoch,frames=frames))
        metrics=validate(model,splits['validation'],counts,targets,'missing')
        score=metrics['score']+.5*metrics['visibility_brier']+.004*metrics['visual_bearing_rms_px']
        item=dict(epoch=epoch,train_loss=losses/lanes,validation_missing=metrics,selection_score=score,mode_frames=mode_counts,seconds=time.monotonic()-started)
        history.append(item)
        saved=dict(schema='aerodock.landing.radio_robust_pose.v1',model=model.state_dict(),epoch=epoch,source_epoch=state['epoch'],source_checkpoint_sha256=file_hash(source),
                   dataset_sha256=file_hash(ROOT/'mixed_dataset.json'),review_manifest_sha256=file_hash(ROOT/'authorization.json'),targets_sha256=file_hash(ROOT/'features/manifest.json'),
                   training=dict(encoder_frozen=True,observation_mode='periodic_no_action_v1',mixed_original_and_new=True,radio_modes=mixed['radio_modes'],
                                 unknown_dock_status='masked to training mean, matching runtime',selection='missing-radio pose, visibility and image-bearing errors'),
                   validation_metrics=metrics,selection_score=score,history=history,optimizer=optimizer.state_dict())
        checkpoint(out/('epoch_%03d.pt'%epoch),saved);checkpoint(out/'latest.pt',saved)
        if score<best:best=score;stale=0;checkpoint(out/'best.pt',saved)
        else:stale+=1
        save(out/'history.json',history);save(out/'progress.json',dict(status='running',phase='epoch_complete',epoch=epoch,selection_score=score))
        print('EPOCH',json.dumps(item),flush=True)
        if epoch>=8 and stale>=4:break
        if epoch>=6 and time.monotonic()-began>40*60:break
    result=dict(status='completed',epochs=len(history),best_score=best,elapsed_s=time.monotonic()-began,best_checkpoint=str(out/'best.pt'),test_data_used=False)
    save(ROOT/'training_result.json',result);save(out/'progress.json',result);print('TRAINING_COMPLETE',json.dumps(result),flush=True)

if __name__=='__main__':main()
