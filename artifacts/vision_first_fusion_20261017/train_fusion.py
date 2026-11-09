"""Train only new radio fusion weights on unchanged approved train/validation RGB."""
import os
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import collections,concurrent.futures,hashlib,json,multiprocessing,sys,time
from pathlib import Path
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[2]
OLD=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
QUAL=BASE/'landing_training/outputs/observable_policy_20261016T203932Z'
sys.path[:0]=[str(BASE),str(ROOT)]
from landing_training import paths
import landing_training
landing_training.__path__.insert(0,str(ROOT/'candidate/code/landing_training'))
from landing_training.radio_robust_20261015.model import RadioRobustPoseModel
from landing_training.radio_robust_20261015.train import Metrics
from landing_training.training_pipeline import ChunkLoader,chunk_plan,frame_counts
from landing_training.recording import numeric_observation
from coherent_radio import augment,MODES

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()
def save(path,value):
    p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False));tmp.replace(p)

def prepare(entry):
    assert entry['role'] in ['training','validation']
    cache=Path(entry['cache']);target=Path(entry['target']);name=hashlib.sha256(str(cache).encode()).hexdigest()[:24]
    output=ROOT/'motion_cache'/(name+'.npz');receipt=output.with_suffix('.json')
    if receipt.exists():
        old=json.loads(receipt.read_text());assert sha(output)==old['motion_sha256'];return old
    assert sha(cache)==entry['cache_sha256'] and sha(target)==entry['target_sha256']
    with h5py.File(cache,'r') as f:
        source=Path(str(f.attrs['source_path']));numeric=f['numeric'][:]
        assert str(f.attrs['role'])==entry['role']
    sensor=np.empty((len(numeric),10),dtype='f8');digest=hashlib.sha256()
    with h5py.File(source,'r') as raw:
        assert len(raw['steps'])==len(numeric) and raw.attrs['role']==entry['role']
        for start in range(0,len(numeric),256):
            encoded=raw['steps'][start:start+256];rows=[json.loads(x) for x in encoded]
            for x in encoded:digest.update(x if isinstance(x,bytes) else x.encode())
            assert np.array_equal(np.asarray([numeric_observation(row) for row in rows]),numeric[start:start+len(rows)])
            for i,row in enumerate(rows,start):
                obs=row['observation'];truth=row['privileged']
                sensor[i]=[row['time_s'],*obs['px4']['position_enu_m'],*truth['pad_position_enu_m'],*truth['pad_velocity_enu_m_s']]
    if entry.get('metadata_sha256'):assert digest.hexdigest()==entry['metadata_sha256']
    assert np.all(np.diff(sensor[:,0])>=0.)
    np.savez(output,sensor=sensor,numeric=numeric,target=np.load(target))
    value=dict(entry)
    value.update(motion=str(output),motion_sha256=sha(output),source_path=str(source),metadata_sha256=digest.hexdigest(),records=len(numeric))
    save(receipt,value);return value

def cache_visual(model,entries):
    done=ROOT/'visual_cache_complete.json'
    if done.exists():return
    paths_=[Path(e['cache']) for e in entries];mapping={e['cache']:e for e in entries}
    counts=frame_counts(paths_);hidden={};opened={};completed=0;began=time.monotonic()
    with ChunkLoader(chunk_plan(paths_,counts,lanes=8,steps=64),cached=True,workers=0,device='cuda') as loader,torch.inference_mode():
        for items in loader.updates():
            groups={}
            for item in items:groups.setdefault(len(item['values'][0]),[]).append(item)
            for group in groups.values():
                features=torch.stack([i['values'][0] for i in group]).cuda()
                numeric=torch.stack([i['values'][1] for i in group]).cuda()
                state=torch.cat([hidden.get(i['spec']['token'],torch.zeros(1,1,128,device='cuda')) for i in group],1)
                prediction,_,state=model.visual_features(features,numeric,state)
                prediction=prediction.cpu().numpy()
                for j,item in enumerate(group):
                    spec=item['spec'];e=mapping[spec['path']];p=Path(e['motion']).with_suffix('.visual.npy')
                    if spec['token'] not in opened:opened[spec['token']]=np.lib.format.open_memmap(p,mode='w+',dtype='f4',shape=(e['records'],15))
                    opened[spec['token']][spec['start']:spec['stop']]=prediction[j]
                    if spec['end']:
                        opened.pop(spec['token']).flush();hidden.pop(spec['token'],None);completed+=1
                        if completed%100==0:
                            save(ROOT/'training_state.json',dict(status='running',stage='independent_visual_cache',completed=completed,planned=len(entries),elapsed_s=time.monotonic()-began))
                            print('VISUAL_CACHE',completed,len(entries),flush=True)
                    else:hidden[spec['token']]=state[:,j:j+1].detach()
    assert not opened
    save(done,dict(complete=True,episodes=completed,parent_sha256=sha(QUAL/'bundle_spatial_r8/pose.pt'),elapsed_s=time.monotonic()-began))

