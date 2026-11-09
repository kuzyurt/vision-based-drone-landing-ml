"""One bounded integration check using existing MuJoCo validation only."""
from pathlib import Path
import importlib,json,time
import numpy as np,torch,h5py
from cache_curriculum_verifier_v23 import ROOT,BUNDLE,PARENT,sha,load_parent,Discriminator,decode,regions,rgb_regions
from train_curriculum_verifier_v23 import load_old,draw,ObjectVerifier,evaluate
def main():
    start=time.monotonic();torch.set_num_threads(2)
    parent=load_parent(BUNDLE,'curriculum_cache_smoke');spatial=importlib.import_module(parent.__package__+'.spatial_acquisition')
    config=json.loads((BUNDLE/'policy.json').read_text())
    runtime=parent.RadioRobustRuntime(BUNDLE/'pose.pt',config['calibration'],config['slew_limits'],'cuda',allow_visual_landing=True)
    saved=torch.load(PARENT,map_location='cuda',weights_only=False);head=Discriminator().cuda();head.load_state_dict(saved['model']);head.eval()
    path=ROOT/'expert_visible_native_v22_tilt/observations.h5'
    assert path.exists(),str(path)
    with h5py.File(path,'r')as h:raw=np.asarray(h['rgb'][0])
    with torch.inference_mode():
        image=torch.from_numpy(raw).permute(2,0,1)[None].cuda()
        fine,context=spatial.encode_spatial(runtime.model.backbone,image)
        predictions=decode({k:v.cpu()for k,v in head(fine,context).items()},minimum_presence=.2,topk=24)[0]
        assert predictions
        boxes=[[*p['pixel'],*p['size_px']]for p in predictions];_,meta=regions(fine,context,boxes,[0]*len(boxes))
        crop=rgb_regions(image,meta);cpu=rgb_regions(image.cpu(),meta.cpu());error=float((crop.cpu().float()-cpu.float()).abs().max());assert error<=.001
    model=ObjectVerifier(mode='rgb_only').cuda();model.load_state_dict(saved['verifier']);data=load_old('validation')
    metrics=evaluate(model,data)
    assert metrics['known_targets']==saved['validation']['known_targets']
    for actual,previous in zip(metrics['operating_points'],saved['validation']['operating_points']):
        for k in ['accepted_true_objects','wrong_object_acceptances','ambiguous_acceptances','background_acceptances']:
            assert actual[k]==previous[k],(k,actual,previous)
    batch=draw([data],np.random.default_rng(42),32);rgb=torch.from_numpy(batch['rgb']).cuda().float();metadata=torch.from_numpy(batch['meta']).cuda().float()
    model.train();output=model(rgb.new_zeros((32,1)),metadata,rgb)
    value=output['identity'].square().mean()+output['marker'].square().mean();value.backward()
    assert any(p.grad is not None and torch.isfinite(p.grad).all()and p.grad.abs().sum()>0 for p in model.parameters())
    receipt=dict(status='passed',parent_sha256=sha(PARENT),actual_recording=str(path),predicted_regions=len(predictions),
        cpu_gpu_rgb_crop_max_error=error,old_validation_operating_counts_exact=True,finite_backward=True,
        original_gate_still_failed=not metrics['expert_gate_passed'],no_checkpoints_written=True,
        heldout_used=False,tidewater_used=False,wall_s=time.monotonic()-start)
    (ROOT/'curriculum_v23/training_integration_probe.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':main()
