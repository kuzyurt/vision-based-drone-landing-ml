from pathlib import Path
import hashlib,json,sys,time
import numpy as np,torch
R=Path(__file__).parent;S=R/'search_v56/sources';sys.path.insert(0,str(S));sys.path.insert(1,str(R))
from target_learning.object_verifier_v55 import ObjectVerifier,agreement
from train_static_verifier_v53b import evaluate,load_cache
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 torch.set_num_threads(1);torch.manual_seed(2026102055);O=R/'perception_ensemble_v55';O.mkdir(exist_ok=False);start=time.monotonic();a=torch.load(R/'perception_training_v47/best.pt',map_location='cpu',weights_only=False);b=torch.load(R/'perception_training_v53/latest.pt',map_location='cpu',weights_only=False);assert all(torch.equal(a['model'][n],b['model'][n])for n in a['model']);model=ObjectVerifier().cuda();model.members[0].load_state_dict(a['verifier']);model.members[1].load_state_dict(b['verifier']);model.eval()
 for _ in range(10):
  x={'identity':torch.randn(1000,3,device='cuda')*5,'marker':torch.randn(1000,device='cuda')*5};y={'identity':torch.randn(1000,3,device='cuda')*5,'marker':torch.randn(1000,device='cuda')*5};z=agreement(x,y);p=z['identity'].softmax(-1);assert torch.isfinite(p).all()and torch.allclose(p.sum(-1),torch.ones(1000,device='cuda'),atol=1e-6)
  for k in [0,1]:assert (p[:,k]<=x['identity'].softmax(-1)[:,k]+2e-7).all()and(p[:,k]<=y['identity'].softmax(-1)[:,k]+2e-7).all()
  assert(z['marker'].sigmoid()<=x['marker'].sigmoid()+2e-7).all()
 data={name:load_cache(R/('roi_cache/'+folder))['validation']for name,folder in [('wide_rehearsal','static_v38'),('new_close','static_v44b'),('new_negatives','static_v52')]};metrics={n:evaluate(model,d)for n,d in data.items()};false=lambda x:sum(x['selected_operating_point'][k]for k in ['wrong_object_acceptances','ambiguous_acceptances','background_acceptances']);zero=all(false(v)==0 for v in metrics.values());strict=zero and metrics['wide_rehearsal']['selected_operating_point']['target_recall']>=75/152 and metrics['new_close']['selected_operating_point']['target_recall']>=62/212-.02 and metrics['new_negatives']['selected_operating_point']['target_recall']>=97/311-.02
 provenance=dict(component_paths=['perception_training_v47/best.pt','perception_training_v53/latest.pt'],component_sha256=[sha(R/'perception_training_v47/best.pt'),sha(R/'perception_training_v53/latest.pt')],secondary_standalone_selection_FAILED_preserved=True,source_sha256=sha(S/'target_learning/object_verifier_v55.py'),predeclaration_sha256=sha(R/'ENSEMBLE_V55_PREDECLARATION.md'),no_new_optimizer_steps=True,rule='minimum target/minimum wrong-design probabilities, remaining unknown; minimum marker',no_teacher_failed_rgb_training=True,detector_backbone_pose_spatial_unchanged=True)
 ck=dict(a);ck.pop('optimizer',None);ck.update(verifier={n:v.detach().cpu()for n,v in model.state_dict().items()},verifier_mode='rgb_intersection_v55',validation=metrics['wide_rehearsal'],validation_groups=metrics,ensemble_provenance=provenance,experimental_not_qualified=True)
 torch.save(ck,O/'candidate.pt');torch.save(dict(components=[a,b],provenance=provenance),O/'components_resume.pt')
 if strict:
  torch.save(ck,O/'best.pt');torch.save(ck,O/'latest.pt')
 result=dict(status='completed_agreement_validation',strict_three_group_selection_passed=strict,zero_false_assertions_all_three_groups=zero,validation_groups=metrics,selected_sha256=sha(O/'best.pt')if strict else None,candidate_sha256=sha(O/'candidate.pt'),wall_s=time.monotonic()-start,qualified_for_production=False,original_static80_gate_still_failed=True,component_rejected_single_gate_remains_failed=True);(O/'provenance.json').write_text(json.dumps(provenance,indent=2));(O/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
