"""Epochs over frozen episode manifests; never accepts review-only recordings."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import h5py
import numpy as np
import torch
from torch import nn
from .gate import require_approval,file_hash
from .recording import numeric_observation
from .policy import LandingPolicy,normalize_actions

def approved_dataset(manifest_path,bundle):
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
        if file_hash(artifact)!=episode['sha256']:raise ValueError('Dataset artifact changed')
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

def train(manifest_path,bundle,output,epochs=10,device='cpu',pretrained=True,finetune_encoder=False):
    path,manifest,training,validation=approved_dataset(manifest_path,bundle)
    if epochs<=0:raise ValueError('Epoch count must be positive')
    random.seed(714);torch.manual_seed(714)
    output=Path(output);output.mkdir(parents=True,exist_ok=True);torch.hub.set_dir(str(output/'weights'))
    model=LandingPolicy(pretrained=pretrained,freeze_encoder=not finetune_encoder).to(device)
    total=np.zeros(32);squared=np.zeros(32);count=0
    for episode in training:
        for row in rows(episode):
            value=numeric_observation(row).astype(np.float64);total+=value;squared+=value*value;count+=1
    mean=total/count;std=np.sqrt(np.maximum(squared/count-mean*mean,1e-6))
    model.observation_mean.copy_(torch.from_numpy(mean).to(device));model.observation_std.copy_(torch.from_numpy(std).to(device))
    optimizer=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=1e-4)
    best=float('inf');history=[]
    for epoch in range(epochs):
        order=training.copy();random.shuffle(order);pending=iter(order);lanes=[];steps=0;total_loss=0.
        for _ in range(8):
            try:lanes.append(Lane(next(pending)))
            except StopIteration:break
        model.train()
        if not finetune_encoder:model.encoder.eval()
        else:
            # Keep frame features independent of future frames in a sequence.
            for module in model.encoder.modules():
                if isinstance(module,nn.BatchNorm2d):module.eval()
        while lanes:
            optimizer.zero_grad();count=len(lanes)
            for lane in lanes:
                image,obs,target,valid,aux_target=lane.chunk(64,device)
                prediction,aux,lane.hidden=model(image,obs,lane.hidden)
                loss=loss_function(prediction,aux,target,valid,aux_target);(loss/count).backward();total_loss+=float(loss.detach())
                lane.hidden=lane.hidden.detach()
            nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step();steps+=1
            next_lanes=[]
            for lane in lanes:
                if lane.done():
                    lane.close()
                    try:next_lanes.append(Lane(next(pending)))
                    except StopIteration:pass
                else:next_lanes.append(lane)
            lanes=next_lanes
        model.eval();validation_losses=[]
        with torch.inference_mode():
            for episode in validation:
                lane=Lane(episode)
                try:
                    while not lane.done():
                        image,obs,target,valid,aux_target=lane.chunk(64,device);prediction,aux,lane.hidden=model(image,obs,lane.hidden)
                        validation_losses.append(float(loss_function(prediction,aux,target,valid,aux_target)))
                finally:lane.close()
        value=float(np.mean(validation_losses));history.append({'epoch':epoch+1,'optimizer_steps':steps,'train_sequence_loss_sum':total_loss,'validation_loss':value})
        checkpoint={'schema':'aerodock.landing.checkpoint.v1','model':model.state_dict(),'epoch':epoch+1,'dataset_sha256':file_hash(path),'review_manifest_sha256':file_hash(Path(bundle)/'manifest.json'),'training':{'sequence_steps':64,'effective_batch_sequences':8,'learning_rate':1e-4},'validation_loss':value}
        torch.save(checkpoint,output/'latest.pt')
        if value<best:best=value;torch.save(checkpoint,output/'best.pt')
        (output/'history.json').write_text(json.dumps(history,indent=2));print(history[-1],flush=True)
    return history

import math
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True);parser.add_argument('--review',required=True);parser.add_argument('--output',required=True);parser.add_argument('--epochs',type=int,default=10);parser.add_argument('--device',default='cpu');parser.add_argument('--no-pretrained',action='store_true');parser.add_argument('--finetune-encoder',action='store_true')
    args=parser.parse_args();train(args.manifest,args.review,args.output,args.epochs,args.device,not args.no_pretrained,args.finetune_encoder)
