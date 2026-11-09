"""Finish the closed cache, measuring CUDA numerical noise explicitly."""
from cache_original_spatial_v1 import *
def main():
    torch.set_num_threads(1);start=time.monotonic();receipt=json.loads((DATA/'receipt.json').read_text());assert sha(DATA/'data.h5')==receipt['data_sha256']
    fine=np.load(OUT/'fine.npy',mmap_mode='r');context=np.load(OUT/'context.npy',mmap_mode='r');labels=np.load(OUT/'labels.npy');assert len(labels)==2120==len(fine)==len(context)
    Pose,spatial=classes();head=spatial.SpatialAcquisition().cuda();head.load_state_dict(torch.load(BUNDLE/'spatial_acquisition.pt',map_location='cuda',weights_only=False)['model']);head.eval()
    ix=np.r_[np.flatnonzero(labels[:,0]>.5)[:4],np.flatnonzero(labels[:,0]<.5)[:4]];x=torch.tensor(np.array(fine[ix]),device='cuda').float();c=torch.tensor(np.array(context[ix]),device='cuda').float();y=torch.tensor(labels[ix],device='cuda')
    def grad(z):
        head.zero_grad();v=spatial_loss(head,x,c,z);v.backward();return float(v.detach()),torch.cat([p.grad.flatten().detach().clone()for p in head.parameters()if p.grad is not None])
    a,g=grad(y);b,g2=grad(y);y2=y.clone();y2[4:,1:3]=1e6;d,g3=grad(y2);y3=y.clone();y3[:4,1]+=150;y3[:4,2]+=80;e,g4=grad(y3)
    noise=float((g-g2).abs().max());effect=float((g-g3).abs().max());positive=float((g-g4).abs().max());tol=max(5e-6,3*noise)
    assert abs(a-d)<=1e-6 and effect<=tol,(a,d,noise,effect,tol);assert positive>10*tol and abs(a-e)>1e-4
    report=dict(status='frozen_original_feature_cache_and_consumer_passed',frames=len(labels),baseline_validation=evaluate(head,spatial,dict(fine=fine,context=context),labels,'validation'),numerics=dict(repeated_gradient_noise=noise,masked_gradient_difference=effect,tolerance=tol,positive_control_gradient_difference=positive,losses=[a,b,d,e]),parent_pose_sha256=sha(BUNDLE/'pose.pt'),parent_spatial_sha256=sha(BUNDLE/'spatial_acquisition.pt'),raw_rgb_cache_sha256=receipt['data_sha256'],source_sha256=sha(__file__),optimizer_steps=0,features={n:sha(OUT/(n+'.npy'))for n in ['fine','context','labels']},elapsed_s=time.monotonic()-start)
    for p in [OUT/'receipt_v2.json',OUT/'state_v2.json',ROOT/'original_consumer_validation_receipt.json']:p.write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
