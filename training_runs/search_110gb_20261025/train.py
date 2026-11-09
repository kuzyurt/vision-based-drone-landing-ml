"""Train only the new acquisition head on this run's fresh lossless episodes."""
from __future__ import annotations
import argparse
from collections import Counter, OrderedDict
import json
import math
from pathlib import Path
import random
import shutil
import sys
import torch
from torch.utils.data import Dataset, DataLoader
from common import (HERE, canonical, config, dataset_root, fingerprint, sha, utc,
                    verify_sources, weight_path, write_json)
from storage import open_read, read_frame
from model import load_backbone, SearchHead, encode_maps, targets, loss


class Frames(Dataset):
    def __init__(self, root, entries):
        self.root=Path(root);self.entries=entries;self.addresses=[];self.connections=OrderedDict()
        for e in entries:
            self.addresses.extend((e['database'],i) for i in range(e['frames']))

    def __len__(self):return len(self.addresses)

    def __getstate__(self):
        return dict(self.__dict__,connections=OrderedDict())

    def __getitem__(self, index):
        path,frame=self.addresses[index]
        if path not in self.connections:
            if len(self.connections)>=2:self.connections.popitem(last=False)[1].close()
            self.connections[path]=open_read(self.root/path)
        self.connections.move_to_end(path)
        rgb,row=read_frame(self.connections[path],frame)
        return torch.from_numpy(rgb).permute(2,0,1),targets(row['supervision']['boats'])

    def close(self):
        for connection in self.connections.values():connection.close()
        self.connections.clear()


def verify_dataset(root):
    if (root/'collection.lock').exists():raise RuntimeError('Collection is still active')
    contract=json.loads((root/'collection.json').read_text())
    manifest=json.loads((root/'manifest.json').read_text())
    if manifest['status'] not in ('complete','budget_complete'):
        raise ValueError('Collection did not finish cleanly')
    if manifest['source_contract_sha256']!=sha(root/'collection.json'):
        raise ValueError('Collection contract changed')
    verify_sources(contract['sources'])
    if manifest['source_fingerprint']!=fingerprint(contract['sources']):raise ValueError('Source identity differs')
    planned={e['id']:e for e in contract['plan']};seen=set();worlds=set();splits=Counter()
    for e in manifest['entries']:
        if e['id'] in seen or e['scenario']['world_seed'] in worlds:raise ValueError('Duplicate world/episode')
        seen.add(e['id']);worlds.add(e['scenario']['world_seed']);splits[e['role']]+=1
        for key,value in planned[e['id']].items():
            if e[key]!=value:raise ValueError('Scenario differs from frozen collection plan')
        path=(root/e['database']).resolve()
        if not path.is_relative_to(root.resolve()):raise ValueError('Foreign database path')
        if sha(path)!=e['database_sha256']:raise ValueError('Database checksum mismatch')
        db=open_read(path)
        try:
            saved=json.loads(db.execute("SELECT value FROM info WHERE key='contract'").fetchone()[0])
            result=json.loads(db.execute("SELECT value FROM info WHERE key='result'").fetchone()[0])
            if saved['source_fingerprint']!=manifest['source_fingerprint'] or saved['entry']!=planned[e['id']]:
                raise ValueError('Foreign or historical recording')
            if saved.get('schema')!='drone.search.fresh_episode.v1' or saved.get('radio') is not False:
                raise ValueError('Recording is outside the fresh no-radio contract')
            if result['frames']!=e['frames'] or not result['condition_valid']:raise ValueError('Incomplete/invalid episode')
            if result['identity_labels']!=e['identity_labels']:raise ValueError('Identity coverage receipt differs')
        finally:db.close()
    for role,minimum in config()['minimum_episodes'].items():
        if splits[role]<minimum:raise ValueError(f'Need at least {minimum} fresh {role} episodes; got {splits[role]}')
    # Test labels/pixels are not read for selection or coverage checks.
    for role in ('training','validation'):
        counts=Counter()
        for e in manifest['entries']:
            if e['role']==role:counts.update(e['identity_labels'])
        if min(counts['target'],counts['different'])<16:
            raise ValueError(f'{role} lacks 16 resolved labels of each class: {dict(counts)}; collect more fresh worlds')
    return manifest


