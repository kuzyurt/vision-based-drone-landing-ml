from pathlib import Path
import json,datetime
R=Path(__file__).parent
s=(R/'train_static_verifier_v38.py').read_text().split('def main():')[0]
s=s.replace("DATA=ROOT/'static_repair_v38';OUT=ROOT/'perception_training_v38'","DATA=ROOT/'static_repair_v44b';OUT=ROOT/'perception_training_v45'").replace("PARENT=OLD/'perception_training_v12_rgb_only/best.pt'","PARENT=ROOT/'perception_training_v38/best.pt'").replace("out=ROOT/'roi_cache/static_v38'","out=ROOT/'roi_cache/static_v44b'")
s=s.replace("frame=dict(label=label,predictions=proposed", "if label.get('static_view_contact_excluded',False):continue\n                        frame=dict(label=label,predictions=proposed")
s=s.replace("if j is None:background+=1", "if j is None:background+=1\n            elif data['classes'][f['offset']+k]==2:unknown+=1")
s+= '''
def load_cache(root):
    m=json.loads((root/'manifest.json').read_text());assert m['status']=='completed';data={}
    for r in m['roles']:
        q=root/r['role']
        for n,digest in r['files'].items():assert sha(q/(n+'.npy'))==digest
        data[r['role']]={n:np.load(q/(n+'.npy'),mmap_mode='r')for n in ['rgb','meta','classes','marker','mask']};data[r['role']]['frames']=json.loads((q/'frames.json').read_text())
    return data
def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['cache','train'],required=True);a=p.parse_args();torch.set_num_threads(1);torch.manual_seed(2026102045);start=time.monotonic()
    assert sha(PARENT)=='52f1c07a09aa781889d6187dab4817047526b0c24234b6ef245920fd709ad588';saved=torch.load(PARENT,map_location='cpu',weights_only=False)
    if a.stage=='cache':cache(saved);print('cache_ready_for_actual_visual_inspection',flush=True);return
    review=json.loads((DATA/'agent_visual_review.json').read_text());assert review['passed']and review['sheet_sha256']==sha(ROOT/'roi_cache/static_v44b/actual_static_labels.jpg')
    OUT.mkdir(exist_ok=False);fresh=load_cache(ROOT/'roi_cache/static_v44b');old=load_cache(ROOT/'roi_cache/static_v38');model=ObjectVerifier(mode='rgb_only').cuda();model.load_state_dict(saved['verifier'])
    groups={'new_close':fresh['validation'],'wide_rehearsal':old['validation']};baseline={k:evaluate(model,d)for k,d in groups.items()};save(OUT/'baseline_validation.json',baseline)
    provenance=dict(parent_sha256=sha(PARENT),source_sha256=sha(__file__),cache_hashes={k:sha(ROOT/('roi_cache/'+k+'/manifest.json'))for k in ['static_v44b','static_v38']},teacher_or_failed_trajectory_images_used=False,action_targets_used=False,tidewater_used=False,heldout_used=False,original_detector_pose_spatial_frozen=True,maximum_epochs=8,patience=3,selection='zero false assertions in BOTH groups, wide recall >= baseline minus .02, new-close false reduced when present; cold cropped unknown counted unknown')
    save(OUT/'provenance.json',provenance);train={n:np.concatenate([old['training'][n],fresh['training'][n]])for n in ['rgb','meta','classes','marker','mask']}
    counts=np.bincount(train['classes'][train['classes']>=0],minlength=3);w=np.sqrt(counts.sum()/np.maximum(counts,1));weights=torch.tensor(w/w.mean(),device='cuda',dtype=torch.float32);optimizer=torch.optim.AdamW([p for n,p in model.named_parameters()if n.startswith('rgb')],lr=5e-5,weight_decay=1e-3);rng=np.random.default_rng(2026102045);history=[];best=float('inf');stale=0;selected=False
    def false(x):return sum(x['selected_operating_point'][k]for k in ['wrong_object_acceptances','ambiguous_acceptances','background_acceptances'])
    for epoch in range(1,9):
        model.train();order=rng.permutation(len(train['classes']));losses=[]
        for at in range(0,len(order),128):
            ix=order[at:at+128];rgb=torch.tensor(train['rgb'][ix],device='cuda').float();meta=torch.tensor(train['meta'][ix],device='cuda').float();y=torch.tensor(train['classes'][ix],device='cuda');mask=torch.tensor(train['mask'][ix],device='cuda');marker=torch.tensor(train['marker'][ix],device='cuda');pred=model(rgb.new_zeros((len(ix),1)),meta,rgb)
            loss=(F.cross_entropy(pred['identity'],y,weight=weights,ignore_index=-100)if(y>=0).any()else pred['identity'].sum()*0)+.25*(F.binary_cross_entropy_with_logits(pred['marker'][mask],marker[mask])if mask.any()else pred['marker'].sum()*0);assert torch.isfinite(loss);optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3);optimizer.step();losses.append(float(loss.detach()))
        metrics={k:evaluate(model,d)for k,d in groups.items()};valid=all(false(v)==0 for v in metrics.values())and metrics['wide_rehearsal']['selected_operating_point']['target_recall']>=baseline['wide_rehearsal']['selected_operating_point']['target_recall']-.02 and (false(baseline['new_close'])==0 or false(metrics['new_close'])<false(baseline['new_close']))
        score=sum(v['score']for v in metrics.values());row=dict(epoch=epoch,loss=float(np.mean(losses)),validation_groups=metrics,admissible=valid,wall_s=time.monotonic()-start);history.append(row)
        ck=dict(saved);ck.update(verifier={k:v.detach().cpu()for k,v in model.state_dict().items()},epoch=epoch,validation=metrics['new_close'],validation_groups=metrics,optimizer=optimizer.state_dict(),numpy_rng_state=rng.bit_generator.state,torch_rng_state=torch.get_rng_state(),provenance_sha256=sha(OUT/'provenance.json'),experimental_not_qualified=True);atomic_pt(OUT/'latest.pt',ck)
        if valid and score<best:best=score;stale=0;selected=True;atomic_pt(OUT/'best.pt',ck)
        else:stale+=1
        save(OUT/'history.json',history);save(OUT/'state.json',dict(status='training',**row));print(json.dumps(row),flush=True)
        if stale>=3 and selected:break
    result=dict(status='completed',improved_validation_candidate=selected,parent_validation_groups=baseline,selected_sha256=sha(OUT/'best.pt')if selected else None,latest_sha256=sha(OUT/'latest.pt'),epochs=len(history),wall_s=time.monotonic()-start,qualified_for_production=False)
    if selected:result['selected_validation']=torch.load(OUT/'best.pt',map_location='cpu',weights_only=False)['validation'];result['selected_validation_groups']=torch.load(OUT/'best.pt',map_location='cpu',weights_only=False)['validation_groups']
    save(OUT/'result.json',result);save(OUT/'state.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
'''
compile(s,'train_static_verifier_v45.py','exec');(R/'train_static_verifier_v45.py').write_text(s)
status=R/'STATUS.md';status.write_text('''# Latest 07:51 UTC — V42 stopped, fresh near-view repair running

V42 natural old-R15 learner collided with a copied-cross board at40.332 task seconds.
No expert takeover occurred. Coordinator658161 and auditor662160 EXITED; seven
other jobs were interrupted after the safety event, ninth never started. This is
not0/9 landing reliability. Raw failed/interrupted cohort explicitly quarantined;
closed receipt search_v42/COHORT_CLOSED_AFTER_SAFETY.json. Exact seven orphaned owned
PX4 processes cleaned at07:47. Old stale running state preserved as history.

Static near-view V44b coordinator663782 active,8bounded workers,3200NEW MuJoCo
images on frozen disjoint train/validation worlds, five maps/palettes, actual pan,
near marker-only/partial views plus wide rehearsal. Static-contact views excluded
from training. No failed V42 RGB or old quarantined datasets used for training.
V45 trainer prepared: V38 initializer/rehearsal plus fresh close views, fixed
validation groups, no extra false assertions, preserve wide recall. Needs actual
label review before training. No bulk teacher trajectories eligible yet.

Proposed sustained-unverified-descent takeover is NOT integrated or qualified:
requires actual>=1m height loss, >=3s observable descent, >=10distinct captures,
then>=2s continued actual descent with fresh learner metric but NO confirmed
teacher design identity. Not a wrong-identity oracle or tiny startup request.
Must replay/test and physically verify before calling it a rescue.

Actual trained V38 best/latest and full V39 runtime recovery already SHA-verified
locally; local Windows CPU restoration passed. Watcher1484 remains independent;
30min heartbeat active. Delivery target13:00 UTC; no further approval pause.

'''+status.read_text())
p=R/'EXECUTION_STATE.json';d=json.loads(p.read_text());d.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase='P02_NEAR_VIEW_REPAIR_AFTER_V42_SAFETY_STOP',active_coordinator_pid=663782,active_auditor_pid=None,latest_failed_cohort='search_v42/COHORT_CLOSED_AFTER_SAFETY.json',next_action='Finish staticV44b/cache, inspect labels, boundedV45training and tested actual-descent intervention; preserve failed raw, no bulk until actual purpose gates.');p.write_text(json.dumps(d,indent=2))
