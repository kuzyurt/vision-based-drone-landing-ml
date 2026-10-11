"""Observable controller phase and coordinate-frame checks."""
import math,unittest
import numpy as np
from .hybrid_policy import LandingController,HybridPosePolicy
from .supervision import supervise_action

FEET=[[-.07,-.12,-.215],[.07,-.12,-.215],[.07,.12,-.215],[-.07,.12,-.215]]
LIMITS=[100.]*6
def obs():
    return {'decision_dt_s':.04,'image_valid':True,'image_age_s':0.,
            'gimbal_rad':[0.,math.pi/2],'previous_executed_action':[0.]*6,
            'px4':{'valid':True,'position_age_s':0.,'attitude_age_s':0.,'armed':True,'landed':False,
                   'velocity_enu_m_s':[0.,0.,0.],'attitude_ned_rad':[0.,0.,math.pi/2],
                   'angular_rate_frd_rad_s':[0.,0.,0.]},
            'beacon':{'valid':True,'age_s':0.,'dock_ready':True,'relative_heading_m':[0.,0.,1.5],'velocity_heading_m_s':[0.,0.,0.]}}
def estimate():
    return {'visibility':1.,'relative_position':[0.,0.,1.5],'relative_velocity':[0.,0.,0.],
            'normal':[0.,0.,-1.],'heading_pair':[0.,1.]}

class ControllerChecks(unittest.TestCase):
    def test_requires_stable_position_speed_heading_before_descent(self):
        controller=LandingController(FEET,LIMITS);o=obs();e=estimate()
        for _ in range(5):
            action,d=controller.act(e,o)
            self.assertNotEqual(d['control_phase'],'descend')
            o['previous_executed_action']=action.tolist()
        action,d=controller.act(e,o)
        self.assertEqual(d['control_phase'],'descend');self.assertGreater(action[2],0.)
        controller.reset();e['relative_velocity']=[.3,0.,0.]
        for _ in range(10):action,d=controller.act(e,o)
        self.assertNotEqual(d['control_phase'],'descend')

    def test_bad_heading_or_missing_visibility_prevents_descent(self):
        controller=LandingController(FEET,LIMITS);o=obs();e=estimate()
        e['heading_pair']=[1.,0.]
        for _ in range(10):action,d=controller.act(e,o)
        self.assertNotEqual(d['control_phase'],'descend')
        e['visibility']=0.
        action,d=controller.act(e,o)
        self.assertFalse(d['pose_valid']);self.assertEqual(d['control_phase'],'acquire')

    def test_foot_clearance_and_contact_use_public_state_only(self):
        controller=LandingController(FEET,LIMITS);o=obs();e=estimate();e['relative_position'][2]=.23
        action,d=controller.act(e,o)
        self.assertAlmostEqual(d['estimated_clearance_m'],.015)
        self.assertEqual(d['control_phase'],'touchdown')
        self.assertGreaterEqual(action[2],.30)
        o['px4']['landed']=True
        action,d=controller.act(e,o);self.assertEqual(d['control_phase'],'confirm')

    def test_existing_supervisor_still_has_final_priority(self):
        controller=LandingController(FEET,LIMITS);o=obs();e=estimate()
        action,_=controller.act(e,o)
        executed,reason=supervise_action(action,o,175.,180.)
        self.assertEqual(reason,'mission_deadline')
        np.testing.assert_array_equal(executed[:4],[0.,0.,-.5,0.])

    def test_nonfinite_pose_and_stale_packet_do_not_trigger_descent(self):
        controller=LandingController(FEET,LIMITS);o=obs();e=estimate()
        e['relative_position'][0]=float('nan');o['beacon']['age_s']=4.
        action,d=controller.act(e,o)
        self.assertFalse(d['pose_valid']);self.assertTrue(np.isfinite(action).all())
        self.assertLess(action[2],0.)

    def test_low_confidence_frames_do_not_extend_last_trusted_pose(self):
        policy=HybridPosePolicy.__new__(HybridPosePolicy)
        policy.last_valid=None;policy.last_valid_time=None
        good=estimate();o=obs();o['image_age_s']=.16
        policy.remember_projection(good,o,np.array([0.,0.,1.]),1.)
        self.assertEqual(policy.last_valid_time,1.)
        bad=dict(good,visibility=.1)
        for time in [1.04,1.08,1.12,2.]:
            policy.remember_projection(bad,o,np.array([0.,0.,1.]),time)
        self.assertEqual(policy.last_valid_time,1.)
        o['image_valid']=False
        policy.remember_projection(good,o,np.array([0.,0.,1.]),3.)
        self.assertEqual(policy.last_valid_time,1.)