def build_rows(entries,epoch,mode):
    chunks=[];counts=collections.Counter()
    for e in entries:
        data=np.load(e['motion']);numeric,quality,chosen=augment(data['sensor'],data['numeric'],key=e['cache'],epoch=epoch,mode=mode)
        counts[chosen]+=len(numeric)
        chunks.append(np.concatenate((np.load(Path(e['motion']).with_suffix('.visual.npy')),numeric,quality,data['target']),axis=1))
    return np.concatenate(chunks).astype('f4'),dict(counts)

def tensor_rows(data):
    x=torch.from_numpy(data).cuda();return x[:,:15],x[:,15:47],x[:,47:49],x[:,49:64]

def assess(model,data):
    metrics=Metrics();weights=[];bad=[]
    with torch.inference_mode():
        for start in range(0,len(data),16384):
            visual,numeric,quality,target=tensor_rows(data[start:start+16384])
            prediction,w,_,position,_=model.fuse(visual,numeric,quality)
            metrics.add(prediction[:,None],target[:,None]);visible=target[:,0]>.5
            mask=visible&(numeric[:,21]>.5)&((position-target[:,1:4]).norm(dim=-1)>2.)
            if mask.any():bad.extend(w[mask,0].cpu().tolist())
            weights.extend(w[visible,0].cpu().tolist())
    result=metrics.result();result.update(mean_radio_weight=float(np.mean(weights)),bad_radio_mean_weight=float(np.mean(bad)) if bad else None,bad_radio_frames=len(bad))
    return result

