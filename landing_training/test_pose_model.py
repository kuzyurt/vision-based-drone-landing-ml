"""Physical invariants for the new supervised pose representation."""
import unittest
import torch
from .pose_model import decode_pose,pose_loss,PoseModel


class PoseChecks(unittest.TestCase):
    def test_position_velocity_priors_and_up_normal(self):
        raw=torch.zeros(1,1,15);numeric=torch.zeros(1,1,32)
        numeric[...,11:14]=torch.tensor([1.,2.,3.])
        numeric[...,14:17]=torch.tensor([.4,.2,.1]);numeric[...,:3]=torch.tensor([.1,.05,.02])
        prediction=decode_pose(raw,numeric)
        torch.testing.assert_close(prediction[...,1:4],numeric[...,11:14])
        torch.testing.assert_close(prediction[...,4:7],torch.tensor([[[.3,.15,.08]]]))
        torch.testing.assert_close(prediction[...,9:12],torch.tensor([[[0.,0.,-1.]]]))

    def test_motion_heading_prior_uses_frd_right_sign(self):
        raw=torch.zeros(1,1,15);numeric=torch.zeros(1,1,32)
        numeric[...,14:16]=torch.tensor([1.,1.])
        pred=decode_pose(raw,numeric)
        torch.testing.assert_close(pred[...,7:9],torch.tensor([[[-1.,0.]]]),atol=1e-6,rtol=1e-6)
        numeric[...,14:16]=-numeric[...,14:16]
        torch.testing.assert_close(decode_pose(raw,numeric)[...,7:9],pred[...,7:9])

    def test_visibility_masks_pose_regression_and_loss_has_finite_gradient(self):
        numeric=torch.zeros(1,2,32);raw=torch.randn(1,2,15,requires_grad=True)
        prediction=decode_pose(raw,numeric)
        target=torch.zeros_like(prediction);target[...,9:12]=torch.tensor([0.,0.,-1.])
        changed=target.clone();changed[...,1:14]+=100.
        self.assertAlmostEqual(float(pose_loss(prediction,target)),float(pose_loss(prediction,changed)),places=5)
        target[...,0]=1.;target[...,8]=1
        loss=pose_loss(prediction,target);loss.backward()
        self.assertTrue(torch.isfinite(loss));self.assertTrue(torch.isfinite(raw.grad).all())

    def test_near_pose_errors_receive_physical_penalty(self):
        target=torch.zeros(1,1,15);target[...,0]=1;target[...,3]=1;target[...,8]=1;target[...,11]=-1
        exact=target.clone();small=exact.clone();large=exact.clone()
        small[...,1]=.05;large[...,1]=.5
        self.assertLess(float(pose_loss(small,target)),float(pose_loss(large,target)))

    def test_encoder_frozen_and_heading_pose_heads_have_gradients(self):
        torch.set_num_threads(1)
        model=PoseModel()
        self.assertFalse(any(p.requires_grad for p in model.backbone.encoder.parameters()))
        features=torch.randn(1,2,1728);numeric=torch.randn(1,2,32)
        prediction,_,_=model.forward_features(features,numeric)
        target=prediction.detach().clone();target[...,0]=1.;target[...,1]+=.1
        pose_loss(prediction,target).backward()
        self.assertIsNotNone(model.backbone.auxiliary.weight.grad)
