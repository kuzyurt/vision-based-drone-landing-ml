"""Fixed-split fresh MuJoCo visual repair; never consumes teacher trajectories."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import hashlib,importlib,json,sys,time
import h5py,numpy as np,torch
from torch.nn import functional as F
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent;SRC=ROOT/'search_v35/sources';DATA=ROOT/'static_repair_v37';OUT=ROOT/'perception_training_v37';BUNDLE=ROOT.parents[1]/'landing_hardening_20261018T011610Z/candidate_r15';PARENT=OLD/'perception_training_v12_rgb_only/best.pt'
sys.path.insert(0,str(SRC));sys.path.insert(1,str(OLD))
from target_learning.expert_adapter_v22 import load_parent
from target_learning.discriminator_v5 import Discriminator,decode
from target_learning.object_verifier import regions
from target_learning.object_verifier_v12 import ObjectVerifier,rgb_regions
from train_object_verifier_v8 import matched
from train_design_and_marker_v12 import class_label
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,x):t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2,allow_nan=False));t.replace(p)
def atomic_pt(p,x):t=p.with_suffix('.tmp');torch.save(x,t);t.replace(p)
@torch.inference_mode()
def cache(saved):
    manifest=json.loads((DATA/'manifest.json').read_text());assert manifest['status']=='completed'and manifest['frames']==720 and not manifest['teacher_actions']
    out=ROOT/'roi_cache/static_v37';out.mkdir(parents=True,exist_ok=False);parent=load_parent(BUNDLE,'static_repair_frozen_features');config=json.loads((BUNDLE/'policy.json').read_text());runtime=parent.RadioRobustRuntime(BUNDLE/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True);spatial=importlib.import_module(parent.__package__+'.spatial_acquisition');detector=Discriminator().cuda();detector.load_state_dict(saved['model']);detector.eval();rng=np.random.default_rng(2026102037);result={};receipts=[]
    from PIL import Image,ImageDraw
    sheet=Image.new('RGB',(1280,1080));shown=0
    for role in ['training','validation']:
        crops=[];metas=[];classes=[];markers=[];mask=[];frames=[];sources=[]
        for e in manifest['entries']:
            j=e['job']
            if j['role']!=role:continue
            path=DATA/j['name']/'data.h5';assert sha(path)==e['data_sha256'];sources.append(dict(path=str(path),sha256=e['data_sha256'],world_seed=j['world_seed']))
            with h5py.File(path,'r')as h:
                assert h.attrs['schema']=='approved.static.visual-development.v36'and not h.attrs['teacher_actions']and h.attrs['role']==role
                for at in range(0,len(h['rgb']),8):
                    raw=np.asarray(h['rgb'][at:at+8]);images=torch.from_numpy(raw).permute(0,3,1,2).cuda();fine,context=spatial.encode_spatial(runtime.model.backbone,images);pred=decode({k:v.cpu()for k,v in detector(fine,context).items()},minimum_presence=.2,topk=24)
                    for b,proposed in enumerate(pred):
                        label=json.loads(h['labels'][at+b]);assert label['role']==role and label['world_seed']==j['world_seed']and hashlib.sha256(raw[b].tobytes()).hexdigest()==label['rgb_sha256'];assert not label['actor_input']and not label['teacher_actions']
                        frame=dict(label=label,predictions=proposed,offset=len(classes),count=len(proposed));frames.append(frame);proposals=list(proposed)
                        if role=='training':
                            for inst in label['instances']:
                                if inst['identity']==-2:continue
                                box=np.asarray(inst['bbox'],float);center=(box[:2]+box[2:])/2;size=box[2:]-box[:2]
                                for _ in range(2 if inst['identity']==1 else 1):proposals.append(dict(pixel=(center+rng.uniform(-.08,.08,2)*size).tolist(),size_px=(size*rng.uniform(.9,1.15,2)).tolist()))
                        if not proposals:continue
                        _,meta=regions(fine[b:b+1],context[b:b+1],[[*p['pixel'],*p['size_px']]for p in proposals],[0]*len(proposals));crop=rgb_regions(images[b:b+1],meta);crops.append(crop.cpu().numpy());metas.append(meta.cpu().numpy())
                        for p in proposals:
                            k=matched(p,label['instances']);inst=label['instances'][k]if k is not None else None;classes.append(class_label(p,inst));marker=False;valid=inst is None or inst.get('marker_label_available',False)
                            if inst is not None:
                                # Actual cyan, restricted to this annotated object and crop.
                                rgb=raw[b].astype(np.int16);cyan=(np.minimum(rgb[...,1],rgb[...,2])-rgb[...,0]>45)&(rgb[...,1]>=rgb[...,2]-12)&(rgb[...,1]>85);x0,y0,x1,y1=inst['bbox'];marker=int(cyan[y0:y1,x0:x1].sum())>=32 and inst.get('marker_visible_pixels',0)>=32
                                if marker and inst.get('pad_pixel')is not None:
                                    point=np.asarray(inst['pad_pixel']);lo=np.asarray(p['pixel'])-1.25*np.asarray(p['size_px']);hi=np.asarray(p['pixel'])+1.25*np.asarray(p['size_px']);marker=bool(np.all(point>=lo)and np.all(point<=hi))
                            markers.append(float(marker));mask.append(bool(valid))
                        if role=='validation'and shown<12 and at+b in [0,8,24]:
                            im=Image.fromarray(raw[b]);d=ImageDraw.Draw(im)
                            for inst in label['instances']:d.rectangle(inst['bbox'],outline='lime'if inst['identity']==1 else'orange',width=2);d.text(tuple(inst['bbox'][:2]),inst['annotation_instance']+':'+str(inst['identity']),fill='white')
                            im=im.resize((320,180));sheet.paste(im,((shown%4)*320,(shown//4)*180));shown+=1
        data=dict(rgb=np.concatenate(crops),meta=np.concatenate(metas),classes=np.asarray(classes,np.int64),marker=np.asarray(markers,np.float32),mask=np.asarray(mask,bool),frames=frames);dst=out/role;dst.mkdir()
        for n in ['rgb','meta','classes','marker','mask']:np.save(dst/(n+'.npy'),data[n])
        save(dst/'frames.json',frames);receipt=dict(role=role,frames=len(frames),regions=len(classes),class_counts=np.bincount(data['classes'][data['classes']>=0],minlength=3).tolist(),sources=sources,validation_deployed_proposals_only=role=='validation',files={n:sha(dst/(n+'.npy'))for n in ['rgb','meta','classes','marker','mask']});save(dst/'receipt.json',receipt);receipts.append(receipt);result[role]=data
    sheet.save(out/'actual_static_labels.jpg',quality=85);assert not({x['world_seed']for x in receipts[0]['sources']}&{x['world_seed']for x in receipts[1]['sources']});save(out/'manifest.json',dict(status='completed',roles=receipts,source_sha256=sha(__file__),data_manifest_sha256=sha(DATA/'manifest.json'),no_action_targets=True,old_quarantined_images_used=False));del runtime,detector;torch.cuda.empty_cache();return result
@torch.inference_mode()
def evaluate(model,data):
    model.eval();prob=[]
    for at in range(0,len(data['rgb']),256):
        raw=torch.tensor(data['rgb'][at:at+256],device='cuda').float();meta=torch.tensor(data['meta'][at:at+256],device='cuda').float();pred=model(raw.new_zeros((len(raw),1)),meta,raw);prob.extend(pred['identity'].softmax(-1).cpu().tolist())
    known=objects=matched_count=true=wrong=unknown=background=0
    for f in data['frames']:
        instances=f['label']['instances'];known+=sum(i['identity']==1 for i in instances);objects+=len(instances);seen=set();accepted=set()
        for k,p in enumerate(f['predictions']):
            j=matched(p,instances)
            if j is not None:seen.add(j)
            if p['presence']<.3 or prob[f['offset']+k][1]<.98:continue
            if j is None:background+=1
            elif instances[j]['identity']==0:wrong+=1
            elif instances[j]['identity']==-1:unknown+=1
            elif instances[j]['identity']==1 and j not in accepted:true+=1;accepted.add(j)
        matched_count+=len(seen)
    point=dict(heat=.3,identity=.98,support=.8,target_recall=true/max(known,1),accepted_true_objects=true,wrong_object_acceptances=wrong,ambiguous_acceptances=unknown,background_acceptances=background)
    return dict(known_targets=known,object_instances=objects,object_recall=matched_count/max(objects,1),selected_operating_point=point,selected_marker_operating_point=dict(threshold=.98),expert_gate_passed=False,original_parent_80pct_gate_remains_failed=True,score=100*(wrong+background)+10*unknown+100*(1-point['target_recall']))
def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['cache','train'],required=True);args=parser.parse_args()
    torch.set_num_threads(1);torch.manual_seed(2026102037);start=time.monotonic();assert sha(PARENT)=='c87dca7541d361b183ce45da5f7756bdc5a358aaf544fb2bc5c3fc08bad1e0e3';saved=torch.load(PARENT,map_location='cpu',weights_only=False)
    if args.stage=='cache':
        cache(saved);print('cache_closed_ready_for_agent_visual_inspection',flush=True);return
    OUT.mkdir(exist_ok=False);cacheroot=ROOT/'roi_cache/static_v37';m=json.loads((cacheroot/'manifest.json').read_text());assert m['status']=='completed'and m['source_sha256']==sha(__file__);visual=json.loads((ROOT/'static_repair_v37/agent_visual_review.json').read_text());assert visual['passed']and visual['sheet_sha256']==sha(cacheroot/'actual_static_labels.jpg')
    data={}
    for receipt in m['roles']:
        role=receipt['role'];q=cacheroot/role
        for n,digest in receipt['files'].items():assert sha(q/(n+'.npy'))==digest
        data[role]={n:np.load(q/(n+'.npy'),mmap_mode='r')for n in ['rgb','meta','classes','marker','mask']};data[role]['frames']=json.loads((q/'frames.json').read_text())
    model=ObjectVerifier(mode='rgb_only').cuda();model.load_state_dict(saved['verifier']);baseline=evaluate(model,data['validation']);save(OUT/'baseline_validation.json',baseline)
    provenance=dict(parent_sha256=sha(PARENT),data_manifest_sha256=sha(DATA/'manifest.json'),cache_manifest_sha256=sha(ROOT/'roi_cache/static_v37/manifest.json'),source_sha256=sha(__file__),new_static_rgb_only=True,old_failed_teacher_images_used=False,teacher_actions_used=False,heldout_used=False,tidewater_used=False,original_pose_spatial_and_detector_frozen=True,maximum_epochs=8,patience=3,fixed_validation_point=[.3,.98]);save(OUT/'provenance.json',provenance)
    optimizer=torch.optim.AdamW([p for n,p in model.named_parameters()if n.startswith('rgb')],lr=1e-4,weight_decay=1e-3);train=data['training'];counts=np.bincount(train['classes'][train['classes']>=0],minlength=3);weights=np.sqrt(counts.sum()/np.maximum(counts,1));weights/=weights.mean();weights=torch.tensor(weights,dtype=torch.float32,device='cuda');rng=np.random.default_rng(2026102037);best=baseline['score'];history=[];stale=0;selected=False
    for epoch in range(1,9):
        model.train();order=rng.permutation(len(train['classes']));losses=[]
        for at in range(0,len(order),128):
            ix=order[at:at+128];rgb=torch.tensor(train['rgb'][ix],device='cuda').float();meta=torch.tensor(train['meta'][ix],device='cuda').float();y=torch.tensor(train['classes'][ix],device='cuda');marker=torch.tensor(train['marker'][ix],device='cuda');mask=torch.tensor(train['mask'][ix],device='cuda');pred=model(rgb.new_zeros((len(ix),1)),meta,rgb)
            identity=F.cross_entropy(pred['identity'],y,weight=weights)if(y>=0).any()else pred['identity'].sum()*0;loss=identity+.25*(F.binary_cross_entropy_with_logits(pred['marker'][mask],marker[mask])if mask.any()else pred['marker'].sum()*0);assert torch.isfinite(loss);optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3);optimizer.step();losses.append(float(loss.detach()))
        metrics=evaluate(model,data['validation']);row=dict(epoch=epoch,loss=float(np.mean(losses)),validation=metrics,wall_s=time.monotonic()-start);history.append(row)
        ck=dict(saved);ck.update(verifier={k:v.detach().cpu()for k,v in model.state_dict().items()},epoch=epoch,validation=metrics,optimizer=optimizer.state_dict(),numpy_rng_state=rng.bit_generator.state,torch_rng_state=torch.get_rng_state(),provenance_sha256=sha(OUT/'provenance.json'),experimental_not_qualified=True)
        atomic_pt(OUT/'latest.pt',ck)
        if metrics['score']<best and metrics['selected_operating_point']['wrong_object_acceptances']<=baseline['selected_operating_point']['wrong_object_acceptances']and metrics['selected_operating_point']['background_acceptances']<=baseline['selected_operating_point']['background_acceptances']:
            best=metrics['score'];stale=0;selected=True;atomic_pt(OUT/'best.pt',ck)
        else:stale+=1
        save(OUT/'history.json',history);save(OUT/'state.json',dict(status='training',**row));print(json.dumps(row),flush=True)
        if stale>=3:break
    result=dict(status='completed',improved_validation_candidate=selected,parent_validation=baseline,selected_sha256=sha(OUT/'best.pt')if selected else None,latest_sha256=sha(OUT/'latest.pt'),epochs=len(history),wall_s=time.monotonic()-start,qualified_for_production=False)
    if selected:result['selected_validation']=torch.load(OUT/'best.pt',map_location='cpu',weights_only=False)['validation']
    save(OUT/'result.json',result);save(OUT/'state.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
