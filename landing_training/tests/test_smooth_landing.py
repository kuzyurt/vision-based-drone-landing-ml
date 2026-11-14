import math
import unittest
import numpy as np
import mujoco
from types import SimpleNamespace
from landing_training.smooth_landing import DescentGate, limit_change, limit_relative_speed, SmoothLandingExpert

class SmoothLandingTests(unittest.TestCase):
    def test_zero_closing_speed_preserves_moving_platform_velocity(self):
        reference=np.array([.6,.3,.02])
        np.testing.assert_allclose(limit_relative_speed(reference,reference,0.),reference)

    def test_closing_limit_does_not_cap_absolute_tracking_speed(self):
        reference=np.array([1.5,0.,0.])
        result=limit_relative_speed(np.array([1.8,.4,-.2]),reference,.1)
        self.assertAlmostEqual(float(np.linalg.norm(result[:2]-reference[:2])),.1)
        self.assertGreater(result[0],1.5)
        self.assertEqual(result[2],-.2)

    def camera_fixture(self, tilt):
        m=mujoco.MjModel.from_xml_string('''<mujoco><worldbody><body name="base">
          <body><joint type="hinge" axis="0 0 1"/><geom type="sphere" size=".01"/>
          <body><joint type="hinge" axis="0 1 0"/><geom type="sphere" size=".01"/>
          <camera name="drone_onboard" quat=".5 .5 -.5 -.5"/></body></body>
          </body></worldbody></mujoco>''')
        d=mujoco.MjData(m); d.qpos[1]=tilt; mujoco.mj_forward(m,d)
        env=SimpleNamespace(model=m,data=d,drone=SimpleNamespace(camera_qpos=[0,1]))
        expert=SmoothLandingExpert(env); expert.landing_active=True
        return expert,m,d

    def test_vertical_camera_does_not_spin_for_tiny_position_change(self):
        e,_,_=self.camera_fixture(math.pi/2)
        left=e.camera_action(np.array([-.001,.001,-2.]))
        right=e.camera_action(np.array([.001,-.001,-2.]))
        self.assertLess(abs(left[0]),.01)
        self.assertLess(abs(right[0]),.01)
        self.assertTrue(np.isfinite(left).all())

    def test_optical_controller_rotates_toward_target(self):
        e,m,d=self.camera_fixture(math.radians(35))
        point=np.array([2.,.2,-2.])
        def error():
            direction=point/np.linalg.norm(point)
            return np.linalg.norm(-d.cam_xmat[0].reshape(3,3)[:,2]-direction)
        before=error()
        for _ in range(15):
            d.qpos[:]+=e.camera_action(point)*.04
            mujoco.mj_forward(m,d)
        self.assertLess(error(),before*.4)

    def test_needs_continuous_settling(self):
        g=DescentGate()
        for _ in range(10): self.assertFalse(g.update(.04,.05,.05,0,0,True,2.))
        self.assertFalse(g.update(.04,.11,.05,0,0,True,2.))
        for _ in range(14): self.assertFalse(g.update(.04,.05,.05,0,0,True,2.))
        for _ in range(2): g.update(.04,.05,.05,0,0,True,2.)
        self.assertTrue(g.active)

    def test_hysteresis_prevents_threshold_chatter(self):
        g=DescentGate()
        for _ in range(16): g.update(.04,.05,.05,0,0,True,2.)
        for error in (.088,.094,.12,.085,.13,.095):
            self.assertTrue(g.update(.04,error,.15,math.radians(6),0,True,2.))
        self.assertFalse(g.update(.04,.17,.05,0,0,True,2.))

    def test_lost_view_exits_immediately(self):
        g=DescentGate(); g.active=True
        self.assertFalse(g.update(.04,.01,.01,0,0,False,1.))
        self.assertEqual(g.settled_s,0)

    def test_tighter_low_altitude_exit(self):
        g=DescentGate(); g.active=True
        self.assertFalse(g.update(.04,.11,.05,0,0,True,.5))

    def test_velocity_and_camera_change_limits(self):
        desired=np.array([2.,2.,1.,1.,2.,2.]); prev=np.zeros(6)
        a=limit_change(prev,desired,.04)
        self.assertLessEqual(np.linalg.norm(a[:2]),.65*.04+1e-10)
        self.assertLessEqual(abs(a[2]),.35*.04+1e-10)
        self.assertLessEqual(abs(a[3]),.35*.04+1e-10)
        self.assertLessEqual(abs(a[4]),math.radians(75)*.04+1e-10)
        self.assertTrue(np.isfinite(a).all())

if __name__=='__main__': unittest.main()
