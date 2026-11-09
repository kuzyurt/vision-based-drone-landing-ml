"""Bounded original-data spatial-head repair with exact delayed-frame masks."""
from cache_original_spatial_v1 import *
def save(p,x):t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2));t.replace(p)
def main():
    torch.set_num_threads(1);torch.manual_seed(20261020);begin=time.monotonic();receipt=json.loads((ROOT/'original_consumer_validation_receipt.json').read_text());assert receipt['status']=='frozen_original_feature_cache_and_consumer_passed'
    for n,digest in receipt['features'].items():assert sha(OUT/(n+'.npy'))==digest
    out=ROOT/'spatial_training_v3';out.mkdir(exist_ok=False);fine=np.load(OUT/'fine.npy',mmap_mode='r');context=np.load(OUT/'context.npy',mmap_mode='r');labels=np.load(OUT/'labels.npy');Pose,spatial=classes();model=spatial.SpatialAcquisition().cuda();model.load_state_dict(torch.load(BUNDLE/'spatial_acquisition.pt',map_location='cuda',weights_only=False)['model']);baseline=evaluate(model,spatial,dict(fine=fine,context=context),labels,'validation');save(out/'baseline.json',baseline)
    provenance=dict(source_sha256=sha(__file__),consumer_receipt_sha256=sha(ROOT/'original_consumer_validation_receipt.json'),parent_spatial_sha256=sha(BUNDLE/'spatial_acquisition.pt'),parent_pose_sha256=sha(BUNDLE/'pose.pt'),action_targets_used=False,identity_labels_used=False,original_test_images_used=False,exact_capture_time_labels=True,maximum_epochs=6,learning_rate=1e-4);save(out/'provenance.json',provenance)
    opt=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4);rng=np.random.default_rng(20261020);indices=np.flatnonzero(labels[:,3]<.5);best=baseline['score'];selected=False;history=[];stale=0
    for epoch in range(1,7):
        model.train();order=rng.permutation(indices);losses=[]
        for at in range(0,len(order),48):
            ix=order[at:at+48];x=torch.tensor(np.array(fine[ix]),device='cuda').float();c=torch.tensor(np.array(context[ix]),device='cuda').float();y=torch.tensor(labels[ix],device='cuda');loss=spatial_loss(model,x,c,y);assert torch.isfinite(loss);opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),3);opt.step();losses.append(float(loss.detach()))
        val=evaluate(model,spatial,dict(fine=fine,context=context),labels,'validation');row=dict(epoch=epoch,loss=float(np.mean(losses)),validation=val,wall_s=time.monotonic()-begin);history.append(row);ck=dict(model={k:v.detach().cpu()for k,v in model.state_dict().items()},optimizer=opt.state_dict(),epoch=epoch,validation=val,parent_pose_sha256=sha(BUNDLE/'pose.pt'),parent_spatial_sha256=sha(BUNDLE/'spatial_acquisition.pt'),provenance_sha256=sha(out/'provenance.json'),experimental_not_qualified=True)
        temp=out/'latest.tmp';torch.save(ck,temp);temp.replace(out/'latest.pt')
        if val['score']<best and val['false_positive_at_08']<=baseline['false_positive_at_08']and val['p90_pixel_error']<=baseline['p90_pixel_error']*1.02:
            best=val['score'];selected=True;stale=0;torch.save(ck,out/'best.tmp');(out/'best.tmp').replace(out/'best.pt')
        else:stale+=1
        save(out/'history.json',history);save(out/'state.json',row);print(json.dumps(row),flush=True)
        if stale>=3:break
    report=dict(status='completed',selected_improvement=selected,parent_validation=baseline,selected_sha256=sha(out/'best.pt')if selected else None,latest_sha256=sha(out/'latest.pt'),epochs=len(history),wall_s=time.monotonic()-begin,production_qualified=False,original_test_unused=True)
    if selected:report['selected_validation']=torch.load(out/'best.pt',map_location='cpu',weights_only=False)['validation']
    save(out/'result.json',report);save(out/'state.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
