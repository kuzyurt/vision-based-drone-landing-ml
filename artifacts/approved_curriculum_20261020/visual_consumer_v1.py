"""Narrow approved derivative consumer; no raw-review/action-policy fallback."""
from pathlib import Path
import hashlib,json
import numpy as np
import torch
from torch.nn import functional as F
SCHEMA='approved.curriculum.visual-derivatives.v1'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def validate_record(record,*,experiment_root,original_root):
    if record.get('schema')!=SCHEMA:raise ValueError('Unknown derivative contract')
    if record.get('role')not in ['training','validation']:raise ValueError('Heldout/review role rejected')
    path=Path(record['source']).resolve();root=Path(experiment_root).resolve();original=Path(original_root).resolve()
    if not(path.is_relative_to(root/'collection_v1/episodes')or path.is_relative_to(original)):
        raise ValueError('Source outside explicit original/new collection roots; quarantined/retired/review cache rejected')
    if record.get('phase')in ['return_home','land_home','home_landed','return_to_home','collection_stop_hold']:
        raise ValueError('Home/stop phase rejected')
    if record.get('action_loss')is not False:raise ValueError('No action-imitation targets admitted')
    if not record.get('exact_capture_join')or len(record.get('source_sha256',''))!=64:
        raise ValueError('Exact source/capture provenance required')
    if not np.isfinite(float(record['capture_s'])):raise ValueError('Invalid capture stamp')
    return path
def masked_identity_loss(logits,labels,mask):
    valid=mask.bool()&(labels>=0)
    return F.cross_entropy(logits[valid],labels[valid])if valid.any()else logits.sum()*0
def masked_center_loss(prediction,targets,mask):
    valid=mask.bool()
    return F.smooth_l1_loss(prediction[valid],targets[valid])if valid.any()else prediction.sum()*0
def self_test(root,original):
    base=dict(schema=SCHEMA,source=str(Path(original)/'training_000/observations.h5'),role='training',phase='target_align',action_loss=False,exact_capture_join=True,source_sha256='a'*64,capture_s=1.)
    validate_record(base,experiment_root=root,original_root=original)
    invalid=[dict(base,role='test'),dict(base,phase='return_home'),dict(base,exact_capture_join=False),dict(base,action_loss=True),dict(base,source=str(Path(root).parent/'curriculum_v23/episodes/bad.h5')),dict(base,source=str(Path(root).parent/'perception_training_v24/rgb_cache.h5'))]
    for value in invalid:
        try:validate_record(value,experiment_root=root,original_root=original)
        except ValueError:pass
        else:raise AssertionError('Invalid derivative admitted')
    torch.manual_seed(31);x=torch.randn(3,3,requires_grad=True);mask=torch.tensor([True,False,True]);y=torch.tensor([1,0,2]);loss=masked_identity_loss(x,y,mask);loss.backward();g=x.grad.clone()
    assert torch.equal(g[1],torch.zeros_like(g[1]))and g[[0,2]].abs().sum()>0
    x2=x.detach().clone().requires_grad_();y2=y.clone();y2[1]=2;l2=masked_identity_loss(x2,y2,mask);l2.backward();assert torch.equal(x2.grad,g)
    p=torch.randn(3,2,requires_grad=True);target=torch.randn(3,2);l=masked_center_loss(p,target,mask);l.backward();g=p.grad.clone();assert torch.equal(g[1],torch.zeros_like(g[1]))and g[[0,2]].abs().sum()>0
    p2=p.detach().clone().requires_grad_();t2=target.clone();t2[1]=1e6;masked_center_loss(p2,t2,mask).backward();assert torch.equal(p2.grad,g)
    return dict(status='passed',rejected_cases=len(invalid),masked_target_changes_leave_loss_and_gradients_unchanged=True,valid_visual_targets_produce_gradient=True,action_imitation=False)
if __name__=='__main__':
    root=Path(__file__).resolve().parent;print(json.dumps(self_test(root,Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/datasets/expert'))))
