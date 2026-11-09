"""Epochs over frozen episode manifests; never accepts review-only recordings."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import h5py
import numpy as np
import torch
from torch import nn
from .gate import require_approval,file_hash
from .recording import numeric_observation
from .policy import LandingPolicy,normalize_actions

def approved_dataset(manifest_path,bundle,verify_roles=None):
    require_approval(bundle)
    path=Path(manifest_path).resolve();manifest=json.loads(path.read_text())
    if manifest.get('review_manifest_sha256')!=file_hash(Path(bundle)/'manifest.json'):raise PermissionError('Dataset belongs to a different review bundle')
    if manifest.get('role')!='dataset' or manifest.get('schema')!='aerodock.landing.dataset.v1':raise PermissionError('Training requires a collected, user-authorized dataset manifest')
    training=[];validation=[]
    group_roles={}
    for episode in manifest['episodes']:
        group=episode['world_seed'];role=episode['role']
        if role not in ('training','validation','test'):raise PermissionError('Invalid dataset split')
        if group in group_roles and group_roles[group]!=role:raise ValueError('World seed leaks across splits')
        group_roles[group]=role
        artifact=(path.parent/episode['path']).resolve()
        if not artifact.is_relative_to(path.parent):raise ValueError('Dataset path escapes manifest directory')
        if (verify_roles is None or role in verify_roles) and file_hash(artifact)!=episode['sha256']:raise ValueError('Dataset artifact changed')
        with h5py.File(artifact) as data:
            if not data.attrs.get('training_eligible',False) or data.attrs['role']!=role:raise PermissionError('Review or incorrectly labelled data cannot be trained on')
        if role=='training':training.append(artifact)
        elif role=='validation':validation.append(artifact)
    if not training or not validation:raise ValueError('Both training and held-out validation episodes are required')
    return path,manifest,training,validation

def rows(path):
    with h5py.File(path) as data:
        for encoded in data['steps']:yield json.loads(encoded)

def auxiliary_target(row):
    p=row['privileged'];o=row['observation'];visible=p['pad_visible']
    pixels=np.array(p['pad_keypoints_px'])[0]/[320.,180.]-1
    yaw=math.pi/2-o['px4']['attitude_ned_rad'][2]
    c,s=math.cos(yaw),math.sin(yaw);rotation=np.array([[c,s,0],[-s,c,0],[0,0,1.]])
    relative=(rotation@(np.array(p['pad_position_enu_m'])-p['drone_position_enu_m']))*[1,-1,-1]
    velocity=(rotation@(np.array(p['pad_velocity_enu_m_s'])-p['drone_velocity_enu_m_s']))*[1,-1,-1]
    return np.r_[float(visible),np.clip(pixels,-2,2),relative/10.,velocity/2.,float(row['outcome'] in ('stable_contact','landed'))].astype(np.float32)

class Lane:
    def __init__(self,path):self.file=h5py.File(path);self.index=0;self.hidden=None
    def chunk(self,length,device):
        stop=min(len(self.file['steps']),self.index+length)
        records=[json.loads(row) for row in self.file['steps'][self.index:stop]]
        images=np.asarray(self.file['rgb'][self.index:stop]);self.index=stop
        obs=np.array([numeric_observation(r) for r in records])
        actions=np.array([r['output'].get('expert_bounded_action',r['output']['executed_action']) for r in records],dtype=np.float32)
        valid=np.array([not r.get('terminal',False) and r['output'].get('action_supervision_valid',True) for r in records],dtype=np.float32)
        aux=np.array([auxiliary_target(r) for r in records])
        return (torch.from_numpy(images).permute(0,3,1,2)[None].to(device),torch.from_numpy(obs)[None].to(device),torch.from_numpy(actions)[None].to(device),torch.from_numpy(valid)[None].to(device),torch.from_numpy(aux)[None].to(device))
    def done(self):return self.index>=len(self.file['steps'])
    def close(self):self.file.close()

def loss_function(prediction,aux,targets,valid,aux_targets):
    imitation=nn.functional.huber_loss(prediction,normalize_actions(targets),reduction='none').mean(-1)
    loss=(imitation*valid).sum()/valid.sum().clamp_min(1)
    visibility=nn.functional.binary_cross_entropy_with_logits(aux[...,0],aux_targets[...,0])
    regression=nn.functional.huber_loss(aux[...,1:9],aux_targets[...,1:9],reduction='none').mean(-1)
    contact=nn.functional.binary_cross_entropy_with_logits(aux[...,9],aux_targets[...,9])
    mask=aux_targets[...,0]
    return loss+.1*visibility+.05*contact+.05*(regression*mask).sum()/mask.sum().clamp_min(1)

def atomic_checkpoint(value,path):
    import os
    temporary=path.with_suffix('.pt.tmp')
    torch.save(value,temporary)
    with temporary.open('rb') as stream:os.fsync(stream.fileno())
    temporary.replace(path)
    if os.name!='nt':
        descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)


def train(manifest_path,bundle,output,epochs=10,device='cpu',pretrained=True,finetune_encoder=False,
          loader_workers='auto',feature_cache='auto',cpu_threads=4,resume=False,patience=3,min_delta=1e-5):
    # Authorization always precedes feature-cache creation or optimizer work.
    training_started=time.monotonic()
    path,manifest,training,validation=approved_dataset(manifest_path,bundle)
    if epochs<=0 or cpu_threads<=0 or patience<0 or not math.isfinite(min_delta) or min_delta<0:raise ValueError('Invalid training budget or early stopping settings')
    if finetune_encoder and feature_cache not in ('auto','off'):raise ValueError('Cannot cache a trainable encoder')
    from .training_pipeline import (build_feature_cache,frame_counts,chunk_plan,ChunkLoader,run_update,
                                    ValidationMetrics,teacher_supervision)
    random.seed(714);torch.manual_seed(714);torch.set_num_threads(cpu_threads)
    output=Path(output)
    if not resume and any((output/name).exists() for name in ('latest.pt','best.pt','history.json','training_result.json')):
        raise FileExistsError('Training results already exist: use --resume or a new output directory')
    output.mkdir(parents=True,exist_ok=True);torch.hub.set_dir(str(output/'weights'))
    from .progress import TrainingProgress,export_loss_history,utc_now
    progress=TrainingProgress(output,epochs,started=training_started)
    progress.save(force=True,phase='initialization')
    model=LandingPolicy(pretrained=pretrained,freeze_encoder=not finetune_encoder).to(device)
    dataset_hash=file_hash(path);review_hash=file_hash(Path(bundle)/'manifest.json');restored=None
    if resume:
        restored=torch.load(output/'latest.pt',map_location=device,weights_only=False)
        if restored.get('schema')!='aerodock.landing.checkpoint.v1' or restored.get('dataset_sha256')!=dataset_hash or restored.get('review_manifest_sha256')!=review_hash:
            raise PermissionError('Resume checkpoint does not match the approved dataset/review')
        if 'optimizer' not in restored or 'rng' not in restored:raise ValueError('Legacy checkpoint cannot resume optimizer/RNG state')
        if restored['training'].get('finetune_encoder')!=finetune_encoder:raise ValueError('Resume must keep the encoder training mode')
        model.load_state_dict(restored['model'])
        progress.save(force=True,completed_epochs=restored['epoch'])
        export_loss_history(output,restored['history'])
    supervision,excluded=teacher_supervision(manifest,path.parent)
    if excluded:print('Masking imitation targets from failed expert flights:',excluded,flush=True)
    cached=not finetune_encoder and feature_cache!='off';cache_info=None
    if cached:
        cache_directory=output/'features' if feature_cache=='auto' else Path(feature_cache)
        source_hashes={str((path.parent/e['path']).resolve()):e['sha256'] for e in manifest['episodes']}
        mapping,cache_info=build_feature_cache(model,training+validation,cache_directory,device,
                                             workers=loader_workers,source_hashes=source_hashes,supervision=supervision,progress=progress.cache)
        training=[Path(mapping[str(p)]) for p in training];validation=[Path(mapping[str(p)]) for p in validation]
    total=np.zeros(32);squared=np.zeros(32);count=0;supervised=0
    progress.save(force=True,phase='normalization',normalization_completed_episodes=0,normalization_total_episodes=len(training))
    for episode_index,episode in enumerate(training):
        if cached:
            with h5py.File(episode,'r') as data:
                for start in range(0,len(data['numeric']),1024):
                    values=np.asarray(data['numeric'][start:start+1024],dtype=np.float64)
                    total+=values.sum(0);squared+=(values*values).sum(0);count+=len(values)
                supervised+=int(np.asarray(data['valid']).sum())
        else:
            for row in rows(episode):
                value=numeric_observation(row).astype(np.float64);total+=value;squared+=value*value;count+=1
                supervised+=int(supervision.get(str(episode),True) and not row.get('terminal',False) and row['output'].get('action_supervision_valid',True))
        progress.save(normalization_completed_episodes=episode_index+1)
    if not count or not supervised:raise ValueError('No valid training teacher actions')
    mean=total/count;std=np.sqrt(np.maximum(squared/count-mean*mean,1e-6))
    model.observation_mean.copy_(torch.from_numpy(mean).to(device));model.observation_std.copy_(torch.from_numpy(std).to(device))
    optimizer=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=1e-4)
    best=float('inf');history=[];counts=frame_counts(training+validation);start_epoch=0;bad_epochs=0
    if restored is not None:
        optimizer.load_state_dict(restored['optimizer']);start_epoch=restored['epoch']
        best=restored['best_validation_loss'];bad_epochs=restored['bad_epochs'];history=restored['history']
        random.setstate(restored['rng']['python']);np.random.set_state(restored['rng']['numpy'])
        torch.set_rng_state(restored['rng']['torch'].cpu())
        if torch.device(device).type=='cuda' and restored['rng']['cuda'] is not None:torch.cuda.set_rng_state(restored['rng']['cuda'].cpu(),device)
        if restored['is_best']:atomic_checkpoint(restored,output/'best.pt')
    stop_reason='epoch_budget_completed'
    for epoch in range(start_epoch,epochs):
        if patience and bad_epochs>=patience:stop_reason='validation_early_stopping';break
        epoch_started=time.monotonic();order=training.copy();random.shuffle(order);steps=0;total_loss=0.;hidden={}
        lanes=0;window_lanes=0;window_loss=0.;sample_started=time.monotonic();done_frames=0
        total_frames=sum(counts[str(p)] for p in training)
        progress.save(force=True,phase='training',current_epoch=epoch+1,completed_epochs=epoch,
                      phase_completed_frames=0,phase_total_frames=total_frames)
        model.train()
        if not finetune_encoder:model.encoder.eval()
        else:
            for module in model.encoder.modules():
                if isinstance(module,nn.BatchNorm2d):module.eval()
        plan=chunk_plan(order,counts,lanes=8,steps=64,supervision=None if cached else supervision)
        # Feature records are tiny: in-process reads avoid multiprocessing overhead.
        epoch_workers=0 if cached else loader_workers
        with ChunkLoader(plan,cached=cached,workers=epoch_workers,device=device) as loader:
            actual_workers=loader.workers
            for update in loader.updates():
                frames,value=run_update(model,optimizer,update,hidden,device,cached=cached)
                total_loss+=value;steps+=1;lanes+=len(update);done_frames+=frames
                window_loss+=value;window_lanes+=len(update)
                progress.save(phase_completed_frames=done_frames,optimizer_steps=steps)
                if time.monotonic()-sample_started>=5:
                    progress.loss_sample(epoch+1,steps,window_lanes,window_loss)
                    window_loss=0.;window_lanes=0;sample_started=time.monotonic()
        if window_lanes:progress.loss_sample(epoch+1,steps,window_lanes,window_loss)
        model.eval();metrics=ValidationMetrics();hidden={}
        done_frames=0
        progress.save(force=True,phase='validation',phase_completed_frames=0,
                      phase_total_frames=sum(counts[str(p)] for p in validation))
        plan=chunk_plan(validation,counts,lanes=1,steps=64,supervision=None if cached else supervision)
        with ChunkLoader(plan,cached=cached,workers=epoch_workers,device=device) as loader,torch.inference_mode():
            for update in loader.updates():
                frames,_=run_update(model,None,update,hidden,device,cached=cached,metrics=metrics)
                done_frames+=frames;progress.save(phase_completed_frames=done_frames)
        validation_metrics=metrics.report();value=validation_metrics['loss']
        improved=value<best-min_delta
        if improved:best=value;bad_epochs=0
        else:bad_epochs+=1
        history.append({'epoch':epoch+1,'optimizer_steps':steps,'train_sequence_loss_sum':total_loss,
                        'train_lane_loss_mean':total_loss/max(1,lanes),
                        'finished_utc':utc_now(),'epoch_seconds':time.monotonic()-epoch_started,
                        'training_elapsed_hours':(progress.prior_seconds+time.monotonic()-progress.started)/3600,
                        'validation_loss':value,'validation_metrics':validation_metrics})
        checkpoint={'schema':'aerodock.landing.checkpoint.v1','model':model.state_dict(),'epoch':epoch+1,
                    'dataset_sha256':dataset_hash,'review_manifest_sha256':review_hash,
                    'training':{'sequence_steps':64,'effective_batch_sequences':8,'learning_rate':1e-4,
                                'loader_workers':actual_workers,'feature_cache':cached,'cpu_threads':cpu_threads,
                                'precision':'float32','batched_lanes':True,'finetune_encoder':finetune_encoder,
                                'validation_metric':'dataset_weighted_components.v1','patience':patience,'min_delta':min_delta},
                    'validation_loss':value,'feature_preparation':cache_info,'optimizer':optimizer.state_dict(),
                    'rng':{'python':random.getstate(),'numpy':np.random.get_state(),'torch':torch.get_rng_state(),
                           'cuda':torch.cuda.get_rng_state(device) if torch.device(device).type=='cuda' else None},
                    'best_validation_loss':best,'bad_epochs':bad_epochs,'history':history,'is_best':improved,
                    'data_quality':{'masked_expert_failures':excluded,'train_steps':count,'supervised_train_steps':supervised,
                                    'training_episodes':len(training),'validation_episodes':len(validation)}}
        atomic_checkpoint(checkpoint,output/'latest.pt')
        if improved:atomic_checkpoint(checkpoint,output/'best.pt')
        from .collection_session import atomic_json
        export_loss_history(output,history);print(history[-1],flush=True)
        progress.save(force=True,completed_epochs=epoch+1,bad_epochs=bad_epochs,
                      latest_train_lane_loss=history[-1]['train_lane_loss_mean'],latest_validation_loss=value)
    if patience and bad_epochs>=patience:stop_reason='validation_early_stopping'
    export_loss_history(output,history)
    progress.save(force=True,status='completed',phase='finished',stop_reason=stop_reason,completed_epochs=len(history),bad_epochs=bad_epochs)
    from .collection_session import atomic_json
    atomic_json(output/'training_result.json',{'status':'completed','stop_reason':stop_reason,'completed_epochs':len(history),
                'best_validation_loss':best,'latest_checkpoint':str(output/'latest.pt'),'best_checkpoint':str(output/'best.pt')})
    return history

import math
if __name__=='__main__':
    import signal
    def cancel(signum,frame):raise KeyboardInterrupt('Training cancelled')
    signal.signal(signal.SIGTERM,cancel)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True);parser.add_argument('--review',required=True);parser.add_argument('--output',required=True);parser.add_argument('--epochs',type=int,default=10);parser.add_argument('--device',default='cpu');parser.add_argument('--no-pretrained',action='store_true');parser.add_argument('--finetune-encoder',action='store_true')
    parser.add_argument('--loader-workers',default='auto');parser.add_argument('--feature-cache',default='auto',help='auto, off, or a cache directory');parser.add_argument('--cpu-threads',type=int,default=4)
    parser.add_argument('--resume',action='store_true');parser.add_argument('--patience',type=int,default=3);parser.add_argument('--min-delta',type=float,default=1e-5)
    args=parser.parse_args();train(args.manifest,args.review,args.output,args.epochs,args.device,not args.no_pretrained,args.finetune_encoder,args.loader_workers,args.feature_cache,args.cpu_threads,args.resume,args.patience,args.min_delta)
