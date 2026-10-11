"""Train physically scaled pad-pose heads using verified frozen features."""
import argparse,hashlib,json,pathlib,random,time
import h5py,numpy as np,torch
from .pose_model import PoseModel,pose_loss
from .training_pipeline import chunk_plan,frame_counts,ChunkLoader
from .gate import file_hash,require_approval
from .collection_session import atomic_json
from .train import atomic_checkpoint
from .progress import TrainingProgress,utc_now


def update(model,items,hidden,targets,device,optimizer=None,errors=None):
    if optimizer is not None:optimizer.zero_grad()
    groups={}
    for item in items:groups.setdefault(item['values'][0].shape[0],[]).append(item)
    total_loss=0.;frames=0
    for group in groups.values():
        features=torch.stack([i['values'][0] for i in group]).to(device)
        numeric=torch.stack([i['values'][1] for i in group]).to(device)
        target=torch.from_numpy(np.stack([targets[i['spec']['path']][i['spec']['start']:i['spec']['stop']] for i in group])).to(device)
        state=torch.cat([hidden.get(i['spec']['token'],torch.zeros(1,1,128,device=device)) for i in group],dim=1)
        prediction,_,state=model.forward_features(features,numeric,state)
        loss=pose_loss(prediction,target)
        if not torch.isfinite(loss):raise FloatingPointError('Nonfinite pose loss')
        if optimizer is not None:(loss*len(group)/len(items)).backward()
        total_loss+=float(loss.detach())*len(group);frames+=features.shape[0]*features.shape[1]
        for j,item in enumerate(group):
            token=item['spec']['token']
            if item['spec']['end']:hidden.pop(token,None)
            else:hidden[token]=state[:,j:j+1].detach()
        if errors is not None:
            visible=target[...,0]>0
            near=visible&(torch.linalg.vector_norm(target[...,1:3],dim=-1)<1.)&(target[...,3].abs()<1.5)
            if near.any():
                xy=torch.linalg.vector_norm(prediction[...,1:3]-target[...,1:3],dim=-1)
                z=(prediction[...,3]-target[...,3]).abs()
                vel=torch.linalg.vector_norm(prediction[...,4:6]-target[...,4:6],dim=-1)
                predicted_angle=torch.atan2(prediction[...,7],prediction[...,8])
                angle=torch.atan2(target[...,7],target[...,8])
                heading=.5*torch.atan2(torch.sin(predicted_angle-angle),torch.cos(predicted_angle-angle)).abs()*180/np.pi
                errors.append(torch.stack([xy,z,vel,heading],dim=-1)[near].detach().cpu().numpy())
    if optimizer is not None:
        norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        if not torch.isfinite(norm):raise FloatingPointError('Nonfinite pose gradient')
        optimizer.step()
    return frames,total_loss