def parameter_hash(module):
    import hashlib
    h=hashlib.sha256()
    for name,tensor in module.state_dict().items():
        h.update(name.encode());h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def epoch(head,base,loader,device,optimizer=None):
    head.train(optimizer is not None);base.eval();counts=0;totals=Counter()
    for images,target in loader:
        images=images.to(device);target={k:v.to(device) for k,v in target.items()}
        fine,context=encode_maps(base,images)
        with torch.set_grad_enabled(optimizer is not None):
            output=head(fine,context);value,parts=loss(output,target)
            if not torch.isfinite(value):raise FloatingPointError('Nonfinite loss')
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True);value.backward()
                norm=torch.nn.utils.clip_grad_norm_(head.parameters(),config()['gradient_clip'])
                if not torch.isfinite(norm):raise FloatingPointError('Nonfinite gradient')
                optimizer.step()
        n=len(images);counts+=n;totals['total']+=float(value.detach())*n
        for k,v in parts.items():totals[k]+=float(v.detach())*n
    if not counts:raise ValueError('Empty data loader')
    return {k:v/counts for k,v in totals.items()}|dict(frames=counts)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir');p.add_argument('--output-dir',type=Path,default=HERE/'output')
    p.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    p.add_argument('--loader-workers',type=int,default=0)
    args=p.parse_args()
    if args.loader_workers<0:p.error('Nonnegative loader worker count required')
    c=config();root=dataset_root(args.data_dir)
    if args.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; explicitly use --device cpu')
    manifest=verify_dataset(root)
    out=args.output_dir.resolve()
    if out.exists():raise FileExistsError('Output directory exists; choose a new --output-dir to preserve checkpoints')
    if shutil.disk_usage(root).free<c['disk_free_reserve_bytes']:
        raise OSError('Keep 5 GB free for training/OS overhead')
    out.mkdir(parents=True)
    torch.set_num_threads(2);torch.manual_seed(c['seed']);random.seed(c['seed'])
    import numpy as np
    np.random.seed(c['seed'])
    base=load_backbone(args.device);before=parameter_hash(base)
    head=SearchHead().to(args.device)
    optimizer=torch.optim.AdamW(head.parameters(),lr=c['learning_rate'],weight_decay=c['weight_decay'])
    train=[e for e in manifest['entries'] if e['role']=='training']
    val=[e for e in manifest['entries'] if e['role']=='validation']
    validation=Frames(root,val)
    def loader(data,shuffle):
        return DataLoader(data,batch_size=c['batch_size'],shuffle=shuffle,num_workers=args.loader_workers,
            generator=torch.Generator().manual_seed(c['seed']),pin_memory=args.device=='cuda')
    vloader=loader(validation,False)
    write_json(out/'provenance.json',dict(created_utc=utc(),dataset_manifest_sha256=sha(root/'manifest.json'),
        source_fingerprint=manifest['source_fingerprint'],configuration=c,base_frozen=True,
        old_records_used=0,test_frames_used=0,pose_sha256=c['pose_sha256'],spatial_sha256=c['spatial_sha256']))
    best=math.inf;history=[]
    # Keep all worlds available. Curriculum weights are distance admission only;
    # a budget-limited corpus may have very few near worlds, so fall back explicitly.
    try:
        for number in range(1,c['epochs']+1):
            maximum=60 if number<=3 else 80 if number<=6 else 100
            selected=[e for e in train if e['scenario']['distance']<=maximum]
            fallback=not selected
            if fallback:selected=train
            dataset=Frames(root,selected)
            try:training=epoch(head,base,loader(dataset,True),args.device,optimizer)
            finally:dataset.close()
            metrics=epoch(head,base,vloader,args.device)
            score=metrics['heat']+metrics['evidence']+metrics['identity']
            row=dict(epoch=number,maximum_distance_m=maximum,curriculum_fallback=fallback,
                     training=training,validation=metrics,selection_score=score)
            history.append(row);write_json(out/'history.json',history);print(canonical(row),flush=True)
            if score<best:
                best=score
                saved=dict(schema='drone.search.transfer_head.v1',model=head.state_dict(),epoch=number,
                    pose_sha256=c['pose_sha256'],spatial_sha256=c['spatial_sha256'],configuration=c,
                    dataset_manifest_sha256=sha(root/'manifest.json'),test_frames_used=0)
                temp=out/'search_best.tmp';torch.save(saved,temp);temp.replace(out/'search_best.pt')
        if parameter_hash(base)!=before:raise AssertionError('Frozen base policy changed')
        # An inference-ready repo-local bundle; production/browser policy is not overwritten.
        (out/'base').mkdir()
        shutil.copy2(weight_path('pose'),out/'base/pose.pt')
        shutil.copy2(weight_path('spatial'),out/'base/spatial_acquisition.pt')
        write_json(out/'policy.json',dict(schema='drone.search.student.v1',runtime='runtime.SearchRuntime',
            checkpoint='search_best.pt',checkpoint_sha256=sha(out/'search_best.pt'),
            base='base/pose.pt',source_fingerprint=manifest['source_fingerprint'],
            allow_visual_landing=True,boat_radio=False,qualified=False))
        write_json(out/'result.json',dict(status='trained',best_validation_score=best,
            frozen_base_unchanged=True,test_frames_used=0,production_policy_changed=False))
    finally:validation.close()


if __name__=='__main__':main()
