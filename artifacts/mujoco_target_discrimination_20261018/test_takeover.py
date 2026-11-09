"""Necessary checks: loss at descent, latched ownership, stale sensor and budgets."""
from dataclasses import replace
import unittest
from target_learning.takeover import Evidence,TakeoverSupervisor,supervised_action

def observation(t=0.,**kw):
    e=Evidence(t,0.,True,True,True,True,20.,.1,.05,False,True,False,True,frame_id=int(t*25))
    return replace(e,**kw)

class ContractTests(unittest.TestCase):
    def test_loss_arrests_descent_and_never_becomes_unassisted(self):
        s=TakeoverSupervisor(minimum_expert_s=1,release_frames=3,return_to_policy=True)
        self.assertEqual(s.step(observation()).owner,'policy')
        d=s.step(observation(.04,pad_pose_valid=False,descending=True))
        self.assertEqual(d.owner,'expert');self.assertFalse(d.learner_success_eligible)
        for t in [.08,.12,.16]:self.assertEqual(s.step(observation(t,expert_recovery_complete=True)).owner,'expert')
        d=s.step(observation(1.2,expert_recovery_complete=True))
        self.assertEqual(d.owner,'policy');self.assertFalse(d.learner_success_eligible)

    def test_replayed_frame_cannot_release_expert(self):
        s=TakeoverSupervisor(minimum_expert_s=0,release_frames=3,return_to_policy=True)
        s.step(observation(0.,descending=True,pad_pose_valid=False))
        for i in range(1,12):
            d=s.step(observation(i*.1,frame_id=1,expert_recovery_complete=True))
            self.assertEqual(d.owner,'expert')

    def test_sensor_hold_is_not_teacher_label_or_success(self):
        s=TakeoverSupervisor();d=s.step(observation(image_age_s=.4))
        self.assertEqual(d.owner,'safety');self.assertFalse(d.action_supervision_valid)
        action,valid=supervised_action(d,[1]*6,[2]*6,[0]*6)
        self.assertEqual(action,[0]*6);self.assertFalse(valid)
        d=s.step(observation(.1,stationary_safe=False))
        self.assertEqual(d.owner,'safety')
        d=s.step(observation(.2));self.assertEqual(d.owner,'expert')

    def test_finite_budget_and_no_clock_reset(self):
        s=TakeoverSupervisor(max_takeovers=1,minimum_expert_s=0,release_frames=2,return_to_policy=True)
        s.step(observation(descending=True,pad_pose_valid=False))
        s.step(observation(.1,expert_recovery_complete=True))
        self.assertEqual(s.step(observation(.2,expert_recovery_complete=True)).owner,'policy')
        d=s.step(observation(.3,descending=True,pad_pose_valid=False))
        self.assertEqual(d.owner,'fallback');self.assertFalse(d.action_supervision_valid)
        with self.assertRaises(ValueError):s.step(observation(.1))

    def test_default_expert_takeover_stays_latched_through_recovery(self):
        s=TakeoverSupervisor(minimum_expert_s=0,release_frames=2)
        s.step(observation(descending=True,pad_pose_valid=False))
        for i in range(1,20):
            self.assertEqual(s.step(observation(float(i),expert_recovery_complete=True)).owner,'expert')

if __name__=='__main__':unittest.main()