def train(args):
    out=pathlib.Path(args.output)
    if out.exists() and any(out.iterdir()):raise FileExistsError('Use a new model output directory')
    require_approval(args.review)
    target_root=pathlib.Path(args.targets);manifest=json.loads((target_root/'manifest.json').read_text())
    if manifest['schema']!='aerodock.landing.pose_targets.v1':raise ValueError('Unknown pose target schema')
    source=pathlib.Path(manifest['source_checkpoint'])
    if file_hash(source)!=manifest['source_checkpoint_sha256']:raise ValueError('Source checkpoint changed')
    checkpoint=torch.load(source,map_location='cpu',weights_only=False)
    if checkpoint['review_manifest_sha256']!=file_hash(pathlib.Path(args.review)/'manifest.json'):raise PermissionError('Review does not match pose targets')
    entries=manifest['entries'];splits={'training':[],'validation':[]};targets={}
    for e in entries:
        if e['role'] not in splits:raise ValueError('No test inputs allowed')
        if file_hash(e['cache'])!=e['cache_sha256'] or file_hash(e['target'])!=e['target_sha256']:raise ValueError('Pose input integrity mismatch')
        path=pathlib.Path(e['cache']);splits[e['role']].append(path);targets[str(path)]=np.load(e['target'])
    out.mkdir(parents=True,exist_ok=True);progress=TrainingProgress(out,args.epochs)
    torch.manual_seed(714);np.random.seed(714);random.seed(714);torch.set_num_threads(4)
    model=PoseModel().to(args.device)
    state=model.backbone.state_dict()
    for name,value in checkpoint['model'].items():
        if name in state and state[name].shape==value.shape:state[name]=value.to(args.device)
    model.backbone.load_state_dict(state)
    optimizer=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=1e-4)
    counts=frame_counts(splits['training']+splits['validation']);history=[];best=float('inf')
    for epoch in range(1,args.epochs+1):
        began=time.monotonic();order=splits['training'].copy();random.shuffle(order)
        model.train();model.backbone.encoder.eval();hidden={};losses=lanes=frames=steps=0
        progress.save(force=True,phase='training',current_epoch=epoch,phase_completed_frames=0,phase_total_frames=sum(counts[str(p)] for p in order))
        with ChunkLoader(chunk_plan(order,counts,lanes=8,steps=64),cached=True,workers=0,device=args.device) as loader:
            for items in loader.updates():
                n,loss=update(model,items,hidden,targets,args.device,optimizer)
                frames+=n;losses+=loss;lanes+=len(items);steps+=1
                progress.save(phase_completed_frames=frames,optimizer_steps=steps)
        model.eval();hidden={};errors=[];val_loss=val_lanes=0
        progress.save(force=True,phase='validation')
        with ChunkLoader(chunk_plan(splits['validation'],counts,lanes=1,steps=64),cached=True,workers=0,device=args.device) as loader,torch.inference_mode():
            for items in loader.updates():
                _,loss=update(model,items,hidden,targets,args.device,errors=errors)
                val_loss+=loss;val_lanes+=len(items)
        a=np.concatenate(errors);rms=np.sqrt((a*a).mean(0));p90=np.quantile(a,.9,axis=0);median=np.median(a,axis=0)
        score=float(rms[0]+.3*rms[1]+.5*rms[2]+.02*rms[3])
        metrics={'near_frames':len(a),'columns':['xy_m','z_m','velocity_m_s','heading_deg'],'rms':rms.tolist(),'p50':median.tolist(),'p90':p90.tolist()}
        item={'epoch':epoch,'train_loss':losses/lanes,'validation_loss':val_loss/val_lanes,'selection_score':score,'validation_metrics':metrics,'epoch_seconds':time.monotonic()-began,'finished_utc':utc_now()}
        improved=score<best
        if improved:best=score
        history.append(item)
        result={'schema':'aerodock.landing.pose.v1','model':model.state_dict(),'epoch':epoch,'dataset_sha256':checkpoint['dataset_sha256'],'review_manifest_sha256':checkpoint['review_manifest_sha256'],'targets_sha256':file_hash(target_root/'manifest.json'),'source_checkpoint_sha256':file_hash(source),'training':{'observation_mode':'periodic_no_action_v1','encoder_frozen':True,'learning_rate':1e-4,'sequence_steps':64,'lanes':8,'pose_units':'m,m_s,sin_cos_2heading,unit_normal,normalized_pixels','selection_metric':'near_xy_rms+.3z_rms+.5velocity_rms+.02heading_deg_rms'},'validation_metrics':metrics,'selection_score':score,'history':history,'optimizer':optimizer.state_dict()}
        atomic_checkpoint(result,out/'latest.pt')
        atomic_checkpoint(result,out/('epoch_%03d.pt'%epoch))
        if improved:atomic_checkpoint(result,out/'best.pt')
        atomic_json(out/'history.json',history);progress.save(force=True,completed_epochs=epoch)
        print(json.dumps(item),flush=True)
    atomic_json(out/'training_result.json',{'status':'completed','completed_epochs':len(history),'best_score':best,'best_checkpoint':str((out/'best.pt').resolve())})
    progress.save(force=True,status='completed',phase='finished')
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ['targets','review','output']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--epochs',type=int,default=12);parser.add_argument('--device',default='cuda')
    args=parser.parse_args()
    if args.epochs<=0:raise ValueError('Positive epoch budget required')
    train(args)