def main():
    started=time.monotonic();torch.set_num_threads(2);torch.manual_seed(271017);np.random.seed(271017)
    mixed=json.loads((OLD/'mixed_dataset.json').read_text())
    assert sha(BASE/'landing_training/datasets/expert/manifest.json')==mixed['original_manifest_sha256']
    assert sha(OLD/'dataset/manifest.json')==mixed['supplemental_manifest_sha256']
    assert sha(OLD/'authorization.json')==mixed['authorization_sha256']
    parent=torch.load(QUAL/'bundle_spatial_r8/pose.pt',map_location='cpu',weights_only=False)
    assert sha(QUAL/'bundle_spatial_r8/pose.pt')=='c2990e69e254cbeddde8dd57d4cf481a2c7daa37735cd96083c7f3095512f5f7'
    old=BASE/'landing_training/outputs/control_iteration_20261010T220632Z/pose_targets/manifest.json';new=OLD/'features/manifest.json'
    entries=json.loads(old.read_text())['entries']+json.loads(new.read_text())['entries']
    assert len(entries)==1220 and all(e['role'] in ['training','validation'] for e in entries)
    # The established image/world partitions remain unchanged. No evaluation
    # traces or beach-sweep images enter training or checkpoint selection.
    (ROOT/'motion_cache').mkdir(exist_ok=True)
    prepared=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        for result in pool.map(prepare,entries,chunksize=1):
            prepared.append(result)
            if len(prepared)%100==0:
                save(ROOT/'training_state.json',dict(status='running',stage='verify_and_extract_recorded_motion',completed=len(prepared),planned=len(entries),elapsed_s=time.monotonic()-started))
                print('MOTION_CACHE',len(prepared),len(entries),flush=True)
    save(ROOT/'motion_manifest.json',dict(entries=prepared,original_manifest_sha256=sha(old),supplemental_manifest_sha256=sha(new),test_data_used=False,rgb_changed=False))
    model=RadioRobustPoseModel().cuda();missing,unexpected=model.load_state_dict(parent['model'],strict=False)
    assert set(missing)=={'fusion_gate.0.weight','fusion_gate.0.bias','fusion_gate.2.weight','fusion_gate.2.bias'} and not unexpected
    for name,p in model.named_parameters():p.requires_grad=name.startswith('fusion_gate.')
    model.eval();cache_visual(model,prepared)
    training=[e for e in prepared if e['role']=='training'];validation=[e for e in prepared if e['role']=='validation']
    assert len(training)==1080 and len(validation)==140
    print('FROZEN_VISION_CACHED',time.monotonic()-started,flush=True)
    held={mode:build_rows(validation,0,mode)[0] for mode in ['clean','biased','missing','stuck']}
    baseline={mode:assess(model,data) for mode,data in held.items()};save(ROOT/'offline_parent_fusion_initialization.json',baseline)
    # Numerical missing-radio invariance: the gate cannot affect this path.
    with torch.inference_mode():
        v,n,q,t=tensor_rows(held['missing'][:4096]);p,w,_,_,_=model.fuse(v,n,q)
        assert torch.equal(p,v) and torch.count_nonzero(w)==0
    optimizer=torch.optim.AdamW(model.fusion_gate.parameters(),lr=8e-4,weight_decay=1e-4)
    history=[];best=float('inf');best_epoch=0
    train_dir=ROOT/'training';train_dir.mkdir(exist_ok=True)
    for epoch in range(1,9):
        epoch_start=time.monotonic();data,modes=build_rows(training,epoch,'mixed');order=np.random.default_rng(epoch+271017).permutation(len(data));total=0.;updates=0
        model.fusion_gate.train()
        for start in range(0,len(data),8192):
            visual,numeric,quality,target=tensor_rows(data[order[start:start+8192]])
            prediction,w,logits,position,velocity=model.fuse(visual,numeric,quality)
            visible=target[:,0]>.5;available=(numeric[:,21]>.5)&(numeric[:,19]<3.);mask=visible&available
            if not mask.any():continue
            near=(target[:,1:3].norm(dim=-1)<1.)&(target[:,3].abs()<2.5)
            weight=torch.where(near,8.,1.)*visible
            position_loss=torch.nn.functional.huber_loss(prediction[:,1:4],target[:,1:4],delta=.1,reduction='none').mean(-1)
            velocity_loss=torch.nn.functional.huber_loss(prediction[:,4:7],target[:,4:7],delta=.05,reduction='none').mean(-1)
            loss=((8*position_loss+2*velocity_loss)*weight).sum()/weight.sum().clamp_min(1.)
            targets=[]
            for base,radio,truth in [(visual[:,1:4],position,target[:,1:4]),(visual[:,4:7],velocity,target[:,4:7])]:
                delta=radio-base;opt=((truth-base)*delta).sum(-1)/delta.square().sum(-1).clamp_min(1e-8)
                targets.append(opt.clamp(0.,model.MAX_RADIO_WEIGHT)/model.MAX_RADIO_WEIGHT)
            oracle=torch.stack(targets,-1).detach()
            loss+=.02*torch.nn.functional.binary_cross_entropy_with_logits(logits[mask],oracle[mask])
            optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.fusion_gate.parameters(),1.);optimizer.step()
            total+=float(loss.detach());updates+=1
        model.eval();metrics={mode:assess(model,x) for mode,x in held.items()}
        # Fixed validation worlds/errors select the head; neither requested
        # evaluation flight nor its images/labels are consumed here.
        score=max(v['score'] for v in metrics.values())+.25*sum(v['score'] for v in metrics.values())/len(metrics)
        item=dict(epoch=epoch,loss=total/updates,validation=metrics,score=score,mode_frames=modes,seconds=time.monotonic()-epoch_start)
        history.append(item)
        saved=dict(parent,model=model.state_dict(),epoch=epoch,source_checkpoint_sha256=sha(QUAL/'bundle_spatial_r8/pose.pt'),
            optimizer=optimizer.state_dict(),optimizer_kind='fusion_gate_only_adamw',
            training=dict(parent_training=parent['training'],vision_frozen=True,only_fusion_gate_trained=True,radio_stream='recorded physical boat motion + causal world-frame biases/noise/drift/latency/outages/stuck fixes',
                independent_visual_recurrence=True,max_radio_weight=model.MAX_RADIO_WEIGHT,new_images=False,new_collection=False,test_data_used=False,
                train_episodes=len(training),validation_episodes=len(validation),selection='fixed training-world-disjoint validation only'),validation_metrics=metrics,history=history)
        torch.save(saved,train_dir/f'epoch_{epoch:03d}.pt')
        if score<best:best=score;best_epoch=epoch;torch.save(saved,train_dir/'best.pt')
        save(ROOT/'training_history.json',history);save(ROOT/'training_state.json',dict(status='running',stage='train_fusion_gate',epoch=epoch,planned_epochs=8,best_epoch=best_epoch,elapsed_s=time.monotonic()-started))
        print('FUSION_EPOCH',json.dumps(item),flush=True)
    best_state=torch.load(train_dir/'best.pt',map_location='cpu',weights_only=False)
    # Confirm every inherited parameter remains byte-identical to the parent.
    assert all(torch.equal(best_state['model'][k],v.cpu()) for k,v in parent['model'].items())
    torch.save(best_state,ROOT/'candidate/pose.pt')
    config=json.loads((ROOT/'candidate/policy.json').read_text());config.update(checkpoint_sha256=sha(ROOT/'candidate/pose.pt'),selected_epoch=best_epoch,
        source_checkpoint_sha256=sha(QUAL/'bundle_spatial_r8/pose.pt'),runtime_revision='vision_first_fusion_v1',training=best_state['training'],
        validation_metrics=best_state['validation_metrics'],closed_loop_evaluated=False,reliability_qualified=False,target_met_on_this_sample=False)
    config['controller_changes']+=['All direct boat-radio controller inputs removed; independently gated radio can influence learned pose only. Visual search/registration cannot be vetoed by radio coordinates.']
    config['file_hashes']={str(p.relative_to(ROOT/'candidate')):sha(p) for p in (ROOT/'candidate').rglob('*') if p.is_file() and p.name!='policy.json'}
    save(ROOT/'candidate/policy.json',config)
    result=dict(status='completed',epochs=8,selected_epoch=best_epoch,train_episodes=len(training),validation_episodes=len(validation),test_data_used=False,
        parent_weights_unchanged=True,only_fusion_gate_trained=True,rgb_unchanged=True,new_collection=False,pose_sha256=config['checkpoint_sha256'],
        elapsed_s=time.monotonic()-started,validation=best_state['validation_metrics'])
    save(ROOT/'training_result.json',result);save(ROOT/'training_state.json',dict(stage='finished',**result));print('FUSION_TRAINING_COMPLETE',json.dumps(result),flush=True)

if __name__=='__main__':main()
